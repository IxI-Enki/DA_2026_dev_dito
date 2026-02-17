"""Chunk size parametric evaluation for thesis table J4.

Compares 256/512/1024 token chunks on the same embedding model and
query set.  Reuses the model comparison evaluation pipeline since the
only variable is ``chunk_size`` in the experiment config.

Usage::

    python -m evaluation.scripts.eval_chunk_size --config experiments/chunk_512.yaml
    python -m evaluation.scripts.eval_chunk_size --compare
    python -m evaluation.scripts.eval_chunk_size --compare --verbose

Thesis-ID: J4
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

EVAL_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = EVAL_ROOT.parent

sys.path.insert(0, str(REPO_ROOT))

from evaluation.config import load_experiment_config
from evaluation.scripts.eval_model_comparison import (
    _get_git_version,
    _metric_mean,
    _print_summary,
    run_model_evaluation,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "J4 Chunk Size Evaluation — compare 256/512/1024 token chunks "
            "on the same embedding model.  Computes NDCG@10, MRR, P@5."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m evaluation.scripts.eval_chunk_size --config experiments/chunk_512.yaml\n"
            "  python -m evaluation.scripts.eval_chunk_size --compare\n"
            "  python -m evaluation.scripts.eval_chunk_size --compare --verbose\n"
        ),
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to a single chunk experiment YAML config",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Run all chunk_*.yaml configs and produce comparison table",
    )
    parser.add_argument(
        "--output-dir",
        default=str(EVAL_ROOT / "results"),
        help="Directory for result JSON files (default: evaluation/results/)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print per-query results to stdout",
    )
    return parser


def _print_chunk_comparison_table(results: list[dict]) -> None:
    """Print a Markdown comparison table for chunk sizes."""
    print("\n## J4 — Chunk Size Impact\n")
    print("| Chunk Size | Overlap | Chunks | MRR | NDCG@10 | P@5 | Hit Rate |")
    print("|------------|---------|--------|-----|---------|-----|----------|")
    for r in results:
        exp = r["experiment"]
        agg = r["aggregate_metrics"]
        perf = r["performance"]
        print(
            f"| {exp['chunk_size']} | {exp.get('chunk_overlap', 50)} "
            f"| {perf['corpus_chunks']} "
            f"| {_metric_mean(agg['mrr']):.4f} | {_metric_mean(agg['ndcg_at_10']):.4f} "
            f"| {_metric_mean(agg['precision_at_5']):.4f} | {agg['hit_rate']:.1%} |"
        )


def main() -> None:
    """Entry point for chunk size evaluation."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = _build_parser()
    args = parser.parse_args()

    if not args.config and not args.compare:
        parser.error("Either --config or --compare is required")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if args.compare:
        experiments_dir = EVAL_ROOT / "experiments"
        config_files = sorted(experiments_dir.glob("chunk_*.yaml"))
        if not config_files:
            logger.error("No chunk_*.yaml configs found in %s", experiments_dir)
            sys.exit(1)

        logger.info("Found %d chunk configs for comparison", len(config_files))
        all_results: list[dict] = []

        print("=" * 60)
        print("  J4 Chunk Size Parametric Evaluation")
        print("=" * 60)

        for cf in config_files:
            config = load_experiment_config(cf)
            logger.info("Running: %s (chunk_size=%d)", config.name, config.chunk_size)

            try:
                result = run_model_evaluation(
                    config, verbose=args.verbose, corpus_source="preprocessed",
                )
                # Add chunk_overlap to experiment for display
                result["experiment"]["chunk_overlap"] = config.chunk_overlap
                all_results.append(result)
                _print_summary(result)

                out_file = output_dir / f"chunk_{config.chunk_size}_{timestamp}.json"
                with open(out_file, "w", encoding="utf-8") as fh:
                    json.dump(result, fh, indent=2, ensure_ascii=False)
                logger.info("Written: %s", out_file)

            except Exception as exc:
                logger.error("Failed for chunk_size=%d: %s", config.chunk_size, exc)
                continue

        if all_results:
            _print_chunk_comparison_table(all_results)

            comparison_file = output_dir / f"chunk_comparison_{timestamp}.json"
            with open(comparison_file, "w", encoding="utf-8") as fh:
                json.dump(
                    {
                        "thesis_id": "J4",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "code_version": _get_git_version(),
                        "chunk_sizes": [
                            {
                                "chunk_size": r["experiment"]["chunk_size"],
                                "corpus_chunks": r["performance"]["corpus_chunks"],
                                "mrr": _metric_mean(r["aggregate_metrics"]["mrr"]),
                                "ndcg_at_10": _metric_mean(r["aggregate_metrics"]["ndcg_at_10"]),
                                "precision_at_5": _metric_mean(r["aggregate_metrics"]["precision_at_5"]),
                                "hit_rate": r["aggregate_metrics"]["hit_rate"],
                            }
                            for r in all_results
                        ],
                    },
                    fh,
                    indent=2,
                    ensure_ascii=False,
                )
            logger.info("Comparison written: %s", comparison_file)
        print("=" * 60)

    else:
        config = load_experiment_config(args.config)
        logger.info("Experiment: %s (chunk_size=%d)", config.name, config.chunk_size)

        try:
            result = run_model_evaluation(config, verbose=args.verbose)
        except Exception as exc:
            logger.error("Evaluation failed: %s", exc)
            sys.exit(1)

        out_file = output_dir / f"chunk_{config.chunk_size}_{timestamp}.json"
        with open(out_file, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2, ensure_ascii=False)

        print("\n" + "=" * 60)
        print(f"  J4 Chunk Size — {config.name}")
        print("=" * 60)
        _print_summary(result)
        print(f"  Output:       {out_file}")
        print("=" * 60)


if __name__ == "__main__":
    main()
