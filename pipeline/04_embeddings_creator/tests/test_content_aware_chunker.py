"""TDD tests for ContentAwareChunker (chunking logic and Chunk format)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from document_loader import Document
from content_aware_chunker import ContentAwareChunker, Chunk


def _make_document(
    content: str,
    collection: str = "pages",
    file_stem: str = "test_page",
    content_type: str = "KNOWLEDGE",
    access_level: str = "public",
    page_id: str = "ns:test_page",
    source: str = "https://wiki.example/page",
    title: str = "Test Page",
    namespace: str = "ns",
) -> Document:
    frontmatter = {
        "title": title,
        "source": source,
        "namespace": namespace,
        "page_id": page_id,
        "access_level": access_level,
        "content_type": content_type,
    }
    return Document(
        file_path=Path(f"{file_stem}.md"),
        collection=collection,
        frontmatter=frontmatter,
        content=content,
    )


@pytest.fixture
def chunker(minimal_chunker_config):
    """ContentAwareChunker with mocked config."""
    with patch("content_aware_chunker.get_config", return_value=minimal_chunker_config):
        yield ContentAwareChunker()


class TestChunkStructure:
    """Chunk output format (id, text, metadata)."""

    def test_chunk_has_required_attributes(self, chunker):
        doc = _make_document("Short paragraph.")
        chunks = chunker.chunk_document(doc)
        assert len(chunks) >= 1
        c = chunks[0]
        assert hasattr(c, "chunk_id")
        assert hasattr(c, "text")
        assert hasattr(c, "chunk_index")
        assert hasattr(c, "total_chunks")
        assert hasattr(c, "document")
        assert hasattr(c, "source")
        assert hasattr(c, "collection")
        assert hasattr(c, "access_level")
        assert c.source == "https://wiki.example/page"
        assert c.collection == "pages"
        assert c.access_level == "public"

    def test_chunk_id_format(self, chunker):
        doc = _make_document("One paragraph.", file_stem="my_page", collection="pages")
        chunks = chunker.chunk_document(doc)
        assert len(chunks) == 1
        assert chunks[0].chunk_id == "pages_my_page_0"

    def test_chunk_index_and_total_chunks(self, chunker):
        doc = _make_document("A\n\nB\n\nC\n\nD\n\nE")
        chunks = chunker.chunk_document(doc)
        assert len(chunks) >= 1
        for i, c in enumerate(chunks):
            assert c.chunk_index == i
            assert c.total_chunks == len(chunks)


class TestShouldSkip:
    """Skip behavior by content_type."""

    def test_skip_empty_content_type(self, chunker):
        doc = _make_document("Some content.", content_type="EMPTY")
        chunks = chunker.chunk_document(doc)
        assert chunks == []

    def test_do_not_skip_knowledge(self, chunker):
        doc = _make_document("Some content.", content_type="KNOWLEDGE")
        chunks = chunker.chunk_document(doc)
        assert len(chunks) >= 1


class TestSemanticChunking:
    """Semantic (paragraph-based) chunking."""

    def test_short_text_single_chunk(self, chunker):
        doc = _make_document("One short paragraph.")
        chunks = chunker.chunk_document(doc)
        assert len(chunks) == 1
        # Text may include frontmatter prefix when include_frontmatter_in_text is True
        assert "One short paragraph." in chunks[0].text

    def test_respects_max_chunk_size(self, chunker):
        # Default max 512 chars; create text that exceeds it
        long_para = "x" * 600
        doc = _make_document(long_para)
        chunks = chunker.chunk_document(doc)
        assert len(chunks) >= 1
        for c in chunks:
            assert len(c.text) <= 600  # may be split with overlap

    def test_paragraph_boundaries(self, chunker):
        doc = _make_document("First para.\n\nSecond para.\n\nThird para.")
        chunks = chunker.chunk_document(doc)
        assert len(chunks) >= 1
        full_text = " ".join(c.text for c in chunks)
        assert "First" in full_text and "Second" in full_text and "Third" in full_text


class TestNaiveChunking:
    """Naive (fixed-size) chunking for content_type NEWS."""

    def test_naive_splits_long_text(self, chunker):
        doc = _make_document("a" * 1500, content_type="NEWS")
        chunks = chunker.chunk_document(doc)
        assert len(chunks) >= 2
        for c in chunks:
            assert len(c.text) <= 1100  # max_size + overlap


class TestPrepareText:
    """Frontmatter prefix in chunk text."""

    def test_prepare_text_adds_frontmatter_when_configured(self, chunker):
        doc = _make_document("Body text.", title="My Title", namespace="ns")
        text = chunker.prepare_text(doc)
        assert "Title:" in text or "title" in text.lower()
        assert "My Title" in text
        assert "Body text." in text

    def test_prepare_text_without_frontmatter_returns_content_only(self, minimal_chunker_config):
        minimal_chunker_config.text_prep["include_frontmatter_in_text"] = False
        with patch("content_aware_chunker.get_config", return_value=minimal_chunker_config):
            chunker = ContentAwareChunker()
        doc = _make_document("Body only.")
        text = chunker.prepare_text(doc)
        assert text.strip() == "Body only."


class TestGetChunkingConfig:
    """Config resolution by content_type."""

    def test_returns_content_type_config(self, chunker):
        cfg = chunker.get_chunking_config("KNOWLEDGE")
        assert cfg.get("method") == "recursive_header"

    def test_returns_default_for_unknown(self, chunker):
        cfg = chunker.get_chunking_config("UNKNOWN_TYPE")
        assert cfg.get("method") == "semantic"
        assert "max_chunk_size" in cfg


class TestChunkAll:
    """chunk_all aggregates multiple documents."""

    def test_chunk_all_returns_flat_list(self, chunker):
        docs = [
            _make_document("Doc one.", file_stem="a"),
            _make_document("Doc two.", file_stem="b"),
        ]
        chunks = chunker.chunk_all(docs)
        assert len(chunks) >= 2
        ids = {c.chunk_id for c in chunks}
        assert any("_a_" in id for id in ids)
        assert any("_b_" in id for id in ids)

    def test_chunk_all_skips_empty_type(self, chunker):
        docs = [
            _make_document("Keep.", content_type="KNOWLEDGE"),
            _make_document("Skip.", content_type="EMPTY"),
        ]
        chunks = chunker.chunk_all(docs)
        assert len(chunks) >= 1
        texts = [c.text for c in chunks]
        assert "Keep." in " ".join(texts)
        assert "Skip." not in " ".join(texts)
