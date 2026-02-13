"""Normalized Discounted Cumulative Gain (NDCG@k) for retrieval evaluation.

NDCG measures ranking quality using graded relevance scores.
Higher-ranked relevant documents contribute more to the score.
Used for FF3 (Embedding Model Comparison) and J4/J6 thesis tables.
"""

from __future__ import annotations

import math


def _dcg_at_k(ranked_results: list[str], relevance_map: dict[str, int], k: int) -> float:
    """Compute Discounted Cumulative Gain at position k.

    Args:
        ranked_results: Ordered list of retrieved document IDs (best first).
        relevance_map: Mapping of document ID to relevance score (0-3).
        k: Number of top results to consider.

    Returns:
        DCG score.
    """
    dcg = 0.0
    for i, doc_id in enumerate(ranked_results[:k]):
        rel = relevance_map.get(doc_id, 0)
        # Standard DCG formula: (2^rel - 1) / log2(i + 2)
        dcg += (2**rel - 1) / math.log2(i + 2)
    return dcg


def _ideal_dcg_at_k(relevance_map: dict[str, int], k: int) -> float:
    """Compute Ideal DCG (best possible ranking) at position k.

    Args:
        relevance_map: Mapping of document ID to relevance score (0-3).
        k: Number of top results to consider.

    Returns:
        IDCG score.
    """
    # Sort relevance scores in descending order
    sorted_rels = sorted(relevance_map.values(), reverse=True)[:k]
    idcg = 0.0
    for i, rel in enumerate(sorted_rels):
        idcg += (2**rel - 1) / math.log2(i + 2)
    return idcg


def ndcg_at_k(
    ranked_results: list[str],
    relevance_map: dict[str, int],
    k: int = 10,
) -> float:
    """Compute NDCG@k for a single query.

    Args:
        ranked_results: Ordered list of retrieved document IDs (best first).
        relevance_map: Mapping of document ID to graded relevance score (0-3).
            Documents not in the map are treated as relevance 0.
        k: Number of top results to consider.

    Returns:
        NDCG score (0.0 to 1.0). Returns 0.0 if no relevant documents exist.
    """
    if k <= 0 or not relevance_map:
        return 0.0
    idcg = _ideal_dcg_at_k(relevance_map, k)
    if idcg == 0.0:
        return 0.0
    dcg = _dcg_at_k(ranked_results, relevance_map, k)
    return dcg / idcg


def mean_ndcg_at_k(
    queries: list[tuple[list[str], dict[str, int]]],
    k: int = 10,
) -> float:
    """Compute mean NDCG@k over multiple queries.

    Args:
        queries: List of (ranked_results, relevance_map) tuples.
        k: Number of top results to consider.

    Returns:
        Mean NDCG@k score (0.0 to 1.0). Returns 0.0 for empty input.
    """
    if not queries:
        return 0.0
    total = sum(ndcg_at_k(ranked, rel_map, k) for ranked, rel_map in queries)
    return total / len(queries)
