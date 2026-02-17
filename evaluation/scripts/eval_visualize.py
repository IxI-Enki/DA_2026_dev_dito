"""Generate thesis-quality charts from evaluation result JSONs.

Usage:
  python -m evaluation.scripts.eval_visualize --results-dir evaluation/results/
  python -m evaluation.scripts.eval_visualize --results-dir evaluation/results/ --format svg --dpi 300
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from evaluation.config import EVAL_ROOT
from evaluation.visualization import EvaluationVisualizer

logger = logging.getLogger(__name__)


def _load_results(results_dir: Path) -> dict[str, dict]:
    """Load all JSON result files from a directory. Returns {name: data}."""
    results: dict[str, dict] = {}
    for p in sorted(results_dir.glob("*.json")):
        try:
            with open(p, encoding="utf-8") as f:
                results[p.stem] = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Skipped %s: %s", p.name, e)
    return results


def _aggregate_from_per_query(data: dict) -> dict[str, float]:
    """Compute aggregate metric means from per_query list."""
    per_query = data.get("per_query", [])
    if not per_query:
        return data.get("aggregate_metrics", {})
    keys = [k for k in per_query[0] if isinstance(per_query[0].get(k), (int, float))]
    agg: dict[str, float] = {}
    for k in keys:
        vals = [row[k] for row in per_query if isinstance(row.get(k), (int, float))]
        agg[k] = sum(vals) / len(vals) if vals else 0.0
    return agg


def _per_query_scores(data: dict) -> dict[str, list[float]]:
    """Extract per-query scores dict from result data."""
    per_query = data.get("per_query", [])
    if not per_query:
        return {}
    keys = [k for k in per_query[0] if isinstance(per_query[0].get(k), (int, float))]
    scores: dict[str, list[float]] = {k: [] for k in keys}
    for row in per_query:
        for k in keys:
            v = row.get(k)
            if isinstance(v, (int, float)):
                scores[k].append(float(v))
    return scores


def main() -> int:
    """Entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Generate evaluation charts from result JSONs")
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=EVAL_ROOT / "results",
        help="Directory containing result JSON files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=EVAL_ROOT / "charts",
        help="Output directory for generated charts",
    )
    parser.add_argument("--format", type=str, default="png", choices=["png", "svg"], help="Chart format (default: png)")
    parser.add_argument("--dpi", type=int, default=300, help="DPI for raster charts (default: 300)")
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    if not results_dir.is_absolute():
        results_dir = (Path.cwd() / results_dir).resolve()
    if not results_dir.exists():
        logger.error("Results directory not found: %s", results_dir)
        return 1

    all_results = _load_results(results_dir)
    if not all_results:
        logger.error("No JSON result files found in %s", results_dir)
        return 1

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = (Path.cwd() / output_dir).resolve()

    viz = EvaluationVisualizer(output_dir=output_dir, fmt=args.format, dpi=args.dpi)

    # Aggregate results for radar + bar
    aggregates: dict[str, dict[str, float]] = {}
    for name, data in all_results.items():
        agg = _aggregate_from_per_query(data)
        if agg:
            aggregates[name] = agg

    if aggregates:
        first_metrics = list(next(iter(aggregates.values())).keys())
        if len(aggregates) >= 1 and len(first_metrics) >= 3:
            try:
                p = viz.radar_chart(aggregates, title="Model Comparison (Radar)")
                logger.info("Radar chart: %s", p)
            except Exception as e:
                logger.warning("Radar chart failed: %s", e)
        if len(aggregates) >= 1:
            try:
                p = viz.bar_comparison(aggregates, title="Model Comparison (Bar)")
                logger.info("Bar chart: %s", p)
            except Exception as e:
                logger.warning("Bar chart failed: %s", e)

    # Box plot from first result with per_query
    for name, data in all_results.items():
        pqs = _per_query_scores(data)
        if pqs:
            try:
                p = viz.box_plot(pqs, title=f"Score Distributions ({name})")
                logger.info("Box plot: %s", p)
            except Exception as e:
                logger.warning("Box plot failed: %s", e)
            break

    # Heatmap: compute correlation from first result with >= 2 metrics
    for name, data in all_results.items():
        pqs = _per_query_scores(data)
        metric_names = list(pqs.keys())
        if len(metric_names) >= 2:
            corr: dict[str, dict[str, float]] = {}
            for m1 in metric_names:
                corr[m1] = {}
                for m2 in metric_names:
                    v1, v2 = pqs[m1], pqs[m2]
                    n = min(len(v1), len(v2))
                    if n < 2:
                        corr[m1][m2] = 0.0
                        continue
                    mean1 = sum(v1[:n]) / n
                    mean2 = sum(v2[:n]) / n
                    cov = sum((v1[i] - mean1) * (v2[i] - mean2) for i in range(n)) / n
                    std1 = (sum((x - mean1) ** 2 for x in v1[:n]) / n) ** 0.5
                    std2 = (sum((x - mean2) ** 2 for x in v2[:n]) / n) ** 0.5
                    corr[m1][m2] = cov / (std1 * std2) if std1 > 0 and std2 > 0 else 0.0
            try:
                p = viz.heatmap(corr, title=f"Metric Correlations ({name})")
                logger.info("Heatmap: %s", p)
            except Exception as e:
                logger.warning("Heatmap failed: %s", e)
            break

    logger.info("Charts saved to %s", output_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
