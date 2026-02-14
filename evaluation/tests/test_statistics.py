"""Unit tests for StatisticalAnalyzer: bootstrap_ci, paired_test, cohens_d, descriptive_stats, compare_configurations."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from evaluation.statistics.statistical_analysis import (
    BootstrapCI,
    ComparisonResult,
    StatisticalAnalyzer,
)


# ---- bootstrap_ci -----------------------------------------------------------


class TestBootstrapCI:
    def test_returns_bootstrap_ci_dataclass(self) -> None:
        analyzer = StatisticalAnalyzer()
        scores = [0.1, 0.2, 0.3, 0.4, 0.5] * 4  # 20 values
        ci = analyzer.bootstrap_ci(scores, n_iterations=100, confidence=0.95)
        assert isinstance(ci, BootstrapCI)
        assert hasattr(ci, "mean") and hasattr(ci, "ci_lower") and hasattr(ci, "ci_upper")
        assert hasattr(ci, "confidence")
        assert ci.confidence == 0.95
        assert ci.ci_lower <= ci.mean <= ci.ci_upper

    def test_small_sample(self) -> None:
        analyzer = StatisticalAnalyzer()
        ci = analyzer.bootstrap_ci([0.5, 0.6, 0.7], n_iterations=50)
        assert ci.mean == pytest.approx(0.6, abs=0.01)
        assert ci.ci_lower <= ci.ci_upper

    def test_empty_scores_raises_or_returns_sensible(self) -> None:
        analyzer = StatisticalAnalyzer()
        with pytest.raises((ValueError, ZeroDivisionError)):
            analyzer.bootstrap_ci([], n_iterations=100)


# ---- paired_test -----------------------------------------------------------


class TestPairedTest:
    def test_returns_comparison_result(self) -> None:
        analyzer = StatisticalAnalyzer()
        a = [0.2, 0.4, 0.5, 0.6, 0.8]
        b = [0.3, 0.5, 0.6, 0.7, 0.9]  # systematically higher
        result = analyzer.paired_test(a, b)
        assert isinstance(result, ComparisonResult)
        assert result.metric == "" or isinstance(result.metric, str)
        assert hasattr(result, "baseline_mean") and hasattr(result, "candidate_mean")
        assert hasattr(result, "p_value") and hasattr(result, "effect_size")
        assert hasattr(result, "effect_interpretation") and hasattr(result, "significant")

    def test_identical_lists(self) -> None:
        analyzer = StatisticalAnalyzer()
        x = [0.1, 0.2, 0.3]
        result = analyzer.paired_test(x, x[:])
        assert result.baseline_mean == result.candidate_mean
        assert result.difference == 0.0
        assert result.effect_size == 0.0

    def test_different_length_raises(self) -> None:
        analyzer = StatisticalAnalyzer()
        with pytest.raises(ValueError):
            analyzer.paired_test([1.0, 2.0], [1.0, 2.0, 3.0])


# ---- cohens_d ---------------------------------------------------------------


class TestCohensD:
    def test_returns_float_and_interpretation(self) -> None:
        analyzer = StatisticalAnalyzer()
        d, interp = analyzer.cohens_d([0.1, 0.2], [0.5, 0.6])
        assert isinstance(d, float)
        assert isinstance(interp, str)
        assert interp in ("vernachlaessigbar", "klein", "mittel", "gross")

    def test_identical_lists_zero_effect(self) -> None:
        analyzer = StatisticalAnalyzer()
        x = [0.5, 0.5, 0.5]
        d, interp = analyzer.cohens_d(x, x[:])
        assert d == 0.0
        assert "vernachlaessigbar" in interp.lower() or interp == "vernachlaessigbar"


# ---- descriptive_stats ------------------------------------------------------


class TestDescriptiveStats:
    def test_returns_dict_with_mean_median_std(self) -> None:
        analyzer = StatisticalAnalyzer()
        scores = [0.1, 0.2, 0.3, 0.4, 0.5]
        stats = analyzer.descriptive_stats(scores)
        assert isinstance(stats, dict)
        assert "mean" in stats and "median" in stats
        assert "std" in stats
        assert stats["mean"] == 0.3
        assert stats["median"] == 0.3

    def test_includes_quartiles_when_specified(self) -> None:
        analyzer = StatisticalAnalyzer()
        scores = [0.1, 0.2, 0.3, 0.4, 0.5]
        stats = analyzer.descriptive_stats(scores)
        assert "q1" in stats or "min" in stats

    def test_empty_list_raises_or_returns_nans(self) -> None:
        analyzer = StatisticalAnalyzer()
        stats = analyzer.descriptive_stats([])
        assert isinstance(stats, dict)
        assert stats.get("mean") is None or (stats.get("n", 0) == 0)


# ---- compare_configurations -------------------------------------------------


class TestCompareConfigurations:
    def test_returns_list_of_comparison_results(self) -> None:
        baseline = {
            "per_query": [
                {"rr": 0.5, "ndcg_at_10": 0.6, "p_at_5": 0.7},
                {"rr": 0.4, "ndcg_at_10": 0.5, "p_at_5": 0.6},
            ],
        }
        candidate = {
            "per_query": [
                {"rr": 0.6, "ndcg_at_10": 0.7, "p_at_5": 0.8},
                {"rr": 0.5, "ndcg_at_10": 0.6, "p_at_5": 0.7},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            base_path = Path(tmp) / "baseline.json"
            cand_path = Path(tmp) / "candidate.json"
            base_path.write_text(json.dumps(baseline), encoding="utf-8")
            cand_path.write_text(json.dumps(candidate), encoding="utf-8")
            analyzer = StatisticalAnalyzer()
            results = analyzer.compare_configurations(base_path, cand_path)
        assert isinstance(results, list)
        assert all(isinstance(r, ComparisonResult) for r in results)
        assert len(results) >= 1  # at least one metric (mrr/rr, ndcg_at_10, p_at_5)

    def test_missing_file_raises(self) -> None:
        analyzer = StatisticalAnalyzer()
        with tempfile.TemporaryDirectory() as tmp:
            with pytest.raises((FileNotFoundError, OSError)):
                analyzer.compare_configurations(Path(tmp) / "none.json", Path(tmp) / "other.json")
