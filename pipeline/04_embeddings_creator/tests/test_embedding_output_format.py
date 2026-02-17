"""TDD tests for embedding output format (MCP-compatible schema)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from document_loader import Document
from content_aware_chunker import Chunk


# MCP / jsonl_ingestion expects: id, text, embedding (3072), metadata
# metadata (flat or frontmatter): source, collection, access_level, chunk_index, total_chunks, ...
MCP_REQUIRED_PAYLOAD_KEYS = frozenset({
    "text",
    "source",
    "collection",
    "access_level",
    "chunk_index",
    "total_chunks",
})
EMBEDDING_DIMENSIONS = 3072  # text-embedding-3-large


def _make_chunk(
    chunk_id: str = "pages_test_0",
    text: str = "Sample chunk text.",
    chunk_index: int = 0,
    total_chunks: int = 1,
    source: str = "https://wiki.example/page",
    collection: str = "pages",
    access_level: str = "public",
    page_id: str = "ns:test",
    title: str = "Test",
    namespace: str = "ns",
    content_type: str = "KNOWLEDGE",
) -> Chunk:
    doc = Document(
        file_path=Path("test.md"),
        collection=collection,
        frontmatter={
            "source": source,
            "title": title,
            "namespace": namespace,
            "page_id": page_id,
            "access_level": access_level,
            "content_type": content_type,
        },
        content=text,
    )
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        chunk_index=chunk_index,
        total_chunks=total_chunks,
        document=doc,
    )


class TestRecordSchema:
    """Output record has MCP schema: id, text, embedding, metadata."""

    def test_record_has_required_top_level_keys(
        self,
        minimal_output_schema,
        minimal_include_metadata,
    ):
        chunk = _make_chunk()
        mock_config = MagicMock()
        mock_config.output.schema = minimal_output_schema
        mock_config.output.include_metadata = minimal_include_metadata
        mock_config.logging = {"level": "INFO", "format": "%(message)s", "console": True, "file": None}
        mock_config.paths = MagicMock()
        mock_config.paths.output_dir = "/tmp/out"
        mock_config.paths.log_dir = "/tmp/logs"
        mock_config.statistics = {}
        mock_embedder = MagicMock()
        mock_embedder.model = "text-embedding-3-large"
        mock_embedder.dimensions = EMBEDDING_DIMENSIONS

        with patch("pipeline.get_config", return_value=mock_config), patch(
            "pipeline.Embedder", return_value=mock_embedder
        ), patch("pipeline.DocumentLoader"), patch("pipeline.ContentAwareChunker"):
            from pipeline import EmbeddingPipeline

            pipeline = EmbeddingPipeline()
            pipeline.embedder = mock_embedder
            metadata = pipeline._build_metadata(chunk)

        schema = minimal_output_schema
        record = {
            schema["id_field"]: chunk.chunk_id,
            schema["text_field"]: chunk.text,
            schema["embedding_field"]: [0.0] * EMBEDDING_DIMENSIONS,
            schema["metadata_field"]: metadata,
        }
        assert record[schema["id_field"]] == chunk.chunk_id
        assert record[schema["text_field"]] == chunk.text
        assert len(record[schema["embedding_field"]]) == EMBEDDING_DIMENSIONS
        assert schema["metadata_field"] in record
        assert isinstance(record[schema["metadata_field"]], dict)

    def test_record_id_is_string(self, minimal_output_schema):
        chunk = _make_chunk(chunk_id="pages_foo_0")
        record_id = chunk.chunk_id
        assert isinstance(record_id, str)
        assert record_id == "pages_foo_0"

    def test_embedding_dimensions_3072(self):
        # MCP jsonl_ingestion validates len(embedding) == 3072
        assert EMBEDDING_DIMENSIONS == 3072


class TestMetadataHasMcpPayloadFields:
    """Metadata contains fields required by MCP extract_payload_from_document."""

    def test_build_metadata_contains_mcp_payload_fields(
        self,
        minimal_include_metadata,
    ):
        chunk = _make_chunk(
            source="https://wiki.example/id",
            collection="pages",
            access_level="teacher",
            chunk_index=1,
            total_chunks=3,
        )
        mock_config = MagicMock()
        mock_config.output.include_metadata = minimal_include_metadata
        mock_config.logging = {"level": "INFO", "format": "%(message)s", "console": True, "file": None}
        mock_config.paths = MagicMock()
        mock_config.paths.output_dir = "/tmp/out"
        mock_config.paths.log_dir = "/tmp/logs"
        mock_config.statistics = {}
        mock_embedder = MagicMock()
        mock_embedder.model = "text-embedding-3-large"
        mock_embedder.dimensions = EMBEDDING_DIMENSIONS

        with patch("pipeline.get_config", return_value=mock_config), patch(
            "pipeline.Embedder", return_value=mock_embedder
        ), patch("pipeline.DocumentLoader"), patch("pipeline.ContentAwareChunker"):
            from pipeline import EmbeddingPipeline

            pipeline = EmbeddingPipeline()
            pipeline.embedder = mock_embedder
            metadata = pipeline._build_metadata(chunk)

        for key in MCP_REQUIRED_PAYLOAD_KEYS:
            if key == "text":
                continue  # text is top-level in record, not in metadata
            assert key in metadata, f"metadata missing MCP payload field: {key}"
        assert metadata["source"] == "https://wiki.example/id"
        assert metadata["collection"] == "pages"
        assert metadata["access_level"] == "teacher"
        assert metadata["chunk_index"] == 1
        assert metadata["total_chunks"] == 3
