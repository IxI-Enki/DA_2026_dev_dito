#!/usr/bin/env python3
"""
Dev Dito Module Fetcher - Entrypoint
====================================
Thin wrapper around fetch_full_wiki_extended.py.
Updates job status in pipeline_runs.json.

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
PIPELINE_PATH = Path(os.environ.get("PIPELINE_PATH", "/pipeline/01_wiki_fetcher"))

STATUS_FILE = DATA_PATH / "logs" / "pipeline_runs.json"
STAGE_NAME = "fetch"


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
    """
    Update job status in pipeline_runs.json.
    
    Args:
        job_id: Unique job identifier
        status: One of: running, success, error, interrupted
        **kwargs: Additional fields (stats, error, output_dir, etc.)
    """
    runs = load_status_file()
    
    # Find existing job or create new
    job = next((r for r in runs if r.get("job_id") == job_id), None)
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


def parse_fetch_output(stdout: str) -> Dict[str, Any]:
    """
    Parse fetch script output to extract statistics.
    
    Args:
        stdout: Standard output from fetch script
        
    Returns:
        Dictionary with stats (pages, media, etc.)
    """
    stats = {}
    
    # Look for common patterns in output
    for line in stdout.split("\n"):
        line_lower = line.lower()
        
        # Pages count
        if "pages" in line_lower and any(c.isdigit() for c in line):
            try:
                # Extract number before "pages"
                parts = line.split()
                for i, part in enumerate(parts):
                    if "page" in part.lower() and i > 0:
                        num = "".join(filter(str.isdigit, parts[i-1]))
                        if num:
                            stats["pages"] = int(num)
                            break
            except (ValueError, IndexError):
                pass
        
        # Media count
        if "media" in line_lower and any(c.isdigit() for c in line):
            try:
                parts = line.split()
                for i, part in enumerate(parts):
                    if "media" in part.lower() and i > 0:
                        num = "".join(filter(str.isdigit, parts[i-1]))
                        if num:
                            stats["media"] = int(num)
                            break
            except (ValueError, IndexError):
                pass
    
    return stats if stats else None


def find_output_dir() -> Optional[str]:
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
    
    if dirs:
        return str(dirs[0].relative_to(DATA_PATH.parent))
    
    return None


# =============================================================================
# Main Execution
# =============================================================================

def main():
    """Main entrypoint for the fetcher module."""
    
    # Generate or use provided job_id
    if len(sys.argv) > 1:
        job_id = sys.argv[1]
    else:
        job_id = f"{STAGE_NAME}_{datetime.now():%Y%m%d_%H%M%S}"
    
    print(f"[INFO] Starting Wiki Fetcher")
    print(f"[INFO] Job ID: {job_id}")
    print(f"[INFO] Config: {CONFIG_PATH}")
    print(f"[INFO] Pipeline: {PIPELINE_PATH}")
    print(f"[INFO] Output: {DATA_PATH}")
    
    # Check prerequisites
    fetch_script = PIPELINE_PATH / "fetch_full_wiki_extended.py"
    if not fetch_script.exists():
        update_status(job_id, "error", error=f"Fetch script not found: {fetch_script}")
        sys.exit(1)
    
    if not CONFIG_PATH.exists():
        update_status(job_id, "error", error=f"Config not found: {CONFIG_PATH}")
        sys.exit(1)
    
    # Mark as running
    update_status(job_id, "running")
    
    try:
        # Prepare environment for fetcher
        env = os.environ.copy()
        env["CONFIG_PATH"] = str(CONFIG_PATH)
        env["OUTPUT_DIR"] = str(DATA_PATH / "fetched")
        
        # Add pipeline directory to PYTHONPATH
        python_path = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{PIPELINE_PATH}:{PIPELINE_PATH.parent.parent}:{python_path}"
        
        print(f"[INFO] Executing: python {fetch_script}")
        
        # Run the fetcher
        result = subprocess.run(
            [sys.executable, str(fetch_script)],
            cwd=str(PIPELINE_PATH),
            capture_output=True,
            text=True,
            env=env,
            timeout=3600  # 1 hour timeout
        )
        
        # Log output
        if result.stdout:
            print("[STDOUT]")
            print(result.stdout[-2000:])  # Last 2000 chars
        
        if result.stderr:
            print("[STDERR]")
            print(result.stderr[-1000:])  # Last 1000 chars
        
        # Determine success/failure
        if result.returncode == 0:
            stats = parse_fetch_output(result.stdout)
            output_dir = find_output_dir()
            
            update_status(
                job_id, 
                "success",
                output_dir=output_dir,
                stats=stats,
                output=result.stdout[-500:] if result.stdout else None
            )
            print(f"[OK] Fetch completed successfully")
            sys.exit(0)
        else:
            error_msg = result.stderr[-500:] if result.stderr else f"Exit code: {result.returncode}"
            update_status(job_id, "error", error=error_msg)
            print(f"[ERROR] Fetch failed: {error_msg}")
            sys.exit(1)
            
    except subprocess.TimeoutExpired:
        update_status(job_id, "error", error="Timeout: Fetch took longer than 1 hour")
        print("[ERROR] Fetch timed out after 1 hour")
        sys.exit(1)
        
    except Exception as e:
        update_status(job_id, "error", error=str(e))
        print(f"[ERROR] Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
