#!/usr/bin/env python3
"""
Dev Dito Pipeline Orchestrator
==============================
Simple HTTP API to trigger pipeline stages via Docker.

This service runs on the HOST (not in a container) and has access to Docker commands.
The DokuWiki PHP plugin calls this API to start/monitor pipeline jobs.

Usage:
    python server.py                    # Start on default port 8089
    python server.py --port 8090        # Custom port

Endpoints:
    GET  /health                        - Health check
    GET  /status                        - Get all pipeline status
    POST /run/{stage}                   - Start a pipeline stage
    GET  /job/{job_id}                  - Get specific job status
"""
import subprocess
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import argparse

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Configuration
REPO_ROOT = Path(__file__).parent.parent.parent
COMPOSE_FILE = REPO_ROOT / "backend_services" / "docker-compose.yml"
STATUS_FILE = REPO_ROOT / "data" / "logs" / "pipeline_runs.json"
PROGRESS_FILE = REPO_ROOT / "data" / "logs" / "pipeline_progress.json"

# Pipeline stages (in execution order)
STAGES = {
    "fetch": {
        "name": "Wiki Fetcher",
        "container": "module_fetcher",
        "description": "Fetcht Wiki-Inhalte via JSON-RPC API"
    },
    "evaluate": {
        "name": "Fetch Evaluation", 
        "container": "module_evaluator",
        "description": "Qualitaetsbewertung der gefetchten Daten"
    },
    "preprocess": {
        "name": "RAG Preprocessing",
        "container": "module_preprocessor",
        "description": "Konvertiert Wiki-Syntax zu Markdown mit Frontmatter"
    },
    "embed": {
        "name": "Embeddings Creator",
        "container": "module_embedder", 
        "description": "Generiert Embeddings via OpenAI/lokales Model"
    },
    "deploy": {
        "name": "Qdrant Deploy",
        "container": "module_deployer",
        "description": "Laedt Embeddings in Qdrant hoch"
    }
}

app = FastAPI(
    title="Dev Dito Pipeline Orchestrator",
    description="HTTP API to trigger and monitor pipeline stages",
    version="0.2.0"
)

# CORS for DokuWiki access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for local dev
    allow_methods=["*"],
    allow_headers=["*"],
)


class JobResponse(BaseModel):
    success: bool
    job_id: str
    message: str
    stage: Optional[str] = None


class StatusResponse(BaseModel):
    stages: list
    active_job: Optional[dict] = None


def load_status() -> list:
    """Load pipeline runs from status file"""
    if not STATUS_FILE.exists():
        return []
    try:
        return json.loads(STATUS_FILE.read_text())
    except json.JSONDecodeError:
        return []


def save_status(runs: list):
    """Save pipeline runs to status file"""
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(runs, indent=2))


def update_job_status(job_id: str, status: str, **kwargs):
    """Update or create job status entry"""
    runs = load_status()
    
    job = next((r for r in runs if r.get("job_id") == job_id), None)
    if not job:
        job = {"job_id": job_id}
        runs.append(job)
    
    job["status"] = status
    job["updated_at"] = datetime.now().isoformat()
    job.update(kwargs)
    
    # Keep only last 100 entries
    if len(runs) > 100:
        runs = runs[-100:]
    
    save_status(runs)
    return job


def get_active_job() -> Optional[dict]:
    """Get currently running job if any"""
    runs = load_status()
    for run in runs:
        if run.get("status") == "running":
            return run
    return None


def get_last_run(stage: str) -> Optional[dict]:
    """Get last run for a specific stage (sorted by updated_at for most recent status)"""
    runs = load_status()
    stage_runs = [r for r in runs if r.get("stage") == stage]
    if not stage_runs:
        return None
    # Sort by updated_at to get the most recent status update
    return sorted(stage_runs, key=lambda x: x.get("updated_at", x.get("started_at", "")), reverse=True)[0]


def check_manifest_exists() -> bool:
    """Check if any fetch has a manifest file (for incremental fetch)"""
    fetched_dir = REPO_ROOT / "data" / "fetched"
    if not fetched_dir.exists():
        return False
    
    # Look for fetch directories with manifests
    for d in sorted(fetched_dir.iterdir(), reverse=True):
        if d.is_dir() and d.name.startswith("fetched_at_"):
            manifest = d / "fetch_manifest.json"
            if manifest.exists():
                return True
    return False


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "pipeline-orchestrator"}


