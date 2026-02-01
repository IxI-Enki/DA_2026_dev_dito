#!/usr/bin/env python3
"""
Dev Dito Module Deployer - Entrypoint
=====================================
Uploads embeddings to Qdrant vector database.
Updates job status and progress in pipeline files.

Constitution Article VII: NO business logic here!
Only: upload vectors, track status, report result.

Usage:
    python entrypoint.py <job_id>
    python entrypoint.py  # Auto-generates job_id
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import VectorParams, Distance, PointStruct
except ImportError:
    print("[ERROR] qdrant-client not installed")
    sys.exit(1)

# =============================================================================
# Configuration
# =============================================================================

CONFIG_PATH = Path(os.environ.get("CONFIG_PATH", "/config/env.yaml"))
DATA_PATH = Path(os.environ.get("DATA_PATH", "/data"))
QDRANT_HOST = os.environ.get("QDRANT_HOST", "qdrant_db")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))
COLLECTION_NAME = os.environ.get("COLLECTION_NAME", "wiki_embeddings")

STATUS_FILE = DATA_PATH / "logs" / "pipeline_runs.json"
PROGRESS_FILE = DATA_PATH / "logs" / "pipeline_progress.json"
STAGE_NAME = "deploy"

# Embedding dimensions (OpenAI text-embedding-ada-002)
VECTOR_SIZE = 1536
BATCH_SIZE = 100


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
    
    def update_progress(self, current: int, total: int, message: str = None):
        pct = int((current / total) * 100) if total > 0 else 0
        self.state["progress"] = {"current": current, "total": total, "percentage": pct}
        if message:
            self.state["message"] = message
        self._write()
    
    def complete(self, stats: Dict = None):
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


def update_status(job_id: str, status: str, **kwargs) -> None:
    runs = load_status_file()
    
    job = next((r for r in runs if isinstance(r, dict) and r.get("job_id") == job_id), None)
    if not job:
        job = {"job_id": job_id, "stage": STAGE_NAME, "started_at": datetime.now().isoformat()}
        runs.append(job)
    
    job["status"] = status
    job["updated_at"] = datetime.now().isoformat()
    
    for key, value in kwargs.items():
        job[key] = value
    
    if status in ("success", "error") and "started_at" in job:
        try:
            start = datetime.fromisoformat(job["started_at"])
            job["finished_at"] = datetime.now().isoformat()
            job["duration_seconds"] = int((datetime.now() - start).total_seconds())
        except ValueError:
            pass
    
    save_status_file(runs)
    print(f"[STATUS] {job_id}: {status}")


# =============================================================================
# Embedding Loading
# =============================================================================

def load_embeddings(embeddings_dir: Path) -> List[Dict]:
    """Load embeddings from JSONL file."""
    embeddings = []
    
    # Find JSONL file
    jsonl_files = list(embeddings_dir.glob("*.jsonl"))
    if not jsonl_files:
        raise FileNotFoundError(f"No JSONL files found in {embeddings_dir}")
    
    embeddings_file = jsonl_files[0]  # Use first/newest
    print(f"[INFO] Loading embeddings from: {embeddings_file.name}")
    
    with open(embeddings_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    record = json.loads(line)
                    embeddings.append(record)
                except json.JSONDecodeError:
                    continue
    
    return embeddings


# =============================================================================
# Qdrant Operations
# =============================================================================

def connect_qdrant() -> QdrantClient:
    """Connect to Qdrant server."""
    print(f"[INFO] Connecting to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}")
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    
    # Test connection
    try:
        client.get_collections()
        print("[OK] Connected to Qdrant")
        return client
    except Exception as e:
        raise ConnectionError(f"Cannot connect to Qdrant: {e}")


def ensure_collection(client: QdrantClient, vector_size: int) -> bool:
    """Create collection if it doesn't exist."""
    collections = client.get_collections().collections
    collection_names = [c.name for c in collections]
    
    if COLLECTION_NAME in collection_names:
        print(f"[INFO] Collection '{COLLECTION_NAME}' exists, will recreate")
        client.delete_collection(COLLECTION_NAME)
    
    print(f"[INFO] Creating collection '{COLLECTION_NAME}'")
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=vector_size,
            distance=Distance.COSINE
        )
    )
    
    return True


