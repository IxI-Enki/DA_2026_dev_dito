"""Hybrid vs Dense retrieval evaluation for thesis table J6.

Compares dense-only retrieval (vector search) against hybrid retrieval
(vector + BM25 keyword fusion) on the same Qdrant collection.

Usage::

    python -m evaluation.scripts.eval_hybrid_vs_dense
    python -m evaluation.scripts.eval_hybrid_vs_dense --verbose

Thesis-ID: J6
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import re
import sys
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    Fusion,
    FusionQuery,
    NamedSparseVector,
    NamedVector,
    Prefetch,
    PointStruct,
    SparseVector,
    SparseVectorParams,
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
from evaluation.metrics.mrr import mean_reciprocal_rank, reciprocal_rank
from evaluation.metrics.ndcg import mean_ndcg_at_k, ndcg_at_k
from evaluation.metrics.precision_at_k import mean_precision_at_k, precision_at_k
from evaluation.scripts.eval_keyword_baseline import source_file_to_page_id
from evaluation.scripts.eval_model_comparison import (
    _embed_in_batches,
    _get_git_version,
    _get_qdrant_client,
    _std,
    calculate_relevance_score,
    create_provider,
    load_corpus,
)

logger = logging.getLogger(__name__)

# German stopwords for BM25 tokenizer (common words that add noise)
_DE_STOPWORDS = frozenset(
    "der die das ein eine einer eines einem einen und oder aber auch"
    "ist sind war waren wird werden hat hatte haben zu in von mit"
    "auf für an bei nach über aus um durch als wie nicht noch wenn"
    "wir sie er es ich du ihr man so da wo was wer wie kann nur"
    "sein seine seiner seinem seinen ihre ihrem ihren ihres im"
    "zum zur des den dem vor bis alle einem einer keine mehr"
    "diese dieser diesem dieses welche welcher welchem welches"
    "schon bereits dann dort hier jetzt sehr viel".split()
)

_TOKEN_RE = re.compile(r"[a-zäöüß]{2,}", re.IGNORECASE)


# ---------------------------------------------------------------------------
# BM25 sparse vector builder
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase terms, filtering stopwords."""
    return [
        t.lower()
        for t in _TOKEN_RE.findall(text)
        if t.lower() not in _DE_STOPWORDS
    ]


def build_vocabulary(corpus_texts: list[str]) -> dict[str, int]:
    """Build a token-to-index vocabulary from the corpus."""
    vocab: dict[str, int] = {}
    for text in corpus_texts:
        for token in set(_tokenize(text)):
            if token not in vocab:
                vocab[token] = len(vocab)
    return vocab


def compute_idf(corpus_texts: list[str], vocab: dict[str, int]) -> dict[int, float]:
    """Compute IDF values for each vocabulary term."""
    n = len(corpus_texts)
    doc_freq: Counter[int] = Counter()
    for text in corpus_texts:
        tokens = set(_tokenize(text))
        for token in tokens:
            if token in vocab:
                doc_freq[vocab[token]] += 1

    idf: dict[int, float] = {}
    for idx, df in doc_freq.items():
        idf[idx] = math.log((n - df + 0.5) / (df + 0.5) + 1.0)
    return idf


def text_to_sparse_vector(
    text: str,
    vocab: dict[str, int],
    idf: dict[int, float],
    *,
    k1: float = 1.5,
    b: float = 0.75,
    avgdl: float = 100.0,
) -> SparseVector:
    """Convert text to a BM25-weighted sparse vector."""
    tokens = _tokenize(text)
    tf: Counter[int] = Counter()
    for token in tokens:
        if token in vocab:
            tf[vocab[token]] += 1

    dl = len(tokens)
    indices: list[int] = []
    values: list[float] = []

    for idx, count in tf.items():
        tf_norm = (count * (k1 + 1)) / (count + k1 * (1 - b + b * dl / avgdl))
        score = idf.get(idx, 0.0) * tf_norm
        if score > 0:
            indices.append(idx)
            values.append(round(score, 6))

    return SparseVector(indices=indices, values=values)


# ---------------------------------------------------------------------------
# Evaluation runner
# ---------------------------------------------------------------------------

