#!/usr/bin/env python3
"""
Dev Dito Pipeline Orchestrator
==============================
HTTP API to trigger pipeline stages via Docker.

Runs as a container in stack-g-devdito.  Uses Docker-out-of-Docker (DooD)
via the mounted Docker socket to spawn sibling pipeline containers with
`docker run`.  Host-side volume paths are discovered at startup by
inspecting the orchestrator's own bind mounts (`docker inspect`).

Usage (container — default):
    Automatically started by docker compose.

Usage (host — development):
    python server.py                    # Container default port 8089 (host map 18089)
    python server.py --port 18089       # On host use 18089 to match Stack-G

Endpoints:
    GET  /health                        - Health check
    GET  /status                        - Get all pipeline status
    POST /run/{stage}                   - Start a pipeline stage
    GET  /job/{job_id}                  - Get specific job status
"""
import argparse
import json
import os
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import uvicorn
from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# =============================================================================
# Configuration — detect container vs host
# =============================================================================
_IN_CONTAINER = os.path.exists("/.dockerenv")

if _IN_CONTAINER:
    # Container paths (volumes mounted by docker-compose.yml)
    DATA_DIR = Path(os.environ.get("DATA_PATH", "/data"))
    CONFIG_DIR = Path(os.environ.get("CONFIG_PATH", "/config/env.yaml")).parent
else:
    # Host paths (development)
    REPO_ROOT = Path(__file__).parent.parent.parent
    DATA_DIR = REPO_ROOT / "data"
    CONFIG_DIR = REPO_ROOT / "config"
    COMPOSE_FILE = REPO_ROOT / "backend_services" / "docker-compose.yml"

STATUS_FILE = DATA_DIR / "logs" / "pipeline_runs.json"
PROGRESS_FILE = DATA_DIR / "logs" / "pipeline_progress.json"

# =============================================================================
# DooD — host path discovery via docker inspect
# =============================================================================
_HOST_PATHS: dict | None = None


def discover_host_paths() -> dict:
    """Discover host-side paths by inspecting own container's volume mounts.

    Returns dict with keys: config, data, repo_root, sep
    """
    global _HOST_PATHS
    if _HOST_PATHS is not None:
        return _HOST_PATHS

    try:
        raw = subprocess.check_output(
            ["docker", "inspect", "dev-dito-orchestrator", "--format", "{{json .Mounts}}"],
            text=True,
            timeout=10,
        )
        mounts = json.loads(raw.strip())
        paths: dict = {}
        for m in mounts:
            dest = m.get("Destination", "")
            src = m.get("Source", "")
            if dest == "/data":
                paths["data"] = src
            elif dest == "/config":
                paths["config"] = src

        # Derive repo root from /data mount  (data is at <repo_root>/data)
        if "data" in paths:
            src = paths["data"]
            sep = "\\" if "\\" in src else "/"
            paths["repo_root"] = src.rsplit(sep, 1)[0]
            paths["sep"] = sep

        _HOST_PATHS = paths
        print(f"[ORCHESTRATOR] Host paths discovered: {json.dumps(paths)}")
        return paths
    except Exception as exc:
        print(f"[ORCHESTRATOR] WARNING — could not discover host paths: {exc}")
        return {}


# =============================================================================
# Unified stage definitions — single source of truth (FR-013)
# =============================================================================
PIPELINE_STAGES: dict[str, dict] = {
    "fetch": {
        "name": "Wiki Fetcher",
        "container": "module_fetcher",
        "description": "Fetcht Wiki-Inhalte via JSON-RPC API",
        "pipeline_dir": "01_wiki_fetcher",
        "extra_host_volumes": ["config.py:/app/config.py:ro"],
        "extra_env": {
            "OUTPUT_DIR": "/data/fetched",
            "TOKEN_PATH": "/config/secrets/json_rpc_api.token",
            "SSL_CERT_PATH": "/config/secrets/ssl.cert",
            "REQUESTS_CA_BUNDLE": "/etc/ssl/certs/ca-certificates.crt",
            "SSL_CERT_FILE": "/etc/ssl/certs/ca-certificates.crt",
        },
        "needs_openai_key": False,
    },
    "evaluate": {
        "name": "Fetch Evaluation",
        "container": "module_evaluator",
        "description": "Qualitaetsbewertung der gefetchten Daten",
        "pipeline_dir": "02_deep_evaluation",
        "extra_env": {},
        "needs_openai_key": False,
    },
    "preprocess": {
        "name": "RAG Preprocessing",
        "container": "module_preprocessor",
        "description": "Konvertiert Wiki-Syntax zu Markdown mit Frontmatter",
        "pipeline_dir": "03_rag_preprocessing",
        "extra_env": {},
        "needs_openai_key": False,
    },
    "embed": {
        "name": "Embeddings Creator",
        "container": "module_embedder",
        "description": "Generiert Embeddings via OpenAI/lokales Model",
        "pipeline_dir": "04_embeddings_creator",
        "extra_env": {},
        "needs_openai_key": True,
    },
    "deploy": {
        "name": "Qdrant Deploy",
        "container": "module_deployer",
        "description": "Laedt Embeddings in Qdrant hoch",
        "pipeline_dir": "05_deploy",
        "extra_env": {
            "QDRANT_HOST": "dev-dito-qdrant",
            "QDRANT_PORT": "6333",
            "COLLECTION_NAME": "wiki_embeddings",
        },
        "needs_openai_key": False,
        # Override default CMD: append these args + job_id instead of just job_id
        "entrypoint_args": ["python", "run_deploy.py", "qdrant", "--job-id"],
    },
}


