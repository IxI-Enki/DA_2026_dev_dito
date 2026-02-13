"""Embedding provider abstraction for model-agnostic evaluation."""

from evaluation.providers.base import EmbeddingProvider
from evaluation.providers.ollama_provider import OllamaProvider

__all__ = ["EmbeddingProvider", "OllamaProvider"]
