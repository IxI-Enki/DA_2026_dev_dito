"""Unit tests for retrieval metrics: MRR, Precision@k, NDCG@k.

Verified against hand-calculated IR textbook examples.
Per Article III, metrics are critical-path and require unit tests.
"""

import math

import pytest

from evaluation.metrics.mrr import mean_reciprocal_rank, reciprocal_rank
from evaluation.metrics.ndcg import ndcg_at_k, mean_ndcg_at_k
from evaluation.metrics.precision_at_k import precision_at_k, mean_precision_at_k


# ── MRR Tests ────────────────────────────────────────────────────────────────


class TestReciprocalRank:
    def test_relevant_at_rank_1(self) -> None:
        assert reciprocal_rank(["a", "b", "c"], {"a"}) == 1.0

    def test_relevant_at_rank_2(self) -> None:
        assert reciprocal_rank(["a", "b", "c"], {"b"}) == 0.5

    def test_relevant_at_rank_3(self) -> None:
        assert reciprocal_rank(["a", "b", "c"], {"c"}) == pytest.approx(1 / 3)

    def test_no_relevant_results(self) -> None:
        assert reciprocal_rank(["a", "b", "c"], {"x"}) == 0.0

    def test_empty_results(self) -> None:
        assert reciprocal_rank([], {"a"}) == 0.0

    def test_empty_relevant_set(self) -> None:
        assert reciprocal_rank(["a", "b"], set()) == 0.0

    def test_multiple_relevant_returns_first(self) -> None:
        # Only the rank of the FIRST relevant result matters
        assert reciprocal_rank(["a", "b", "c"], {"b", "c"}) == 0.5


class TestMeanReciprocalRank:
    def test_basic_mrr(self) -> None:
        queries = [
            (["a", "b", "c"], {"a"}),  # RR = 1.0
            (["x", "b", "c"], {"b"}),  # RR = 0.5
            (["x", "y", "c"], {"c"}),  # RR = 1/3
        ]
        expected = (1.0 + 0.5 + 1 / 3) / 3
        assert mean_reciprocal_rank(queries) == pytest.approx(expected)

    def test_empty_queries(self) -> None:
        assert mean_reciprocal_rank([]) == 0.0

    def test_all_miss(self) -> None:
        queries = [
            (["a", "b"], {"x"}),
            (["c", "d"], {"y"}),
        ]
        assert mean_reciprocal_rank(queries) == 0.0

    def test_perfect_mrr(self) -> None:
        queries = [
            (["a", "b"], {"a"}),
            (["c", "d"], {"c"}),
        ]
        assert mean_reciprocal_rank(queries) == 1.0


# ── Precision@k Tests ────────────────────────────────────────────────────────


class TestPrecisionAtK:
    def test_all_relevant(self) -> None:
        assert precision_at_k(["a", "b", "c"], {"a", "b", "c"}, k=3) == 1.0

    def test_none_relevant(self) -> None:
        assert precision_at_k(["a", "b", "c"], {"x", "y"}, k=3) == 0.0

    def test_partial_relevant(self) -> None:
        # 2 out of 5 relevant
        assert precision_at_k(
            ["a", "b", "c", "d", "e"], {"a", "c"}, k=5
        ) == pytest.approx(0.4)

    def test_k_larger_than_results(self) -> None:
        # Only 2 results but k=5, precision = 1/5 = 0.2
        assert precision_at_k(["a", "b"], {"a"}, k=5) == pytest.approx(0.2)

    def test_k_zero(self) -> None:
        assert precision_at_k(["a", "b"], {"a"}, k=0) == 0.0

    def test_empty_results(self) -> None:
        assert precision_at_k([], {"a"}, k=5) == 0.0

    def test_p_at_5(self) -> None:
        # FF1 thesis metric: P@5
        ranked = ["p1", "p2", "p3", "p4", "p5", "p6", "p7"]
        relevant = {"p1", "p3", "p5"}
        assert precision_at_k(ranked, relevant, k=5) == pytest.approx(3 / 5)


