"""LaTeX table export for all thesis evaluation results.

Reads result JSON files from ``evaluation/results/`` and generates
LaTeX ``\\begin{tabular}`` tables with ``\\toprule/\\midrule/\\bottomrule``
formatting for direct inclusion in the diploma thesis.

Usage::

    python -m evaluation.scripts.eval_export_latex
    python -m evaluation.scripts.eval_export_latex --output-dir thesis/tables/

Generates tables:
- FF1: Keyword vs Semantic Search
- FF3: Embedding Model Comparison (aggregate + by difficulty)

Thesis-ID: US5 (LaTeX Export)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

EVAL_ROOT = Path(__file__).resolve().parent.parent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _metric_val(m: dict | float) -> float:
    """Extract mean from metric (dict with mean/std or plain float)."""
    if isinstance(m, dict):
        return m.get("mean", 0.0)
    return float(m)


def _metric_std(m: dict | float) -> float | None:
    """Extract std from metric if available."""
    if isinstance(m, dict):
        return m.get("std")
    return None


def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _find_latest(directory: Path, pattern: str) -> Path | None:
    """Find the most recent file matching a glob pattern."""
    candidates = sorted(directory.glob(pattern), reverse=True)
    return candidates[0] if candidates else None


def _short_model_name(model: str) -> str:
    """Shorten model identifier for table display."""
    replacements = {
        "BAAI/bge-m3-unsupervised": "bge-m3",
        "bflhc/Octen-Embedding-4B": "Octen-4B",
        "telepix/PIXIE-Rune-v1.0": "PIXIE-Rune",
        "Snowflake/snowflake-arctic-embed-l-v2.0": "Snowflake Arctic",
        "text-embedding-3-large": "OpenAI 3-large",
    }
    return replacements.get(model, model)


# ---------------------------------------------------------------------------
# LaTeX table generators
# ---------------------------------------------------------------------------

def generate_ff1_table(results_dir: Path) -> str | None:
    """FF1: Keyword vs Semantic Search comparison.

    Shows both keyword modes + all semantic models for full comparison.
    """
    # Find keyword baselines
    kw_full = _find_latest(results_dir, "keyword_baseline_2*.json")
    kw_keywords = _find_latest(results_dir, "keyword_baseline_keywords_*.json")

    # Find model results (individual files in subdirectory)
    model_dir = results_dir / "results_of_full_wiki_corpus_78q"
    model_files = sorted(model_dir.glob("model_*.json")) if model_dir.exists() else []

    if not kw_full and not model_files:
        logger.warning("FF1: No keyword or model results found")
        return None

    rows: list[tuple[str, float, float, float]] = []

    # Keyword baselines
    if kw_full:
        kw = _load_json(kw_full)
        agg = kw["aggregate_metrics"]
        mode = kw.get("experiment", {}).get("query_mode", "fullquestion")
        rows.append((
            "Keyword (full question)",
            _metric_val(agg["mrr"]),
            _metric_val(agg["precision_at_5"]),
            _metric_val(agg.get("hit_rate", 0)),
        ))

    if kw_keywords:
        kw2 = _load_json(kw_keywords)
        agg2 = kw2["aggregate_metrics"]
        rows.append((
            "Keyword (optimal keywords)",
            _metric_val(agg2["mrr"]),
            _metric_val(agg2["precision_at_5"]),
            _metric_val(agg2.get("hit_rate", 0)),
        ))

    # Semantic models (sorted by MRR descending)
    model_rows: list[tuple[str, float, float, float]] = []
    for mf in model_files:
        data = _load_json(mf)
        agg = data["aggregate_metrics"]
        name = _short_model_name(data["experiment"]["model"])
        model_rows.append((
            f"Semantic: {name}",
            _metric_val(agg["mrr"]),
            _metric_val(agg.get("precision_at_5", 0)),
            _metric_val(agg.get("hit_rate", 0)),
        ))
    model_rows.sort(key=lambda r: r[1], reverse=True)
    rows.extend(model_rows)

    # Find best MRR for bolding
    best_mrr = max(r[1] for r in rows)

    lines = [
        r"\begin{table}[htbp]",
        r"  \centering",
        r"  \caption{FF1 --- Keyword vs.\ Semantic Search Comparison (78 queries)}",
        r"  \label{tab:ff1-keyword-vs-semantic}",
        r"  \begin{tabular}{lccc}",
        r"    \toprule",
        r"    Retrieval Method & MRR & P@5 & Hit Rate \\",
        r"    \midrule",
    ]
    for i, (name, mrr, p5, hr) in enumerate(rows):
        mrr_str = f"\\textbf{{{mrr:.4f}}}" if mrr == best_mrr else f"{mrr:.4f}"
        lines.append(f"    {name} & {mrr_str} & {p5:.4f} & {hr:.1%} \\\\")
        # Add midrule between keyword and semantic sections
        if kw_keywords and i == 1:
            lines.append(r"    \midrule")
        elif not kw_keywords and kw_full and i == 0:
            lines.append(r"    \midrule")
    lines.extend([
        r"    \bottomrule",
        r"  \end{tabular}",
        r"\end{table}",
    ])
    return "\n".join(lines)


def generate_ff3_table(results_dir: Path) -> str | None:
    """FF3: Embedding Model Comparison (aggregate metrics)."""
    model_dir = results_dir / "results_of_full_wiki_corpus_78q"
    if not model_dir.exists():
        logger.warning("FF3: results_of_full_wiki_corpus_78q/ not found")
        return None

    model_files = sorted(model_dir.glob("model_*.json"))
    if not model_files:
        logger.warning("FF3: No model result files found")
        return None

    # Collect model data
    models: list[dict] = []
    for mf in model_files:
        data = _load_json(mf)
        exp = data["experiment"]
        agg = data["aggregate_metrics"]
        models.append({
            "name": _short_model_name(exp["model"]),
            "dims": exp["dimensions"],
            "mrr": _metric_val(agg["mrr"]),
            "mrr_std": _metric_std(agg["mrr"]),
            "ndcg": _metric_val(agg["ndcg_at_10"]),
            "p5": _metric_val(agg.get("precision_at_5", 0)),
            "recall": _metric_val(agg.get("recall_at_10", 0)),
            "hit_rate": _metric_val(agg.get("hit_rate", 0)),
        })

    # Sort by MRR descending
    models.sort(key=lambda m: m["mrr"], reverse=True)
    best_mrr = models[0]["mrr"]

    lines = [
        r"\begin{table}[htbp]",
        r"  \centering",
        r"  \caption{FF3 --- Embedding Model Comparison on LeoWiki (78 queries, 10{,}841 chunks)}",
        r"  \label{tab:ff3-model-comparison}",
        r"  \begin{tabular}{lrccccr}",
        r"    \toprule",
        r"    Model & Dim & MRR & NDCG@10 & P@5 & Recall@10 & Hit Rate \\",
        r"    \midrule",
    ]
    for m in models:
        mrr_str = f"\\textbf{{{m['mrr']:.4f}}}" if m["mrr"] == best_mrr else f"{m['mrr']:.4f}"
        std_str = f" \\tiny{{$\\pm${m['mrr_std']:.2f}}}" if m["mrr_std"] is not None else ""
        lines.append(
            f"    {m['name']} & {m['dims']} "
            f"& {mrr_str}{std_str} & {m['ndcg']:.4f} "
            f"& {m['p5']:.4f} & {m['recall']:.4f} & {m['hit_rate']:.1%} \\\\"
        )
    lines.extend([
        r"    \bottomrule",
        r"  \end{tabular}",
        r"\end{table}",
    ])
    return "\n".join(lines)


def generate_ff3_difficulty_table(results_dir: Path) -> str | None:
    """FF3: Results broken down by difficulty level."""
    model_dir = results_dir / "results_of_full_wiki_corpus_78q"
    if not model_dir.exists():
        return None

    model_files = sorted(model_dir.glob("model_*.json"))
    if not model_files:
        return None

    # Collect per-difficulty data
    models: list[dict] = []
    for mf in model_files:
        data = _load_json(mf)
        exp = data["experiment"]
        by_diff = data.get("by_difficulty", {})
        entry = {"name": _short_model_name(exp["model"])}
        for diff in ("easy", "medium", "hard"):
            d = by_diff.get(diff, {})
            entry[f"{diff}_mrr"] = _metric_val(d.get("mrr", 0))
            entry[f"{diff}_hit"] = _metric_val(d.get("hit_rate", 0))
        entry["overall_mrr"] = _metric_val(data["aggregate_metrics"]["mrr"])
        models.append(entry)

    models.sort(key=lambda m: m["overall_mrr"], reverse=True)

    lines = [
        r"\begin{table}[htbp]",
        r"  \centering",
        r"  \caption{FF3 --- MRR by Question Difficulty}",
        r"  \label{tab:ff3-by-difficulty}",
        r"  \begin{tabular}{lcccccc}",
        r"    \toprule",
        r"    & \multicolumn{2}{c}{Easy ($n=17$)} & \multicolumn{2}{c}{Medium ($n=40$)} & \multicolumn{2}{c}{Hard ($n=21$)} \\",
        r"    \cmidrule(lr){2-3} \cmidrule(lr){4-5} \cmidrule(lr){6-7}",
        r"    Model & MRR & Hit\% & MRR & Hit\% & MRR & Hit\% \\",
        r"    \midrule",
    ]
    for m in models:
        lines.append(
            f"    {m['name']} "
            f"& {m['easy_mrr']:.3f} & {m['easy_hit']:.0%} "
            f"& {m['medium_mrr']:.3f} & {m['medium_hit']:.0%} "
            f"& {m['hard_mrr']:.3f} & {m['hard_hit']:.0%} \\\\"
        )
    lines.extend([
        r"    \bottomrule",
        r"  \end{tabular}",
        r"\end{table}",
    ])
    return "\n".join(lines)


def generate_ff3_performance_table(results_dir: Path) -> str | None:
    """FF3: Embedding speed and cost comparison."""
    model_dir = results_dir / "results_of_full_wiki_corpus_78q"
    if not model_dir.exists():
        return None

    model_files = sorted(model_dir.glob("model_*.json"))
    if not model_files:
        return None

    models: list[dict] = []
    for mf in model_files:
        data = _load_json(mf)
        exp = data["experiment"]
        perf = data.get("performance", {})
        models.append({
            "name": _short_model_name(exp["model"]),
            "mrr": _metric_val(data["aggregate_metrics"]["mrr"]),
            "embed_time": perf.get("embedding_time_seconds", 0),
            "chunks": perf.get("corpus_chunks", 0),
        })

    models.sort(key=lambda m: m["mrr"], reverse=True)

    lines = [
        r"\begin{table}[htbp]",
        r"  \centering",
        r"  \caption{FF3 --- Embedding Performance (10{,}841 chunks, RTX 4080 12\,GB)}",
        r"  \label{tab:ff3-performance}",
        r"  \begin{tabular}{lccr}",
        r"    \toprule",
        r"    Model & MRR & Embed Time & Speed \\",
        r"    \midrule",
    ]
    for m in models:
        t = m["embed_time"]
        if t > 0:
            speed = m["chunks"] / t if m["chunks"] else 0
            time_str = f"{t:.0f}\\,s" if t < 120 else f"{t/60:.1f}\\,min"
            speed_str = f"{speed:.0f}\\,chunks/s"
        else:
            time_str = "---"
            speed_str = "---"
        lines.append(
            f"    {m['name']} & {m['mrr']:.4f} & {time_str} & {speed_str} \\\\"
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
            "LaTeX Table Export -- generate thesis tables from evaluation results."
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
    thesis_tables = (
        Path(__file__).resolve().parents[3]
        / "dev_prompts_instructions_notes" / "thesis" / "tables"
    )
    parser.add_argument(
        "--output-dir",
        default=str(thesis_tables),
        help="Directory for .tex output files (default: ../dev_prompts_instructions_notes/thesis/tables/)",
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
        "ff3_by_difficulty": generate_ff3_difficulty_table,
        "ff3_performance": generate_ff3_performance_table,
    }

    generated = 0
    for name, gen_fn in generators.items():
        latex = gen_fn(results_dir)
        if latex:
            out_file = output_dir / f"table_{name}.tex"
            out_file.write_text(latex, encoding="utf-8")
            logger.info("Generated: %s", out_file)
            print(f"\n--- {name} ---")
            print(latex)
            generated += 1
        else:
            logger.info("Skipped %s (no result data)", name)

    print(f"\nGenerated {generated}/{len(generators)} LaTeX tables in {output_dir}")


if __name__ == "__main__":
    main()
