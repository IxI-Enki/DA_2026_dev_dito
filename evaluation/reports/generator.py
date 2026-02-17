"""Structured Markdown and JSON evaluation report generator.

Produces thesis-quality reports with:
- Executive Summary (best model, key findings)
- Custom Metrics table (MRR, NDCG, P@K, MAP, Recall@K)
- RAGAS Metrics table (Context P/R, Faithfulness, Answer Correctness)
- Statistical Comparison section (CI, p-values, effect sizes)
- Difficulty Breakdown (easy / medium / hard)
- NFR-005 reproducibility fields (timestamp, config-hash, code-version)
"""

from __future__ import annotations

import json
import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CUSTOM_METRIC_KEYS = ("rr", "ndcg_at_10", "p_at_5", "recall_at_k", "map", "hit_rate")


def _load_results(results_dir: Path) -> dict[str, dict]:
    """Load all .json result files from *results_dir*. Returns {stem: data}."""
    results: dict[str, dict] = {}
    for p in sorted(results_dir.glob("*.json")):
        try:
            with open(p, encoding="utf-8") as f:
                results[p.stem] = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Skipped %s: %s", p.name, e)
    return results


def _aggregate(per_query: list[dict], keys: tuple[str, ...] | None = None) -> dict[str, float]:
    """Mean of numeric keys across per_query rows."""
    if not per_query:
        return {}
    if keys is None:
        keys = tuple(k for k in per_query[0] if isinstance(per_query[0].get(k), (int, float)))
    agg: dict[str, float] = {}
    for k in keys:
        vals = [float(row[k]) for row in per_query if isinstance(row.get(k), (int, float))]
        agg[k] = sum(vals) / len(vals) if vals else 0.0
    return agg


def _difficulty_breakdown(
    per_query: list[dict], keys: tuple[str, ...] | None = None
) -> dict[str, dict[str, float]]:
    """Break down metrics by difficulty level."""
    if not per_query:
        return {}
    if keys is None:
        keys = tuple(k for k in per_query[0] if isinstance(per_query[0].get(k), (int, float)))
    buckets: dict[str, list[dict]] = {}
    for row in per_query:
        diff = row.get("difficulty", "unknown")
        buckets.setdefault(diff, []).append(row)
    breakdown: dict[str, dict[str, float]] = {}
    for diff, rows in sorted(buckets.items()):
        breakdown[diff] = _aggregate(rows, keys)
        breakdown[diff]["count"] = float(len(rows))
    return breakdown


