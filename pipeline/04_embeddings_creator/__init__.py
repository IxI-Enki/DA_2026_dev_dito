"""
Qdrant Embeddings Creator
=========================
Creates optimized embeddings for Qdrant based on Deep Evaluation strategies.
"""

from __future__ import annotations

from content_aware_chunker import ContentAwareChunker
from document_loader import DocumentLoader
from embedder import Embedder

from config import Config, get_config
from pipeline import EmbeddingPipeline

__all__ = [
    "get_config",
    "Config",
    "DocumentLoader",
    "ContentAwareChunker",
    "Embedder",
    "EmbeddingPipeline",
]
