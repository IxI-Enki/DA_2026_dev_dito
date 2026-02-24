"""Generate J4 and J6 thesis figures from evaluation result JSONs.

Usage (from repo root):
  python -m evaluation.scripts.eval_visualize_j4_j6
  python -m evaluation.scripts.eval_visualize_j4_j6 --results-dir evaluation/results --output-dir evaluation/figures --dpi 300
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


def _find_latest(directory: Path, pattern: str) -> Path | None:
    candidates = sorted(directory.glob(pattern), reverse=True)
    return candidates[0] if candidates else None


def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def run_j4(viz: EvaluationVisualizer, results_dir: Path) -> None:
    """J4: Chunk comparison bar chart from chunk_comparison_*.json."""
    result_file = _find_latest(results_dir, "chunk_comparison_*.json")
    if not result_file:
        logger.warning("J4: No chunk_comparison_*.json found; skipping bar chart (FR-013)")
        return
    data = _load_json(result_file)
    chunk_sizes = data.get("chunk_sizes", [])
    if not chunk_sizes:
        logger.warning("J4: chunk_sizes empty in %s; skipping", result_file.name)
        return
    path = viz.chunk_comparison_bar(
        chunk_sizes,
        metrics=["mrr", "ndcg_at_10"],
        title="MRR and NDCG@10 by chunk size",
        name="j4_chunk_comparison_bar",
    )
    logger.info("J4 bar chart: %s", path)


def run_j6(viz: EvaluationVisualizer, results_dir: Path) -> None:
    """J6: Hybrid vs Dense bar chart and scatter from hybrid_vs_dense_*.json."""
    result_file = _find_latest(results_dir, "hybrid_vs_dense_*.json")
    if not result_file:
        logger.warning("J6: No hybrid_vs_dense_*.json found; skipping (FR-013)")
        return
    data = _load_json(result_file)
    comparison = data.get("comparison", {})
    dense = comparison.get("dense", {})
    hybrid = comparison.get("hybrid", {})
    if not dense or not hybrid:
        logger.warning("J6: comparison.dense or comparison.hybrid missing; skipping bar")
        return
    path_bar = viz.hybrid_vs_dense_bar(
        dense,
        hybrid,
        title="Dense vs Hybrid retrieval",
        name="j6_hybrid_vs_dense_bar",
    )
    logger.info("J6 bar chart: %s", path_bar)

    dense_block = data.get("dense", {})
    hybrid_block = data.get("hybrid", {})
    dense_pq = dense_block.get("per_query", [])
    hybrid_pq = hybrid_block.get("per_query", [])
    if not dense_pq or not hybrid_pq:
        logger.warning("J6: per_query missing; skipping scatter (show bar only)")
        return
    dense_by_id = {q.get("id"): q.get("rr", q.get("mrr", 0.0)) for q in dense_pq if q.get("id")}
    hybrid_by_id = {q.get("id"): q.get("rr", q.get("mrr", 0.0)) for q in hybrid_pq if q.get("id")}
    try:
        path_scatter = viz.hybrid_vs_dense_scatter(
            dense_by_id,
            hybrid_by_id,
            title="Dense vs Hybrid MRR per query",
            name="j6_hybrid_vs_dense_scatter",
        )
        logger.info("J6 scatter: %s", path_scatter)
    except ValueError as e:
        logger.warning("J6 scatter skipped: %s", e)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="Generate J4/J6 evaluation figures")
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=EVAL_ROOT / "results",
        help="Directory containing chunk_comparison_*.json and hybrid_vs_dense_*.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=EVAL_ROOT / "figures",
        help="Output directory for PNG figures",
    )
    parser.add_argument("--dpi", type=int, default=300, help="DPI for PNG (default 300)")
    args = parser.parse_args()

    results_dir = (
        args.results_dir
        if args.results_dir.is_absolute()
        else (Path.cwd() / args.results_dir).resolve()
    )
    output_dir = (
        args.output_dir
        if args.output_dir.is_absolute()
        else (Path.cwd() / args.output_dir).resolve()
    )

    if not results_dir.exists():
        logger.error("Results directory not found: %s", results_dir)
        return 1

    viz = EvaluationVisualizer(output_dir=output_dir, fmt="png", dpi=args.dpi)
    run_j4(viz, results_dir)
    run_j6(viz, results_dir)
    logger.info("Figures written to %s", output_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
