"""Retrieval quality metrics: MRR, Precision@k, NDCG@k, Recall@k, MAP, Hit Rate; LLM-as-Judge."""

from evaluation.metrics.hit_rate import hit_at_k, hit_rate
from evaluation.metrics.llm_judge import (
    LLMJudgeEvaluator,
    LLMJudgeMetrics,
    LLMJudgeResult,
)
from evaluation.metrics.mean_average_precision import (
    average_precision,
    mean_average_precision,
)
from evaluation.metrics.mrr import mean_reciprocal_rank
from evaluation.metrics.ndcg import ndcg_at_k
from evaluation.metrics.precision_at_k import precision_at_k
from evaluation.metrics.recall_at_k import mean_recall_at_k, recall_at_k
from evaluation.metrics.statistical import (
    ConfidenceInterval,
    bootstrap_confidence_interval,
)

__all__ = [
    "mean_reciprocal_rank",
    "precision_at_k",
    "ndcg_at_k",
    "recall_at_k",
    "mean_recall_at_k",
    "average_precision",
    "mean_average_precision",
    "hit_at_k",
    "hit_rate",
    "LLMJudgeEvaluator",
    "LLMJudgeMetrics",
    "LLMJudgeResult",
    "ConfidenceInterval",
    "bootstrap_confidence_interval",
]
