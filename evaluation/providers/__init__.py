"""Embedding provider abstraction for model-agnostic evaluation."""

from evaluation.providers.base import EmbeddingProvider
from evaluation.providers.ollama_provider import OllamaProvider
from evaluation.providers.sentence_transformers_provider import SentenceTransformersProvider

__all__ = ["EmbeddingProvider", "OllamaProvider", "SentenceTransformersProvider"]
