"""Bootstrap confidence intervals and statistical helpers for evaluation metrics.

Ported from techstack/ragas/professional_evaluation/metrics/statistical_analysis.py.
Use evaluation.statistics for full StatisticalAnalyzer (paired tests, compare_configurations).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

import numpy as np


@dataclass
class ConfidenceInterval:
    """Confidence interval for a metric."""

    mean: float
    lower: float
    upper: float
    confidence_level: float
    method: str  # "bootstrap" or "t"


def bootstrap_confidence_interval(
    data: List[float],
    statistic_func: Callable[[np.ndarray], float] = np.mean,
    confidence_level: float = 0.95,
    n_iterations: int = 1000,
    random_seed: Optional[int] = 42,
) -> ConfidenceInterval:
    """Bootstrap confidence interval for a statistic.

    Args:
        data: Sample values.
        statistic_func: Function to compute the statistic (default: mean).
        confidence_level: e.g. 0.95 for 95% CI.
        n_iterations: Number of bootstrap samples.
        random_seed: For reproducibility.

    Returns:
        ConfidenceInterval with mean, lower, upper, confidence_level, method="bootstrap".
    """
    if random_seed is not None:
        np.random.seed(random_seed)
    arr = np.asarray([x for x in data if x is not None and not np.isnan(x)], dtype=float)
    if len(arr) == 0:
        return ConfidenceInterval(
            mean=np.nan,
            lower=np.nan,
            upper=np.nan,
            confidence_level=confidence_level,
            method="bootstrap",
        )
    if len(arr) == 1:
        val = float(arr[0])
        return ConfidenceInterval(
            mean=val,
            lower=val,
            upper=val,
            confidence_level=confidence_level,
            method="bootstrap",
        )
    bootstrap_stats = []
    for _ in range(n_iterations):
        sample = np.random.choice(arr, size=len(arr), replace=True)
        bootstrap_stats.append(statistic_func(sample))
    bootstrap_stats = np.asarray(bootstrap_stats)
    alpha = 1 - confidence_level
    lower = float(np.percentile(bootstrap_stats, alpha / 2 * 100))
    upper = float(np.percentile(bootstrap_stats, (1 - alpha / 2) * 100))
    return ConfidenceInterval(
        mean=float(statistic_func(arr)),
        lower=lower,
        upper=upper,
        confidence_level=confidence_level,
        method="bootstrap",
    )


