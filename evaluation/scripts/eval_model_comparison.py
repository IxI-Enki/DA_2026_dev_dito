"""Embedding model comparison evaluation for thesis table FF3.

Compares multiple embedding models on the same corpus and query set
by embedding ALL test-corpus documents into temporary Qdrant collections
and measuring retrieval quality with NDCG@10, MRR, P@5, Recall@10,
MAP, and Hit Rate.

Usage::

    python -m evaluation.scripts.eval_model_comparison \\
        --config evaluation/experiments/model_bge_m3_unsupervised.yaml -v
    python -m evaluation.scripts.eval_model_comparison --compare-all -v
    python -m evaluation.scripts.eval_model_comparison --compare-all --verbose

Thesis-ID: FF3 / J2
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

EVAL_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = EVAL_ROOT.parent

sys.path.insert(0, str(REPO_ROOT))

from evaluation.config import (
    ExperimentConfig,
    load_experiment_config,
    load_ground_truth,
)
from evaluation.metrics.mean_average_precision import average_precision
from evaluation.metrics.mrr import mean_reciprocal_rank, reciprocal_rank
from evaluation.metrics.ndcg import mean_ndcg_at_k, ndcg_at_k
from evaluation.metrics.precision_at_k import mean_precision_at_k, precision_at_k
from evaluation.metrics.recall_at_k import recall_at_k
from evaluation.providers.base import EmbeddingProvider

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Multi-signal relevance scoring (aligned with prototype in
# research/techstack/ragas/professional_evaluation/metrics/retrieval_metrics.py)
# ---------------------------------------------------------------------------


def calculate_relevance_score(
    chunk_text: str,
    ground_truth: str,
    context_keywords: list[str] | None = None,
) -> float:
    """Multi-signal relevance score combining word overlap, keywords, fragments.

    Ported from the prototype ``RetrievalMetricsCalculator._calculate_relevance_scores``
    in ``ragas/professional_evaluation/metrics/retrieval_metrics.py``.

    Args:
        chunk_text: Retrieved chunk text.
        ground_truth: Expected answer text.
        context_keywords: Optional keywords from ground truth entry.

    Returns:
        Relevance score in [0.0, 1.0].
    """
    ctx_lower = chunk_text.lower()
    gt_lower = ground_truth.lower()
    ctx_words = set(ctx_lower.split())
    gt_words = set(gt_lower.split())

    # Signal 1: Word overlap with ground truth
    overlap = len(gt_words & ctx_words)
    word_score = overlap / len(gt_words) if gt_words else 0.0

    # Signal 2: Keyword matching
    keyword_score = 0.0
    if context_keywords:
        matched = sum(1 for kw in context_keywords if kw.lower() in ctx_lower)
        keyword_score = matched / len(context_keywords)

    # Signal 3: Ground truth fragment matching
    fragment_score = 0.0
    gt_fragments = [gt_lower[i : i + 20] for i in range(0, max(len(gt_lower) - 20, 1), 10)]
    if gt_fragments:
        matched_frags = sum(1 for frag in gt_fragments if frag in ctx_lower)
        fragment_score = matched_frags / len(gt_fragments)

    combined = 0.4 * word_score + 0.3 * keyword_score + 0.3 * fragment_score
    return min(1.0, combined)


def _std(values: list[float]) -> float:
    """Standard deviation (population)."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5


# ---------------------------------------------------------------------------
# Simple chunker (evaluation-only, no pipeline dependency)
# ---------------------------------------------------------------------------


