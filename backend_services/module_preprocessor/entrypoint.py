#!/usr/bin/env python3
"""
Dev Dito Module Preprocessor - Entrypoint
=========================================
Thin wrapper around 03_rag_preprocessing/main.py.
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
PIPELINE_PATH = Path(os.environ.get("PIPELINE_PATH", "/pipeline/03_rag_preprocessing"))

STATUS_FILE = DATA_PATH / "logs" / "pipeline_runs.json"
PROGRESS_FILE = DATA_PATH / "logs" / "pipeline_progress.json"
STAGE_NAME = "preprocess"


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
            "total_steps": 8,
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
        self.state["substeps"].append(f"[{step_index}/{self.state['total_steps']}] {step_name}")
        if len(self.state["substeps"]) > 20:
            self.state["substeps"] = self.state["substeps"][-20:]
        self._write()
    
    def set_progress(self, current: int, total: int, message: str = ""):
        """Set progress within current step."""
        self.state["progress"]["current"] = current
        self.state["progress"]["total"] = total
        self.state["progress"]["percentage"] = round(current / total * 100) if total > 0 else 0
        if message:
            self.state["message"] = message
        self._write()
    
    def set_stats(self, stats: Dict[str, Any]):
        """Set statistics."""
        self.state["stats"] = stats
        self._write()
    
    def add_error(self, error: str):
        """Add an error message."""
        self.state["errors"].append(error)
        self._write()
    
    def complete(self, success: bool = True, message: str = ""):
        """Mark job as complete."""
        self.state["status"] = "success" if success else "error"
        self.state["message"] = message or ("Complete" if success else "Failed")
        self.state["progress"]["percentage"] = 100 if success else self.state["progress"]["percentage"]
        self._write()


# =============================================================================
# Job Status Management
# =============================================================================

def load_status() -> list:
    """Load current pipeline status (list of job runs)."""
    if STATUS_FILE.exists():
        try:
            with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Handle both list format (orchestrator) and dict format (legacy)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and "runs" in data:
                    return data["runs"]
                return []
        except (json.JSONDecodeError, IOError):
            pass
    return []


def save_status(runs: list):
    """Save pipeline status (list of job runs)."""
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATUS_FILE, 'w', encoding='utf-8') as f:
        json.dump(runs, f, indent=2, ensure_ascii=False)


def update_job_status(job_id: str, updates: Dict):
    """Update a specific job's status."""
    runs = load_status()
    
    for run in runs:
        if isinstance(run, dict) and run.get("job_id") == job_id:
            run.update(updates)
            save_status(runs)
            return
    
    # Job not found, create new entry
    new_run = {"job_id": job_id, "stage": STAGE_NAME, **updates}
    runs.append(new_run)
    save_status(runs)


def find_latest_fetch_dir() -> Optional[Path]:
    """Find the latest fetched_at_* directory."""
    fetched_base = DATA_PATH / "fetched"
    if not fetched_base.exists():
        return None
    
    fetch_dirs = sorted(
        [d for d in fetched_base.iterdir() if d.is_dir() and d.name.startswith('fetched_at_')],
        key=lambda x: x.name,
        reverse=True
    )
    return fetch_dirs[0] if fetch_dirs else None


