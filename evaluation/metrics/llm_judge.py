"""LLM-as-Judge metrics for RAG evaluation (RAGAS-style).

Implements:
- Faithfulness: factual consistency of the answer with the context
- Answer Relevancy: relevance of the answer to the question
- Context Precision: precision of retrieved contexts
- Context Recall: completeness of retrieved contexts for the ground truth
- Answer Correctness: correctness of the answer vs. ground truth

Uses any OpenAI-compatible LLM endpoint (LM Studio, Ollama, OpenAI API).
"""

from __future__ import annotations

import json
import re
import time
import logging
from dataclasses import dataclass
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class LLMJudgeResult:
    """Result of LLM-as-Judge evaluation for a single question."""

    question_id: str
    faithfulness: Optional[float] = None
    answer_relevancy: Optional[float] = None
    context_precision: Optional[float] = None
    context_recall: Optional[float] = None
    answer_correctness: Optional[float] = None
    error: Optional[str] = None


class LLMJudgeMetrics:
    """Compute RAGAS-style metrics via LLM-as-Judge (OpenAI-compatible API)."""

    def __init__(
        self,
        llm_base_url: str = "http://localhost:1234/v1",
        llm_model: str = "qwen2.5-7b-instruct",
        llm_api_key: str = "not-needed",
        temperature: float = 0.1,
        max_tokens: int = 500,
        timeout: int = 60,
    ):
        self.llm_base_url = llm_base_url.rstrip("/")
        self.llm_model = llm_model
        self.llm_api_key = llm_api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    def _call_llm(self, prompt: str, max_retries: int = 2) -> str:
        """Call LLM and return response text. On failure returns error string."""
        for attempt in range(max_retries + 1):
            try:
                r = requests.post(
                    f"{self.llm_base_url}/chat/completions",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.llm_api_key}",
                    },
                    json={
                        "model": self.llm_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": self.temperature,
                        "max_tokens": self.max_tokens,
                        "stop": ["\n\n", "```", "---"],
                    },
                    timeout=self.timeout,
                )
                if r.status_code != 200:
                    if attempt < max_retries:
                        continue
                    return f"ERROR: HTTP {r.status_code}"
                content = r.json()["choices"][0]["message"]["content"].strip()
                if content and ("{" in content or "score" in content.lower()):
                    return content
                if attempt < max_retries:
                    continue
                return content or "ERROR: empty response"
            except requests.exceptions.Timeout:
                if attempt < max_retries:
                    logger.warning("LLM timeout (attempt %d), retrying", attempt + 1)
                    continue
                return f"ERROR: Timeout after {self.timeout}s"
            except Exception as e:
                if attempt < max_retries:
                    continue
                return f"ERROR: {e}"
        return "ERROR: All retries failed"

    def _parse_score(self, response: str) -> Optional[float]:
        """Extract a score in [0, 1] from LLM response."""
        try:
            if "{" in response:
                start = response.find("{")
                end = response.rfind("}") + 1
                data = json.loads(response[start:end])
                if "score" in data:
                    val = float(data["score"])
                    return self._normalize_score(val)
            for num in re.findall(
                r"(?:score|Score|SCORE)?[:\s]*([0-9]*\.?[0-9]+)", response
            ):
                val = float(num)
                n = self._normalize_score(val)
                if n is not None:
                    return n
            return None
        except Exception:
            return None

    @staticmethod
    def _normalize_score(val: float) -> Optional[float]:
        if val < 0:
            return None
        if 0 <= val <= 1:
            return val
        if 1 < val <= 10:
            return val / 10
        if 10 < val <= 100:
            return val / 100
        return None

    def _faithfulness(self, answer: str, contexts: list[str]) -> Optional[float]:
        context_text = "\n---\n".join((c[:500] for c in (contexts or [])[:5]))
        prompt = f"""You are an evaluator for RAG systems. Rate the FAITHFULNESS of the following answer to the context.

CONTEXT:
{context_text}

ANSWER:
{answer}

TASK: Identify all factual claims in the answer. For each, check if it is supported by the context. Score = (supported claims) / (total claims). Reply ONLY with JSON: {{"score": <0.0-1.0>, "reasoning": "<brief>"}}"""
        return self._parse_score(self._call_llm(prompt))

    def _answer_relevancy(self, question: str, answer: str) -> Optional[float]:
        prompt = f"""You are an evaluator for RAG systems. Rate how well the ANSWER addresses the QUESTION.

QUESTION: {question}

ANSWER: {answer}

Score: 1.0 = fully answers, 0.7-0.9 = mostly, 0.4-0.6 = partially, 0.0 = irrelevant. Reply ONLY with JSON: {{"score": <0.0-1.0>, "reasoning": "<brief>"}}"""
        return self._parse_score(self._call_llm(prompt))

    def _context_precision(
        self, question: str, contexts: list[str], ground_truth: str
    ) -> Optional[float]:
        if not contexts:
            return 0.0
        numbered = "\n".join(
            f"[{i+1}] {c[:400]}..." if len(c) > 400 else f"[{i+1}] {c}"
            for i, c in enumerate(contexts[:5])
        )
        prompt = f"""Rate CONTEXT PRECISION for this RAG query.

QUESTION: {question}
EXPECTED ANSWER: {ground_truth}

CONTEXTS:
{numbered}

How many contexts are relevant? 1.0=all, 0.8=most, 0.5=half, 0.0=none. Reply ONLY with JSON: {{"score": <0.0-1.0>, "reasoning": "<brief>"}}"""
        return self._parse_score(self._call_llm(prompt))

    def _context_recall(self, contexts: list[str], ground_truth: str) -> Optional[float]:
        context_text = "\n---\n".join(
            (c[:300] for c in (contexts or [])[:3])
        )
        prompt = f"""CONTEXT RECALL: How much of the expected answer can be derived from the contexts?

Expected answer: "{ground_truth}"

Contexts:
{context_text}

Score: 1.0=100%, 0.8=80%, 0.5=50%, 0.0=0%. Reply ONLY with JSON: {{"score": <0.0-1.0>, "reasoning": "<brief>"}}"""
        return self._parse_score(self._call_llm(prompt))

    def _answer_correctness(self, answer: str, ground_truth: str) -> Optional[float]:
        prompt = f"""You are an evaluator for RAG systems. Compare the GENERATED answer to the GROUND TRUTH.

GROUND TRUTH: {ground_truth}

GENERATED ANSWER: {answer}

Score: 1.0=semantically same, 0.8-0.9=mostly correct, 0.5-0.7=partial, 0.0=wrong. Reply ONLY with JSON: {{"score": <0.0-1.0>, "reasoning": "<brief>"}}"""
        return self._parse_score(self._call_llm(prompt))

    def evaluate_single(
        self,
        question_id: str,
        question: str,
        answer: str,
        contexts: list[str],
        ground_truth: str,
    ) -> LLMJudgeResult:
        """Compute all LLM-as-Judge metrics for one Q&A pair."""
        result = LLMJudgeResult(question_id=question_id)
        try:
            result.faithfulness = self._faithfulness(answer, contexts or [])
            result.answer_relevancy = self._answer_relevancy(question, answer)
            result.context_precision = self._context_precision(
                question, contexts or [], ground_truth
            )
            result.context_recall = self._context_recall(
                contexts or [], ground_truth
            )
            result.answer_correctness = self._answer_correctness(answer, ground_truth)
        except Exception as e:
            result.error = str(e)
            logger.warning("LLMJudge evaluate_single failed: %s", e)
        return result

    def evaluate_batch(
        self,
        data: list[dict[str, Any]],
        show_progress: bool = True,
    ) -> list[LLMJudgeResult]:
        """Evaluate a list of items. Each item: question_id?, question, answer, contexts, ground_truth."""
        try:
            from tqdm import tqdm
            iterator = tqdm(data, desc="LLM-as-Judge") if show_progress else data
        except ImportError:
            iterator = data
        results = []
        for item in iterator:
            r = self.evaluate_single(
                question_id=item.get("question_id", item.get("id", "")),
                question=item["question"],
                answer=item["answer"],
                contexts=item.get("contexts", []),
                ground_truth=item["ground_truth"],
            )
            results.append(r)
        return results

    def aggregate(self, results: list[LLMJudgeResult]) -> dict[str, float]:
        """Return mean score per metric (for pipeline compatibility)."""
        out: dict[str, float] = {}
        for key in ("faithfulness", "answer_relevancy", "context_precision", "context_recall", "answer_correctness"):
            vals = [getattr(r, key) for r in results if getattr(r, key) is not None]
            out[key] = float(sum(vals) / len(vals)) if vals else 0.0
        valid = [out["faithfulness"], out["answer_relevancy"], out["context_precision"], out["context_recall"]]
        valid = [v for v in valid if v > 0]
        out["ragas_score"] = len(valid) / sum(1 / v for v in valid) if valid else 0.0
        return out


class LLMJudgeEvaluator:
    """Evaluator interface for eval_pipeline: evaluate(data) -> dict[str, float]."""

    def __init__(
        self,
        llm_base_url: str,
        model: str,
        temperature: float = 0.1,
        api_key: str = "not-needed",
    ):
        self._metrics = LLMJudgeMetrics(
            llm_base_url=llm_base_url,
            llm_model=model,
            llm_api_key=api_key,
            temperature=temperature,
        )

    def evaluate(self, ragas_data: list[dict[str, Any]]) -> dict[str, float]:
        """Run LLM-as-Judge on each item and return aggregate mean scores.

        ragas_data: list of {question, answer, ground_truth, contexts}.
        Returns: {faithfulness, answer_relevancy, context_precision, context_recall, answer_correctness, ragas_score}.
        """
        if not ragas_data:
            return {}
        results = self._metrics.evaluate_batch(ragas_data, show_progress=True)
        return self._metrics.aggregate(results)