def _git_version() -> str:
    """Return short git commit hash, or 'unknown'."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
        )
        return out.strip()
    except Exception:
        return "unknown"


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    """Build a simple Markdown table."""
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


class ReportGenerator:
    """Generates structured Markdown + JSON evaluation reports.

    Args:
        output_dir: Directory for report files (created if missing).
    """

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = Path(output_dir)

    def generate(
        self,
        results_dir: Path,
        ragas_scores: dict[str, float] | None = None,
        comparison: list[dict] | None = None,
    ) -> tuple[Path, Path]:
        """Generate Markdown and JSON reports from result JSONs.

        Args:
            results_dir: Directory containing per-experiment result JSONs.
            ragas_scores: Optional RAGAS metric scores dict.
            comparison: Optional list of statistical comparison dicts.

        Returns:
            Tuple of (markdown_path, json_path).
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        all_results = _load_results(results_dir)
        if not all_results:
            raise FileNotFoundError(f"No JSON result files in {results_dir}")

        timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        code_version = _git_version()
        config_hashes = {name: data.get("config_hash", "n/a") for name, data in all_results.items()}

        # Aggregate per model
        aggregates: dict[str, dict[str, float]] = {}
        difficulty_all: dict[str, dict[str, dict[str, float]]] = {}
        for name, data in all_results.items():
            pq = data.get("per_query", [])
            aggregates[name] = _aggregate(pq)
            difficulty_all[name] = _difficulty_breakdown(pq)

        # Executive summary
        best_model = ""
        best_score = -1.0
        for name, agg in aggregates.items():
            mrr = agg.get("rr", 0.0)
            if mrr > best_score:
                best_score = mrr
                best_model = name

        executive = {
            "best_model": best_model,
            "best_mrr": round(best_score, 4),
            "n_models": len(all_results),
            "n_metrics": len(aggregates.get(best_model, {})),
        }

        # Build JSON report
        report_json: dict[str, Any] = {
            "timestamp": timestamp,
            "code_version": code_version,
            "config_hashes": config_hashes,
            "executive_summary": executive,
            "custom_metrics": aggregates,
            "difficulty_breakdown": {name: diff for name, diff in difficulty_all.items()},
        }
        if ragas_scores:
            report_json["ragas_metrics"] = ragas_scores
        if comparison:
            report_json["statistical_comparison"] = comparison

        # Build Markdown report
        md_lines: list[str] = []
        md_lines.append("# Evaluation Report")
        md_lines.append("")
        md_lines.append(f"**Generated**: {timestamp}  ")
        md_lines.append(f"**Code Version**: `{code_version}`  ")
        md_lines.append(f"**Models**: {len(all_results)}")
        md_lines.append("")

        # Executive Summary (T056)
        md_lines.append("## Executive Summary")
        md_lines.append("")
        md_lines.append(f"- **Best Model**: {best_model} (MRR = {best_score:.4f})")
        md_lines.append(f"- **Models Evaluated**: {len(all_results)}")
        md_lines.append("")

        # Custom Metrics Table (T057)
        md_lines.append("## Custom Metrics")
        md_lines.append("")
        if aggregates:
            first_metrics = list(next(iter(aggregates.values())).keys())
            headers = ["Model"] + first_metrics
            rows = []
            for name, agg in aggregates.items():
                row = [name] + [f"{agg.get(m, 0.0):.4f}" for m in first_metrics]
                rows.append(row)
            md_lines.append(_md_table(headers, rows))
            md_lines.append("")

        # RAGAS Metrics Table (T058)
        if ragas_scores:
            md_lines.append("## RAGAS Metrics (LLM-as-Judge)")
            md_lines.append("")
            r_headers = ["Metric", "Score"]
            r_rows = [[k, f"{v:.4f}"] for k, v in sorted(ragas_scores.items())]
            md_lines.append(_md_table(r_headers, r_rows))
            md_lines.append("")

        # Statistical Comparison (T059)
        if comparison:
            md_lines.append("## Statistical Comparison")
            md_lines.append("")
            c_headers = ["Metric", "p-value", "Effect Size", "Interpretation"]
            c_rows = []
            for c in comparison:
                c_rows.append(
                    [
                        c.get("metric", ""),
                        f"{c.get('p_value', 0.0):.4f}",
                        f"{c.get('effect_size', 0.0):.4f}",
                        c.get("interpretation", ""),
                    ]
                )
            md_lines.append(_md_table(c_headers, c_rows))
            md_lines.append("")

        # Difficulty Breakdown (T060)
        md_lines.append("## Difficulty Breakdown")
        md_lines.append("")
        for name, diff_data in difficulty_all.items():
            md_lines.append(f"### {name}")
            md_lines.append("")
            if diff_data:
                first_diff_metrics = [k for k in next(iter(diff_data.values())) if k != "count"]
                d_headers = ["Difficulty", "Count"] + first_diff_metrics
                d_rows = []
                for diff, metrics in diff_data.items():
                    row = [diff, str(int(metrics.get("count", 0)))]
                    row += [f"{metrics.get(m, 0.0):.4f}" for m in first_diff_metrics]
                    d_rows.append(row)
                md_lines.append(_md_table(d_headers, d_rows))
                md_lines.append("")

        # NFR-005 Reproducibility (T061)
        md_lines.append("## Reproducibility (NFR-005)")
        md_lines.append("")
        md_lines.append(f"- **Timestamp**: {timestamp}")
        md_lines.append(f"- **Code Version**: `{code_version}`")
        for name, h in config_hashes.items():
            md_lines.append(f"- **Config Hash ({name})**: `{h}`")
        md_lines.append("")

        md_text = "\n".join(md_lines)

        md_path = self.output_dir / "evaluation_report.md"
        json_path = self.output_dir / "evaluation_report.json"

        md_path.write_text(md_text, encoding="utf-8")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_json, f, indent=2, ensure_ascii=False)

        logger.info("Report generated: %s, %s", md_path, json_path)
        return md_path, json_path