class TestMeanPrecisionAtK:
    def test_basic(self) -> None:
        queries = [
            (["a", "b"], {"a"}),      # P@2 = 0.5
            (["c", "d"], {"c", "d"}),  # P@2 = 1.0
        ]
        assert mean_precision_at_k(queries, k=2) == pytest.approx(0.75)

    def test_empty(self) -> None:
        assert mean_precision_at_k([], k=5) == 0.0


# ── NDCG@k Tests ─────────────────────────────────────────────────────────────


class TestNdcgAtK:
    def test_perfect_ranking(self) -> None:
        # Documents ranked in ideal order by relevance
        ranked = ["a", "b", "c"]
        relevance = {"a": 3, "b": 2, "c": 1}
        assert ndcg_at_k(ranked, relevance, k=3) == pytest.approx(1.0)

    def test_reverse_ranking(self) -> None:
        # Worst possible ranking (least relevant first)
        ranked = ["c", "b", "a"]
        relevance = {"a": 3, "b": 2, "c": 1}
        result = ndcg_at_k(ranked, relevance, k=3)
        assert 0.0 < result < 1.0

    def test_no_relevant_documents(self) -> None:
        ranked = ["a", "b", "c"]
        relevance: dict[str, int] = {}
        assert ndcg_at_k(ranked, relevance, k=3) == 0.0

    def test_empty_results(self) -> None:
        ranked: list[str] = []
        relevance = {"a": 3}
        assert ndcg_at_k(ranked, relevance, k=3) == 0.0

    def test_k_zero(self) -> None:
        assert ndcg_at_k(["a"], {"a": 3}, k=0) == 0.0

    def test_hand_calculated_example(self) -> None:
        """Verify against hand-calculated DCG/IDCG.

        ranked: [d1, d2, d3] with relevance {d1: 3, d2: 1, d3: 2}
        DCG@3 = (2^3-1)/log2(2) + (2^1-1)/log2(3) + (2^2-1)/log2(4)
              = 7/1 + 1/1.585 + 3/2 = 7.0 + 0.631 + 1.5 = 9.131

        Ideal ranking: [d1, d3, d2] with relevance [3, 2, 1]
        IDCG@3 = (2^3-1)/log2(2) + (2^2-1)/log2(3) + (2^1-1)/log2(4)
               = 7/1 + 3/1.585 + 1/2 = 7.0 + 1.893 + 0.5 = 9.393

        NDCG@3 = 9.131 / 9.393 ≈ 0.972
        """
        ranked = ["d1", "d2", "d3"]
        relevance = {"d1": 3, "d2": 1, "d3": 2}

        dcg = (7 / math.log2(2)) + (1 / math.log2(3)) + (3 / math.log2(4))
        idcg = (7 / math.log2(2)) + (3 / math.log2(3)) + (1 / math.log2(4))
        expected = dcg / idcg

        assert ndcg_at_k(ranked, relevance, k=3) == pytest.approx(expected, rel=1e-6)

    def test_single_relevant_at_various_positions(self) -> None:
        """NDCG decreases as the single relevant document moves down."""
        relevance = {"target": 3}
        ndcg_rank1 = ndcg_at_k(["target", "x", "y"], relevance, k=3)
        ndcg_rank2 = ndcg_at_k(["x", "target", "y"], relevance, k=3)
        ndcg_rank3 = ndcg_at_k(["x", "y", "target"], relevance, k=3)
        assert ndcg_rank1 > ndcg_rank2 > ndcg_rank3


class TestMeanNdcgAtK:
    def test_basic(self) -> None:
        queries = [
            (["a", "b"], {"a": 3, "b": 1}),
            (["c", "d"], {"c": 2, "d": 2}),
        ]
        result = mean_ndcg_at_k(queries, k=2)
        assert 0.0 < result <= 1.0

    def test_empty(self) -> None:
        assert mean_ndcg_at_k([], k=10) == 0.0
