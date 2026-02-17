"""Unit tests for embedding provider interface compliance.

Tests that providers implement the EmbeddingProvider ABC correctly.
Per Article III, provider interfaces are critical-path.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from evaluation.providers.base import EmbeddingProvider
from evaluation.providers.ollama_provider import OllamaProvider
from evaluation.providers.openai_provider import OpenAIProvider


class TestEmbeddingProviderABC:
    """Verify the abstract interface cannot be instantiated directly."""

    def test_cannot_instantiate_abc(self) -> None:
        with pytest.raises(TypeError):
            EmbeddingProvider()  # type: ignore[abstract]


class TestOllamaProvider:
    """Test OllamaProvider interface compliance with mocked SDK."""

    def test_properties(self) -> None:
        provider = OllamaProvider(model="bge-m3", dimensions=1024)
        assert provider.model_name == "bge-m3"
        assert provider.dimensions == 1024
        assert provider.cost_per_token == 0.0

    def test_is_embedding_provider(self) -> None:
        provider = OllamaProvider(model="bge-m3", dimensions=1024)
        assert isinstance(provider, EmbeddingProvider)

    @patch("evaluation.providers.ollama_provider.ollama.Client")
    def test_embed_calls_sdk(self, mock_client_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.embed.return_value = {"embeddings": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]}
        mock_client_cls.return_value = mock_client

        provider = OllamaProvider(model="bge-m3", dimensions=3)
        result = provider.embed(["hello", "world"])

        mock_client.embed.assert_called_once_with(model="bge-m3", input=["hello", "world"])
        assert len(result) == 2
        assert result[0] == [0.1, 0.2, 0.3]


class TestOpenAIProvider:
    """Test OpenAIProvider interface compliance with mocked SDK."""

    @patch("evaluation.providers.openai_provider.openai.OpenAI")
    def test_properties(self, mock_openai_cls: MagicMock) -> None:
        provider = OpenAIProvider(model="text-embedding-3-large", dimensions=3072)
        assert provider.model_name == "text-embedding-3-large"
        assert provider.dimensions == 3072
        assert provider.cost_per_token > 0.0
        assert provider.total_tokens == 0

    @patch("evaluation.providers.openai_provider.openai.OpenAI")
    def test_is_embedding_provider(self, mock_openai_cls: MagicMock) -> None:
        provider = OpenAIProvider(model="text-embedding-3-large", dimensions=3072)
        assert isinstance(provider, EmbeddingProvider)

    @patch("evaluation.providers.openai_provider.openai.OpenAI")
    def test_embed_tracks_tokens(self, mock_openai_cls: MagicMock) -> None:
        # Mock the embeddings response
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        mock_embedding = MagicMock()
        mock_embedding.embedding = [0.1, 0.2, 0.3]

        mock_usage = MagicMock()
        mock_usage.total_tokens = 10

        mock_response = MagicMock()
        mock_response.data = [mock_embedding]
        mock_response.usage = mock_usage

        mock_client.embeddings.create.return_value = mock_response

        provider = OpenAIProvider(model="text-embedding-3-large", dimensions=3)
        result = provider.embed(["hello"])

        assert len(result) == 1
        assert provider.total_tokens == 10
        assert provider.estimated_cost_usd > 0.0