def _read_openai_key() -> str | None:
    """Read OpenAI API key (env var > token file)."""
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key
    token_path = CONFIG_DIR / "secrets" / "openai.token"
    if token_path.exists():
        return token_path.read_text().strip()
    return None


def _resolve_image(service_name: str) -> str:
    """Return the Docker image name for a service, checking both project-name
    variants (stack-g-devdito-* and backend_services-*)."""
    candidates = [
        f"stack-g-devdito-{service_name}",
        f"backend_services-{service_name}",
    ]
    try:
        existing = (
            subprocess.check_output(
                ["docker", "images", "--format", "{{.Repository}}"], text=True, timeout=10
            )
            .strip()
            .splitlines()
        )
        for c in candidates:
            if c in existing:
                return c
    except Exception:
        pass
    # Default to project-name variant
    return candidates[0]


def build_run_cmd(
    stage: str, service_name: str, job_id: str, options: dict[str, str] | None = None
) -> Tuple[List[str], str]:
    """Build the docker command + cwd to run a pipeline module.

    Returns (cmd_list, working_directory).
    """
    opts = options or {}
    if _IN_CONTAINER:
        return _build_docker_run(stage, service_name, job_id, opts)
    else:
        return _build_compose_run(stage, service_name, job_id, opts)


def _build_docker_run(
    stage: str, service_name: str, job_id: str, options: dict[str, str]
) -> Tuple[List[str], str]:
    """Build `docker run` command using host paths (DooD)."""
    hp = discover_host_paths()
    if not hp or "repo_root" not in hp:
        raise RuntimeError(
            "Cannot determine host paths — docker inspect failed. " "Is the Docker socket mounted?"
        )

    repo = hp["repo_root"]
    sep = hp["sep"]
    image = _resolve_image(service_name)
    stage_cfg = PIPELINE_STAGES.get(stage, {})

    cmd: List[str] = [
        "docker",
        "run",
        "--rm",
        "--network",
        "leonidas-network",
        "-v",
        f"{hp['config']}:/config:ro",
        "-v",
        f"{hp['data']}:/data",
    ]

    # Pipeline directory mount
    pipeline_dir = stage_cfg.get("pipeline_dir")
    if pipeline_dir:
        host_pipeline = f"{repo}{sep}pipeline{sep}{pipeline_dir}"
        cmd.extend(["-v", f"{host_pipeline}:/pipeline/{pipeline_dir}:ro"])

    # Extra host-relative volume mounts
    for ev in stage_cfg.get("extra_host_volumes", []):
        host_rel, rest = ev.split(":", 1)
        host_abs = f"{repo}{sep}{host_rel.replace('/', sep)}"
        cmd.extend(["-v", f"{host_abs}:{rest}"])

    # Common environment
    cmd.extend(
        [
            "-e",
            "CONFIG_PATH=/config/env.yaml",
            "-e",
            "DATA_PATH=/data",
            "-e",
            f"JOB_ID={job_id}",
            "-e",
            f"STAGE={stage}",
        ]
    )

    if pipeline_dir:
        cmd.extend(["-e", f"PIPELINE_PATH=/pipeline/{pipeline_dir}"])

    # Stage-specific environment
    for k, v in stage_cfg.get("extra_env", {}).items():
        cmd.extend(["-e", f"{k}={v}"])

    # Options forwarded as env vars (FR-001)
    if stage == "fetch" and options.get("mode") == "incremental":
        cmd.extend(["-e", "FETCH_MODE=incremental"])

    # OpenAI API key (read from token file)
    if stage_cfg.get("needs_openai_key"):
        api_key = _read_openai_key()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set and /config/secrets/openai.token not found")
        cmd.extend(["-e", f"OPENAI_API_KEY={api_key}"])

    cmd.append(image)

    # Use stage-specific entrypoint args if defined (FR-002), else default to job_id
    entrypoint_args = stage_cfg.get("entrypoint_args")
    if entrypoint_args:
        cmd.extend(entrypoint_args)
        cmd.append(job_id)
    else:
        cmd.append(job_id)

    return cmd, "/app"