def _evaluate_dense(
    qdrant: QdrantClient,
    collection_name: str,
    provider,
    qa_pairs: list[dict],
    *,
    top_k: int = 10,
    verbose: bool = False,
) -> dict:
    """Run dense-only evaluation using named vectors."""
    return _run_queries(
        qdrant, collection_name, provider, qa_pairs,
        mode="dense", use_hybrid=False, vocab=None, idf=None, avgdl=0,
        top_k=top_k, verbose=verbose,
    )


def _evaluate_hybrid(
    qdrant: QdrantClient,
    collection_name: str,
    provider,
    qa_pairs: list[dict],
    *,
    vocab: dict[str, int],
    idf: dict[int, float],
    avgdl: float,
    top_k: int = 10,
    verbose: bool = False,
) -> dict:
    """Run hybrid (dense + BM25 sparse) evaluation with RRF fusion."""
    return _run_queries(
        qdrant, collection_name, provider, qa_pairs,
        mode="hybrid", use_hybrid=True, vocab=vocab, idf=idf, avgdl=avgdl,
        top_k=top_k, verbose=verbose,
    )


def _run_queries(
    qdrant: QdrantClient,
    collection_name: str,
    provider,
    qa_pairs: list[dict],
    *,
    mode: str,
    use_hybrid: bool,
    vocab: dict[str, int] | None,
    idf: dict[int, float] | None,
    avgdl: float,
    top_k: int = 10,
    verbose: bool = False,
) -> dict:
    """Run evaluation queries in dense or hybrid mode."""
    per_query: list[dict] = []
    mrr_inputs: list[tuple[list[str], set[str]]] = []
    ndcg_inputs: list[tuple[list[str], dict[str, int]]] = []
    p5_inputs: list[tuple[list[str], set[str]]] = []

    for i, qa in enumerate(qa_pairs):
        question = qa["question"]
        # Use explicit sources field if present, fall back to source_file
        if qa.get("sources"):
            expected_pages = set(qa["sources"])
        else:
            expected_pages = {source_file_to_page_id(qa["source_file"])}
        relevance_map = {p: 1 for p in expected_pages}
        gt_text = qa["ground_truth"]
        keywords = qa.get("context_keywords", [])
        difficulty = qa.get("difficulty", "unknown")

        query_embedding = provider.embed([question])[0]

        if use_hybrid and vocab is not None and idf is not None:
            # Hybrid: dense + sparse with RRF fusion
            query_sparse = text_to_sparse_vector(
                question, vocab, idf, avgdl=avgdl,
            )
            search_results = qdrant.query_points(
                collection_name=collection_name,
                prefetch=[
                    Prefetch(
                        query=query_embedding,
                        using="dense",
                        limit=top_k * 2,
                    ),
                    Prefetch(
                        query=query_sparse,
                        using="sparse",
                        limit=top_k * 2,
                    ),
                ],
                query=FusionQuery(fusion=Fusion.RRF),
                limit=top_k,
                with_payload=True,
            ).points
        else:
            # Dense only: use named vector
            search_results = qdrant.query_points(
                collection_name=collection_name,
                query=query_embedding,
                using="dense",
                limit=top_k,
                with_payload=True,
            ).points

        # Deduplicate by page_id
        seen: set[str] = set()
        ranked_pages: list[str] = []
        for hit in search_results:
            if hit.payload is None or "page_id" not in hit.payload:
                continue
            pid = hit.payload["page_id"]
            if pid not in seen:
                seen.add(pid)
                ranked_pages.append(pid)

        rr = reciprocal_rank(ranked_pages, expected_pages)
        ndcg = ndcg_at_k(ranked_pages, relevance_map, k=10)
        p5 = precision_at_k(ranked_pages, expected_pages, k=5)

        # Content relevance of best chunk
        best_rel = 0.0
        for hit in search_results:
            payload = hit.payload or {}
            chunk_text = payload.get("text", "")
            rel = calculate_relevance_score(chunk_text, gt_text, keywords)
            if rel > best_rel:
                best_rel = rel

        mrr_inputs.append((ranked_pages, expected_pages))
        ndcg_inputs.append((ranked_pages, relevance_map))
        p5_inputs.append((ranked_pages, expected_pages))

        entry = {
            "id": qa["id"],
            "question": question,
            "expected_pages": sorted(expected_pages),
            "difficulty": difficulty,
            "mode": mode,
            "ranked_pages": ranked_pages[:10],
            "rr": round(rr, 4),
            "ndcg_at_10": round(ndcg, 4),
            "p_at_5": round(p5, 4),
            "top1_content_relevance": round(best_rel, 4),
            "hit_in_top_k": bool(expected_pages & set(ranked_pages)),
        }
        per_query.append(entry)

        if verbose:
            hit_str = "HIT" if entry["hit_in_top_k"] else "MISS"
            print(
                f"  [{mode:6s}] [{i+1:2d}/{len(qa_pairs)}] "
                f"RR={rr:.3f} NDCG={ndcg:.3f} P@5={p5:.3f} {hit_str}  {qa['id']}"
            )

    # Aggregate
    agg_mrr = mean_reciprocal_rank(mrr_inputs)
    agg_ndcg = mean_ndcg_at_k(ndcg_inputs, k=10)
    agg_p5 = mean_precision_at_k(p5_inputs, k=5)

    rr_vals = [q["rr"] for q in per_query]
    ndcg_vals = [q["ndcg_at_10"] for q in per_query]
    p5_vals = [q["p_at_5"] for q in per_query]
    hits = sum(1 for q in per_query if q["hit_in_top_k"])
    total = len(per_query)

    return {
        "mode": mode,
        "aggregate_metrics": {
            "mrr": {"mean": round(agg_mrr, 4), "std": round(_std(rr_vals), 4)},
            "ndcg_at_10": {"mean": round(agg_ndcg, 4), "std": round(_std(ndcg_vals), 4)},
            "precision_at_5": {"mean": round(agg_p5, 4), "std": round(_std(p5_vals), 4)},
            "hit_rate": round(hits / total, 4) if total else 0.0,
        },
        "summary": {
            "total_queries": total,
            "hits": hits,
            "misses": total - hits,
        },
        "per_query": per_query,
    }


