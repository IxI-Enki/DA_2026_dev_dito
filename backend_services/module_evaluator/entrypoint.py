#!/usr/bin/env python3
"""
Dev Dito Module Evaluator - Entrypoint
======================================
Thin wrapper around evaluator.py.
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
from typing import Any, Dict, List, Optional

# =============================================================================
# Configuration
# =============================================================================

CONFIG_PATH = Path(os.environ.get("CONFIG_PATH", "/config/env.yaml"))
DATA_PATH = Path(os.environ.get("DATA_PATH", "/data"))
PIPELINE_PATH = Path(os.environ.get("PIPELINE_PATH", "/pipeline/02_deep_evaluation"))

STATUS_FILE = DATA_PATH / "logs" / "pipeline_runs.json"
PROGRESS_FILE = DATA_PATH / "logs" / "pipeline_progress.json"
STAGE_NAME = "evaluate"


# =============================================================================
# Progress Tracking
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
        """Write state to file."""
        self.state["updated_at"] = datetime.now().isoformat()
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)
    
    def start(self):
        """Mark job as started."""
        self.state["status"] = "running"
        self.state["started_at"] = datetime.now().isoformat()
        self.state["message"] = f"Starting {self.stage}..."
        self._write()
    
    def set_step(self, step_name: str, step_index: int):
        """Set current step."""
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
    
    def update_progress(self, current: int, total: int, message: str = None):
        """Update progress within step."""
        pct = int((current / total) * 100) if total > 0 else 0
        self.state["progress"] = {"current": current, "total": total, "percentage": pct}
        if message:
            self.state["message"] = message
        self._write()
    
    def complete(self, stats: Dict = None):
        """Mark as complete."""
        self.state["status"] = "success"
        self.state["completed_at"] = datetime.now().isoformat()
        self.state["progress"]["percentage"] = 100
        self.state["message"] = "Complete"
        if stats:
            self.state["stats"] = stats
        self._write()
    
    def fail(self, error: str):
        """Mark as failed."""
        self.state["status"] = "error"
        self.state["error"] = error
        self.state["message"] = f"Failed: {error[:100]}"
        self._write()


# =============================================================================
# Status Management
# =============================================================================

def load_status_file() -> list:
    """Load existing pipeline runs from JSON file."""
    if STATUS_FILE.exists():
        try:
            return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"[WARN] Could not parse {STATUS_FILE}, starting fresh")
    return []


def save_status_file(runs: list) -> None:
    """Save pipeline runs to JSON file."""
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(runs, indent=2, ensure_ascii=False), encoding="utf-8")


def update_status(job_id: str, status: str, **kwargs) -> None:
    """Update job status in pipeline_runs.json."""
    runs = load_status_file()
    
    # Find existing job or create new
    job = next((r for r in runs if isinstance(r, dict) and r.get("job_id") == job_id), None)
    if not job:
        job = {
            "job_id": job_id,
            "stage": STAGE_NAME,
            "started_at": datetime.now().isoformat()
        }
        runs.append(job)
    
    # Update fields
    job["status"] = status
    job["updated_at"] = datetime.now().isoformat()
    
    for key, value in kwargs.items():
        job[key] = value
    
    # Calculate duration if finished
    if status in ("success", "error", "interrupted") and "started_at" in job:
        try:
            start = datetime.fromisoformat(job["started_at"])
            job["finished_at"] = datetime.now().isoformat()
            job["duration_seconds"] = int((datetime.now() - start).total_seconds())
        except ValueError:
            pass
    
    save_status_file(runs)
    print(f"[STATUS] {job_id}: {status}")


def find_latest_fetch_dir() -> Optional[Path]:
    """Find the most recent fetch output directory."""
    fetched_dir = DATA_PATH / "fetched"
    if not fetched_dir.exists():
        return None
    
    # Find directories matching pattern
    dirs = sorted(
        [d for d in fetched_dir.iterdir() if d.is_dir() and d.name.startswith("fetched_at_")],
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    return dirs[0] if dirs else None


# =============================================================================
# Main Execution
# =============================================================================

def main():
    """Main entrypoint for the evaluator module."""
    
    # Generate or use provided job_id
    if len(sys.argv) > 1:
        job_id = sys.argv[1]
    else:
        job_id = f"{STAGE_NAME}_{datetime.now():%Y%m%d_%H%M%S}"
    
    print(f"[INFO] Starting Content Evaluator")
    print(f"[INFO] Job ID: {job_id}")
    print(f"[INFO] Config: {CONFIG_PATH}")
    print(f"[INFO] Pipeline: {PIPELINE_PATH}")
    print(f"[INFO] Output: {DATA_PATH}")
    
    # Initialize progress tracker
    tracker = ProgressTracker(job_id, STAGE_NAME)
    tracker.start()
    
    # Find latest fetch directory
    tracker.set_step("[1/10] Finding fetch data", 1)
    fetch_dir = find_latest_fetch_dir()
    
    if not fetch_dir:
        error = "No fetch directory found in /data/fetched/"
        update_status(job_id, "error", error=error)
        tracker.fail(error)
        print(f"[ERROR] {error}")
        sys.exit(1)
    
    print(f"[INFO] Using fetch: {fetch_dir.name}")
    tracker.update_progress(1, 1, f"Found: {fetch_dir.name}")
    
    # Check evaluator script exists
    tracker.set_step("[2/10] Checking evaluator script", 2)
    evaluator_script = PIPELINE_PATH / "evaluator.py"
    if not evaluator_script.exists():
        error = f"Evaluator script not found: {evaluator_script}"
        update_status(job_id, "error", error=error)
        tracker.fail(error)
        print(f"[ERROR] {error}")
        sys.exit(1)
    
    # Mark as running
    update_status(job_id, "running")
    
    try:
        # Prepare environment
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{PIPELINE_PATH}:{PIPELINE_PATH.parent}:{env.get('PYTHONPATH', '')}"
        
        # Prepare output directory
        output_dir = DATA_PATH / "evaluated"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        tracker.set_step("[3/10] Initializing evaluator", 3)
        tracker.update_progress(0, 1, "Loading configuration...")
        
        tracker.set_step("[4/10] Collecting pages", 4)
        tracker.update_progress(0, 209, "Scanning pages...")
        
        tracker.set_step("[5/10] Building link graph", 5)
        tracker.update_progress(0, 1, "Analyzing links...")
        
        tracker.set_step("[6/10] Evaluating content quality", 6)
        
        print(f"[INFO] Executing: python {evaluator_script} {fetch_dir} -o {output_dir}")
        
        # Run the evaluator
        result = subprocess.run(
            [sys.executable, str(evaluator_script), str(fetch_dir), "-o", str(output_dir)],
            cwd=str(PIPELINE_PATH),
            capture_output=True,
            text=True,
            env=env,
            timeout=1800  # 30 minute timeout
        )
        
        # Log output
        if result.stdout:
            print("[STDOUT]")
            print(result.stdout[-3000:])
            
            # Parse stats from output
            stats = parse_evaluation_output(result.stdout)
            tracker.update_progress(
                stats.get("pages_evaluated", 0),
                stats.get("pages_evaluated", 1),
                f"Evaluated {stats.get('pages_evaluated', 0)} pages"
            )
        
        if result.stderr:
            print("[STDERR]")
            print(result.stderr[-1000:])
        
        tracker.set_step("[7/10] Calculating statistics", 7)
        tracker.set_step("[8/10] Identifying issues", 8)
        tracker.set_step("[9/10] Generating report", 9)
        
        if result.returncode == 0:
            tracker.set_step("[10/10] Complete", 10)
            
            # Parse final stats
            stats = parse_evaluation_output(result.stdout)
            
            update_status(
                job_id,
                "success",
                output_dir=str(output_dir.relative_to(DATA_PATH.parent)),
                stats=stats
            )
            
            tracker.complete(stats)
            print(f"[OK] Evaluation completed successfully")
            sys.exit(0)
        else:
            error_msg = result.stderr[-500:] if result.stderr else f"Exit code: {result.returncode}"
            update_status(job_id, "error", error=error_msg)
            tracker.fail(error_msg)
            print(f"[ERROR] Evaluation failed: {error_msg}")
            sys.exit(1)
            
    except subprocess.TimeoutExpired:
        error = "Timeout: Evaluation took longer than 30 minutes"
        update_status(job_id, "error", error=error)
        tracker.fail(error)
        print(f"[ERROR] {error}")
        sys.exit(1)
        
    except Exception as e:
        update_status(job_id, "error", error=str(e))
        tracker.fail(str(e))
        print(f"[ERROR] Unexpected error: {e}")
        sys.exit(1)


def parse_evaluation_output(stdout: str) -> Dict[str, Any]:
    """Parse evaluation output for statistics."""
    stats = {}
    
    for line in stdout.split("\n"):
        line_clean = line.strip()
        
        # Pages evaluated
        if "Pages evaluated:" in line_clean:
            try:
                num = int(line_clean.split(":")[-1].strip())
                stats["pages_evaluated"] = num
            except ValueError:
                pass
        
        # Overall quality
        if "Overall quality:" in line_clean:
            try:
                num = float(line_clean.split(":")[-1].strip())
                stats["overall_quality"] = num
            except ValueError:
                pass
        
        # To include
        if "To include:" in line_clean:
            try:
                num = int(line_clean.split(":")[-1].strip())
                stats["pages_to_include"] = num
            except ValueError:
                pass
        
        # To exclude
        if "To exclude:" in line_clean:
            try:
                num = int(line_clean.split(":")[-1].strip())
                stats["pages_to_exclude"] = num
            except ValueError:
                pass
        
        # To review
        if "To review:" in line_clean:
            try:
                num = int(line_clean.split(":")[-1].strip())
                stats["pages_to_review"] = num
            except ValueError:
                pass
    
    return stats


if __name__ == "__main__":
    main()