def upload_embeddings(
    client: QdrantClient,
    embeddings: List[Dict],
    tracker: ProgressTracker
) -> int:
    """Upload embeddings to Qdrant in batches."""
    total = len(embeddings)
    uploaded = 0
    
    # Process in batches
    for i in range(0, total, BATCH_SIZE):
        batch = embeddings[i:i + BATCH_SIZE]
        points = []
        
        for idx, record in enumerate(batch):
            # Extract vector and payload
            vector = record.get("embedding", record.get("vector", []))
            
            # Build payload (everything except the vector)
            payload = {k: v for k, v in record.items() if k not in ("embedding", "vector")}
            
            # Ensure we have an ID
            point_id = record.get("id", i + idx)
            if isinstance(point_id, str):
                # Convert string ID to integer hash
                point_id = abs(hash(point_id)) % (2**63)
            
            points.append(PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            ))
        
        # Upload batch
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )
        
        uploaded += len(batch)
        tracker.update_progress(uploaded, total, f"Uploaded {uploaded}/{total} vectors")
        print(f"[INFO] Uploaded {uploaded}/{total} vectors")
    
    return uploaded


# =============================================================================
# Main Execution
# =============================================================================

def main():
    """Main entrypoint for the deployer module."""
    
    # Generate or use provided job_id
    if len(sys.argv) > 1:
        job_id = sys.argv[1]
    else:
        job_id = f"{STAGE_NAME}_{datetime.now():%Y%m%d_%H%M%S}"
    
    print(f"[INFO] Starting Qdrant Deployer")
    print(f"[INFO] Job ID: {job_id}")
    print(f"[INFO] Qdrant: {QDRANT_HOST}:{QDRANT_PORT}")
    print(f"[INFO] Collection: {COLLECTION_NAME}")
    
    # Initialize tracker
    tracker = ProgressTracker(job_id, STAGE_NAME)
    tracker.start()
    
    # Find embeddings
    tracker.set_step("[1/10] Finding embeddings", 1)
    embeddings_dir = DATA_PATH / "embeddings"
    
    if not embeddings_dir.exists():
        error = "No embeddings directory found. Run embedder first."
        update_status(job_id, "error", error=error)
        tracker.fail(error)
        sys.exit(1)
    
    update_status(job_id, "running")
    
    try:
        # Load embeddings
        tracker.set_step("[2/10] Loading embeddings", 2)
        embeddings = load_embeddings(embeddings_dir)
        
        if not embeddings:
            error = "No embeddings found in JSONL file"
            update_status(job_id, "error", error=error)
            tracker.fail(error)
            sys.exit(1)
        
        print(f"[INFO] Loaded {len(embeddings)} embeddings")
        tracker.update_progress(len(embeddings), len(embeddings), f"Loaded {len(embeddings)} embeddings")
        
        # Determine vector size from first embedding
        first_vector = embeddings[0].get("embedding", embeddings[0].get("vector", []))
        vector_size = len(first_vector)
        print(f"[INFO] Vector size: {vector_size}")
        
        # Connect to Qdrant
        tracker.set_step("[3/10] Connecting to Qdrant", 3)
        client = connect_qdrant()
        
        # Ensure collection
        tracker.set_step("[4/10] Creating collection", 4)
        ensure_collection(client, vector_size)
        
        # Upload
        tracker.set_step("[5/10] Uploading vectors", 5)
        uploaded = upload_embeddings(client, embeddings, tracker)
        
        # Verify
        tracker.set_step("[9/10] Verifying upload", 9)
        collection_info = client.get_collection(COLLECTION_NAME)
        points_count = collection_info.points_count
        print(f"[INFO] Collection has {points_count} points")
        
        tracker.set_step("[10/10] Complete", 10)
        
        stats = {
            "embeddings_loaded": len(embeddings),
            "vectors_uploaded": uploaded,
            "collection_points": points_count,
            "vector_size": vector_size,
            "collection": COLLECTION_NAME
        }
        
        update_status(job_id, "success", stats=stats)
        tracker.complete(stats)
        print(f"[OK] Deploy completed: {points_count} vectors in '{COLLECTION_NAME}'")
        sys.exit(0)
        
    except Exception as e:
        error_msg = str(e)
        update_status(job_id, "error", error=error_msg)
        tracker.fail(error_msg)
        print(f"[ERROR] Deploy failed: {error_msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()
