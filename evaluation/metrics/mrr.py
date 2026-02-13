"""Mean Reciprocal Rank (MRR) for retrieval evaluation.

MRR measures where the first relevant result appears in the ranked list.
Score = 1/rank of first relevant result, averaged over all queries.
Used for FF1 (Keyword vs Semantic Search) thesis table.
"""

from __future__ import annotations


def reciprocal_rank(ranked_results: list[str], relevant: set[str]) -> float:
    """Compute reciprocal rank for a single query.

    Args:
        ranked_results: Ordered list of retrieved document IDs (best first).
        relevant: Set of document IDs that are relevant for this query.

    Returns:
        1/rank of the first relevant result, or 0.0 if none found.
    """
    for rank, doc_id in enumerate(ranked_results, start=1):
        if doc_id in relevant:
            return 1.0 / rank
    return 0.0


def mean_reciprocal_rank(
    queries: list[tuple[list[str], set[str]]],
) -> float:
    """Compute Mean Reciprocal Rank over multiple queries.

    Args:
        queries: List of (ranked_results, relevant_set) tuples.

    Returns:
        MRR score (0.0 to 1.0). Returns 0.0 for empty input.
    """
    if not queries:
        return 0.0
    total = sum(reciprocal_rank(ranked, rel) for ranked, rel in queries)
    return total / len(queries)
