"""Ollama embedding provider using the official Python SDK.

Wraps ollama.embed() for any locally available model.
Per Article VIII, uses the ollama SDK directly without abstraction layers.
"""

from __future__ import annotations

import logging

import ollama

from evaluation.providers.base import EmbeddingProvider

logger = logging.getLogger(__name__)


class OllamaProvider(EmbeddingProvider):
    """Embedding provider using locally running Ollama models.

    Args:
        model: Model name as shown in `ollama list` (e.g. 'bge-m3').
        dimensions: Expected vector dimensionality for the model.
        host: Ollama API base URL. Defaults to http://localhost:11434.
    """

    def __init__(
        self,
        model: str,
        dimensions: int,
        host: str = "http://localhost:11434",
    ) -> None:
        self._model = model
        self._dimensions = dimensions
        self._client = ollama.Client(host=host)

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts using Ollama's embed endpoint.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors.

        Raises:
            ollama.ResponseError: If the model is not available locally.
        """
        logger.debug("Embedding %d texts with %s", len(texts), self._model)
        response = self._client.embed(model=self._model, input=texts)
        embeddings: list[list[float]] = response["embeddings"]
        return embeddings

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions
