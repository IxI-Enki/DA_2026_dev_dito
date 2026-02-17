"""Thesis-quality evaluation charts.

Provides EvaluationVisualizer for radar, box, bar, heatmap,
speed-vs-quality scatter, and miss-analysis heatmap (DPI >= 300).
"""

from evaluation.visualization.charts import EvaluationVisualizer

__all__: list[str] = ["EvaluationVisualizer"]
