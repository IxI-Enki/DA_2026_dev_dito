"""RAGAS evaluator wrapper.

Wraps the RAGAS library with an Ollama-compatible OpenAI endpoint so that
local LLMs can be used as the judge for context precision, faithfulness, etc.

Constitution Article X+XI: Evaluation-First + Thesis Alignment.
"""
from __future__ import annotations

import logging
from typing import Any

from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


class RAGASEvaluator:
    """Evaluate RAG quality using RAGAS metrics with a local LLM judge.

    Args:
        llm_base_url: OpenAI-compatible base URL (e.g. http://localhost:11434/v1).
        model: Model name to use as the judge LLM.
    """

    def __init__(self, llm_base_url: str, model: str) -> None:
        self.llm_base_url = llm_base_url
        self.model = model
        self._llm = ChatOpenAI(
            base_url=llm_base_url,
            model=model,
            temperature=0.0,
        )

    def evaluate(self, data: list[dict[str, Any]]) -> dict[str, float]:
        """Run RAGAS evaluation on a list of question/context/answer records.

        Args:
            data: List of dicts with keys ``question``, ``ground_truth``,
                ``contexts``, and ``answer``.

        Returns:
            Dict mapping metric name to mean score.
        """
        return self._run_ragas_evaluate(data)

    def _run_ragas_evaluate(self, data: list[dict[str, Any]]) -> dict[str, float]:
        """Execute RAGAS evaluation pipeline (override in tests via mock).

        Args:
            data: Same format as :meth:`evaluate`.

        Returns:
            Dict mapping RAGAS metric name to mean score.
        """
        try:
            from datasets import Dataset
            from ragas import evaluate
            from ragas.metrics import context_precision, faithfulness
        except ImportError as exc:
            raise ImportError(
                "RAGAS dependencies missing. Run: pip install ragas datasets langchain-openai"
            ) from exc

        if not data:
            return {}

        dataset = Dataset.from_list(data)
        result = evaluate(
            dataset,
            metrics=[context_precision, faithfulness],
            llm=self._llm,
        )
        return dict(result)