def run_hybrid_vs_dense(
    config: ExperimentConfig,
    *,
    verbose: bool = False,
) -> dict:
    """Run both dense and hybrid retrieval and compare.

    Creates a Qdrant collection with both dense vectors (embedding model)
    and sparse vectors (BM25-weighted term frequencies).  Dense mode queries
    only the dense vectors; hybrid mode uses Reciprocal Rank Fusion (RRF)
    to combine dense and sparse results.

    Args:
        config: Experiment configuration.
        verbose: Print per-query results.

    Returns:
        Comparison result dict.
    """
    # Load corpus
    gt_path = config.ground_truth_file
    if not Path(gt_path).is_absolute():
        gt_path = EVAL_ROOT / gt_path
    gt_data = load_ground_truth(gt_path)
    qa_pairs = gt_data["qa_pairs"]

    corpus_chunks = load_corpus(
        corpus_source="preprocessed",
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
    )

    if not corpus_chunks:
        raise RuntimeError("No corpus chunks loaded")

    # Embed corpus (dense)
    provider = create_provider(config)
    logger.info("Embedding %d chunks with %s", len(corpus_chunks), provider.model_name)

    chunk_texts = [c["text"] for c in corpus_chunks]
    t_start = time.monotonic()
    chunk_embeddings = _embed_in_batches(provider, chunk_texts)
    embed_time = time.monotonic() - t_start

    # Build BM25 sparse vectors
    logger.info("Building BM25 sparse vectors for %d chunks...", len(chunk_texts))
    vocab = build_vocabulary(chunk_texts)
    idf = compute_idf(chunk_texts, vocab)
    avgdl = sum(len(_tokenize(t)) for t in chunk_texts) / len(chunk_texts)
    logger.info(
        "Vocabulary: %d terms, avg document length: %.1f tokens",
        len(vocab), avgdl,
    )

    sparse_vectors = [
        text_to_sparse_vector(text, vocab, idf, avgdl=avgdl)
        for text in chunk_texts
    ]

    # Create temp Qdrant collection with both dense + sparse vectors
    collection_name = (
        f"{config.collection_prefix}hybrid_dense_{uuid.uuid4().hex[:6]}"
    )
    qdrant = _get_qdrant_client()

    try:
        qdrant.create_collection(
            collection_name=collection_name,
            vectors_config={
                "dense": VectorParams(
                    size=config.dimensions,
                    distance=Distance.COSINE,
                ),
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams(),
            },
        )

        points = [
            PointStruct(
                id=i,
                vector={
                    "dense": chunk_embeddings[i],
                    "sparse": sparse_vectors[i],
                },
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

        # Run DENSE evaluation (vector search only)
        logger.info("Running dense retrieval evaluation...")
        dense_result = _evaluate_dense(
            qdrant, collection_name, provider, qa_pairs,
            top_k=config.top_k, verbose=verbose,
        )

        # Run HYBRID evaluation (dense + BM25 sparse with RRF fusion)
        logger.info("Running hybrid retrieval evaluation (dense + BM25 RRF)...")
        hybrid_result = _evaluate_hybrid(
            qdrant, collection_name, provider, qa_pairs,
            vocab=vocab, idf=idf, avgdl=avgdl,
            top_k=config.top_k, verbose=verbose,
        )

    finally:
        try:
            qdrant.delete_collection(collection_name)
            logger.info("Deleted temporary collection: %s", collection_name)
        except Exception as exc:
            logger.warning("Failed to delete %s: %s", collection_name, exc)

    result = {
        "experiment": {
            "name": config.name,
            "type": config.experiment_type,
            "thesis_id": config.thesis_id,
            "model": config.model,
            "chunk_size": config.chunk_size,
            "top_k": config.top_k,
            "config_hash": config.config_hash,
            "code_version": _get_git_version(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sparse_method": "BM25 (k1=1.5, b=0.75)",
            "fusion_method": "Reciprocal Rank Fusion (RRF)",
            "vocabulary_size": len(vocab),
            "avg_doc_length": round(avgdl, 1),
        },
        "comparison": {
            "dense": dense_result["aggregate_metrics"],
            "hybrid": hybrid_result["aggregate_metrics"],
        },
        "performance": {
            "corpus_chunks": len(corpus_chunks),
            "embedding_time_seconds": round(embed_time, 2),
        },
        "dense": dense_result,
        "hybrid": hybrid_result,
    }

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "J6 Hybrid vs Dense Retrieval — compare dense-only and hybrid "
            "(dense + BM25) retrieval on the same collection."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m evaluation.scripts.eval_hybrid_vs_dense\n"
            "  python -m evaluation.scripts.eval_hybrid_vs_dense --verbose\n"
        ),
    )
    parser.add_argument(
        "--config",
        default=str(EVAL_ROOT / "experiments" / "hybrid_vs_dense.yaml"),
        help="Path to experiment YAML config",
    )
    parser.add_argument(
        "--output-dir",
        default=str(EVAL_ROOT / "results"),
        help="Directory for result JSON files",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print per-query results to stdout",
    )
    return parser


def _metric_mean(m: dict | float) -> float:
    return m["mean"] if isinstance(m, dict) else m


def main() -> None:
    """Entry point for hybrid vs dense evaluation."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = _build_parser()
    args = parser.parse_args()

    config = load_experiment_config(args.config)
    logger.info("Experiment: %s (thesis_id=%s)", config.name, config.thesis_id)

    try:
        result = run_hybrid_vs_dense(config, verbose=args.verbose)
    except Exception as exc:
        logger.error("Evaluation failed: %s", exc)
        sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = output_dir / f"hybrid_vs_dense_{timestamp}.json"

    with open(out_file, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)

    # Print comparison table
    comp = result["comparison"]
    print("\n" + "=" * 60)
    print("  J6 — Hybrid vs Dense Retrieval Comparison")
    print("=" * 60)
    print(f"\n  {'Mode':8s} | {'MRR':>8s} | {'NDCG@10':>8s} | {'P@5':>8s} | {'Hit Rate':>8s}")
    print(f"  {'-'*8} | {'-'*8} | {'-'*8} | {'-'*8} | {'-'*8}")
    for mode_name in ("dense", "hybrid"):
        m = comp[mode_name]
        print(
            f"  {mode_name:8s} | {_metric_mean(m['mrr']):>8.4f} "
            f"| {_metric_mean(m['ndcg_at_10']):>8.4f} "
            f"| {_metric_mean(m['precision_at_5']):>8.4f} "
            f"| {m['hit_rate']:>7.1%}"
        )
    print(f"\n  Output: {out_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()