def find_latest_evaluation() -> Optional[Path]:
    """Find the latest evaluation_*.json file."""
    evaluated_base = DATA_PATH / "evaluated"
    if not evaluated_base.exists():
        return None
    
    eval_files = sorted(
        [f for f in evaluated_base.iterdir() if f.is_file() and f.name.startswith('evaluation_')],
        key=lambda x: x.name,
        reverse=True
    )
    return eval_files[0] if eval_files else None


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main entrypoint for the preprocessor module."""
    # Get job ID from argument or generate one
    job_id = sys.argv[1] if len(sys.argv) > 1 else f"preprocess_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"[INFO] Starting RAG Preprocessing")
    print(f"[INFO] Job ID: {job_id}")
    print(f"[INFO] Config: {CONFIG_PATH}")
    print(f"[INFO] Data: {DATA_PATH}")
    print(f"[INFO] Pipeline: {PIPELINE_PATH}")
    
    tracker = ProgressTracker(job_id, STAGE_NAME)
    tracker.start()
    
    # Update job status
    update_job_status(job_id, {
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "stage": STAGE_NAME,
    })
    
    try:
        # Step 1: Find input directory
        tracker.set_step("Finding input data", 1)
        input_dir = find_latest_fetch_dir()
        if not input_dir:
            raise ValueError("No fetched data found")
        print(f"[INFO] Input directory: {input_dir}")
        
        # Step 2: Find evaluation file
        tracker.set_step("Loading evaluation results", 2)
        eval_file = find_latest_evaluation()
        if eval_file:
            print(f"[INFO] Evaluation file: {eval_file}")
        else:
            print("[WARN] No evaluation file found, proceeding without")
        
        # Step 3: Prepare output directory
        tracker.set_step("Preparing output", 3)
        output_dir = DATA_PATH / "preprocessed" / f"preprocess_at_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"[INFO] Output directory: {output_dir}")
        
        # Step 4: Run preprocessing
        tracker.set_step("Running preprocessing", 4)
        
        # Build command
        script_path = PIPELINE_PATH / "main.py"
        cmd = [
            sys.executable, str(script_path),
            "--input-dir", str(input_dir),
            "--output-dir", str(output_dir),
            "--log-level", "INFO",
        ]
        if eval_file:
            cmd.extend(["--evaluation-file", str(eval_file)])
        
        # Add PYTHONPATH
        env = os.environ.copy()
        env["PYTHONPATH"] = str(PIPELINE_PATH)
        
        print(f"[INFO] Executing: {' '.join(cmd)}")
        
        # Run the preprocessing script
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            cwd=str(PIPELINE_PATH),
        )
        
        pages_count = 0
        media_count = 0
        
        # Stream output and parse progress
        for line in process.stdout:
            line = line.strip()
            print(line)
            
            # Parse progress from output
            if "Found" in line and "page files" in line:
                try:
                    pages_count = int(line.split("Found")[1].split("page")[0].strip())
                    tracker.set_progress(0, pages_count, f"Processing {pages_count} pages")
                except (ValueError, IndexError):
                    pass
            
            if "Found" in line and "media files" in line:
                try:
                    media_count = int(line.split("Found")[1].split("media")[0].strip())
                except (ValueError, IndexError):
                    pass
            
            if "Processing pages" in line:
                tracker.set_step("Converting pages to Markdown", 5)
            
            if "Processing media" in line:
                tracker.set_step("Extracting text from media", 6)
            
            if "Manifest written" in line:
                tracker.set_step("Generating manifest", 7)
        
        process.wait()
        
        if process.returncode != 0:
            raise RuntimeError(f"Preprocessing failed with exit code {process.returncode}")
        
        # Step 8: Finalize
        tracker.set_step("Finalizing", 8)
        
        # Count output files
        pages_dir = output_dir / "pages"
        media_dir = output_dir / "media"
        
        output_pages = len(list(pages_dir.glob("*.md"))) if pages_dir.exists() else 0
        output_media = len(list(media_dir.glob("*.txt"))) if media_dir.exists() else 0
        
        stats = {
            "input_pages": pages_count,
            "input_media": media_count,
            "output_pages": output_pages,
            "output_media": output_media,
            "output_dir": str(output_dir),
        }
        tracker.set_stats(stats)
        
        # Success
        tracker.complete(success=True, message=f"Preprocessed {output_pages} pages, {output_media} media files")
        
        update_job_status(job_id, {
            "status": "success",
            "completed_at": datetime.now().isoformat(),
            "result": stats,
        })
        
        print(f"\n[OK] Preprocessing complete!")
        print(f"[OK] Pages: {output_pages}")
        print(f"[OK] Media: {output_media}")
        print(f"[OK] Output: {output_dir}")
        
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] {error_msg}")
        
        tracker.add_error(error_msg)
        tracker.complete(success=False, message=error_msg)
        
        update_job_status(job_id, {
            "status": "error",
            "completed_at": datetime.now().isoformat(),
            "error": error_msg,
        })
        
        sys.exit(1)


if __name__ == "__main__":
    main()
