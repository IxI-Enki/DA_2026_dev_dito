"""A/B comparison of two evaluation result JSONs with p-values and CIs.

Usage:
  python -m evaluation.scripts.eval_compare --baseline a.json --candidate b.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from evaluation.statistics.statistical_analysis import StatisticalAnalyzer

logger = logging.getLogger(__name__)


def main() -> None:
    """Entry point for A/B comparison."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Compare two result JSONs: Bootstrap CI, paired test, Cohen's d",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        required=True,
        help="Path to baseline result JSON",
    )
    parser.add_argument(
        "--candidate",
        type=Path,
        required=True,
        help="Path to candidate result JSON",
    )
    args = parser.parse_args()

    base_path = Path(args.baseline)
    cand_path = Path(args.candidate)
    if not base_path.exists():
        logger.error("Baseline not found: %s", base_path)
        sys.exit(1)
    if not cand_path.exists():
        logger.error("Candidate not found: %s", cand_path)
        sys.exit(1)

    analyzer = StatisticalAnalyzer()
    try:
        results = analyzer.compare_configurations(base_path, cand_path)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error("%s", e)
        sys.exit(1)

    print("\nComparison (baseline vs candidate):")
    print("-" * 70)
    print(
        f"  {'Metric':18s} {'Baseline':>10s} {'Candidate':>10s} "
        f"{'Diff':>8s} {'p-value':>8s} {'Cohen d':>8s} {'Effect':12s} {'Sig':>5s}"
    )
    print("-" * 70)
    for r in results:
        sig = "yes" if r.significant else "no"
        print(
            f"  {r.metric:18s} {r.baseline_mean:10.4f} {r.candidate_mean:10.4f} "
            f"{r.difference:+8.4f} {r.p_value:8.4f} {r.effect_size:+8.4f} "
            f"{r.effect_interpretation:12s} {sig:>5s}"
        )
    print()
    return None


if __name__ == "__main__":
    main()
