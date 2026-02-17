"""Single-run descriptive statistics and bootstrap CIs for evaluation results.

Usage:
  python -m evaluation.scripts.eval_statistics --results path/to/result.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from evaluation.statistics.category_analysis import breakdown_by_difficulty
from evaluation.statistics.statistical_analysis import (
    PER_QUERY_METRIC_KEYS,
    StatisticalAnalyzer,
)

logger = logging.getLogger(__name__)


def main() -> None:
    """Entry point for single-run statistics."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Descriptive statistics and 95%% bootstrap CIs for one result JSON",
    )
    parser.add_argument(
        "results",
        type=Path,
        help="Path to result JSON (e.g. evaluation/results/model_xyz.json)",
    )
    parser.add_argument(
        "--n-bootstrap",
        type=int,
        default=1000,
        help="Bootstrap iterations for CI (default: 1000)",
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=0.95,
        help="Confidence level (default: 0.95)",
    )
    args = parser.parse_args()

    path = Path(args.results)
    if not path.exists():
        logger.error("Results file not found: %s", path)
        sys.exit(1)

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    per_query = data.get("per_query", [])
    if not per_query:
        logger.error("No per_query in result JSON")
        sys.exit(1)

    analyzer = StatisticalAnalyzer()
    print(f"\nDescriptive stats (n={len(per_query)}):")
    print("-" * 50)
    for key, metric_name in PER_QUERY_METRIC_KEYS:
        if key not in per_query[0]:
            continue
        scores = [q[key] for q in per_query]
        stats_dict = analyzer.descriptive_stats(scores)
        ci = analyzer.bootstrap_ci(
            scores,
            n_iterations=args.n_bootstrap,
            confidence=args.confidence,
        )
        print(
            f"  {metric_name:18s}: mean={stats_dict['mean']:.4f} "
            f"median={stats_dict['median']:.4f} std={stats_dict['std']:.4f}"
        )
        print(f"    {args.confidence:.0%} CI: [{ci.ci_lower:.4f}, {ci.ci_upper:.4f}]")

    by_diff = breakdown_by_difficulty(per_query)
    if by_diff:
        print("\nBy difficulty:")
        for diff, metrics in sorted(by_diff.items()):
            print(f"  {diff:8s}: n={metrics['count']} ", end="")
            for k, v in metrics.items():
                if k != "count" and isinstance(v, (int, float)):
                    print(f" {k}={v:.4f}", end="")
            print()

    print()
    return None


if __name__ == "__main__":
    main()
