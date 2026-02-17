"""Sentence-Transformers embedding provider for local HuggingFace models.

Loads models from HuggingFace Hub via the sentence-transformers library,
runs inference on GPU (CUDA), and supports float16 for large models.
Provides explicit GPU memory cleanup for sequential model evaluation.
"""

from __future__ import annotations

import gc
import logging
from typing import Literal

import torch
from sentence_transformers import SentenceTransformer

from evaluation.providers.base import EmbeddingProvider

logger = logging.getLogger(__name__)


class SentenceTransformersProvider(EmbeddingProvider):
    """Embedding provider using sentence-transformers with GPU support.

    Args:
        model: HuggingFace model ID (e.g. 'BAAI/bge-m3-unsupervised').
        dimensions: Expected embedding vector dimensionality.
        torch_dtype: Torch dtype string ('float16' or 'float32').
            Use float16 for large models (>2 GB) on limited VRAM.
        device: Torch device ('cuda', 'cpu', or 'auto').
        batch_size: Default batch size for encoding.
        trust_remote_code: Whether to trust remote code from HuggingFace.
    """

    def __init__(
        self,
        model: str,
        dimensions: int,
        torch_dtype: Literal["float16", "float32"] = "float32",
        device: str = "cuda",
        batch_size: int = 32,
        trust_remote_code: bool = True,
    ) -> None:
        self._model_id = model
        self._dimensions = dimensions
        self._batch_size = batch_size

        dtype = torch.float16 if torch_dtype == "float16" else torch.float32

        if device == "cuda" and not torch.cuda.is_available():
            logger.warning("CUDA not available, falling back to CPU")
            device = "cpu"

        logger.info(
            "Loading %s (dim=%d, dtype=%s, device=%s)",
            model, dimensions, torch_dtype, device,
        )

        self._st_model = SentenceTransformer(
            model,
            device=device,
            trust_remote_code=trust_remote_code,
            model_kwargs={"torch_dtype": dtype},
        )

        if device == "cuda":
            vram_mb = torch.cuda.memory_allocated() / 1024 / 1024
            logger.info("Model loaded. VRAM used: %.0f MB", vram_mb)

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts using the loaded sentence-transformers model.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors (each a list of floats).
        """
        logger.debug("Encoding %d texts with %s", len(texts), self._model_id)
        embeddings = self._st_model.encode(
            texts,
            batch_size=self._batch_size,
            show_progress_bar=len(texts) > 100,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return embeddings.tolist()

    @property
    def model_name(self) -> str:
        return self._model_id

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def unload(self) -> None:
        """Explicitly release GPU memory for sequential model evaluation."""
        logger.info("Unloading %s from GPU", self._model_id)
        del self._st_model
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            vram_mb = torch.cuda.memory_allocated() / 1024 / 1024
            logger.info("VRAM after unload: %.0f MB", vram_mb)
