"""Integration tests: end-to-end with local Qdrant and optional Ollama.

These tests require running services:
- Qdrant test instance: docker compose -p stack-g-devdito --profile test up qdrant-test
  (uses port 18336, isolated volume)
- Falls back to main qdrant (port 18334) if test instance not available
- Ollama (optional for test_e2e_qdrant_embed_query_metrics): required only for full embed+query flow

Run when Docker Desktop (or Stack-G) is up:
  pytest evaluation/tests/test_integration.py -v
  pytest evaluation/tests/test_integration.py -v -k e2e

Skip when services are down (tests are skipped, not failed).
Task: T029
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
import yaml

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

# Import from eval_model_comparison to reuse provider setup
from evaluation.scripts.eval_model_comparison import create_provider
from evaluation.config import load_experiment_config
from evaluation.metrics.mrr import reciprocal_rank, mean_reciprocal_rank

EVAL_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = EVAL_ROOT.parent


def _get_test_qdrant_client() -> QdrantClient:
    """Create Qdrant client for tests — prefers test instance (18336), falls back to main (18334)."""
    env_path = REPO_ROOT / "config" / "env.yaml"
    
    # Default: test instance (host ports 18xxx)
    host = "localhost"
    port = 18336
    
    if env_path.exists():
        with open(env_path, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
        # Prefer qdrant_test if configured
        test_cfg = raw.get("SERVICES", {}).get("qdrant_test", {})
        if test_cfg:
            host = test_cfg.get("host", host)
            port = test_cfg.get("port", port)
    
    # Try test instance first
    try:
        client = QdrantClient(host=host, port=port, timeout=5)
        client.get_collections()
        return client
    except Exception:
        pass
    
    # Fall back to main qdrant (18334)
    raw: dict = {}
    if env_path.exists():
        with open(env_path, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
    main_cfg = raw.get("SERVICES", {}).get("qdrant", {})
    host = main_cfg.get("host", "localhost")
    port = main_cfg.get("port", 18334)
    return QdrantClient(host=host, port=port, timeout=5, check_compatibility=False)


def _qdrant_available() -> bool:
    """Return True if any Qdrant instance is reachable."""
    try:
        client = _get_test_qdrant_client()
        client.get_collections()
        return True
    except Exception:
        return False


def _ollama_available() -> bool:
    """Return True if Ollama is reachable and bge-m3 (or small model) can embed."""
    try:
        config = load_experiment_config(EVAL_ROOT / "experiments" / "model_bge_m3.yaml")
        provider = create_provider(config)
        provider.embed(["test"])
        return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def qdrant_client() -> QdrantClient:
    """Provide Qdrant client; skip if Qdrant is not available."""
    if not _qdrant_available():
        pytest.skip("Qdrant not reachable (start: docker compose -p stack-g-devdito --profile test up qdrant-test)")
    return _get_test_qdrant_client()


@pytest.mark.integration
def test_qdrant_connection(qdrant_client: QdrantClient) -> None:
    """Verify we can connect to Qdrant and list collections (smoke test)."""
    collections = qdrant_client.get_collections()
    assert collections is not None
    # We only assert the API responded; collection count is arbitrary


@pytest.mark.integration
def test_e2e_qdrant_embed_query_metrics(qdrant_client: QdrantClient) -> None:
    """End-to-end: embed small corpus, create collection, query, verify metrics are non-zero.

    Uses one chunk and one query with the same text so that the relevant document
    is at rank 1, giving MRR = 1.0. Requires both Qdrant and Ollama to be running.
    """
    if not _ollama_available():
        pytest.skip("Ollama not reachable or model not available (e.g. ollama pull bge-m3)")

    config = load_experiment_config(EVAL_ROOT / "experiments" / "model_bge_m3.yaml")
    provider = create_provider(config)

    # One document, one query — same text so query retrieves the doc at rank 1
    text = "Reife- und Diplompruefung bestehen aus drei Saeulen."
    vectors = provider.embed([text])
    assert len(vectors) == 1
    assert len(vectors[0]) == config.dimensions

    collection_name = f"eval_integration_{uuid.uuid4().hex[:8]}"
    page_id = "test:integration:page"

    try:
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=config.dimensions,
                distance=Distance.COSINE,
            ),
        )
        qdrant_client.upsert(
            collection_name=collection_name,
            points=[
                PointStruct(
                    id=0,
                    vector=vectors[0],
                    payload={"page_id": page_id, "chunk_index": 0, "text": text},
                )
            ],
        )

        query_vector = provider.embed([text])[0]
        response = qdrant_client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=5,
        )
        search_results = response.points
        assert len(search_results) >= 1
        ranked_pages = [
            hit.payload["page_id"]
            for hit in search_results
            if hit.payload is not None and "page_id" in hit.payload
        ]
        assert ranked_pages, "Search returned no payloads with page_id"
        relevant = {page_id}

        rr = reciprocal_rank(ranked_pages, relevant)
        mrr = mean_reciprocal_rank([(ranked_pages, relevant)])
        assert rr > 0, "Expected reciprocal rank > 0 (relevant doc in results)"
        assert mrr > 0, "Expected mean reciprocal rank > 0"
    finally:
        try:
            qdrant_client.delete_collection(collection_name)
        except Exception:
            pass
