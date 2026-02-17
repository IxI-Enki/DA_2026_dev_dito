"""Recall@K for retrieval evaluation.

Recall@K is the fraction of relevant documents that appear in the top-k results.
Used alongside Precision@K for thesis retrieval tables (US8).
"""

from __future__ import annotations


def recall_at_k(
    ranked_results: list[str],
    relevant: set[str],
    k: int = 10,
) -> float:
    """Compute Recall@K for a single query.

    Args:
        ranked_results: Ordered list of retrieved document IDs (best first).
        relevant: Set of document IDs that are relevant for this query.
        k: Number of top results to consider.

    Returns:
        Fraction of relevant documents found in top-k (0.0 to 1.0).
        Returns 0.0 if relevant is empty.
    """
    if not relevant or k <= 0:
        return 0.0
    top_k = ranked_results[:k]
    found = sum(1 for doc_id in top_k if doc_id in relevant)
    return found / len(relevant)


def mean_recall_at_k(
    queries: list[tuple[list[str], set[str]]],
    k: int = 10,
) -> float:
    """Compute mean Recall@K over multiple queries.

    Args:
        queries: List of (ranked_results, relevant_set) tuples.
        k: Number of top results to consider.

    Returns:
        Mean Recall@K score (0.0 to 1.0). Returns 0.0 for empty input.
    """
    if not queries:
        return 0.0
    total = sum(recall_at_k(ranked, rel, k) for ranked, rel in queries)
    return total / len(queries)
