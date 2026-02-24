"""Statistical analysis for evaluation results.

Provides Bootstrap CIs, paired tests (t-test/Wilcoxon), Cohen's d,
and per-difficulty category breakdown.
"""

from evaluation.statistics.category_analysis import breakdown_by_difficulty
from evaluation.statistics.statistical_analysis import (
    BootstrapCI,
    ComparisonResult,
    StatisticalAnalyzer,
)

__all__ = [
    "BootstrapCI",
    "ComparisonResult",
    "StatisticalAnalyzer",
    "breakdown_by_difficulty",
]
