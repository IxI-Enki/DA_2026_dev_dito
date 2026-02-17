"""Abstract base class for embedding providers.

Defines the interface that all embedding providers (Ollama, OpenAI, etc.)
must implement. Per Article VIII, providers use framework SDKs directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Abstract embedding provider for model-agnostic evaluation."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts into vectors.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors (one per input text).
        """
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Human-readable model identifier (e.g. 'bge-m3')."""
        ...

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Dimensionality of the embedding vectors."""
        ...

    @property
    def cost_per_token(self) -> float:
        """Cost per token in USD. Returns 0.0 for local models."""
        return 0.0
