"""LaTeX table export for all thesis evaluation results.

Reads result JSON files from ``evaluation/results/`` and generates
LaTeX ``\\begin{tabular}`` tables with ``\\toprule/\\midrule/\\bottomrule``
formatting for direct inclusion in the diploma thesis.

Usage::

    python -m evaluation.scripts.eval_export_latex
    python -m evaluation.scripts.eval_export_latex --output-dir thesis/tables/

Generates 4 tables:
- FF1: Keyword vs Semantic Search
- FF3: Embedding Model Comparison
- J4: Chunk Size Impact
- J6: Hybrid vs Dense Retrieval

Thesis-ID: US5 (LaTeX Export)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

EVAL_ROOT = Path(__file__).resolve().parent.parent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _metric_mean(m: dict | float) -> float:
    """Extract mean from metric (dict with mean/std or plain float)."""
    if isinstance(m, dict):
        return m.get("mean", 0.0)
    return float(m)


def _find_latest_result(results_dir: Path, pattern: str) -> Path | None:
    """Find the most recent result file matching a glob pattern."""
    candidates = sorted(results_dir.glob(pattern), reverse=True)
    return candidates[0] if candidates else None


def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# LaTeX table generators
# ---------------------------------------------------------------------------

def generate_ff1_table(results_dir: Path) -> str | None:
    """FF1: Keyword vs Semantic Search comparison.

    Expects:
    - keyword_baseline_*.json (keyword baseline)
    - model_bge*_*.json (semantic baseline with bge-m3)
    """
    kw_file = _find_latest_result(results_dir, "keyword_baseline_*.json")
    sem_file = _find_latest_result(results_dir, "model_bge*_*.json")

    if not kw_file:
        logger.warning("FF1: No keyword_baseline result found")
        return None

    kw = _load_json(kw_file)
    kw_agg = kw["aggregate_metrics"]

    rows = [
        ("Keyword (core.searchPages)", _metric_mean(kw_agg["mrr"]), _metric_mean(kw_agg["precision_at_5"]), kw_agg.get("hit_rate", 0)),
    ]

    if sem_file:
        sem = _load_json(sem_file)
        sem_agg = sem["aggregate_metrics"]
        model_name = sem["experiment"].get("model", "bge-m3")
        rows.append(
            (f"Semantic ({model_name})", _metric_mean(sem_agg["mrr"]), _metric_mean(sem_agg.get("precision_at_5", 0)), sem_agg.get("hit_rate", 0))
        )

    lines = [
        r"\begin{table}[htbp]",
        r"  \centering",
        r"  \caption{FF1 --- Keyword vs Semantic Search Comparison}",
        r"  \label{tab:ff1-keyword-vs-semantic}",
        r"  \begin{tabular}{lccc}",
        r"    \toprule",
        r"    Retrieval Method & MRR & P@5 & Hit Rate \\",
        r"    \midrule",
    ]
    for name, mrr, p5, hr in rows:
        lines.append(f"    {name} & {mrr:.4f} & {p5:.4f} & {hr:.1%} \\\\")
    lines.extend([
        r"    \bottomrule",
        r"  \end{tabular}",
        r"\end{table}",
    ])
    return "\n".join(lines)


def generate_ff3_table(results_dir: Path) -> str | None:
    """FF3: Embedding Model Comparison."""
    comp_file = _find_latest_result(results_dir, "model_comparison_*.json")
    if not comp_file:
        logger.warning("FF3: No model_comparison result found")
        return None

    comp = _load_json(comp_file)
    models = comp.get("models", [])
    if not models:
        return None

    lines = [
        r"\begin{table}[htbp]",
        r"  \centering",
        r"  \caption{FF3 --- Embedding Model Comparison}",
        r"  \label{tab:ff3-model-comparison}",
        r"  \begin{tabular}{llcccc}",
        r"    \toprule",
        r"    Model & Provider & Dim & MRR & NDCG@10 & Hit Rate \\",
        r"    \midrule",
    ]
    for m in models:
        lines.append(
            f"    {m['model']} & {m['provider']} & {m['dimensions']} "
            f"& {_metric_mean(m['mrr']):.4f} & {_metric_mean(m['ndcg_at_10']):.4f} "
            f"& {_metric_mean(m.get('hit_rate', 0)):.1%} \\\\"
        )
    lines.extend([
        r"    \bottomrule",
        r"  \end{tabular}",
        r"\end{table}",
    ])
    return "\n".join(lines)


def generate_j4_table(results_dir: Path) -> str | None:
    """J4: Chunk Size Impact."""
    comp_file = _find_latest_result(results_dir, "chunk_comparison_*.json")
    if not comp_file:
        logger.warning("J4: No chunk_comparison result found")
        return None

    comp = _load_json(comp_file)
    sizes = comp.get("chunk_sizes", [])
    if not sizes:
        return None

    lines = [
        r"\begin{table}[htbp]",
        r"  \centering",
        r"  \caption{J4 --- Impact of Chunk Size on Retrieval Quality}",
        r"  \label{tab:j4-chunk-size}",
        r"  \begin{tabular}{rrccc}",
        r"    \toprule",
        r"    Chunk Size & Chunks & MRR & NDCG@10 & Hit Rate \\",
        r"    \midrule",
    ]
    for s in sizes:
        lines.append(
            f"    {s['chunk_size']} & {s['corpus_chunks']} "
            f"& {_metric_mean(s['mrr']):.4f} & {_metric_mean(s['ndcg_at_10']):.4f} "
            f"& {_metric_mean(s.get('hit_rate', 0)):.1%} \\\\"
        )
    lines.extend([
        r"    \bottomrule",
        r"  \end{tabular}",
        r"\end{table}",
    ])
    return "\n".join(lines)


def generate_j6_table(results_dir: Path) -> str | None:
    """J6: Hybrid vs Dense Retrieval."""
    result_file = _find_latest_result(results_dir, "hybrid_vs_dense_*.json")
    if not result_file:
        logger.warning("J6: No hybrid_vs_dense result found")
        return None

    data = _load_json(result_file)
    comp = data.get("comparison", {})
    if not comp:
        return None

    lines = [
        r"\begin{table}[htbp]",
        r"  \centering",
        r"  \caption{J6 --- Hybrid vs Dense Retrieval Comparison}",
        r"  \label{tab:j6-hybrid-vs-dense}",
        r"  \begin{tabular}{lcccc}",
        r"    \toprule",
        r"    Mode & MRR & NDCG@10 & P@5 & Hit Rate \\",
        r"    \midrule",
    ]
    for mode_name in ("dense", "hybrid"):
        m = comp.get(mode_name, {})
        if m:
            lines.append(
                f"    {mode_name.capitalize()} "
                f"& {_metric_mean(m.get('mrr', 0)):.4f} "
                f"& {_metric_mean(m.get('ndcg_at_10', 0)):.4f} "
                f"& {_metric_mean(m.get('precision_at_5', 0)):.4f} "
                f"& {_metric_mean(m.get('hit_rate', 0)):.1%} \\\\"
            )
    lines.extend([
        r"    \bottomrule",
        r"  \end{tabular}",
        r"\end{table}",
    ])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "LaTeX Table Export — generate thesis tables from evaluation results."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m evaluation.scripts.eval_export_latex\n"
            "  python -m evaluation.scripts.eval_export_latex --output-dir thesis/tables/\n"
        ),
    )
    parser.add_argument(
        "--results-dir",
        default=str(EVAL_ROOT / "results"),
        help="Directory containing result JSON files",
    )
    parser.add_argument(
        "--output-dir",
        default=str(EVAL_ROOT / "results"),
        help="Directory for .tex output files",
    )
    return parser


def main() -> None:
    """Entry point for LaTeX export."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = _build_parser()
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    generators = {
        "ff1_keyword_vs_semantic": generate_ff1_table,
        "ff3_model_comparison": generate_ff3_table,
        "j4_chunk_size": generate_j4_table,
        "j6_hybrid_vs_dense": generate_j6_table,
    }

    generated = 0
    for name, gen_fn in generators.items():
        latex = gen_fn(results_dir)
        if latex:
            out_file = output_dir / f"table_{name}.tex"
            out_file.write_text(latex, encoding="utf-8")
            logger.info("Generated: %s", out_file)
            generated += 1
        else:
            logger.info("Skipped %s (no result data)", name)

    print(f"\nGenerated {generated}/{len(generators)} LaTeX tables in {output_dir}")


if __name__ == "__main__":
    main()
