"""OpenAI embedding provider with cost tracking.

Uses the official openai Python SDK. Tracks token usage and estimated
cost per run for NFR-003 compliance (< $5/run).
Per Article VI, API key is loaded from a token file, never hardcoded.
"""

from __future__ import annotations

import logging
from pathlib import Path

import openai

from evaluation.providers.base import EmbeddingProvider

logger = logging.getLogger(__name__)

# Pricing as of 2026-02: text-embedding-3-large = $0.13/1M tokens
_OPENAI_COST_PER_TOKEN: dict[str, float] = {
    "text-embedding-3-large": 0.00000013,
    "text-embedding-3-small": 0.00000002,
}


class OpenAIProvider(EmbeddingProvider):
    """Embedding provider using OpenAI API with cost tracking.

    Args:
        model: OpenAI model name (e.g. 'text-embedding-3-large').
        dimensions: Expected vector dimensionality.
        api_key_file: Path to file containing the OpenAI API key.
            Per Article VI, secrets are in separate files.
    """

    def __init__(
        self,
        model: str,
        dimensions: int,
        api_key_file: str | Path | None = None,
    ) -> None:
        self._model = model
        self._dimensions = dimensions
        self._total_tokens = 0

        api_key: str | None = None
        if api_key_file is not None:
            key_path = Path(api_key_file)
            if key_path.exists():
                api_key = key_path.read_text(encoding="utf-8").strip()
            else:
                logger.warning("API key file not found: %s", key_path)

        self._client = openai.OpenAI(api_key=api_key)

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts using OpenAI embeddings API.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors.

        Raises:
            openai.APIError: On API communication failure.
        """
        logger.debug("Embedding %d texts with OpenAI %s", len(texts), self._model)
        response = self._client.embeddings.create(
            model=self._model,
            input=texts,
        )
        self._total_tokens += response.usage.total_tokens
        return [item.embedding for item in response.data]

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def cost_per_token(self) -> float:
        return _OPENAI_COST_PER_TOKEN.get(self._model, 0.0)

    @property
    def total_tokens(self) -> int:
        """Total tokens consumed across all embed() calls."""
        return self._total_tokens

    @property
    def estimated_cost_usd(self) -> float:
        """Estimated total cost in USD based on consumed tokens."""
        return self._total_tokens * self.cost_per_token
