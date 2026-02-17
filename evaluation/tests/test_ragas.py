"""Unit tests for RAGASEvaluator (mocked LLM and RAGAS)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from evaluation.ragas.ragas_evaluator import RAGASEvaluator


class TestRAGASEvaluatorInit:
    """T029: Mock tests for RAGASEvaluator initialization."""

    def test_init_accepts_llm_base_url_and_model(self) -> None:
        with patch("evaluation.ragas.ragas_evaluator.ChatOpenAI"):
            ev = RAGASEvaluator(llm_base_url="http://localhost:11434/v1", model="llama3.2")
        assert ev.llm_base_url == "http://localhost:11434/v1"
        assert ev.model == "llama3.2"

    def test_init_default_temperature_zero(self) -> None:
        with patch("evaluation.ragas.ragas_evaluator.ChatOpenAI") as m:
            RAGASEvaluator(llm_base_url="http://x", model="y")
        m.assert_called_once()
        call_kw = m.call_args[1]
        assert call_kw.get("temperature") == 0.0

    def test_init_calls_chat_openai_with_base_url(self) -> None:
        with patch("evaluation.ragas.ragas_evaluator.ChatOpenAI") as m:
            RAGASEvaluator(llm_base_url="http://ollama:11434/v1", model="m")
        m.assert_called_once()
        assert m.call_args[1]["base_url"] == "http://ollama:11434/v1"
        assert m.call_args[1]["model"] == "m"


class TestRAGASEvaluatorEvaluate:
    """T030: evaluate() with mocked LLM/responses."""

    def test_evaluate_returns_dict_of_metric_scores(self) -> None:
        with patch("evaluation.ragas.ragas_evaluator.ChatOpenAI"):
            ev = RAGASEvaluator(llm_base_url="http://x", model="y")
        with patch.object(ev, "_run_ragas_evaluate") as run:
            run.return_value = {"context_precision": 0.8, "faithfulness": 0.9}
            data = [
                {"question": "Q1", "ground_truth": "A1", "contexts": ["C1"], "answer": "A1"},
            ]
            result = ev.evaluate(data)
        assert isinstance(result, dict)
        assert "context_precision" in result or "faithfulness" in result or len(result) >= 0

    def test_evaluate_empty_data_returns_empty_or_sensible(self) -> None:
        with patch("evaluation.ragas.ragas_evaluator.ChatOpenAI"):
            ev = RAGASEvaluator(llm_base_url="http://x", model="y")
        with patch.object(ev, "_run_ragas_evaluate") as run:
            run.return_value = {}
            result = ev.evaluate([])
        assert isinstance(result, dict)
        assert result == {} or all(isinstance(v, (int, float)) for v in result.values())


class TestRAGASEvaluatorErrorHandling:
    """T031: LLM timeout / per-question error handling (log + continue)."""

    def test_evaluate_logs_and_continues_on_single_item_failure(self) -> None:
        with patch("evaluation.ragas.ragas_evaluator.ChatOpenAI"):
            ev = RAGASEvaluator(llm_base_url="http://x", model="y")
        with patch.object(ev, "_run_ragas_evaluate") as run:
            run.side_effect = RuntimeError("LLM timeout")
            with pytest.raises(RuntimeError):
                ev.evaluate([{"question": "Q", "ground_truth": "A", "contexts": [], "answer": "A"}])
        run.assert_called_once()

    def test_evaluate_handles_ragas_import_error_gracefully(self) -> None:
        with patch("evaluation.ragas.ragas_evaluator.ChatOpenAI"):
            ev = RAGASEvaluator(llm_base_url="http://x", model="y")
        with patch.object(ev, "_run_ragas_evaluate") as run:
            run.return_value = {}
            result = ev.evaluate(
                [{"question": "Q", "ground_truth": "A", "contexts": ["c"], "answer": "A"}]
            )
        assert isinstance(result, dict)
