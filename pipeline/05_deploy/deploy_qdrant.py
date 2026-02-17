"""Qdrant Deployment (T086-T090)

Deploys embeddings to Qdrant via direct upload or watchdog export mode.

Usage:
  python pipeline/05_deploy/deploy_qdrant.py --mode direct --jsonl path/to/embedded.jsonl
  python pipeline/05_deploy/deploy_qdrant.py --mode watchdog --jsonl path/to/embedded.jsonl --output-dir /mnt/watchdog
  python pipeline/05_deploy/deploy_qdrant.py --mode direct --dry-run --jsonl path/to/embedded.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import shutil
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Batch size for Qdrant upserts
_UPSERT_BATCH_SIZE = 100


def _parse_jsonl(jsonl_path: Path) -> list[dict[str, Any]]:
    """Parse a JSONL file into a list of dicts.

    Accepts MCP/embeddings_creator schema: id, text, embedding, metadata.
    Also accepts deploy schema: id, vector, payload.
    """
    records: list[dict[str, Any]] = []
    with open(jsonl_path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                logger.warning("Skipped malformed line %d: %s", lineno, e)
    return records


def _normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    """Normalize record to deploy schema (id, vector, payload).

    Accepts MCP schema (id, text, embedding, metadata) or deploy schema
    (id, vector, payload). Returns dict with id, vector, payload.
    """
    vector = record.get("vector") or record.get("embedding")
    payload = record.get("payload")
    if payload is None:
        metadata = record.get("metadata") or {}
        payload = dict(metadata)
        if "text" not in payload and "text" in record:
            payload["text"] = record["text"]
    elif "text" not in payload and record.get("text") is not None:
        payload = {**payload, "text": record["text"]}
    rid = record.get("id")
    if rid is None and payload:
        text = payload.get("text", "")
        rid = hashlib.md5(text.encode()).hexdigest()
    return {"id": rid, "vector": vector, "payload": payload}


class QdrantDeployer:
    """Deploys embeddings to Qdrant (direct upload or watchdog export).

    Args:
        host: Qdrant server host.
        port: Qdrant REST port (default 6333).
    """

    def __init__(self, host: str = "192.168.8.3", port: int = 6333) -> None:
        try:
            from qdrant_client import QdrantClient

            self.client = QdrantClient(host=host, port=port)
        except ImportError:
            logger.warning("qdrant_client not installed; only watchdog mode available")
            self.client = None  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # Direct upload (T087)
    # ------------------------------------------------------------------

    def deploy_direct(
        self,
        jsonl_path: Path,
        collection_name: str,
        recreate: bool = False,
        dry_run: bool = False,
    ) -> int:
        """Upload JSONL embeddings directly to Qdrant.

        Args:
            jsonl_path: Path to the embeddings ``.jsonl`` file.
            collection_name: Target Qdrant collection name.
            recreate: If True, delete and recreate the collection first.
            dry_run: If True, validate without uploading.

        Returns:
            Number of points uploaded (or validated in dry-run mode).
        """
        raw_records = _parse_jsonl(jsonl_path)
        if not raw_records:
            logger.warning("No records in %s", jsonl_path)
            return 0
        records = [_normalize_record(r) for r in raw_records]
        first_vec = records[0].get("vector") if records else None
        if not first_vec:
            raise ValueError(
                "JSONL records must have 'vector' or 'embedding' field. "
                "Check file format (MCP: id, text, embedding, metadata)."
            )
        vec_dim = len(first_vec)
        logger.info(
            "Loaded %d records (vector_dim=%d) from %s",
            len(records), vec_dim, jsonl_path.name,
        )

        if dry_run:
            logger.info("[DRY-RUN] Would upload %d points to '%s' (dim=%d)",
                        len(records), collection_name, vec_dim)
            return len(records)

        if self.client is None:
            raise RuntimeError(
                "Qdrant client not available; install qdrant-client for direct upload."
            )

        # Collection management (T089)
        existing = {
            c.name
            for c in self.client.get_collections().collections
        }

        if recreate and collection_name in existing:
            logger.info("Recreating collection '%s'", collection_name)
            self.client.delete_collection(collection_name=collection_name)
            existing.discard(collection_name)

        if collection_name not in existing:
            from qdrant_client.models import VectorParams, Distance

            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vec_dim, distance=Distance.COSINE),
            )
            logger.info("Created collection '%s' (dim=%d)", collection_name, vec_dim)

        # Upsert in batches (records already normalized: id, vector, payload)
        from qdrant_client.models import PointStruct

        total = 0
        for i in range(0, len(records), _UPSERT_BATCH_SIZE):
            batch = records[i : i + _UPSERT_BATCH_SIZE]
            points = [
                PointStruct(
                    id=_point_id(rec),
                    vector=rec["vector"],
                    payload=rec.get("payload") or {},
                )
                for rec in batch
            ]
            self.client.upsert(collection_name=collection_name, points=points)
            total += len(points)
            logger.debug("Upserted batch %d-%d", i, i + len(points))

        logger.info("Uploaded %d points to '%s'", total, collection_name)
        return total

    # ------------------------------------------------------------------
    # Watchdog export (T088)
    # ------------------------------------------------------------------

    def deploy_watchdog(self, jsonl_path: Path, output_dir: Path) -> Path:
        """Copy JSONL to MCP watchdog directory for auto-ingestion.

        Args:
            jsonl_path: Source JSONL file.
            output_dir: Watchdog folder that Qdrant monitors.

        Returns:
            Path to the copied file.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        dest = output_dir / jsonl_path.name
        shutil.copy2(jsonl_path, dest)
        logger.info("Copied %s -> %s", jsonl_path.name, dest)
        return dest


def _point_id(record: dict[str, Any]) -> str | int:
    """Extract or generate a stable point ID from a normalized record."""
    rid = record.get("id")
    if rid is not None:
        return rid
    text = (record.get("payload") or {}).get("text", "")
    return hashlib.md5(text.encode()).hexdigest()


# ------------------------------------------------------------------
# CLI (T090)
# ------------------------------------------------------------------


def main() -> int:
    """CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Deploy embeddings to Qdrant")
    parser.add_argument("--mode", choices=["direct", "watchdog"], default="direct")
    parser.add_argument("--jsonl", type=Path, required=True, help="Embeddings JSONL file")
    parser.add_argument("--collection", default="leowiki", help="Qdrant collection name")
    parser.add_argument("--host", default="192.168.8.3", help="Qdrant host")
    parser.add_argument("--port", type=int, default=6333, help="Qdrant port")
    parser.add_argument("--output-dir", type=Path, default=None, help="Watchdog output dir")
    parser.add_argument("--recreate", action="store_true", help="Delete and recreate collection")
    parser.add_argument("--dry-run", action="store_true", help="Validate without uploading")
    args = parser.parse_args()

    if not args.jsonl.exists():
        logger.error("JSONL file not found: %s", args.jsonl)
        return 1

    try:
        deployer = QdrantDeployer(host=args.host, port=args.port)

        if args.mode == "direct":
            count = deployer.deploy_direct(
                args.jsonl, args.collection,
                recreate=args.recreate, dry_run=args.dry_run,
            )
            print(f"[OK] {count} points {'validated' if args.dry_run else 'uploaded'}")
        else:
            if args.output_dir is None:
                logger.error("--output-dir required for watchdog mode")
                return 1
            dest = deployer.deploy_watchdog(args.jsonl, args.output_dir)
            print(f"[OK] Copied to {dest}")

    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
        return 130
    except Exception as e:
        logger.error("Deployment failed: %s", e)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
