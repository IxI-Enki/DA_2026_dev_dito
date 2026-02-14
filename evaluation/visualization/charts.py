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
    plt.rcParams.update({
        "axes.labelsize": 12,
        "axes.titlesize": 14,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "figure.titlesize": 16,
        "figure.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.1,
    })
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
        for patch, colour in zip(bp["boxes"], colours):
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