def simple_chunk(text: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
    """Split text into chunks by paragraph boundaries respecting size limits.

    Args:
        text: Input text to chunk.
        chunk_size: Target chunk size in characters.
        overlap: Number of overlap characters between chunks.

    Returns:
        List of text chunks.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return [text.strip()] if text.strip() else []

    chunks: list[str] = []
    current_parts: list[str] = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para)

        if para_len > chunk_size:
            # Flush current
            if current_parts:
                chunks.append("\n\n".join(current_parts))
                current_parts = []
                current_len = 0
            # Split large paragraph by sentences
            sentences = para.replace(". ", ".\n").split("\n")
            for sent in sentences:
                sent = sent.strip()
                if not sent:
                    continue
                if current_len + len(sent) > chunk_size and current_parts:
                    chunks.append("\n\n".join(current_parts))
                    current_parts = []
                    current_len = 0
                current_parts.append(sent)
                current_len += len(sent)
            continue

        if current_len + para_len > chunk_size and current_parts:
            chunks.append("\n\n".join(current_parts))
            # Overlap: keep last part if small enough
            if overlap > 0 and current_parts and len(current_parts[-1]) <= overlap:
                current_parts = [current_parts[-1]]
                current_len = len(current_parts[0])
            else:
                current_parts = []
                current_len = 0

        current_parts.append(para)
        current_len += para_len

    if current_parts:
        chunks.append("\n\n".join(current_parts))

    return chunks


# ---------------------------------------------------------------------------
# Corpus loader
# ---------------------------------------------------------------------------

_IMAGE_SUFFIXES = (".jpg.md", ".png.md", ".gif.md", ".jpeg.md", ".svg.md", ".webp.md", ".bmp.md")


def _extract_page_id(text: str, filename: str) -> str:
    """Extract page_id or media_id from YAML frontmatter, fallback to filename."""
    for line in text.split("\n")[:25]:
        stripped = line.strip()
        if stripped.startswith("page_id:"):
            return stripped.split(":", 1)[1].strip().strip("'\"")
        if stripped.startswith("media_id:"):
            return stripped.split(":", 1)[1].strip().strip("'\"")
    stem = filename.rsplit(".", 1)[0] if filename.endswith(".md") else filename
    return stem.replace("_", ":", 1)


def _strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter (between --- markers) from document text."""
    if not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    if end == -1:
        return text
    return text[end + 4 :].strip()


def _load_md_dir(
    directory: Path,
    chunk_size: int,
    chunk_overlap: int,
    exclude_images: bool = True,
) -> list[dict]:
    """Load and chunk all .md files from a single directory."""
    md_files = sorted(directory.glob("*.md"))
    chunks: list[dict] = []
    skipped = 0
    for md_path in md_files:
        if exclude_images and md_path.name.lower().endswith(_IMAGE_SUFFIXES):
            skipped += 1
            continue
        raw_text = md_path.read_text(encoding="utf-8")
        page_id = _extract_page_id(raw_text, md_path.name)
        body = _strip_frontmatter(raw_text)
        if len(body.strip()) < 50:
            continue
        for i, chunk_text in enumerate(
            simple_chunk(body, chunk_size=chunk_size, overlap=chunk_overlap)
        ):
            chunks.append({"page_id": page_id, "chunk_index": i, "text": chunk_text})
    if skipped:
        logger.info("  Skipped %d image files in %s", skipped, directory.name)
    return chunks


def _find_preprocessed_dir() -> Path:
    """Find the most recent preprocessed data directory."""
    base = REPO_ROOT / "data" / "preprocessed"
    if not base.exists():
        raise FileNotFoundError(f"Preprocessed data not found: {base}")
    candidates = sorted(base.glob("preprocessed_at_*"), reverse=True)
    if not candidates:
        raise FileNotFoundError(f"No preprocessed_at_* dirs in {base}")
    return candidates[0]


def _find_fetched_dir() -> Path:
    """Find the most recent fetched data directory."""
    base = REPO_ROOT / "data" / "fetched"
    if not base.exists():
        raise FileNotFoundError(f"Fetched data not found: {base}")
    candidates = sorted(base.glob("fetched_at_*"), reverse=True)
    if not candidates:
        raise FileNotFoundError(f"No fetched_at_* dirs in {base}")
    return candidates[0]


def load_corpus(
    corpus_source: str = "test_corpus",
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> list[dict]:
    """Load and chunk documents from the specified corpus source.

    Args:
        corpus_source: Either 'test_corpus' (evaluation/test_corpus/, 75 docs)
            or 'preprocessed' (data/preprocessed/.../{pages,media}, ~436 docs).
        chunk_size: Target chunk size in characters.
        chunk_overlap: Overlap between chunks.

    Returns:
        List of dicts with ``page_id``, ``chunk_index``, ``text`` keys.
    """
    all_chunks: list[dict] = []

    if corpus_source == "preprocessed":
        pp_dir = _find_preprocessed_dir()
        pages_dir = pp_dir / "pages"
        media_dir = pp_dir / "media"
        logger.info("Loading FULL preprocessed corpus from %s", pp_dir)

        if pages_dir.exists():
            page_chunks = _load_md_dir(pages_dir, chunk_size, chunk_overlap, exclude_images=False)
            logger.info("  Pages: %d chunks", len(page_chunks))
            all_chunks.extend(page_chunks)

        if media_dir.exists():
            media_chunks = _load_md_dir(media_dir, chunk_size, chunk_overlap, exclude_images=True)
            logger.info("  Media (no images): %d chunks", len(media_chunks))
            all_chunks.extend(media_chunks)

    else:
        corpus_dir = EVAL_ROOT / "test_corpus"
        if not corpus_dir.exists():
            raise FileNotFoundError(f"Test corpus not found: {corpus_dir}")
        all_chunks = _load_md_dir(corpus_dir, chunk_size, chunk_overlap, exclude_images=True)

    doc_count = len({c["page_id"] for c in all_chunks})
    logger.info(
        "Corpus loaded: %d chunks from %d documents (source=%s)",
        len(all_chunks),
        doc_count,
        corpus_source,
    )
    return all_chunks


def load_corpus_for_ground_truth(
    ground_truth: dict,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> list[dict]:
    """Load and chunk only the documents referenced in the ground truth.

    Loads plain-text files from ``data/fetched/fetched_at_*/page_content/``
    using the ``source_file`` fields from the ground-truth QA pairs.

    Args:
        ground_truth: Ground truth dict with a ``qa_pairs`` list, each entry
            containing a ``source_file`` field.
        chunk_size: Target chunk size in characters.
        chunk_overlap: Overlap between chunks.

    Returns:
        List of dicts with ``page_id``, ``chunk_index``, ``text`` keys.
    """
    qa_pairs = ground_truth.get("qa_pairs", [])
    source_files = sorted({qa["source_file"] for qa in qa_pairs if qa.get("source_file")})

    fetched_dir = _find_fetched_dir()
    content_dir = fetched_dir / "page_content"

    all_chunks: list[dict] = []
    for source_file in source_files:
        file_path = content_dir / source_file
        if not file_path.exists():
            logger.warning("Source file not found in fetched corpus: %s", file_path)
            continue
        text = file_path.read_text(encoding="utf-8")
        stem = source_file.rsplit(".", 1)[0] if "." in source_file else source_file
        page_id = stem.replace("_", ":", 1)
        for i, chunk_text in enumerate(
            simple_chunk(text, chunk_size=chunk_size, overlap=chunk_overlap)
        ):
            all_chunks.append({"page_id": page_id, "chunk_index": i, "text": chunk_text})

    doc_count = len({c["page_id"] for c in all_chunks})
    logger.info(
        "Corpus loaded: %d chunks from %d documents (ground-truth sources)",
        len(all_chunks),
        doc_count,
    )
    return all_chunks


# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------


def create_provider(config: ExperimentConfig) -> EmbeddingProvider:
    """Instantiate the embedding provider from experiment config.

    Supports 'sentence-transformers' (local HF models on GPU),
    'ollama' (local Ollama server), and 'openai' (API).
    """
    if config.provider == "sentence-transformers":
        from evaluation.providers.sentence_transformers_provider import (
            SentenceTransformersProvider,
        )

        dtype_str = getattr(config, "torch_dtype", "float32")
        dtype_val: Literal["float16", "float32"] = (
            "float16" if dtype_str == "float16" else "float32"
        )
        return SentenceTransformersProvider(
            model=config.model,
            dimensions=config.dimensions,
            torch_dtype=dtype_val,
        )
    elif config.provider == "ollama":
        from evaluation.providers.ollama_provider import OllamaProvider

        return OllamaProvider(
            model=config.model,
            dimensions=config.dimensions,
        )
    elif config.provider == "openai":
        from evaluation.providers.openai_provider import OpenAIProvider

        api_key_file = REPO_ROOT / "config" / "secrets" / "openai.token"
        return OpenAIProvider(
            model=config.model,
            dimensions=config.dimensions,
            api_key_file=api_key_file if api_key_file.exists() else None,
        )
    else:
        raise ValueError(f"Unknown provider: {config.provider}")


# ---------------------------------------------------------------------------
# Qdrant helpers
# ---------------------------------------------------------------------------


def _get_qdrant_client(host: str = "localhost", port: int = 6333) -> QdrantClient:
    """Create Qdrant client for local evaluation instance.

    Args:
        host: Qdrant host (default: localhost).
        port: Qdrant gRPC/HTTP port (default: 6333).
    """
    logger.info("Connecting to Qdrant at %s:%d", host, port)
    return QdrantClient(host=host, port=port, timeout=30)


def _embed_in_batches(
    provider: EmbeddingProvider,
    texts: list[str],
    batch_size: int = 32,
) -> list[list[float]]:
    """Embed texts in batches to avoid memory issues."""
    all_embeddings: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        embeddings = provider.embed(batch)
        all_embeddings.extend(embeddings)
        if i > 0 and i % (batch_size * 5) == 0:
            logger.info("  Embedded %d / %d texts", i, len(texts))
    return all_embeddings


# ---------------------------------------------------------------------------
# Evaluation runner
# ---------------------------------------------------------------------------


def _get_git_version() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=5,
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _unload_provider(provider: EmbeddingProvider) -> None:
    """Release GPU memory if the provider supports it."""
    unload_fn = getattr(provider, "unload", None)
    if callable(unload_fn):
        unload_fn()


def _expected_sources(qa: dict) -> list[str]:
    """Get expected source page IDs from ground truth entry.

    Prefers the 'sources' field (from YAML frontmatter).
    Falls back to deriving from 'source_file' if 'sources' is missing.
    """
    sources = qa.get("sources", [])
    if sources:
        return list(sources)
    sf = qa.get("source_file", "")
    if sf:
        stem = sf.rsplit(".", 1)[0] if "." in sf else sf
        return [stem.replace("_", ":", 1)]
    return []


def run_model_evaluation(
    config: ExperimentConfig,
    *,
    verbose: bool = False,
    corpus_source: str = "test_corpus",
) -> dict:
    """Execute the model evaluation for a single experiment config.

    Steps:
      1. Load and chunk corpus documents.
      2. Embed all chunks with the configured provider.
      3. Create a temporary Qdrant collection and upsert vectors.
      4. For each ground-truth question, embed the query and search.
      5. Compute NDCG@10, MRR, P@5, Recall@10, MAP, Hit Rate.
      6. Delete the temporary collection.
      7. Return result dict.

    Args:
        config: Experiment configuration.
        verbose: Print per-query results.
        corpus_source: 'test_corpus' or 'preprocessed'.

    Returns:
        Result dict ready for JSON serialisation.
    """
    # 1. Load ground truth and corpus
    gt_path = config.ground_truth_file
    if not Path(gt_path).is_absolute():
        gt_path = EVAL_ROOT / gt_path
    gt_data = load_ground_truth(gt_path)
    qa_pairs = gt_data["qa_pairs"]

    corpus_chunks = load_corpus_for_ground_truth(
        gt_data,
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
    )

    if not corpus_chunks:
        raise RuntimeError("No corpus chunks loaded -- check evaluation/test_corpus/")

    # 2. Embed corpus chunks
    provider = create_provider(config)
    logger.info(
        "Embedding %d chunks with %s (dim=%d)",
        len(corpus_chunks),
        provider.model_name,
        provider.dimensions,
    )

    chunk_texts = [c["text"] for c in corpus_chunks]
    t_start = time.monotonic()
    chunk_embeddings = _embed_in_batches(provider, chunk_texts)
    embed_time = time.monotonic() - t_start
    logger.info("Embedding completed in %.1f seconds", embed_time)

    # 3. Create temporary Qdrant collection
    collection_name = (
        f"{config.collection_prefix}{config.model.replace('/', '_')}"
        f"_{config.chunk_size}_{uuid.uuid4().hex[:6]}"
    )
    qdrant = _get_qdrant_client()

    try:
        qdrant.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=config.dimensions,
                distance=Distance.COSINE,
            ),
        )
        logger.info("Created Qdrant collection: %s", collection_name)

        points = [
            PointStruct(
                id=i,
                vector=chunk_embeddings[i],
                payload={
                    "page_id": corpus_chunks[i]["page_id"],
                    "chunk_index": corpus_chunks[i]["chunk_index"],
                    "text": corpus_chunks[i]["text"],
                },
            )
            for i in range(len(corpus_chunks))
        ]

        batch_size = 100
        for i in range(0, len(points), batch_size):
            qdrant.upsert(
                collection_name=collection_name,
                points=points[i : i + batch_size],
            )
        logger.info("Upserted %d points into %s", len(points), collection_name)

        # 4. Query each ground-truth question
        per_query_results: list[dict] = []
        mrr_inputs: list[tuple[list[str], set[str]]] = []
        ndcg_inputs: list[tuple[list[str], dict[str, int]]] = []
        p_at_5_inputs: list[tuple[list[str], set[str]]] = []
        recall_inputs: list[tuple[list[str], set[str]]] = []
        ap_inputs: list[tuple[list[str], set[str]]] = []

        for i, qa in enumerate(qa_pairs):
            question = qa["question"]
            expected_sources = _expected_sources(qa)
            relevant = set(expected_sources)
            relevance_map = {pid: 1 for pid in relevant}
            gt_text = qa.get("ground_truth", "")
            keywords = qa.get("context_keywords", [])
            difficulty = qa.get("difficulty", "unknown")

            query_embedding = provider.embed([question])[0]

            search_results = qdrant.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=max(config.top_k, 10),
                with_payload=True,
            )

            seen: set[str] = set()
            ranked_pages: list[str] = []
            best_relevance_by_page: dict[str, float] = {}
            for hit in search_results:
                payload: dict = hit.payload if hit.payload is not None else {}
                pid = payload.get("page_id", "")
                if not pid:
                    continue
                chunk_text = payload.get("text", "")
                rel_score = calculate_relevance_score(chunk_text, gt_text, keywords)
                if pid not in best_relevance_by_page or rel_score > best_relevance_by_page[pid]:
                    best_relevance_by_page[pid] = rel_score
                if pid not in seen:
                    seen.add(pid)
                    ranked_pages.append(pid)

            rr = reciprocal_rank(ranked_pages, relevant)
            ndcg = ndcg_at_k(ranked_pages, relevance_map, k=10)
            p5 = precision_at_k(ranked_pages, relevant, k=5)
            rec10 = recall_at_k(ranked_pages, relevant, k=10)
            ap = average_precision(ranked_pages, relevant)
            top1_rel = best_relevance_by_page.get(ranked_pages[0], 0.0) if ranked_pages else 0.0

            mrr_inputs.append((ranked_pages, relevant))
            ndcg_inputs.append((ranked_pages, relevance_map))
            p_at_5_inputs.append((ranked_pages, relevant))
            recall_inputs.append((ranked_pages, relevant))
            ap_inputs.append((ranked_pages, relevant))

            entry = {
                "id": qa["id"],
                "question": question,
                "expected_sources": expected_sources,
                "difficulty": difficulty,
                "ranked_pages": ranked_pages[:10],
                "rr": round(rr, 4),
                "ndcg_at_10": round(ndcg, 4),
                "p_at_5": round(p5, 4),
                "recall_at_10": round(rec10, 4),
                "average_precision": round(ap, 4),
                "top1_content_relevance": round(top1_rel, 4),
                "hit_in_top_k": bool(relevant & set(ranked_pages)),
            }
            per_query_results.append(entry)

            if verbose:
                hit_str = "[HIT]" if entry["hit_in_top_k"] else "[MISS]"
                print(
                    f"  [{i+1:2d}/{len(qa_pairs)}] RR={rr:.3f} "
                    f"NDCG@10={ndcg:.3f} P@5={p5:.3f} R@10={rec10:.3f} "
                    f"rel={top1_rel:.2f} {hit_str}  {qa['id']}"
                )

    finally:
        try:
            qdrant.delete_collection(collection_name)
            logger.info("Deleted temporary collection: %s", collection_name)
        except Exception as exc:
            logger.warning("Failed to delete collection %s: %s", collection_name, exc)

    # 5. Aggregate metrics
    agg_mrr = mean_reciprocal_rank(mrr_inputs)
    agg_ndcg = mean_ndcg_at_k(ndcg_inputs, k=10)
    agg_p5 = mean_precision_at_k(p_at_5_inputs, k=5)

    rr_values = [q["rr"] for q in per_query_results]
    ndcg_values = [q["ndcg_at_10"] for q in per_query_results]
    p5_values = [q["p_at_5"] for q in per_query_results]
    rec10_values = [q["recall_at_10"] for q in per_query_results]
    ap_values = [q["average_precision"] for q in per_query_results]
    rel_values = [q["top1_content_relevance"] for q in per_query_results]

    n = len(per_query_results) or 1
    agg_recall = sum(rec10_values) / n
    agg_map = sum(ap_values) / n
    hits = sum(1 for q in per_query_results if q.get("hit_in_top_k", False))
    total = len(per_query_results)

    by_difficulty: dict[str, dict] = {}
    for diff in ("easy", "medium", "hard"):
        subset = [q for q in per_query_results if q.get("difficulty") == diff]
        if subset:
            by_difficulty[diff] = {
                "count": len(subset),
                "mrr": round(sum(q["rr"] for q in subset) / len(subset), 4),
                "ndcg_at_10": round(sum(q["ndcg_at_10"] for q in subset) / len(subset), 4),
                "hit_rate": round(sum(1 for q in subset if q["hit_in_top_k"]) / len(subset), 4),
            }

    cost_info = {}
    from evaluation.providers.openai_provider import OpenAIProvider

    if isinstance(provider, OpenAIProvider):
        cost_info = {
            "total_tokens": provider.total_tokens,
            "estimated_cost_usd": round(provider.estimated_cost_usd, 6),
        }

    _unload_provider(provider)

    result = {
        "experiment": {
            "name": config.name,
            "type": config.experiment_type,
            "thesis_id": config.thesis_id,
            "model": config.model,
            "provider": config.provider,
            "dimensions": config.dimensions,
            "chunk_size": config.chunk_size,
            "top_k": config.top_k,
            "config_hash": config.config_hash,
            "code_version": _get_git_version(),
            "timestamp": datetime.now(UTC).isoformat(),
        },
        "aggregate_metrics": {
            "mrr": {"mean": round(agg_mrr, 4), "std": round(_std(rr_values), 4)},
            "ndcg_at_10": {"mean": round(agg_ndcg, 4), "std": round(_std(ndcg_values), 4)},
            "precision_at_5": {"mean": round(agg_p5, 4), "std": round(_std(p5_values), 4)},
            "recall_at_10": {"mean": round(agg_recall, 4), "std": round(_std(rec10_values), 4)},
            "map": {"mean": round(agg_map, 4), "std": round(_std(ap_values), 4)},
            "content_relevance": {
                "mean": round(sum(rel_values) / max(len(rel_values), 1), 4),
                "std": round(_std(rel_values), 4),
            },
            "hit_rate": round(hits / total, 4) if total else 0.0,
        },
        "by_difficulty": by_difficulty,
        "performance": {
            "corpus_chunks": len(corpus_chunks),
            "embedding_time_seconds": round(embed_time, 2),
            **cost_info,
        },
        "summary": {
            "total_queries": total,
            "hits": hits,
            "misses": total - hits,
        },
        "per_query": per_query_results,
    }

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "FF3 Embedding Model Comparison — embed corpus and evaluate "
            "retrieval quality with NDCG@10, MRR, and P@5."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m evaluation.scripts.eval_model_comparison --config experiments/model_bge_m3.yaml\n"
            "  python -m evaluation.scripts.eval_model_comparison --compare-all\n"
            "  python -m evaluation.scripts.eval_model_comparison --compare-all --verbose\n"
        ),
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to a single experiment YAML config",
    )
    parser.add_argument(
        "--compare-all",
        action="store_true",
        help="Run all model_*.yaml configs and produce comparison table",
    )
    parser.add_argument(
        "--output-dir",
        default=str(EVAL_ROOT / "results"),
        help="Directory for result JSON files (default: evaluation/results/)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print per-query results to stdout",
    )
    parser.add_argument(
        "--corpus",
        choices=["test_corpus", "preprocessed"],
        default="test_corpus",
        help="Corpus source: 'test_corpus' (75 docs) or 'preprocessed' (full ~436 docs)",
    )
    parser.add_argument(
        "--gt",
        default=None,
        help="Override ground truth file (relative to evaluation/)",
    )
    return parser