def _build_compose_run(
    stage: str, service_name: str, job_id: str, options: dict[str, str]
) -> Tuple[List[str], str]:
    """Build `docker compose run` command (host-mode only)."""
    stage_cfg = PIPELINE_STAGES.get(stage, {})

    cmd = [
        "docker",
        "compose",
        "-p",
        "stack-g-devdito",
        "-f",
        str(COMPOSE_FILE),
        "--profile",
        "pipeline",
        "run",
        "--rm",
        "-e",
        f"JOB_ID={job_id}",
        "-e",
        f"STAGE={stage}",
    ]

    # Stage-specific environment (FR-003: mirror docker run behaviour)
    for k, v in stage_cfg.get("extra_env", {}).items():
        cmd.extend(["-e", f"{k}={v}"])

    # Options forwarded as env vars (FR-001)
    if stage == "fetch" and options.get("mode") == "incremental":
        cmd.extend(["-e", "FETCH_MODE=incremental"])

    cmd.append(service_name)

    # Use stage-specific entrypoint args if defined (FR-002)
    entrypoint_args = stage_cfg.get("entrypoint_args")
    if entrypoint_args:
        cmd.extend(entrypoint_args)
        cmd.append(job_id)
    else:
        cmd.append(job_id)

    return cmd, str(COMPOSE_FILE.parent)


# =============================================================================
# FastAPI app + models
# =============================================================================

app = FastAPI(
    title="Dev Dito Pipeline Orchestrator",
    description="HTTP API to trigger and monitor pipeline stages",
    version="0.3.0",
)

# CORS for DokuWiki access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for local dev
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    """Request body for POST /run/{stage}. All fields optional."""

    options: dict[str, str] = {}


class JobResponse(BaseModel):
    success: bool
    job_id: str
    message: str
    stage: str | None = None


class StatusResponse(BaseModel):
    stages: list
    active_job: dict | None = None


# =============================================================================
# Status file helpers
# =============================================================================


def load_status() -> list:
    """Load pipeline runs from status file."""
    if not STATUS_FILE.exists():
        return []
    try:
        return json.loads(STATUS_FILE.read_text())
    except json.JSONDecodeError:
        return []


def save_status(runs: list) -> None:
    """Save pipeline runs to status file."""
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(runs, indent=2))


def update_job_status(job_id: str, status: str, **kwargs) -> dict:
    """Update or create job status entry."""
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


def get_active_job() -> dict | None:
    """Get currently running job if any."""
    runs = load_status()
    for run in runs:
        if run.get("status") == "running":
            return run
    return None


def get_last_run(stage: str) -> dict | None:
    """Get most recent run for a stage, sorted by started_at (FR-006)."""
    runs = load_status()
    stage_runs = [r for r in runs if r.get("stage") == stage]
    if not stage_runs:
        return None
    return sorted(stage_runs, key=lambda x: x.get("started_at", ""), reverse=True)[0]


def check_manifest_exists() -> bool:
    """Check if any fetch has a manifest file (for incremental fetch)."""
    fetched_dir = DATA_DIR / "fetched"
    if not fetched_dir.exists():
        return False

    for d in sorted(fetched_dir.iterdir(), reverse=True):
        if d.is_dir() and d.name.startswith("fetched_at_"):
            manifest = d / "fetch_manifest.json"
            if manifest.exists():
                return True
    return False


# =============================================================================
# Route handlers
# =============================================================================


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "service": "pipeline-orchestrator"}


@app.get("/status")
async def get_pipeline_status() -> dict:
    """Get status of all pipeline stages."""
    stages = []
    has_manifest = check_manifest_exists()

    for stage_id, info in PIPELINE_STAGES.items():
        last_run = get_last_run(stage_id)
        last_run_time = None
        if last_run:
            last_run_time = (
                last_run.get("finished_at")
                or last_run.get("completed_at")
                or last_run.get("updated_at")
            )
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
            "stats": stats,
        }

        if stage_id == "fetch":
            stage_data["has_manifest"] = has_manifest

        stages.append(stage_data)

    return {
        "stages": stages,
        "active_job": get_active_job(),
    }


def _monitor_subprocess(proc: subprocess.Popen, job_id: str, stage: str) -> None:
    """Background monitor: detect docker-level failures and update status."""
    try:
        stdout, stderr = proc.communicate(timeout=3600)
        code = proc.returncode
        if code != 0:
            err = stderr.decode("utf-8", errors="replace")[-500:] if stderr else ""
            print(f"[ORCHESTRATOR] Container for {job_id} exited code={code}: {err[:200]}")
            # Only update if entrypoint.py hasn't already updated status
            runs = load_status()
            job = next((r for r in runs if r.get("job_id") == job_id), None)
            if job and job.get("status") == "running":
                update_job_status(
                    job_id,
                    "error",
                    error=f"Container exit code {code}: {err[:200]}",
                    finished_at=datetime.now().isoformat(),
                )
        else:
            print(f"[ORCHESTRATOR] Container for {job_id} completed (exit 0)")
    except subprocess.TimeoutExpired:
        proc.kill()
        print(f"[ORCHESTRATOR] Container for {job_id} timed out (1h)")
        update_job_status(job_id, "error", error="Container timeout (1 hour)")
    except Exception as e:
        print(f"[ORCHESTRATOR] Monitor error for {job_id}: {e}")


