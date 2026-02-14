"""Statistical analysis for evaluation results.

Bootstrap CIs, paired t-test/Wilcoxon, Cohen's d, descriptive stats.
Adapted to work with existing result JSON format (per_query scores).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)

# Per-query keys in result JSON that map to metric names for comparison
PER_QUERY_METRIC_KEYS = [
    ("rr", "mrr"),
    ("ndcg_at_10", "ndcg_at_10"),
    ("p_at_5", "precision_at_5"),
]


@dataclass(frozen=True)
class BootstrapCI:
    """Bootstrap confidence interval for a sample mean."""

    mean: float
    ci_lower: float
    ci_upper: float
    confidence: float


@dataclass(frozen=True)
class ComparisonResult:
    """Result of paired comparison (baseline vs candidate)."""

    metric: str
    baseline_mean: float
    candidate_mean: float
    difference: float
    p_value: float
    effect_size: float
    effect_interpretation: str
    significant: bool


def _interpret_cohens_d(d: float) -> str:
    """Return German interpretation of Cohen's d (thesis language)."""
    abs_d = abs(d)
    if abs_d < 0.2:
        return "vernachlaessigbar"
    if abs_d < 0.5:
        return "klein"
    if abs_d < 0.8:
        return "mittel"
    return "gross"


class StatisticalAnalyzer:
    """Statistical analysis for evaluation results (no state)."""

    def bootstrap_ci(
        self,
        scores: list[float],
        n_iterations: int = 1000,
        confidence: float = 0.95,
    ) -> BootstrapCI:
        """Bootstrap 95% CI for the mean of scores.

        Args:
            scores: Sample of per-query scores.
            n_iterations: Number of bootstrap samples.
            confidence: Confidence level (e.g. 0.95).

        Returns:
            BootstrapCI with mean, ci_lower, ci_upper, confidence.

        Raises:
            ValueError: If scores is empty.
        """
        if not scores:
            raise ValueError("bootstrap_ci requires at least one score")
        arr = np.asarray(scores, dtype=float)
        n = len(arr)
        rng = np.random.default_rng()
        bootstrap_means = [
            float(np.mean(rng.choice(arr, size=n, replace=True)))
            for _ in range(n_iterations)
        ]
        alpha = 1.0 - confidence
        low = (alpha / 2) * 100
        high = (1 - alpha / 2) * 100
        ci_lower = float(np.percentile(bootstrap_means, low))
        ci_upper = float(np.percentile(bootstrap_means, high))
        return BootstrapCI(
            mean=float(np.mean(arr)),
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            confidence=confidence,
        )

    def paired_test(
        self,
        scores_a: list[float],
        scores_b: list[float],
        metric: str = "",
    ) -> ComparisonResult:
        """Paired comparison: t-test or Wilcoxon based on normality.

        Args:
            scores_a: Baseline per-query scores.
            scores_b: Candidate per-query scores (same order as a).
            metric: Metric name for the result.

        Returns:
            ComparisonResult with means, p_value, Cohen's d, interpretation.

        Raises:
            ValueError: If lengths differ.
        """
        if len(scores_a) != len(scores_b):
            raise ValueError(
                f"paired_test requires same length: {len(scores_a)} vs {len(scores_b)}"
            )
        a = np.asarray(scores_a, dtype=float)
        b = np.asarray(scores_b, dtype=float)
        diff = b - a
        if len(diff) < 3:
            p_value = 1.0
            effect_size = 0.0
        else:
            _, p_sw = stats.shapiro(diff)
            if p_sw >= 0.05:
                stat, p_value = stats.ttest_rel(a, b)
            else:
                stat, p_value = stats.wilcoxon(a, b)
            if np.std(a) > 0 or np.std(b) > 0:
                pooled_std = np.sqrt((np.var(a) + np.var(b)) / 2)
                effect_size = float((np.mean(b) - np.mean(a)) / pooled_std) if pooled_std > 0 else 0.0
            else:
                effect_size = 0.0
        interp = _interpret_cohens_d(effect_size)
        return ComparisonResult(
            metric=metric,
            baseline_mean=float(np.mean(a)),
            candidate_mean=float(np.mean(b)),
            difference=float(np.mean(b) - np.mean(a)),
            p_value=float(p_value),
            effect_size=effect_size,
            effect_interpretation=interp,
            significant=(float(p_value) < 0.05),
        )

    def cohens_d(
        self,
        scores_a: list[float],
        scores_b: list[float],
    ) -> tuple[float, str]:
        """Cohen's d for two paired samples and German interpretation.

        Returns:
            (d, interpretation) with interpretation in thesis language.
        """
        a = np.asarray(scores_a, dtype=float)
        b = np.asarray(scores_b, dtype=float)
        if len(a) != len(b) or len(a) < 2:
            return 0.0, "vernachlaessigbar"
        pooled_std = np.sqrt((np.var(a) + np.var(b)) / 2)
        if pooled_std == 0:
            return 0.0, "vernachlaessigbar"
        d = float((np.mean(b) - np.mean(a)) / pooled_std)
        return d, _interpret_cohens_d(d)

    def descriptive_stats(self, scores: list[float]) -> dict[str, float]:
        """Descriptive statistics: mean, median, std, n, q1, q3, min, max."""
        if not scores:
            return {"n": 0.0, "mean": 0.0, "median": 0.0, "std": 0.0}
        arr = np.asarray(scores, dtype=float)
        return {
            "n": float(len(arr)),
            "mean": float(np.mean(arr)),
            "median": float(np.median(arr)),
            "std": float(np.std(arr)) if len(arr) > 1 else 0.0,
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "q1": float(np.percentile(arr, 25)),
            "q3": float(np.percentile(arr, 75)),
        }

    def compare_configurations(
        self,
        baseline_path: Path,
        candidate_path: Path,
    ) -> list[ComparisonResult]:
        """Load two result JSONs and compare per-metric with paired test.

        Expects result JSON with "per_query" list of dicts containing
        rr, ndcg_at_10, p_at_5 (and optionally more). Returns one
        ComparisonResult per metric present in both files.
        """
        base_path = Path(baseline_path)
        cand_path = Path(candidate_path)
        if not base_path.exists():
            raise FileNotFoundError(f"Baseline not found: {base_path}")
        if not cand_path.exists():
            raise FileNotFoundError(f"Candidate not found: {cand_path}")

        with open(base_path, encoding="utf-8") as f:
            base_data = json.load(f)
        with open(cand_path, encoding="utf-8") as f:
            cand_data = json.load(f)

        base_per = base_data.get("per_query", [])
        cand_per = cand_data.get("per_query", [])
        if len(base_per) != len(cand_per):
            logger.warning(
                "Per-query length mismatch: baseline=%d, candidate=%d",
                len(base_per),
                len(cand_per),
            )

        results: list[ComparisonResult] = []
        for key, metric_name in PER_QUERY_METRIC_KEYS:
            if not base_per or not cand_per:
                continue
            if key not in base_per[0] or key not in cand_per[0]:
                continue
            scores_a = [q[key] for q in base_per]
            scores_b = [q[key] for q in cand_per]
            if len(scores_a) != len(scores_b):
                continue
            res = self.paired_test(scores_a, scores_b, metric=metric_name)
            results.append(res)
        return results