@app.get("/status")
async def get_pipeline_status():
    """Get status of all pipeline stages"""
    stages = []
    has_manifest = check_manifest_exists()
    
    for stage_id, info in STAGES.items():
        last_run = get_last_run(stage_id)
        # Get last_run timestamp (try multiple field names for compatibility)
        last_run_time = None
        if last_run:
            last_run_time = last_run.get("finished_at") or last_run.get("completed_at") or last_run.get("updated_at")
        # Get stats (try both 'stats' and 'result' for compatibility)
        stats = None
        if last_run:
            stats = last_run.get("stats") or last_run.get("result")
        stage_data = {
            "id": stage_id,
            "name": info["name"],
            "description": info["description"],
            "status": last_run.get("status", "never_run") if last_run else "never_run",
            "last_run": last_run_time,
            "duration_seconds": last_run.get("duration") if last_run else None,
            "stats": stats
        }
        
        # Add manifest info for fetch stage
        if stage_id == "fetch":
            stage_data["has_manifest"] = has_manifest
        
        stages.append(stage_data)
    
    return {
        "stages": stages,
        "active_job": get_active_job()
    }


@app.post("/run/{stage}")
async def run_stage(stage: str):
    """Start a pipeline stage"""
    if stage not in STAGES:
        raise HTTPException(status_code=400, detail=f"Unknown stage: {stage}")
    
    # Check if another job is running
    active = get_active_job()
    if active:
        raise HTTPException(
            status_code=409, 
            detail=f"Job already running: {active['job_id']}"
        )
    
    job_id = f"{stage}_{datetime.now():%Y%m%d_%H%M%S}"
    container = STAGES[stage]["container"]
    
    # Update status to running
    update_job_status(
        job_id, 
        "running",
        stage=stage,
        started_at=datetime.now().isoformat()
    )
    
    try:
        # Build docker compose command with environment variables for progress tracking
        # Use -p stack-g-devdito to match the main DokuWiki stack
        cmd = [
            "docker", "compose",
            "-p", "stack-g-devdito",
            "-f", str(COMPOSE_FILE),
            "--profile", "pipeline",
            "run", "--rm",
            "-e", f"JOB_ID={job_id}",
            "-e", f"STAGE={stage}",
            container,
            job_id
        ]
        
        print(f"[ORCHESTRATOR] Running: {' '.join(cmd)}")
        
        # Run in background (detached)
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(COMPOSE_FILE.parent)
        )
        
        # Don't wait for completion - let it run in background
        # The container's entrypoint.py will update status when done
        
        return JobResponse(
            success=True,
            job_id=job_id,
            message=f"{STAGES[stage]['name']} gestartet",
            stage=stage
        )
        
    except Exception as e:
        update_job_status(job_id, "error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/job/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a specific job"""
    runs = load_status()
    job = next((r for r in runs if r.get("job_id") == job_id), None)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    return job


@app.get("/progress")
async def get_progress():
    """Get current job progress (live updates from progress file)"""
    if not PROGRESS_FILE.exists():
        return {
            "status": "no_progress",
            "message": "No progress file found"
        }
    
    try:
        data = json.loads(PROGRESS_FILE.read_text())
        return data
    except json.JSONDecodeError:
        return {
            "status": "error",
            "message": "Could not parse progress file"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@app.get("/progress/{job_id}")
async def get_job_progress(job_id: str):
    """Get progress for a specific job"""
    progress = await get_progress()
    
    # Check if progress is for the requested job
    if progress.get("job_id") == job_id:
        return progress
    
    # If not, check if job exists in status file
    runs = load_status()
    job = next((r for r in runs if r.get("job_id") == job_id), None)
    
    if job:
        return {
            "job_id": job_id,
            "status": job.get("status", "unknown"),
            "message": "Progress not available for this job"
        }
    
    raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")


@app.post("/cancel/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a running job (best effort)"""
    runs = load_status()
    job = next((r for r in runs if r.get("job_id") == job_id), None)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    if job.get("status") != "running":
        raise HTTPException(status_code=400, detail="Job is not running")
    
    # Try to stop the container
    stage = job.get("stage", "")
    if stage in STAGES:
        container_name = f"dev-dito-{STAGES[stage]['container'].replace('_', '-')}"
        try:
            subprocess.run(["docker", "stop", container_name], timeout=10)
        except Exception:
            pass  # Best effort
    
    update_job_status(job_id, "cancelled", finished_at=datetime.now().isoformat())
    
    return {"success": True, "message": f"Job {job_id} cancelled"}


def main():
    parser = argparse.ArgumentParser(description="Dev Dito Pipeline Orchestrator")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8089, help="Port to listen on (default: 8089)")
    args = parser.parse_args()
    
    print(f"""
============================================================
  Dev Dito Pipeline Orchestrator
============================================================
  Listening on: http://{args.host}:{args.port}
  
  Endpoints:
    GET  /health          - Health check
    GET  /status          - Pipeline status
    POST /run/{{stage}}     - Start stage (fetch/evaluate/embed/deploy)
    GET  /job/{{job_id}}    - Job status
    POST /cancel/{{job_id}} - Cancel job
============================================================
""")
    
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
