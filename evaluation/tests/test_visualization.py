"""Unit tests for EvaluationVisualizer (T038-T042)."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def tmp_output(tmp_path: Path) -> Path:
    """Provide a temporary output directory for chart files."""
    return tmp_path / "charts"


@pytest.fixture()
def sample_results() -> dict[str, dict[str, float]]:
    """Multi-model aggregate results for radar/bar charts."""
    return {
        "bge-m3": {"mrr": 0.72, "ndcg_at_10": 0.68, "p_at_5": 0.55, "recall_at_10": 0.80},
        "nomic-embed": {"mrr": 0.65, "ndcg_at_10": 0.61, "p_at_5": 0.50, "recall_at_10": 0.74},
    }


@pytest.fixture()
def per_query_scores() -> dict[str, list[float]]:
    """Per-query scores for box plots."""
    return {
        "mrr": [0.5, 0.7, 0.8, 0.6, 0.9, 0.4, 0.75, 0.65],
        "ndcg_at_10": [0.4, 0.6, 0.7, 0.55, 0.85, 0.35, 0.7, 0.6],
        "p_at_5": [0.3, 0.5, 0.6, 0.45, 0.8, 0.25, 0.55, 0.5],
    }


@pytest.fixture()
def correlation_data() -> dict[str, dict[str, float]]:
    """Correlation matrix for heatmap."""
    return {
        "mrr": {"mrr": 1.0, "ndcg": 0.85, "p_at_5": 0.70},
        "ndcg": {"mrr": 0.85, "ndcg": 1.0, "p_at_5": 0.78},
        "p_at_5": {"mrr": 0.70, "ndcg": 0.78, "p_at_5": 1.0},
    }


class TestRadarChart:
    """T038: Tests for radar_chart() output."""

    def test_radar_chart_returns_path(self, tmp_output: Path, sample_results: dict) -> None:
        from evaluation.visualization.charts import EvaluationVisualizer

        viz = EvaluationVisualizer(output_dir=tmp_output, fmt="png", dpi=150)
        path = viz.radar_chart(sample_results, title="Model Comparison")
        assert path.exists()
        assert path.suffix == ".png"

    def test_radar_chart_file_not_empty(self, tmp_output: Path, sample_results: dict) -> None:
        from evaluation.visualization.charts import EvaluationVisualizer

        viz = EvaluationVisualizer(output_dir=tmp_output, fmt="png", dpi=150)
        path = viz.radar_chart(sample_results, title="Test Radar")
        assert path.stat().st_size > 0

    def test_radar_chart_creates_output_dir(self, tmp_output: Path, sample_results: dict) -> None:
        from evaluation.visualization.charts import EvaluationVisualizer

        assert not tmp_output.exists()
        viz = EvaluationVisualizer(output_dir=tmp_output, fmt="png", dpi=150)
        viz.radar_chart(sample_results, title="Test")
        assert tmp_output.exists()


class TestBoxPlot:
    """T039: Tests for box_plot() generation."""

    def test_box_plot_returns_path(self, tmp_output: Path, per_query_scores: dict) -> None:
        from evaluation.visualization.charts import EvaluationVisualizer

        viz = EvaluationVisualizer(output_dir=tmp_output, fmt="png", dpi=150)
        path = viz.box_plot(per_query_scores, title="Score Distributions")
        assert path.exists()
        assert path.suffix == ".png"

    def test_box_plot_file_not_empty(self, tmp_output: Path, per_query_scores: dict) -> None:
        from evaluation.visualization.charts import EvaluationVisualizer

        viz = EvaluationVisualizer(output_dir=tmp_output, fmt="png", dpi=150)
        path = viz.box_plot(per_query_scores, title="Test Box")
        assert path.stat().st_size > 0


class TestBarComparison:
    """T040: Tests for bar_comparison() generation."""

    def test_bar_comparison_returns_path(self, tmp_output: Path, sample_results: dict) -> None:
        from evaluation.visualization.charts import EvaluationVisualizer

        viz = EvaluationVisualizer(output_dir=tmp_output, fmt="png", dpi=150)
        path = viz.bar_comparison(sample_results, title="Bar Comparison")
        assert path.exists()
        assert path.suffix == ".png"

    def test_bar_comparison_file_not_empty(self, tmp_output: Path, sample_results: dict) -> None:
        from evaluation.visualization.charts import EvaluationVisualizer

        viz = EvaluationVisualizer(output_dir=tmp_output, fmt="png", dpi=150)
        path = viz.bar_comparison(sample_results, title="Test Bar")
        assert path.stat().st_size > 0


class TestHeatmap:
    """T041: Tests for heatmap() generation."""

    def test_heatmap_returns_path(self, tmp_output: Path, correlation_data: dict) -> None:
        from evaluation.visualization.charts import EvaluationVisualizer

        viz = EvaluationVisualizer(output_dir=tmp_output, fmt="png", dpi=150)
        path = viz.heatmap(correlation_data, title="Metric Correlations")
        assert path.exists()
        assert path.suffix == ".png"

    def test_heatmap_file_not_empty(self, tmp_output: Path, correlation_data: dict) -> None:
        from evaluation.visualization.charts import EvaluationVisualizer

        viz = EvaluationVisualizer(output_dir=tmp_output, fmt="png", dpi=150)
        path = viz.heatmap(correlation_data, title="Test Heatmap")
        assert path.stat().st_size > 0


class TestSVGOutput:
    """T042: Tests for SVG output format option."""

    def test_svg_radar_chart(self, tmp_output: Path, sample_results: dict) -> None:
        from evaluation.visualization.charts import EvaluationVisualizer

        viz = EvaluationVisualizer(output_dir=tmp_output, fmt="svg", dpi=300)
        path = viz.radar_chart(sample_results, title="SVG Radar")
        assert path.exists()
        assert path.suffix == ".svg"

    def test_svg_bar_comparison(self, tmp_output: Path, sample_results: dict) -> None:
        from evaluation.visualization.charts import EvaluationVisualizer

        viz = EvaluationVisualizer(output_dir=tmp_output, fmt="svg", dpi=300)
        path = viz.bar_comparison(sample_results, title="SVG Bar")
        assert path.exists()
        assert path.suffix == ".svg"

    def test_svg_box_plot(self, tmp_output: Path, per_query_scores: dict) -> None:
        from evaluation.visualization.charts import EvaluationVisualizer

        viz = EvaluationVisualizer(output_dir=tmp_output, fmt="svg", dpi=300)
        path = viz.box_plot(per_query_scores, title="SVG Box")
        assert path.exists()
        assert path.suffix == ".svg"

    def test_svg_heatmap(self, tmp_output: Path, correlation_data: dict) -> None:
        from evaluation.visualization.charts import EvaluationVisualizer

        viz = EvaluationVisualizer(output_dir=tmp_output, fmt="svg", dpi=300)
        path = viz.heatmap(correlation_data, title="SVG Heatmap")
        assert path.exists()
        assert path.suffix == ".svg"
