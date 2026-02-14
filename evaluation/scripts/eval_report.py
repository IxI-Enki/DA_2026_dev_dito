"""Generate structured Markdown + JSON evaluation reports from result JSONs.

Usage:
  python -m evaluation.scripts.eval_report --results evaluation/results/
  python -m evaluation.scripts.eval_report --results evaluation/results/ --ragas-scores ragas_scores.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from evaluation.config import EVAL_ROOT
from evaluation.reports import ReportGenerator

logger = logging.getLogger(__name__)


def main() -> int:
    """Entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Generate evaluation report from result JSONs")
    parser.add_argument(
        "--results",
        type=Path,
        default=EVAL_ROOT / "results",
        help="Directory containing result JSON files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=EVAL_ROOT / "reports_output",
        help="Output directory for generated report files",
    )
    parser.add_argument(
        "--ragas-scores",
        type=Path,
        default=None,
        help="Optional JSON file with RAGAS scores",
    )
    args = parser.parse_args()

    results_dir = Path(args.results)
    if not results_dir.is_absolute():
        results_dir = (Path.cwd() / results_dir).resolve()
    if not results_dir.exists():
        logger.error("Results directory not found: %s", results_dir)
        return 1

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = (Path.cwd() / output_dir).resolve()

    ragas_scores = None
    if args.ragas_scores and args.ragas_scores.exists():
        with open(args.ragas_scores, encoding="utf-8") as f:
            ragas_scores = json.load(f)

    try:
        gen = ReportGenerator(output_dir=output_dir)
        md_path, json_path = gen.generate(results_dir, ragas_scores=ragas_scores)
    except FileNotFoundError as e:
        logger.error("%s", e)
        return 1

    print(f"Markdown report: {md_path}")
    print(f"JSON report:     {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