_DEFAULT_RUN_REQUEST = Body(default=RunRequest())


@app.post("/run/{stage}")
async def run_stage(stage: str, request: RunRequest = _DEFAULT_RUN_REQUEST) -> JobResponse:
    """Start a pipeline stage (FR-001: forwards options to container)."""
    if stage not in PIPELINE_STAGES:
        raise HTTPException(status_code=400, detail=f"Unknown stage: {stage}")

    # FR-004: reject concurrent starts
    active = get_active_job()
    if active:
        raise HTTPException(status_code=409, detail=f"Job already running: {active['job_id']}")

    job_id = f"{stage}_{datetime.now():%Y%m%d_%H%M%S}"
    container = PIPELINE_STAGES[stage]["container"]

    update_job_status(job_id, "running", stage=stage, started_at=datetime.now().isoformat())

    try:
        cmd, cwd = build_run_cmd(stage, container, job_id, request.options)

        print(f"[ORCHESTRATOR] Running: {' '.join(cmd)}")

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)

        monitor = threading.Thread(
            target=_monitor_subprocess, args=(process, job_id, stage), daemon=True
        )
        monitor.start()

        return JobResponse(
            success=True,
            job_id=job_id,
            message=f"{PIPELINE_STAGES[stage]['name']} gestartet",
            stage=stage,
        )

    except Exception as e:
        update_job_status(job_id, "error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/job/{job_id}")
async def get_job_status(job_id: str) -> dict:
    """Get status of a specific job."""
    runs = load_status()
    job = next((r for r in runs if r.get("job_id") == job_id), None)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    return job


@app.get("/progress")
async def get_progress() -> dict:
    """Get current job progress (live updates from progress file)."""
    if not PROGRESS_FILE.exists():
        return {"status": "no_progress", "message": "No progress file found"}

    try:
        data = json.loads(PROGRESS_FILE.read_text())
        return data
    except json.JSONDecodeError:
        return {"status": "error", "message": "Could not parse progress file"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/progress/{job_id}")
async def get_job_progress(job_id: str) -> dict:
    """Get progress for a specific job."""
    progress = await get_progress()

    if progress.get("job_id") == job_id:
        return progress

    runs = load_status()
    job = next((r for r in runs if r.get("job_id") == job_id), None)

    if job:
        return {
            "job_id": job_id,
            "status": job.get("status", "unknown"),
            "message": "Progress not available for this job",
        }

    raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")


@app.post("/cancel/{job_id}")
async def cancel_job(job_id: str) -> dict:
    """Cancel a running job (best effort)."""
    runs = load_status()
    job = next((r for r in runs if r.get("job_id") == job_id), None)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    if job.get("status") != "running":
        raise HTTPException(status_code=400, detail="Job is not running")

    stage = job.get("stage", "")
    if stage in PIPELINE_STAGES:
        container_name = f"dev-dito-{PIPELINE_STAGES[stage]['container'].replace('_', '-')}"
        try:
            subprocess.run(["docker", "stop", container_name], timeout=10)
        except Exception:
            pass  # Best effort

    update_job_status(job_id, "cancelled", finished_at=datetime.now().isoformat())

    return {"success": True, "message": f"Job {job_id} cancelled"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Dev Dito Pipeline Orchestrator")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8089)
    args = parser.parse_args()

    mode = "CONTAINER (DooD)" if _IN_CONTAINER else "HOST"
    print(
        f"""
============================================================
  Dev Dito Pipeline Orchestrator  [{mode}]
============================================================
  Listening on: http://{args.host}:{args.port}
  Data dir:     {DATA_DIR}
  Status file:  {STATUS_FILE}

  Endpoints:
    GET  /health          - Health check
    GET  /status          - Pipeline status (5 stages)
    POST /run/{{stage}}     - Start stage (fetch/evaluate/preprocess/embed/deploy)
    GET  /job/{{job_id}}    - Job status
    POST /cancel/{{job_id}} - Cancel job
============================================================
"""
    )

    if _IN_CONTAINER:
        hp = discover_host_paths()
        if hp:
            print(f"[ORCHESTRATOR] Host repo root: {hp.get('repo_root', '?')}")
        else:
            print("[ORCHESTRATOR] WARNING: Could not discover host paths!")

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
