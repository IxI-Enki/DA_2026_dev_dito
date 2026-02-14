"""Hit Rate for retrieval evaluation.

Hit Rate is the fraction of queries that have at least one relevant
document in the top-k results. Binary per-query metric. US8.
"""

from __future__ import annotations


def hit_at_k(
    ranked_results: list[str],
    relevant: set[str],
    k: int = 10,
) -> int:
    """Return 1 if at least one relevant doc is in top-k, else 0.

    Args:
        ranked_results: Ordered list of retrieved document IDs (best first).
        relevant: Set of document IDs that are relevant for this query.
        k: Number of top results to consider.

    Returns:
        1 if any relevant in top-k, 0 otherwise.
    """
    if not relevant or k <= 0:
        return 0
    top_k = ranked_results[:k]
    return 1 if any(doc_id in relevant for doc_id in top_k) else 0


def hit_rate(
    queries: list[tuple[list[str], set[str]]],
    k: int = 10,
) -> float:
    """Compute Hit Rate over multiple queries.

    Args:
        queries: List of (ranked_results, relevant_set) tuples.
        k: Number of top results to consider.

    Returns:
        Fraction of queries with at least one relevant in top-k (0.0 to 1.0).
        Returns 0.0 for empty input.
    """
    if not queries:
        return 0.0
    hits = sum(hit_at_k(ranked, rel, k) for ranked, rel in queries)
    return hits / len(queries)
