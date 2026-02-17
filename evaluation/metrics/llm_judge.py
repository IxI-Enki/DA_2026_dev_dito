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
import logging
import re
import time
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
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "You are a precise evaluation assistant. "
                                    "Always reply with a single JSON object "
                                    'containing "score" (float 0.0-1.0) and '
                                    '"reasoning" (brief string). No other text.'
                                ),
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": self.temperature,
                        "max_tokens": self.max_tokens,
                    },
                    timeout=self.timeout,
                )
                if r.status_code != 200:
                    logger.warning(
                        "LLM HTTP %d (attempt %d): %s",
                        r.status_code,
                        attempt + 1,
                        r.text[:200],
                    )
                    if attempt < max_retries:
                        time.sleep(1)
                        continue
                    return f"ERROR: HTTP {r.status_code}"
                content = r.json()["choices"][0]["message"]["content"].strip()
                if content:
                    return content
                if attempt < max_retries:
                    continue
                return "ERROR: empty response"
            except requests.exceptions.Timeout:
                if attempt < max_retries:
                    logger.warning("LLM timeout (attempt %d), retrying", attempt + 1)
                    time.sleep(1)
                    continue
                return f"ERROR: Timeout after {self.timeout}s"
            except Exception as e:
                if attempt < max_retries:
                    time.sleep(1)
                    continue
                return f"ERROR: {e}"
        return "ERROR: All retries failed"

    def _parse_score(self, response: str) -> Optional[float]:
        """Extract a score in [0, 1] from LLM response."""
        if response.startswith("ERROR"):
            logger.debug("LLM error response: %s", response[:100])
            return None
        try:
            # Try JSON extraction first (preferred)
            if "{" in response and "}" in response:
                start = response.find("{")
                end = response.rfind("}") + 1
                data = json.loads(response[start:end])
                if "score" in data:
                    val = float(data["score"])
                    return self._normalize_score(val)
            # Fallback: look for "score": <number> pattern
            m = re.search(r'"?score"?\s*[:=]\s*([0-9]*\.?[0-9]+)', response, re.IGNORECASE)
            if m:
                return self._normalize_score(float(m.group(1)))
            # Last resort: any standalone number
            m = re.search(r"\b([01]\.?\d*)\b", response)
            if m:
                return self._normalize_score(float(m.group(1)))
            return None
        except Exception:
            logger.debug("Score parse failed for: %s", response[:100])
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

    def _call_llm_generate(self, prompt: str) -> str:
        """Call LLM for free-form generation (no scoring system prompt)."""
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
                },
                timeout=self.timeout,
            )
            if r.status_code != 200:
                return ""
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.warning("LLM generate call failed: %s", e)
            return ""

    def generate_answer(self, question: str, contexts: list[str]) -> str:
        """Generate an answer from retrieved contexts (for answer-based metrics).

        Args:
            question: The user question.
            contexts: Retrieved text chunks.

        Returns:
            Generated answer string, or empty string on failure.
        """
        if not contexts:
            return ""
        context_text = "\n---\n".join(c[:800] for c in contexts[:5])
        prompt = (
            f"Answer the following question based ONLY on the provided contexts. "
            f"Be concise and factual. If the contexts don't contain the answer, say so.\n\n"
            f"QUESTION: {question}\n\nCONTEXTS:\n{context_text}"
        )
        return self._call_llm_generate(prompt)

    def _faithfulness(self, answer: str, contexts: list[str]) -> Optional[float]:
        if not contexts or not answer:
            return None
        context_text = "\n---\n".join(c[:800] for c in contexts[:5])
        prompt = (
            f"Rate FAITHFULNESS: Is the answer factually supported by the contexts?\n\n"
            f"CONTEXTS:\n{context_text}\n\n"
            f"ANSWER: {answer}\n\n"
            f"Count factual claims in the answer. Score = supported_claims / total_claims."
        )
        return self._parse_score(self._call_llm(prompt))

    def _answer_relevancy(self, question: str, answer: str) -> Optional[float]:
        if not answer:
            return None
        prompt = (
            f"Rate ANSWER RELEVANCY: How well does the answer address the question?\n\n"
            f"QUESTION: {question}\n\n"
            f"ANSWER: {answer}\n\n"
            f"1.0=fully answers, 0.7-0.9=mostly, 0.4-0.6=partially, 0.0=irrelevant."
        )
        return self._parse_score(self._call_llm(prompt))

    def _context_precision(
        self, question: str, contexts: list[str], ground_truth: str
    ) -> Optional[float]:
        if not contexts:
            return 0.0
        numbered = "\n".join(f"[{i+1}] {c[:600]}" for i, c in enumerate(contexts[:5]))
        prompt = (
            f"Rate CONTEXT PRECISION: What fraction of retrieved contexts are relevant?\n\n"
            f"QUESTION: {question}\n"
            f"EXPECTED ANSWER: {ground_truth}\n\n"
            f"RETRIEVED CONTEXTS:\n{numbered}\n\n"
            f"1.0=all relevant, 0.5=half relevant, 0.0=none relevant."
        )
        return self._parse_score(self._call_llm(prompt))

    def _context_recall(self, contexts: list[str], ground_truth: str) -> Optional[float]:
        if not contexts:
            return 0.0
        context_text = "\n---\n".join(c[:600] for c in contexts[:5])
        prompt = (
            f"Rate CONTEXT RECALL: How much of the expected answer can be derived "
            f"from the retrieved contexts?\n\n"
            f"EXPECTED ANSWER: {ground_truth}\n\n"
            f"RETRIEVED CONTEXTS:\n{context_text}\n\n"
            f"1.0=fully derivable, 0.5=partially, 0.0=not at all."
        )
        return self._parse_score(self._call_llm(prompt))

    def _answer_correctness(self, answer: str, ground_truth: str) -> Optional[float]:
        if not answer or answer == ground_truth:
            return None
        prompt = (
            f"Rate ANSWER CORRECTNESS: Compare the generated answer to the ground truth.\n\n"
            f"GROUND TRUTH: {ground_truth}\n\n"
            f"GENERATED ANSWER: {answer}\n\n"
            f"1.0=semantically identical, 0.7-0.9=mostly correct, 0.4-0.6=partial, 0.0=wrong."
        )
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
            result.context_recall = self._context_recall(contexts or [], ground_truth)
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
        for key in (
            "faithfulness",
            "answer_relevancy",
            "context_precision",
            "context_recall",
            "answer_correctness",
        ):
            vals = [getattr(r, key) for r in results if getattr(r, key) is not None]
            out[key] = float(sum(vals) / len(vals)) if vals else 0.0
        valid = [
            out["faithfulness"],
            out["answer_relevancy"],
            out["context_precision"],
            out["context_recall"],
        ]
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
