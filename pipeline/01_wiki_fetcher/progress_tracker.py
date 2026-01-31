"""
Progress Tracker for Pipeline Stages
=====================================
Writes progress updates to a JSON file that can be polled by the dashboard.

Usage:
    from progress_tracker import ProgressTracker
    
    tracker = ProgressTracker(job_id="fetch_20260131_123456", stage="fetch")
    tracker.start()
    tracker.update_step("Fetching pages", current=50, total=209)
    tracker.complete(stats={"pages": 209, "media": 335})
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class ProgressTracker:
    """Tracks and reports progress of pipeline stages."""
    
    def __init__(
        self,
        job_id: str,
        stage: str,
        progress_file: Optional[Path] = None
    ):
        """
        Initialize progress tracker.
        
        Args:
            job_id: Unique job identifier
            stage: Pipeline stage name (fetch, evaluate, embed, deploy)
            progress_file: Path to progress file (default: data/logs/pipeline_progress.json)
        """
        self.job_id = job_id
        self.stage = stage
        
        # Determine progress file path
        if progress_file:
            self.progress_file = Path(progress_file)
        else:
            # Default: data/logs/pipeline_progress.json
            data_dir = os.environ.get("DATA_PATH", "")
            if data_dir:
                self.progress_file = Path(data_dir) / "logs" / "pipeline_progress.json"
            else:
                # Fallback to repo root
                repo_root = Path(__file__).parent.parent.parent
                self.progress_file = repo_root / "data" / "logs" / "pipeline_progress.json"
        
        # Ensure directory exists
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Progress state
        self.state: Dict[str, Any] = {
            "job_id": job_id,
            "stage": stage,
            "status": "initializing",
            "started_at": None,
            "updated_at": None,
            "current_step": "",
            "current_step_index": 0,
            "total_steps": 0,
            "progress": {
                "current": 0,
                "total": 0,
                "percentage": 0
            },
            "message": "",
            "substeps": [],
            "errors": [],
            "stats": {}
        }
    
    def _write(self):
        """Write current state to progress file."""
        self.state["updated_at"] = datetime.now().isoformat()
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[PROGRESS] Warning: Could not write progress file: {e}")
    
    def start(self, total_steps: int = 10):
        """
        Mark job as started.
        
        Args:
            total_steps: Total number of major steps in the pipeline
        """
        self.state["status"] = "running"
        self.state["started_at"] = datetime.now().isoformat()
        self.state["total_steps"] = total_steps
        self.state["message"] = f"Starting {self.stage}..."
        self._write()
    
    def set_step(
        self, 
        step_name: str, 
        step_index: int,
        message: Optional[str] = None
    ):
        """
        Set current major step.
        
        Args:
            step_name: Name of the current step (e.g., "[1/10] Fetching page list")
            step_index: 1-based index of the step
            message: Optional status message
        """
        self.state["current_step"] = step_name
        self.state["current_step_index"] = step_index
        self.state["message"] = message or step_name
        
        # Reset sub-progress
        self.state["progress"]["current"] = 0
        self.state["progress"]["total"] = 0
        self.state["progress"]["percentage"] = 0
        
        # Add to substeps
        self.state["substeps"].append({
            "step": step_name,
            "index": step_index,
            "status": "running",
            "started_at": datetime.now().isoformat()
        })
        
        self._write()
    
    def update_progress(
        self,
        current: int,
        total: int,
        message: Optional[str] = None
    ):
        """
        Update progress within current step.
        
        Args:
            current: Current item count
            total: Total item count
            message: Optional progress message
        """
        percentage = int((current / total) * 100) if total > 0 else 0
        
        self.state["progress"]["current"] = current
        self.state["progress"]["total"] = total
        self.state["progress"]["percentage"] = percentage
        
        if message:
            self.state["message"] = message
        else:
            self.state["message"] = f"{self.state['current_step']}: {current}/{total} ({percentage}%)"
        
        self._write()
    
    def complete_step(self, stats: Optional[Dict] = None):
        """
        Mark current step as complete.
        
        Args:
            stats: Optional statistics for this step
        """
        if self.state["substeps"]:
            last_step = self.state["substeps"][-1]
            last_step["status"] = "complete"
            last_step["completed_at"] = datetime.now().isoformat()
            if stats:
                last_step["stats"] = stats
        
        self._write()
    
    def add_error(self, error: str, context: Optional[str] = None):
        """
        Log an error.
        
        Args:
            error: Error message
            context: Optional context (e.g., page ID)
        """
        self.state["errors"].append({
            "error": error[:500],  # Truncate long errors
            "context": context,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last 50 errors
        if len(self.state["errors"]) > 50:
            self.state["errors"] = self.state["errors"][-50:]
        
        self._write()
    
    def complete(self, stats: Optional[Dict] = None, success: bool = True):
        """
        Mark job as complete.
        
        Args:
            stats: Final statistics
            success: Whether the job completed successfully
        """
        self.state["status"] = "success" if success else "error"
        self.state["completed_at"] = datetime.now().isoformat()
        
        # Calculate duration
        if self.state["started_at"]:
            start = datetime.fromisoformat(self.state["started_at"])
            end = datetime.now()
            self.state["duration_seconds"] = (end - start).total_seconds()
        
        if stats:
            self.state["stats"] = stats
        
        self.state["progress"]["percentage"] = 100 if success else self.state["progress"]["percentage"]
        self.state["message"] = "Complete" if success else "Failed with errors"
        
        self._write()
    
    def fail(self, error: str):
        """
        Mark job as failed.
        
        Args:
            error: Error message
        """
        self.state["status"] = "error"
        self.state["error"] = error
        self.state["completed_at"] = datetime.now().isoformat()
        self.state["message"] = f"Failed: {error[:100]}"
        self._write()


# Convenience function for creating tracker from environment
def create_tracker_from_env() -> Optional[ProgressTracker]:
    """
    Create a ProgressTracker from environment variables.
    
    Expected env vars:
        JOB_ID: Job identifier
        STAGE: Pipeline stage name
        DATA_PATH: Data directory path
    
    Returns:
        ProgressTracker instance or None if env vars not set
    """
    job_id = os.environ.get("JOB_ID")
    stage = os.environ.get("STAGE", "fetch")
    
    if not job_id:
        return None
    
    return ProgressTracker(job_id=job_id, stage=stage)
