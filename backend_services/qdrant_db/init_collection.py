#!/usr/bin/env python3
"""
Initialize Qdrant collection with embeddings from JSONL file.
Runs on container startup to populate the vector database.
"""
import json
import os
import sys
import time
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

# Configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "wiki_embeddings")
EMBEDDINGS_FILE = os.getenv("EMBEDDINGS_FILE", "/data/embeddings/embedded_chunks.jsonl")
VECTOR_DIM = 3072  # text-embedding-3-large dimension
BATCH_SIZE = 100


def wait_for_qdrant(client: QdrantClient, max_retries: int = 30, delay: float = 2.0):
    """Wait for Qdrant to be ready."""
    for i in range(max_retries):
        try:
            client.get_collections()
            print(f"[OK] Qdrant is ready after {i * delay:.0f}s")
            return True
        except Exception as e:
            print(f"[INFO] Waiting for Qdrant... ({i + 1}/{max_retries})")
            time.sleep(delay)
    print("[ERROR] Qdrant did not become ready in time")
    return False


def collection_exists(client: QdrantClient, name: str) -> bool:
    """Check if collection already exists."""
    try:
        collections = client.get_collections().collections
        return any(c.name == name for c in collections)
    except Exception:
        return False


def get_collection_count(client: QdrantClient, name: str) -> int:
    """Get number of points in collection."""
    try:
        info = client.get_collection(name)
        return info.points_count
    except Exception:
        return 0


def create_collection(client: QdrantClient, name: str):
    """Create the vector collection."""
    print(f"[INFO] Creating collection '{name}' with dim={VECTOR_DIM}")
    client.create_collection(
        collection_name=name,
        vectors_config=VectorParams(
            size=VECTOR_DIM,
            distance=Distance.COSINE,
        ),
    )
    print(f"[OK] Collection '{name}' created")


def load_embeddings(filepath: str):
    """Load embeddings from JSONL file."""
    print(f"[INFO] Loading embeddings from {filepath}")
    embeddings = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if line.strip():
                try:
                    data = json.loads(line)
                    embeddings.append(data)
                except json.JSONDecodeError as e:
                    print(f"[WARN] Skipping line {line_num}: {e}")
    print(f"[OK] Loaded {len(embeddings)} embeddings")
    return embeddings


def upsert_embeddings(client: QdrantClient, collection: str, embeddings: list):
    """Upsert embeddings into collection in batches."""
    total = len(embeddings)
    print(f"[INFO] Upserting {total} embeddings in batches of {BATCH_SIZE}")
    
    for i in range(0, total, BATCH_SIZE):
        batch = embeddings[i:i + BATCH_SIZE]
        points = []
        
        for item in batch:
            point_id = item.get("id")
            if isinstance(point_id, str):
                # Convert string ID to integer hash for Qdrant
                point_id = abs(hash(point_id)) % (2**63)
            
            payload = {
                "original_id": item.get("id"),
                "text": item.get("text", ""),
                "metadata": item.get("metadata", {}),
            }
            
            points.append(
                PointStruct(
                    id=point_id,
                    vector=item["embedding"],
                    payload=payload,
                )
            )
        
        client.upsert(collection_name=collection, points=points)
        progress = min(i + BATCH_SIZE, total)
        print(f"[INFO] Progress: {progress}/{total} ({100 * progress / total:.1f}%)")
    
    print(f"[OK] Upserted {total} embeddings")


def main():
    """Main initialization routine."""
    print("=" * 60)
    print("Qdrant Collection Initializer")
    print("=" * 60)
    
    # Check if embeddings file exists
    if not Path(EMBEDDINGS_FILE).exists():
        print(f"[ERROR] Embeddings file not found: {EMBEDDINGS_FILE}")
        sys.exit(1)
    
    # Connect to Qdrant (suppress version warning)
    print(f"[INFO] Connecting to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}")
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, check_compatibility=False)
    
    if not wait_for_qdrant(client):
        sys.exit(1)
    
    # Check if collection already has data
    if collection_exists(client, COLLECTION_NAME):
        count = get_collection_count(client, COLLECTION_NAME)
        if count > 0:
            print(f"[INFO] Collection '{COLLECTION_NAME}' already has {count} points")
            print("[INFO] Skipping initialization (use FORCE_REINIT=1 to override)")
            if not os.getenv("FORCE_REINIT"):
                return
            print("[INFO] FORCE_REINIT set, recreating collection...")
            client.delete_collection(COLLECTION_NAME)
    
    # Create collection
    if not collection_exists(client, COLLECTION_NAME):
        create_collection(client, COLLECTION_NAME)
    
    # Load and upsert embeddings
    embeddings = load_embeddings(EMBEDDINGS_FILE)
    upsert_embeddings(client, COLLECTION_NAME, embeddings)
    
    # Verify
    final_count = get_collection_count(client, COLLECTION_NAME)
    print("=" * 60)
    print(f"[OK] Initialization complete. Collection has {final_count} points.")
    print("=" * 60)


if __name__ == "__main__":
    main()
