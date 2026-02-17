"""Per-difficulty breakdown and category analysis for evaluation results.

Uses per_query results and optional difficulty field from ground truth.
"""

from __future__ import annotations

from typing import Any


def breakdown_by_difficulty(
    per_query: list[dict[str, Any]],
    difficulty_key: str = "difficulty",
    metric_keys: tuple[str, ...] = ("rr", "ndcg_at_10", "p_at_5"),
) -> dict[str, dict[str, Any]]:
    """Compute per-difficulty metrics from per_query results.

    Args:
        per_query: List of per-query result dicts (must include difficulty_key).
        difficulty_key: Key for difficulty level (easy/medium/hard).
        metric_keys: Per-query metric keys to aggregate.

    Returns:
        Dict mapping difficulty -> {count, <metric>: mean, hit_rate, ...}.
    """
    by_diff: dict[str, list[dict[str, Any]]] = {}
    for q in per_query:
        diff = q.get(difficulty_key) or "unknown"
        by_diff.setdefault(diff, []).append(q)

    out: dict[str, dict[str, Any]] = {}
    for diff, subset in sorted(by_diff.items()):
        n = len(subset)
        if n == 0:
            continue
        entry: dict[str, Any] = {"count": n}
        for key in metric_keys:
            if key in subset[0]:
                vals = [q[key] for q in subset]
                entry[key] = round(sum(vals) / n, 4)
        hit_key = "hit_in_top_k"
        if hit_key in subset[0]:
            hits = sum(1 for q in subset if q.get(hit_key, False))
            entry["hit_rate"] = round(hits / n, 4)
        out[diff] = entry
    return out