def _fmt_metric(m: dict | float) -> str:
    """Format a metric value (may be dict with mean/std or plain float)."""
    if isinstance(m, dict):
        return f"{m['mean']:.4f} (±{m['std']:.4f})"
    return f"{m:.4f}"


def _metric_mean(m: dict | float) -> float:
    """Extract mean from metric (dict or float)."""
    return m["mean"] if isinstance(m, dict) else m


def _print_summary(result: dict) -> None:
    """Print a human-readable summary of a single evaluation result."""
    exp = result["experiment"]
    agg = result["aggregate_metrics"]
    perf = result["performance"]
    summary = result["summary"]

    print(f"\n  Model:        {exp['model']} ({exp['provider']})")
    print(f"  Dimensions:   {exp['dimensions']}")
    print(f"  MRR:          {_fmt_metric(agg['mrr'])}")
    print(f"  NDCG@10:      {_fmt_metric(agg['ndcg_at_10'])}")
    print(f"  Precision@5:  {_fmt_metric(agg['precision_at_5'])}")
    print(f"  Recall@10:    {_fmt_metric(agg.get('recall_at_10', 0.0))}")
    print(f"  MAP:          {_fmt_metric(agg.get('map', 0.0))}")
    print(f"  Content Rel:  {_fmt_metric(agg.get('content_relevance', 0.0))}")
    print(f"  Hit Rate:     {agg['hit_rate']:.1%}")
    print(f"  Queries:      {summary['total_queries']} total, {summary['hits']} hits")
    print(f"  Chunks:       {perf['corpus_chunks']}, embed time: {perf['embedding_time_seconds']}s")
    if "estimated_cost_usd" in perf:
        print(f"  Cost:         ${perf['estimated_cost_usd']:.4f} ({perf['total_tokens']} tokens)")

    by_diff = result.get("by_difficulty", {})
    if by_diff:
        print("  By difficulty:")
        for diff, metrics in sorted(by_diff.items()):
            print(
                f"    {diff:8s}: MRR={metrics['mrr']:.3f}  NDCG@10={metrics['ndcg_at_10']:.3f}  hit={metrics['hit_rate']:.0%}  (n={metrics['count']})"
            )


