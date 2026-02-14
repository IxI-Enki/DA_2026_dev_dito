"""RAGAS.io LLM-as-Judge evaluation wrapper.

Provides RAGASEvaluator for Context Precision/Recall, Faithfulness,
and Answer Correctness via Ollama OpenAI-compatible API.
"""

from evaluation.ragas.ragas_evaluator import RAGASEvaluator

__all__: list[str] = ["RAGASEvaluator"]
