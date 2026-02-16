"""Evaluation Report Generator (US8, T046).

Produces:
- JSON report with per-document scores + aggregate summary
- Markdown report for human review

Output: ``evaluation_report_{timestamp}.json`` and ``.md``
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .metrics import (
    DocumentScore,
    THRESHOLDS,
    REGRESSION_THRESHOLD,
    check_regression,
    passes_thresholds,
)

logger = logging.getLogger(__name__)


def generate_report(
    scores: list[DocumentScore],
    output_dir: Path,
    *,
    fetched_dir: str = "",
    preprocessed_dir: str = "",
) -> Path:
    """Generate JSON and Markdown evaluation reports.

    Args:
        scores: Per-document evaluation results.
        output_dir: Directory to write reports into.
        fetched_dir: Path to the original fetched data (for metadata).
        preprocessed_dir: Path to the preprocessed output (for metadata).

    Returns:
        Path to the generated JSON report.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # Build aggregate summary
    aggregate = _build_aggregate(scores)
    regression = check_regression(scores)

    report_data = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "fetched_dir": fetched_dir,
            "preprocessed_dir": preprocessed_dir,
            "total_documents": len(scores),
            "schema_version": "1.0",
        },
        "thresholds": {
            k: {"operator": op, "value": val}
            for k, (op, val) in THRESHOLDS.items()
        },
        "aggregate": aggregate,
        "regression": regression,
        "per_document": [asdict(ds) for ds in scores],
    }

    json_path = output_dir / f"evaluation_report_{timestamp}.json"
    json_path.write_text(
        json.dumps(report_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("JSON report written: %s", json_path)

    md_path = output_dir / f"evaluation_report_{timestamp}.md"
    md_path.write_text(
        _render_markdown(report_data),
        encoding="utf-8",
    )
    logger.info("Markdown report written: %s", md_path)

    return json_path


def _build_aggregate(scores: list[DocumentScore]) -> dict[str, Any]:
    """Compute aggregate statistics across all documents."""
    if not scores:
        return {}

    n = len(scores)
    fields = [
        "content_completeness",
        "semantic_similarity",
        "entity_preservation",
        "link_integrity",
        "noise_ratio",
        "readability",
        "structure_preservation",
    ]

    agg: dict[str, Any] = {}
    for field in fields:
        values = [getattr(ds, field) for ds in scores]
        op, threshold = THRESHOLDS[field]

        if op == ">=":
            passing = sum(1 for v in values if v >= threshold)
        else:
            passing = sum(1 for v in values if v <= threshold)

        agg[field] = {
            "mean": sum(values) / n,
            "min": min(values),
            "max": max(values),
            "pass_rate": passing / n,
            "passing": passing,
            "total": n,
        }

    # Overall pass rate (documents passing ALL thresholds)
    all_pass = sum(1 for ds in scores if passes_thresholds(ds))
    agg["overall"] = {
        "all_pass_count": all_pass,
        "all_pass_rate": all_pass / n,
        "total": n,
    }

    return agg


def _render_markdown(report: dict[str, Any]) -> str:
    """Render evaluation report as Markdown for human review."""
    meta = report["metadata"]
    agg = report.get("aggregate", {})
    regression = report.get("regression", {})
    lines: list[str] = []

    lines.append("# Preprocessing Evaluation Report")
    lines.append("")
    lines.append(f"**Generated**: {meta['generated_at']}")
    lines.append(f"**Documents**: {meta['total_documents']}")
    if meta.get("fetched_dir"):
        lines.append(f"**Fetched**: {meta['fetched_dir']}")
    if meta.get("preprocessed_dir"):
        lines.append(f"**Preprocessed**: {meta['preprocessed_dir']}")
    lines.append("")

    # Aggregate table
    lines.append("## Aggregate Summary")
    lines.append("")
    lines.append("| Metric | Mean | Min | Max | Pass Rate | Status |")
    lines.append("|--------|------|-----|-----|-----------|--------|")

    for field in [
        "content_completeness",
        "semantic_similarity",
        "entity_preservation",
        "link_integrity",
        "noise_ratio",
        "readability",
        "structure_preservation",
    ]:
        if field not in agg:
            continue
        a = agg[field]
        op, thresh = THRESHOLDS[field]
        status = "PASS" if a["pass_rate"] >= 0.95 else "WARN" if a["pass_rate"] >= 0.90 else "FAIL"
        lines.append(
            f"| {field} | {a['mean']:.3f} | {a['min']:.3f} | "
            f"{a['max']:.3f} | {a['pass_rate']:.1%} | {status} |"
        )

    if "overall" in agg:
        o = agg["overall"]
        lines.append("")
        lines.append(
            f"**Overall**: {o['all_pass_count']}/{o['total']} documents "
            f"pass all thresholds ({o['all_pass_rate']:.1%})"
        )

    # Regression check
    lines.append("")
    lines.append("## Regression Check")
    lines.append("")
    lines.append(f"Threshold: aggregate pass-rate >= {REGRESSION_THRESHOLD:.0%}")
    lines.append("")
    lines.append("| Metric | Pass Rate | Status |")
    lines.append("|--------|-----------|--------|")

    for field, result in regression.items():
        status = "PASS" if result["pass"] else "FAIL"
        lines.append(f"| {field} | {result['pass_rate']:.1%} | {status} |")

    lines.append("")
    return "\n".join(lines)