def _print_comparison_table(results: list[dict]) -> None:
    """Print a Markdown comparison table to stdout."""
    print("\n## FF3 -- Embedding Model Comparison\n")
    print("| Model | Dim | MRR | NDCG@10 | P@5 | R@10 | MAP | Hit Rate |")
    print("|-------|-----|-----|---------|-----|------|-----|----------|")
    for r in results:
        exp = r["experiment"]
        agg = r["aggregate_metrics"]
        print(
            f"| {exp['model']} | {exp['dimensions']} "
            f"| {_metric_mean(agg['mrr']):.4f} "
            f"| {_metric_mean(agg['ndcg_at_10']):.4f} "
            f"| {_metric_mean(agg['precision_at_5']):.4f} "
            f"| {_metric_mean(agg.get('recall_at_10', 0.0)):.4f} "
            f"| {_metric_mean(agg.get('map', 0.0)):.4f} "
            f"| {agg['hit_rate']:.1%} |"
        )


def main() -> None:
    """Entry point for model comparison evaluation."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = _build_parser()
    args = parser.parse_args()

    if not args.config and not args.compare_all:
        parser.error("Either --config or --compare-all is required")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    corpus_source: str = args.corpus
    gt_override: str | None = args.gt

    def _apply_gt_override(config: ExperimentConfig) -> ExperimentConfig:
        """Return a new config with overridden ground_truth_file if --gt given."""
        if gt_override is None:
            return config
        return ExperimentConfig(
            **{
                **{f.name: getattr(config, f.name) for f in config.__dataclass_fields__.values()},
                "ground_truth_file": gt_override,
            }
        )

    if args.compare_all:
        experiments_dir = EVAL_ROOT / "experiments"
        config_files = sorted(experiments_dir.glob("model_*.yaml"))
        if not config_files:
            logger.error("No model_*.yaml configs found in %s", experiments_dir)
            sys.exit(1)

        logger.info("Found %d model configs for comparison", len(config_files))
        logger.info("Corpus source: %s", corpus_source)
        if gt_override:
            logger.info("Ground truth override: %s", gt_override)
        all_results: list[dict] = []

        print("=" * 60)
        print("  FF3 Embedding Model Comparison")
        print(f"  Corpus: {corpus_source}")
        print("=" * 60)

        for cf in config_files:
            config = _apply_gt_override(load_experiment_config(cf))
            logger.info("Running: %s (%s)", config.name, config.model)

            try:
                result = run_model_evaluation(
                    config,
                    verbose=args.verbose,
                    corpus_source=corpus_source,
                )
                all_results.append(result)
                _print_summary(result)

                out_file = output_dir / f"model_{config.model.replace('/', '_')}_{timestamp}.json"
                with open(out_file, "w", encoding="utf-8") as fh:
                    json.dump(result, fh, indent=2, ensure_ascii=False)
                logger.info("Written: %s", out_file)

            except Exception as exc:
                logger.error("Failed for %s: %s", config.model, exc)
                continue

        if all_results:
            _print_comparison_table(all_results)

            comparison_file = output_dir / f"model_comparison_{timestamp}.json"
            with open(comparison_file, "w", encoding="utf-8") as fh:
                json.dump(
                    {
                        "thesis_id": "FF3",
                        "timestamp": datetime.now(UTC).isoformat(),
                        "code_version": _get_git_version(),
                        "corpus_source": corpus_source,
                        "ground_truth": gt_override or "from config",
                        "models": [
                            {
                                "model": r["experiment"]["model"],
                                "provider": r["experiment"]["provider"],
                                "dimensions": r["experiment"]["dimensions"],
                                "mrr": _metric_mean(r["aggregate_metrics"]["mrr"]),
                                "ndcg_at_10": _metric_mean(r["aggregate_metrics"]["ndcg_at_10"]),
                                "precision_at_5": _metric_mean(
                                    r["aggregate_metrics"]["precision_at_5"]
                                ),
                                "hit_rate": r["aggregate_metrics"]["hit_rate"],
                            }
                            for r in all_results
                        ],
                    },
                    fh,
                    indent=2,
                    ensure_ascii=False,
                )
            logger.info("Comparison written: %s", comparison_file)
        print("=" * 60)

    else:
        config = _apply_gt_override(load_experiment_config(args.config))
        logger.info("Experiment: %s (thesis_id=%s)", config.name, config.thesis_id)

        try:
            result = run_model_evaluation(
                config,
                verbose=args.verbose,
                corpus_source=corpus_source,
            )
        except Exception as exc:
            logger.error("Evaluation failed: %s", exc)
            sys.exit(1)

        out_file = output_dir / f"model_{config.model.replace('/', '_')}_{timestamp}.json"
        with open(out_file, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2, ensure_ascii=False)

        print("\n" + "=" * 60)
        print(f"  FF3 Model Evaluation -- {config.name}")
        print("=" * 60)
        _print_summary(result)
        print(f"  Output:       {out_file}")
        print("=" * 60)


if __name__ == "__main__":
    main()
