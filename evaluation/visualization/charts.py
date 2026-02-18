"""Thesis-quality evaluation charts.

Provides radar, box-plot, grouped-bar, and heatmap charts with English labels,
DPI >= 300, and PNG/SVG output for LaTeX \\includegraphics.
"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any, cast

import matplotlib

matplotlib.use("Agg")  # non-interactive backend; must be before pyplot import

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

logger = logging.getLogger(__name__)

# Academic chart styling
_STYLE_APPLIED = False


def _apply_style() -> None:
    global _STYLE_APPLIED
    if _STYLE_APPLIED:
        return
    sns.set_theme(style="whitegrid", font="serif")
    plt.rcParams.update(
        {
            "axes.labelsize": 12,
            "axes.titlesize": 14,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "legend.fontsize": 10,
            "figure.titlesize": 16,
            "figure.dpi": 300,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.1,
        }
    )
    _STYLE_APPLIED = True


class EvaluationVisualizer:
    """Generates thesis-quality charts from evaluation results.

    Args:
        output_dir: Directory for chart files (created if missing).
        fmt: Output format ('png' or 'svg').
        dpi: Dots per inch (>= 300 for print quality).
    """

    def __init__(self, output_dir: Path, fmt: str = "png", dpi: int = 300) -> None:
        self.output_dir = Path(output_dir)
        self.fmt = fmt.lower().strip()
        self.dpi = max(dpi, 150)
        _apply_style()

    def _ensure_dir(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _save(self, fig: Any, name: str) -> Path:
        """Save figure and close; return path."""
        self._ensure_dir()
        path = self.output_dir / f"{name}.{self.fmt}"
        fig.savefig(str(path), format=self.fmt, dpi=self.dpi)
        plt.close(fig)
        logger.info("Saved chart: %s", path)
        return path

    # ------------------------------------------------------------------
    # T044: Radar chart
    # ------------------------------------------------------------------
    def radar_chart(
        self,
        results: dict[str, dict[str, float]],
        title: str = "Model Comparison",
    ) -> Path:
        """Radar (spider) chart comparing multiple models on shared metrics.

        Args:
            results: {model_name: {metric: score, ...}, ...}
            title: Chart title.

        Returns:
            Path to saved chart file.
        """
        models = list(results.keys())
        if not models:
            raise ValueError("results must contain at least one model")
        metrics = list(results[models[0]].keys())
        n = len(metrics)
        if n < 3:
            raise ValueError("Radar chart requires at least 3 metrics")

        angles = np.linspace(0, 2 * math.pi, n, endpoint=False).tolist()
        angles += angles[:1]

        fig, ax = plt.subplots(figsize=(7, 7), subplot_kw={"polar": True})
        from matplotlib.projections.polar import PolarAxes

        ax = cast(PolarAxes, ax)
        colours = sns.color_palette("husl", len(models))
        for i, model in enumerate(models):
            values = [results[model].get(m, 0.0) for m in metrics]
            values += values[:1]
            ax.plot(angles, values, "o-", linewidth=2, label=model, color=colours[i])
            ax.fill(angles, values, alpha=0.15, color=colours[i])

        ax.set_thetagrids(
            [a * 180 / math.pi for a in angles[:-1]],
            metrics,
        )
        ax.set_ylim(0, 1.05)
        ax.set_title(title, pad=20, fontweight="bold")
        ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1))
        return self._save(fig, "radar_chart")

    # ------------------------------------------------------------------
    # T045: Box plot
    # ------------------------------------------------------------------
    def box_plot(
        self,
        per_query_scores: dict[str, list[float]],
        title: str = "Score Distributions",
    ) -> Path:
        """Box plot showing score distributions per metric.

        Args:
            per_query_scores: {metric_name: [score_per_query, ...], ...}
            title: Chart title.

        Returns:
            Path to saved chart file.
        """
        fig, ax = plt.subplots(figsize=(max(6, len(per_query_scores) * 1.5), 5))
        labels = list(per_query_scores.keys())
        data = [per_query_scores[l] for l in labels]
        bp = ax.boxplot(
            data,
            patch_artist=True,
            tick_labels=labels,
            showmeans=True,
            meanprops={"marker": "D", "markerfacecolor": "red", "markersize": 6},
        )
        colours = sns.color_palette("pastel", len(labels))
        for patch, colour in zip(bp["boxes"], colours, strict=False):
            patch.set_facecolor(colour)
        ax.set_ylabel("Score")
        ax.set_title(title, fontweight="bold")
        ax.set_ylim(0, 1.05)
        return self._save(fig, "box_plot")

    # ------------------------------------------------------------------
    # T046: Bar comparison
    # ------------------------------------------------------------------
    def bar_comparison(
        self,
        results: dict[str, dict[str, float]],
        title: str = "Model Comparison",
    ) -> Path:
        """Grouped bar chart comparing models on multiple metrics.

        Args:
            results: {model_name: {metric: score, ...}, ...}
            title: Chart title.

        Returns:
            Path to saved chart file.
        """
        models = list(results.keys())
        if not models:
            raise ValueError("results must contain at least one model")
        metrics = list(results[models[0]].keys())
        n_models = len(models)
        n_metrics = len(metrics)

        x = np.arange(n_metrics)
        width = 0.8 / max(n_models, 1)
        fig, ax = plt.subplots(figsize=(max(8, n_metrics * 2), 5))
        colours = sns.color_palette("muted", n_models)
        for i, model in enumerate(models):
            vals = [results[model].get(m, 0.0) for m in metrics]
            offset = (i - n_models / 2 + 0.5) * width
            ax.bar(x + offset, vals, width, label=model, color=colours[i])

        ax.set_ylabel("Score")
        ax.set_title(title, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(metrics, rotation=30, ha="right")
        ax.set_ylim(0, 1.05)
        ax.legend()
        return self._save(fig, "bar_comparison")

    # ------------------------------------------------------------------
    # T047: Heatmap
    # ------------------------------------------------------------------
    def heatmap(
        self,
        correlation_matrix: dict[str, dict[str, float]],
        title: str = "Metric Correlations",
    ) -> Path:
        """Heatmap for a correlation or confusion matrix.

        Args:
            correlation_matrix: {row_label: {col_label: value, ...}, ...}
            title: Chart title.

        Returns:
            Path to saved chart file.
        """
        labels = list(correlation_matrix.keys())
        n = len(labels)
        data = np.zeros((n, n))
        for i, row in enumerate(labels):
            for j, col in enumerate(labels):
                data[i, j] = correlation_matrix[row].get(col, 0.0)

        fig, ax = plt.subplots(figsize=(max(6, n * 1.2), max(5, n)))
        sns.heatmap(
            data,
            annot=True,
            fmt=".2f",
            xticklabels=labels,
            yticklabels=labels,
            cmap="YlOrRd",
            vmin=0,
            vmax=1,
            ax=ax,
            square=True,
            linewidths=0.5,
        )
        ax.set_title(title, fontweight="bold")
        return self._save(fig, "heatmap")

    # ------------------------------------------------------------------
    # Speed vs. quality scatter
    # ------------------------------------------------------------------
    def speed_vs_quality_scatter(
        self,
        model_names: list[str],
        quality_scores: list[float],
        chunks_per_second: list[float],
        sizes: list[float] | None = None,
        quality_label: str = "MRR",
        title: str = "Embedding speed vs. retrieval quality",
        name: str = "speed_vs_quality",
    ) -> Path:
        """Scatter: x=quality (e.g. MRR), y=chunks/sec; optional bubble size.

        Args:
            model_names: Short names per model.
            quality_scores: e.g. MRR mean per model.
            chunks_per_second: Throughput per model.
            sizes: Optional bubble sizes (e.g. param count in B).
            quality_label: Label for x-axis.
            title: Chart title.
            name: Base filename for save.

        Returns:
            Path to saved chart file.
        """
        fig, ax = plt.subplots(figsize=(8, 6))
        n = len(model_names)
        if sizes is None:
            sizes = [80.0] * n
        else:
            sizes = [80.0 + s * 40 for s in sizes]
        colours = sns.color_palette("colorblind", n)
        for i in range(n):
            ax.scatter(
                quality_scores[i],
                chunks_per_second[i],
                s=sizes[i],
                alpha=0.7,
                label=model_names[i],
                color=colours[i],
            )
            ax.annotate(
                model_names[i],
                (quality_scores[i], chunks_per_second[i]),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=9,
            )
        ax.set_xlabel(quality_label)
        ax.set_ylabel("Chunks per second")
        ax.set_title(title, fontweight="bold")
        ax.legend(loc="upper left")
        return self._save(fig, name)

    # ------------------------------------------------------------------
    # Miss analysis heatmap
    # ------------------------------------------------------------------
    def miss_analysis_heatmap(
        self,
        model_names: list[str],
        question_ids: list[str],
        hit_matrix: list[list[float]],
        title: str = "Hit/Miss by model and question",
        name: str = "miss_heatmap",
    ) -> Path:
        """Heatmap: rows=models, cols=questions, color=hit (1) / miss (0).

        Args:
            model_names: One per row.
            question_ids: One per column.
            hit_matrix: [model_idx][query_idx] = 1.0 (hit) or 0.0 (miss).
            title: Chart title.
            name: Base filename for save.

        Returns:
            Path to saved chart file.
        """
        data = np.asarray(hit_matrix)
        n_m, n_q = data.shape
        fig, ax = plt.subplots(figsize=(max(12, n_q * 0.15), max(5, n_m * 1.2)))
        sns.heatmap(
            data,
            xticklabels=question_ids,
            yticklabels=model_names,
            cmap="RdYlGn",
            vmin=0,
            vmax=1,
            cbar_kws={"label": "Hit (1) / Miss (0)"},
            ax=ax,
        )
        ax.set_title(title, fontweight="bold")
        ax.set_xlabel("Question ID")
        plt.setp(ax.get_xticklabels(), rotation=90, fontsize=8)
        return self._save(fig, name)

    # ------------------------------------------------------------------
    # J4: Chunk comparison bar chart (MRR / NDCG@10 by chunk_size)
    # ------------------------------------------------------------------
    def chunk_comparison_bar(
        self,
        chunk_sizes: list[dict[str, Any]],
        metrics: list[str] | None = None,
        title: str = "MRR and NDCG@10 by chunk size",
        name: str = "j4_chunk_comparison_bar",
    ) -> Path:
        """Grouped bar chart: x=chunk_size, bars=MRR and NDCG@10 (and optional metrics).

        Args:
            chunk_sizes: List of dicts with chunk_size, mrr, ndcg_at_10, etc.
            metrics: Metric keys to plot (default: mrr, ndcg_at_10).
            title: Chart title.
            name: Base filename for save.

        Returns:
            Path to saved chart file.
        """
        if metrics is None:
            metrics = ["mrr", "ndcg_at_10"]
        sorted_rows = sorted(chunk_sizes, key=lambda r: r.get("chunk_size", 0))
        labels = [str(r.get("chunk_size", "")) for r in sorted_rows]
        x = np.arange(len(labels))
        width = 0.8 / max(len(metrics), 1)
        fig, ax = plt.subplots(figsize=(max(6, len(labels) * 2), 5))
        colours = sns.color_palette("muted", len(metrics))
        for i, metric in enumerate(metrics):
            vals = [r.get(metric, 0.0) for r in sorted_rows]
            offset = (i - len(metrics) / 2 + 0.5) * width
            ax.bar(x + offset, vals, width, label=metric.replace("_", " ").title(), color=colours[i])
        ax.set_ylabel("Score")
        ax.set_xlabel("Chunk size (chars)")
        ax.set_title(title, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.set_ylim(0, 1.05)
        ax.legend()
        return self._save(fig, name)

    # ------------------------------------------------------------------
    # J6: Hybrid vs Dense bar chart (Dense vs Hybrid per metric)
    # ------------------------------------------------------------------
    def hybrid_vs_dense_bar(
        self,
        dense_metrics: dict[str, Any],
        hybrid_metrics: dict[str, Any],
        metrics_order: list[str] | None = None,
        title: str = "Dense vs Hybrid retrieval",
        name: str = "j6_hybrid_vs_dense_bar",
    ) -> Path:
        """Grouped bar chart: Dense vs Hybrid for MRR, NDCG@10, Precision@5, Hit rate.

        Args:
            dense_metrics: e.g. { "mrr": {"mean": 0.87}, "ndcg_at_10": {"mean": 0.89}, ... }
            hybrid_metrics: Same shape. Use .get("mean", val) for scalar.
            metrics_order: Keys to plot in order (default: mrr, ndcg_at_10, precision_at_5, hit_rate).
            title: Chart title.
            name: Base filename for save.

        Returns:
            Path to saved chart file.
        """
        if metrics_order is None:
            metrics_order = ["mrr", "ndcg_at_10", "precision_at_5", "hit_rate"]

        def _val(d: dict[str, Any], k: str) -> float:
            v = d.get(k)
            if isinstance(v, dict) and "mean" in v:
                return float(v["mean"])
            if isinstance(v, (int, float)):
                return float(v)
            return 0.0

        labels = [m.replace("_", " ").title() for m in metrics_order]
        x = np.arange(len(labels))
        width = 0.35
        dense_vals = [_val(dense_metrics, m) for m in metrics_order]
        hybrid_vals = [_val(hybrid_metrics, m) for m in metrics_order]
        fig, ax = plt.subplots(figsize=(max(8, len(labels) * 1.5), 5))
        ax.bar(x - width / 2, dense_vals, width, label="Dense", color=sns.color_palette("muted", 2)[0])
        ax.bar(x + width / 2, hybrid_vals, width, label="Hybrid", color=sns.color_palette("muted", 2)[1])
        ax.set_ylabel("Score")
        ax.set_title(title, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=30, ha="right")
        ax.set_ylim(0, 1.05)
        ax.legend()
        return self._save(fig, name)

    # ------------------------------------------------------------------
    # J6: Dense-MRR vs Hybrid-MRR scatter with y=x line
    # ------------------------------------------------------------------
    def hybrid_vs_dense_scatter(
        self,
        dense_rr_by_id: dict[str, float],
        hybrid_rr_by_id: dict[str, float],
        title: str = "Dense vs Hybrid MRR per query",
        name: str = "j6_hybrid_vs_dense_scatter",
    ) -> Path:
        """Scatter: x=Dense RR, y=Hybrid RR; y=x reference line. Match by query id.

        Args:
            dense_rr_by_id: { query_id: rr, ... }
            hybrid_rr_by_id: { query_id: rr, ... }
            title: Chart title.
            name: Base filename for save.

        Returns:
            Path to saved chart file.
        """
        ids = sorted(set(dense_rr_by_id) & set(hybrid_rr_by_id))
        if not ids:
            raise ValueError("No common query ids between dense and hybrid per_query data")
        x_vals = [dense_rr_by_id[q] for q in ids]
        y_vals = [hybrid_rr_by_id[q] for q in ids]
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.scatter(x_vals, y_vals, alpha=0.7, s=40, color=sns.color_palette("muted", 1)[0], label="Queries")
        lim_lo = min(min(x_vals), min(y_vals), 0.0)
        lim_hi = max(max(x_vals), max(y_vals), 1.0)
        ax.plot([lim_lo, lim_hi], [lim_lo, lim_hi], "k--", alpha=0.7, label="y = x")
        ax.set_xlabel("Dense MRR (RR)")
        ax.set_ylabel("Hybrid MRR (RR)")
        ax.set_title(title, fontweight="bold")
        ax.set_aspect("equal", adjustable="box")
        ax.legend()
        ax.set_xlim(lim_lo - 0.02, lim_hi + 0.02)
        ax.set_ylim(lim_lo - 0.02, lim_hi + 0.02)
        return self._save(fig, name)
