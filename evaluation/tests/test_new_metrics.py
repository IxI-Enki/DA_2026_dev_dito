"""Unit tests for Recall@K, MAP, and Hit Rate.

Same style as test_metrics.py; verified against hand-calculated examples.
"""

from __future__ import annotations

import pytest

from evaluation.metrics.recall_at_k import recall_at_k, mean_recall_at_k
from evaluation.metrics.mean_average_precision import (
    average_precision,
    mean_average_precision,
)
from evaluation.metrics.hit_rate import hit_at_k, hit_rate


# ---- Recall@K ----------------------------------------------------------------


class TestRecallAtK:
    def test_all_relevant_in_top_k(self) -> None:
        assert recall_at_k(["a", "b", "c"], {"a", "b", "c"}, k=3) == 1.0

    def test_some_relevant_in_top_k(self) -> None:
        assert recall_at_k(["a", "b", "x"], {"a", "b", "c"}, k=3) == pytest.approx(2 / 3)

    def test_none_relevant_in_top_k(self) -> None:
        assert recall_at_k(["x", "y", "z"], {"a", "b"}, k=3) == 0.0

    def test_empty_relevant(self) -> None:
        assert recall_at_k(["a", "b"], set(), k=2) == 0.0

    def test_empty_results(self) -> None:
        assert recall_at_k([], {"a", "b"}, k=2) == 0.0

    def test_k_larger_than_results(self) -> None:
        assert recall_at_k(["a", "b"], {"a", "b"}, k=10) == 1.0

    def test_k_smaller_than_relevant_count(self) -> None:
        # 2 relevant in top 2, 3 relevant total -> 2/3
        assert recall_at_k(["a", "b", "c"], {"a", "b", "c"}, k=2) == pytest.approx(2 / 3)


class TestMeanRecallAtK:
    def test_basic_mean_recall(self) -> None:
        queries = [
            (["a", "b", "c"], {"a", "b"}),   # 2/2 = 1.0
            (["x", "a", "b"], {"a", "b"}),   # 2/2 = 1.0
            (["x", "y", "z"], {"a", "b"}),   # 0/2 = 0.0
        ]
        assert mean_recall_at_k(queries, k=3) == pytest.approx(2 / 3)

    def test_empty_queries(self) -> None:
        assert mean_recall_at_k([], k=5) == 0.0


# ---- MAP --------------------------------------------------------------------


class TestAveragePrecision:
    def test_perfect_ranking(self) -> None:
        assert average_precision(["a", "b", "c"], {"a", "b", "c"}) == 1.0

    def test_first_two_relevant(self) -> None:
        # Ranks 1,2 relevant -> P@1=1, P@2=1 -> AP = (1+1)/2 = 1.0
        assert average_precision(["a", "b", "x"], {"a", "b"}) == 1.0

    def test_one_relevant_at_rank_2(self) -> None:
        # One relevant at rank 2 -> P@2 = 1/2 -> AP = 0.5
        assert average_precision(["x", "a", "b"], {"a"}) == 0.5

    def test_no_relevant(self) -> None:
        assert average_precision(["x", "y"], {"a"}) == 0.0

    def test_empty_relevant(self) -> None:
        assert average_precision(["a", "b"], set()) == 0.0


class TestMeanAveragePrecision:
    def test_basic_map(self) -> None:
        queries = [
            (["a", "b"], {"a", "b"}),   # AP = 1.0
            (["x", "a"], {"a"}),       # AP = 0.5
        ]
        assert mean_average_precision(queries) == pytest.approx(0.75)

    def test_empty_queries(self) -> None:
        assert mean_average_precision([]) == 0.0


# ---- Hit Rate ---------------------------------------------------------------


class TestHitAtK:
    def test_hit_when_relevant_in_top_k(self) -> None:
        assert hit_at_k(["a", "b", "c"], {"b"}, k=3) == 1

    def test_miss_when_no_relevant_in_top_k(self) -> None:
        assert hit_at_k(["a", "b", "c"], {"x"}, k=3) == 0

    def test_hit_at_rank_1(self) -> None:
        assert hit_at_k(["a", "b"], {"a"}, k=2) == 1

    def test_empty_relevant(self) -> None:
        assert hit_at_k(["a", "b"], set(), k=2) == 0

    def test_empty_results(self) -> None:
        assert hit_at_k([], {"a"}, k=2) == 0


class TestHitRate:
    def test_all_hits(self) -> None:
        queries = [
            (["a", "b"], {"a"}),
            (["c", "d"], {"c"}),
        ]
        assert hit_rate(queries, k=2) == 1.0

    def test_all_misses(self) -> None:
        queries = [
            (["a", "b"], {"x"}),
            (["c", "d"], {"y"}),
        ]
        assert hit_rate(queries, k=2) == 0.0

    def test_half_hits(self) -> None:
        queries = [
            (["a", "b"], {"a"}),
            (["c", "d"], {"x"}),
        ]
        assert hit_rate(queries, k=2) == 0.5

    def test_empty_queries(self) -> None:
        assert hit_rate([], k=5) == 0.0
