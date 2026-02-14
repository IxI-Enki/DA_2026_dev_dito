"""RAGAS.io LLM-as-Judge evaluation wrapper.

Uses existing ground truth (e.g. leowiki_qa_50_verified.json). Evaluates
Context Precision/Recall, Faithfulness, Answer Correctness via Ollama.
"""

from __future__ import annotations

import logging
import math
from typing import Any

from langchain_openai import ChatOpenAI
from pydantic import SecretStr

logger = logging.getLogger(__name__)


def _build_samples(data: list[dict[str, Any]]) -> list[Any]:
    """Build RAGAS SingleTurnSample list from our ground-truth-style rows."""
    try:
        from ragas import EvaluationDataset, SingleTurnSample
    except ImportError:
        return []
    samples = []
    for row in data:
        user_input = row.get("question", row.get("user_input", ""))
        reference = row.get("ground_truth", row.get("reference", ""))
        response = row.get("answer", row.get("response", reference))
        contexts = row.get("contexts", row.get("retrieved_contexts", []))
        if not isinstance(contexts, list):
            contexts = [contexts] if contexts else []
        if not user_input and not response:
            continue
        samples.append(
            SingleTurnSample(
                user_input=str(user_input),
                reference=str(reference),
                response=str(response),
                retrieved_contexts=[str(c) for c in contexts],
            )
        )
    return samples


def _get_metrics(has_contexts: bool = True):
    """Return RAGAS metric list. When has_contexts is False (ground-truth-only, no RAG run),
    only answer_correctness is used so we avoid faithfulness/context metrics that need
    statement extraction and contexts (they cause 'No statements were generated' and parse failures).
    """
    try:
        from ragas.metrics import answer_correctness
        if not has_contexts:
            return [answer_correctness]
        from ragas.metrics import context_precision, faithfulness
        metrics = [context_precision, faithfulness, answer_correctness]
        try:
            from ragas.metrics import context_recall
            metrics.insert(1, context_recall)
        except ImportError:
            pass
        return metrics
    except ImportError:
        return []


class RAGASEvaluator:
    """Wraps RAGAS.io library for LLM-as-Judge evaluation (Ollama)."""

    def __init__(
        self,
        llm_base_url: str,
        model: str,
        temperature: float = 0.0,
    ) -> None:
        self.llm_base_url = llm_base_url
        self.model = model
        self.temperature = temperature
        self.llm = ChatOpenAI(
            base_url=llm_base_url,
            model=model,
            temperature=temperature,
            api_key=SecretStr("not-needed"),
        )

    def evaluate(self, data: list[dict[str, Any]]) -> dict[str, float]:
        """Run RAGAS evaluation on a list of rows (question, ground_truth, contexts, answer).

        Args:
            data: List of dicts with question, ground_truth, contexts (list), answer (optional).

        Returns:
            Dict of metric_name -> aggregate score. Empty dict on error or no data.
        """
        if not data:
            return {}
        return self._run_ragas_evaluate(data)

    def _run_ragas_evaluate(self, data: list[dict[str, Any]]) -> dict[str, float]:
        """Build dataset, call ragas.evaluate; log and continue on per-question errors where possible."""
        try:
            from ragas import EvaluationDataset, evaluate
        except ImportError as e:
            logger.warning("RAGAS not available: %s", e)
            return {}
        samples = _build_samples(data)
        if not samples:
            logger.warning("No valid samples for RAGAS")
            return {}
        def _contexts_list(row: dict) -> list:
            c = row.get("contexts", row.get("retrieved_contexts", []))
            return c if isinstance(c, list) else ([c] if c else [])
        has_contexts = any(len(_contexts_list(row)) > 0 for row in data)
        if not has_contexts:
            logger.info("No contexts in data; running answer_correctness only (skip faithfulness/context metrics).")
        metrics = _get_metrics(has_contexts=has_contexts)
        if not metrics:
            logger.warning("No RAGAS metrics available")
            return {}
        try:
            dataset = EvaluationDataset(samples=samples)
            eval_kw: dict[str, Any] = {
                "dataset": dataset,
                "metrics": metrics,
                "show_progress": True,
                "raise_exceptions": False,
            }
            try:
                result = evaluate(llm=self.llm, **eval_kw)
            except TypeError:
                eval_kw.pop("llm", None)
                result = evaluate(**eval_kw)  # raise_exceptions still in eval_kw
        except Exception as e:
            logger.exception("RAGAS evaluate failed: %s", e)
            return {}
        scores: dict[str, float] = {}
        result_scores = getattr(result, "scores", None)
        if result_scores and isinstance(result_scores, dict):
            for k, v in result_scores.items():
                if isinstance(v, (int, float)):
                    scores[k] = float(v) if not math.isnan(float(v)) else 0.0
                elif hasattr(v, "__iter__") and not isinstance(v, str):
                    vals: list[float] = []
                    try:
                        for x in v:
                            try:
                                f = float(x)
                                if not math.isnan(f):
                                    vals.append(f)
                            except (TypeError, ValueError):
                                pass
                        scores[k] = sum(vals) / len(vals) if vals else 0.0
                    except (TypeError, ValueError):
                        scores[k] = 0.0
        to_pandas_fn = getattr(result, "to_pandas", None)
        if callable(to_pandas_fn) and not scores:
            try:
                df = to_pandas_fn()
                if df is not None and hasattr(df, "columns"):
                    cols = getattr(df, "columns", ())
                    for col in cols:
                        if col not in scores:
                            ser = getattr(df, "__getitem__", lambda _: None)(col)
                            if ser is not None and hasattr(ser, "mean"):
                                m = ser.mean()
                                scores[col] = float(m) if m is not None and not math.isnan(float(m)) else 0.0
            except Exception:
                pass
        return scores
