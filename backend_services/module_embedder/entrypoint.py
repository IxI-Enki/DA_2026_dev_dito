#!/usr/bin/env python3
"""
Dev Dito Module Embedder - Entrypoint
=====================================
Thin wrapper around 04_embeddings_creator/run_embeddings.py.
Updates job status and progress in pipeline files.

Constitution Article VII: NO business logic here!
Only: start script, track status, report result.

Usage:
    python entrypoint.py <job_id>
    python entrypoint.py  # Auto-generates job_id
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# =============================================================================
# Configuration
# =============================================================================

CONFIG_PATH = Path(os.environ.get("CONFIG_PATH", "/config/env.yaml"))
DATA_PATH = Path(os.environ.get("DATA_PATH", "/data"))
PIPELINE_PATH = Path(os.environ.get("PIPELINE_PATH", "/pipeline/04_embeddings_creator"))

STATUS_FILE = DATA_PATH / "logs" / "pipeline_runs.json"
PROGRESS_FILE = DATA_PATH / "logs" / "pipeline_progress.json"
STAGE_NAME = "embed"


# =============================================================================
# Progress Tracking (same pattern as evaluator)
# =============================================================================

class ProgressTracker:
    """Simple progress tracker that writes to JSON file."""
    
    def __init__(self, job_id: str, stage: str):
        self.job_id = job_id
        self.stage = stage
        self.progress_file = PROGRESS_FILE
        self.state = {
            "job_id": job_id,
            "stage": stage,
            "status": "initializing",
            "started_at": None,
            "updated_at": None,
            "current_step": "",
            "current_step_index": 0,
            "total_steps": 10,
            "progress": {"current": 0, "total": 0, "percentage": 0},
            "message": "",
            "substeps": [],
            "errors": [],
            "stats": {}
        }
    
    def _write(self):
        self.state["updated_at"] = datetime.now().isoformat()
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)
    
    def start(self):
        self.state["status"] = "running"
        self.state["started_at"] = datetime.now().isoformat()
        self.state["message"] = f"Starting {self.stage}..."
        self._write()
    
    def set_step(self, step_name: str, step_index: int):
        self.state["current_step"] = step_name
        self.state["current_step_index"] = step_index
        self.state["message"] = step_name
        self.state["substeps"].append({
            "step": step_name,
            "index": step_index,
            "status": "running",
            "started_at": datetime.now().isoformat()
        })
        self._write()
    
    def update_progress(self, current: int, total: int, message: str | None = None):
        pct = int((current / total) * 100) if total > 0 else 0
        self.state["progress"] = {"current": current, "total": total, "percentage": pct}
        if message:
            self.state["message"] = message
        self._write()
    
    def complete(self, stats: Dict | None = None):
        self.state["status"] = "success"
        self.state["completed_at"] = datetime.now().isoformat()
        self.state["progress"]["percentage"] = 100
        self.state["message"] = "Complete"
        if stats:
            self.state["stats"] = stats
        self._write()
    
    def fail(self, error: str):
        self.state["status"] = "error"
        self.state["error"] = error
        self.state["message"] = f"Failed: {error[:100]}"
        self._write()


# =============================================================================
# Status Management
# =============================================================================

def load_status_file() -> list:
    if STATUS_FILE.exists():
        try:
            return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return []


def save_status_file(runs: list) -> None:
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(runs, indent=2, ensure_ascii=False), encoding="utf-8")


def update_status(job_id: str, status: str, **kwargs: Any) -> None:
    runs = load_status_file()
    job: Dict[str, Any] | None = next(
        (r for r in runs if isinstance(r, dict) and r.get("job_id") == job_id), None
    )
    if not job:
        job = {"job_id": job_id, "stage": STAGE_NAME, "started_at": datetime.now().isoformat()}
        runs.append(job)
    assert job is not None
    job["status"] = status
    job["updated_at"] = datetime.now().isoformat()
    for key, value in kwargs.items():
        job[key] = value
    if status in ("success", "error") and "started_at" in job:
        try:
            start = datetime.fromisoformat(str(job["started_at"]))
            job["finished_at"] = datetime.now().isoformat()
            job["duration_seconds"] = int((datetime.now() - start).total_seconds())
        except ValueError:
            pass
    
    save_status_file(runs)
    print(f"[STATUS] {job_id}: {status}")


def find_input_data() -> Optional[Path]:
    """Find input data: prefer evaluated, fallback to fetched."""
    # First check for evaluated data
    evaluated_dir = DATA_PATH / "evaluated"
    if evaluated_dir.exists():
        eval_files = list(evaluated_dir.glob("evaluation_*.json"))
        if eval_files:
            # Return the directory containing evaluations
            return evaluated_dir
    
    # Fallback to fetched data
    fetched_dir = DATA_PATH / "fetched"
    if fetched_dir.exists():
        dirs = sorted(
            [d for d in fetched_dir.iterdir() if d.is_dir() and d.name.startswith("fetched_at_")],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        if dirs:
            return dirs[0]
    
    return None


# =============================================================================
# Main Execution
# =============================================================================

def main():
    """Main entrypoint for the embedder module."""
    
    # Generate or use provided job_id
    if len(sys.argv) > 1:
        job_id = sys.argv[1]
    else:
        job_id = f"{STAGE_NAME}_{datetime.now():%Y%m%d_%H%M%S}"
    
    print(f"[INFO] Starting Embeddings Creator")
    print(f"[INFO] Job ID: {job_id}")
    print(f"[INFO] Config: {CONFIG_PATH}")
    print(f"[INFO] Pipeline: {PIPELINE_PATH}")
    print(f"[INFO] Output: {DATA_PATH}")
    
    # Check for OpenAI API key
    if not os.environ.get("OPENAI_API_KEY"):
        error = "OPENAI_API_KEY environment variable not set"
        print(f"[ERROR] {error}")
        update_status(job_id, "error", error=error)
        sys.exit(1)
    
    # Initialize tracker
    tracker = ProgressTracker(job_id, STAGE_NAME)
    tracker.start()
    
    # Find input data
    tracker.set_step("[1/10] Finding input data", 1)
    input_path = find_input_data()
    
    if not input_path:
        error = "No input data found. Run fetcher and evaluator first."
        update_status(job_id, "error", error=error)
        tracker.fail(error)
        sys.exit(1)
    
    print(f"[INFO] Input: {input_path}")
    tracker.update_progress(1, 1, f"Found: {input_path.name}")
    
    # Check main script
    tracker.set_step("[2/10] Checking embedder script", 2)
    main_script = PIPELINE_PATH / "run_embeddings.py"
    if not main_script.exists():
        error = f"Embedder script not found: {main_script}"
        update_status(job_id, "error", error=error)
        tracker.fail(error)
        sys.exit(1)
    
    update_status(job_id, "running")
    
    try:
        # Prepare environment
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{PIPELINE_PATH}:{env.get('PYTHONPATH', '')}"
        
        # Output directory
        output_dir = DATA_PATH / "embeddings"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        tracker.set_step("[3/10] Loading documents", 3)
        tracker.set_step("[4/10] Chunking content", 4)
        tracker.set_step("[5/10] Preparing embeddings", 5)
        tracker.set_step("[6/10] Calling OpenAI API", 6)
        
        print(f"[INFO] Executing: python {main_script}")
        
        # Run the embedder
        result = subprocess.run(
            [sys.executable, str(main_script)],
            cwd=str(PIPELINE_PATH),
            capture_output=True,
            text=True,
            env=env,
            timeout=3600  # 1 hour timeout
        )
        
        if result.stdout:
            print("[STDOUT]")
            print(result.stdout[-3000:])
        
        if result.stderr:
            print("[STDERR]")
            print(result.stderr[-1000:])
        
        tracker.set_step("[7/10] Processing batches", 7)
        tracker.set_step("[8/10] Writing output", 8)
        tracker.set_step("[9/10] Calculating costs", 9)
        
        if result.returncode == 0:
            tracker.set_step("[10/10] Complete", 10)
            
            # Find output file
            output_files = list(output_dir.glob("*.jsonl"))
            stats = {
                "output_file": str(output_files[0].name) if output_files else "unknown",
                "output_count": len(output_files)
            }
            
            # Try to parse stats from output
            for line in result.stdout.split("\n"):
                if "Records:" in line:
                    try:
                        stats["records"] = int(line.split(":")[-1].strip())
                    except ValueError:
                        pass
                if "Cost:" in line:
                    try:
                        stats["cost"] = line.split(":")[-1].strip()
                    except ValueError:
                        pass
            
            update_status(job_id, "success", stats=stats)
            tracker.complete(stats)
            print("[OK] Embedding completed successfully")
            sys.exit(0)
        else:
            error_msg = result.stderr[-500:] if result.stderr else f"Exit code: {result.returncode}"
            update_status(job_id, "error", error=error_msg)
            tracker.fail(error_msg)
            print(f"[ERROR] Embedding failed: {error_msg}")
            sys.exit(1)
            
    except subprocess.TimeoutExpired:
        error = "Timeout: Embedding took longer than 1 hour"
        update_status(job_id, "error", error=error)
        tracker.fail(error)
        sys.exit(1)
        
    except Exception as e:
        update_status(job_id, "error", error=str(e))
        tracker.fail(str(e))
        print(f"[ERROR] Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
