"""Precision@k for retrieval evaluation.

Precision@k measures the fraction of retrieved documents in the top-k
that are relevant. Used for FF1 thesis table (P@5).
"""

from __future__ import annotations


def precision_at_k(
    ranked_results: list[str],
    relevant: set[str],
    k: int = 5,
) -> float:
    """Compute Precision@k for a single query.

    Args:
        ranked_results: Ordered list of retrieved document IDs (best first).
        relevant: Set of document IDs that are relevant for this query.
        k: Number of top results to consider.

    Returns:
        Fraction of top-k results that are relevant (0.0 to 1.0).
    """
    if k <= 0:
        return 0.0
    top_k = ranked_results[:k]
    if not top_k:
        return 0.0
    relevant_in_top_k = sum(1 for doc_id in top_k if doc_id in relevant)
    return relevant_in_top_k / k


def mean_precision_at_k(
    queries: list[tuple[list[str], set[str]]],
    k: int = 5,
) -> float:
    """Compute mean Precision@k over multiple queries.

    Args:
        queries: List of (ranked_results, relevant_set) tuples.
        k: Number of top results to consider.

    Returns:
        Mean P@k score (0.0 to 1.0). Returns 0.0 for empty input.
    """
    if not queries:
        return 0.0
    total = sum(precision_at_k(ranked, rel, k) for ranked, rel in queries)
    return total / len(queries)
