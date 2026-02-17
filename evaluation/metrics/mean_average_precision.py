"""Mean Average Precision (MAP) for retrieval evaluation.

MAP averages per-query Average Precision: at each rank where a relevant
document appears, precision at that rank is summed and normalized by
the number of relevant documents. Used for thesis retrieval tables (US8).
"""

from __future__ import annotations


def average_precision(
    ranked_results: list[str],
    relevant: set[str],
) -> float:
    """Compute Average Precision for a single query.

    Args:
        ranked_results: Ordered list of retrieved document IDs (best first).
        relevant: Set of document IDs that are relevant for this query.

    Returns:
        Average Precision (0.0 to 1.0). Returns 0.0 if no relevant docs.
    """
    if not relevant:
        return 0.0
    precision_sum = 0.0
    num_relevant_seen = 0
    for i, doc_id in enumerate(ranked_results):
        if doc_id in relevant:
            num_relevant_seen += 1
            precision_at_i = num_relevant_seen / (i + 1)
            precision_sum += precision_at_i
    return precision_sum / len(relevant)


def mean_average_precision(
    queries: list[tuple[list[str], set[str]]],
) -> float:
    """Compute Mean Average Precision over multiple queries.

    Args:
        queries: List of (ranked_results, relevant_set) tuples.

    Returns:
        MAP score (0.0 to 1.0). Returns 0.0 for empty input.
    """
    if not queries:
        return 0.0
    total = sum(average_precision(ranked, rel) for ranked, rel in queries)
    return total / len(queries)
