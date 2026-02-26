"""
Content-Aware Chunker
=====================
Chunks documents based on their content type using strategies from Deep Evaluation.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from document_loader import Document

from config import get_config

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Represents a text chunk ready for embedding."""

    chunk_id: str
    text: str
    chunk_index: int
    total_chunks: int
    document: Document

    # Metadata from document
    source: str = ""
    collection: str = ""
    title: str = ""
    namespace: str = ""
    page_id: str = ""
    media_id: str = ""
    access_level: str = "public"
    content_type: str = ""

    def __post_init__(self):
        """Copy metadata from document."""
        self.source = self.document.source
        self.collection = self.document.collection
        self.title = self.document.title
        self.namespace = self.document.namespace
        self.page_id = self.document.page_id
        self.media_id = self.document.media_id
        self.access_level = self.document.access_level
        self.content_type = self.document.content_type


class ContentAwareChunker:
    """
    Chunks documents based on their content type.
    Uses strategies defined in preprocessing_strategies.yaml from Deep Evaluation.
    """

    # Header patterns for semantic chunking
    HEADER_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

    def __init__(self):
        self.config = get_config()
        self.default_config = self.config.chunking.default
        self.content_type_configs = self.config.chunking.content_types
        self.text_prep = self.config.text_prep

    def get_chunking_config(self, content_type: str) -> dict[str, Any]:
        """Get chunking configuration for a content type."""
        if content_type and content_type.upper() in self.content_type_configs:
            return self.content_type_configs[content_type.upper()]
        return self.default_config

    def should_skip(self, document: Document) -> bool:
        """Check if document should be skipped based on content type."""
        config = self.get_chunking_config(document.content_type)
        return config.get("action") == "skip"

    def prepare_text(self, document: Document) -> str:
        """
        Prepare text for chunking by optionally including frontmatter fields.

        This improves semantic search by adding title, namespace, etc. to the chunk.
        """
        text = document.content

        if not self.text_prep.get("include_frontmatter_in_text", False):
            return text

        fields = self.text_prep.get("frontmatter_fields_in_text", [])
        if not fields:
            return text

        prefix_parts = []
        for field in fields:
            value = document.frontmatter.get(field)
            if value:
                if isinstance(value, list):
                    value = ", ".join(str(v) for v in value)
                prefix_parts.append(f"{field.title()}: {value}")

        if prefix_parts:
            prefix = "\n".join(prefix_parts)
            return f"{prefix}\n\n{text}"

        return text

    # #region agent log helpers
    @staticmethod
    def _dbg_write(payload: dict) -> None:
        import json, time
        payload.setdefault("timestamp", int(time.time() * 1000))
        log_path = r"d:\_Repositories\_Diploma_Thesis_Repositories\dev_dito\.cursor\debug.log"
        try:
            with open(log_path, "a", encoding="utf-8") as _f:
                _f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception:
            pass
    # #endregion

    def chunk_document(self, document: Document) -> list[Chunk]:
        """
        Chunk a document based on its content type.

        Args:
            document: Document to chunk

        Returns:
            List of Chunk objects
        """
        # Check if should skip
        if self.should_skip(document):
            logger.debug(
                f"Skipping document: {document.doc_id} (content_type: {document.content_type})"
            )
            return []

        # Get chunking config for this content type
        config = self.get_chunking_config(document.content_type)
        method = config.get("method", "semantic")

        # Prepare text (add frontmatter fields if configured)
        text = self.prepare_text(document)

        # Skip empty documents
        if not text.strip():
            logger.warning(f"Empty document after preparation: {document.doc_id}")
            return []

        # Chunk based on method
        if method == "recursive_header":
            raw_chunks = self._chunk_recursive_header(text, config)
        elif method == "semantic":
            raw_chunks = self._chunk_semantic(text, config)
        elif method == "naive":
            raw_chunks = self._chunk_naive(text, config)
        elif method in ("table_aware", "table_row", "markdown_table"):
            raw_chunks = self._chunk_table_aware(text, config)
            # #region agent log – H1/H2/H4/H5
            if document.page_id == "org:termine-2026":
                for _ci, _ct in enumerate(raw_chunks):
                    _tbl_lines = sum(1 for _l in _ct.split("\n") if _l.strip().startswith("|"))
                    _has_prefix = _ct.startswith("## ")
                    _has_hitm = "AHITM" in _ct or "BHITM" in _ct
                    _has_muendlich = "ndliche" in _ct  # covers ü and mojibake ?
                    _umlaut_ok = "ü" in _ct or "ö" in _ct or "ä" in _ct
                    ContentAwareChunker._dbg_write({
                        "hypothesisId": "H1-H2-H4", "location": "content_aware_chunker.py:chunk_document",
                        "message": f"table_chunk {_ci}/{len(raw_chunks)-1}",
                        "data": {"page_id": document.page_id, "chunk_idx": _ci,
                                 "total_chunks": len(raw_chunks), "char_len": len(_ct),
                                 "table_lines": _tbl_lines, "has_header_prefix": _has_prefix,
                                 "has_hitm": _has_hitm, "has_muendlich": _has_muendlich,
                                 "umlaut_ok": _umlaut_ok,
                                 "preview_start": _ct[:120].replace("\n", " "),
                                 "preview_end": _ct[-80:].replace("\n", " ")}})
            # #endregion
        elif method in ("metadata_only", "parent_context", "index_as_context_only"):
            # For these methods, create a single "metadata" chunk
            raw_chunks = [text[: config.get("max_chunk_size", 500)]]
        else:
            raw_chunks = self._chunk_semantic(text, config)

        # #region agent log – H5
        if document.page_id == "org:termine-2026":
            ContentAwareChunker._dbg_write({
                "hypothesisId": "H5", "location": "content_aware_chunker.py:chunk_document",
                "message": "access_level check for org:termine-2026",
                "data": {"access_level": document.access_level, "content_type": document.content_type,
                         "method": method, "total_raw_chunks": len(raw_chunks)}})
        # #endregion

        # Create Chunk objects
        total_chunks = len(raw_chunks)
        chunks = []

        for i, chunk_text in enumerate(raw_chunks):
            chunk_id = f"{document.collection}_{document.file_path.stem}_{i}"

            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    text=chunk_text,
                    chunk_index=i,
                    total_chunks=total_chunks,
                    document=document,
                )
            )

        return chunks

    def _chunk_semantic(self, text: str, config: dict[str, Any]) -> list[str]:
        """
        Semantic chunking by paragraphs with size limits.
        """
        max_size = config.get("max_chunk_size", 1024)
        overlap = config.get("chunk_overlap", 150)
        min_size = config.get("min_chunk_size", 200)

        chunks = []
        current_chunk = []
        current_size = 0

        # Split by paragraphs (double newline)
        paragraphs = text.split("\n\n")

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para_size = len(para)

            # If this paragraph alone exceeds max_size, split it
            if para_size > max_size:
                # Flush current chunk first
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_size = 0

                # Split large paragraph by sentences or fixed size
                sub_chunks = self._split_large_paragraph(para, max_size, overlap)
                chunks.extend(sub_chunks)
                continue

            # If adding this paragraph would exceed max_size, start new chunk
            if current_size + para_size > max_size and current_chunk:
                chunks.append("\n\n".join(current_chunk))

                # Keep last paragraph for overlap if configured
                if overlap > 0 and current_chunk:
                    last_para = current_chunk[-1]
                    if len(last_para) < overlap:
                        current_chunk = [last_para]
                        current_size = len(last_para)
                    else:
                        current_chunk = []
                        current_size = 0
                else:
                    current_chunk = []
                    current_size = 0

            current_chunk.append(para)
            current_size += para_size

        # Add remaining content
        if current_chunk:
            final_chunk = "\n\n".join(current_chunk)
            if len(final_chunk) >= min_size or not chunks:
                chunks.append(final_chunk)
            elif chunks:
                # Append to last chunk if too small
                chunks[-1] += "\n\n" + final_chunk

        return chunks

    def _chunk_recursive_header(self, text: str, config: dict[str, Any]) -> list[str]:
        """
        Chunk by headers (Markdown headings), then by size.
        """
        max_size = config.get("max_chunk_size", 1024)
        config.get("chunk_overlap", 150)

        # Find all headers and their positions
        headers = list(self.HEADER_PATTERN.finditer(text))

        if not headers:
            # No headers, fall back to semantic chunking
            return self._chunk_semantic(text, config)

        chunks = []

        for i, header in enumerate(headers):
            # Get content until next header
            start = header.start()
            end = headers[i + 1].start() if i + 1 < len(headers) else len(text)

            section = text[start:end].strip()

            if len(section) > max_size:
                # Split large section semantically
                sub_config = {**config, "max_chunk_size": max_size}
                sub_chunks = self._chunk_semantic(section, sub_config)
                chunks.extend(sub_chunks)
            elif section:
                chunks.append(section)

        # Handle content before first header
        if headers and headers[0].start() > 0:
            intro = text[: headers[0].start()].strip()
            if intro:
                if len(intro) > max_size:
                    chunks = self._chunk_semantic(intro, config) + chunks
                else:
                    chunks.insert(0, intro)

        return chunks

    def _chunk_naive(self, text: str, config: dict[str, Any]) -> list[str]:
        """
        Simple fixed-size chunking with overlap.
        """
        max_size = config.get("max_chunk_size", 1024)
        overlap = config.get("chunk_overlap", 150)

        chunks = []
        start = 0

        while start < len(text):
            end = start + max_size
            chunk = text[start:end]

            # Try to end at a sentence boundary
            if end < len(text):
                last_period = chunk.rfind(". ")
                if last_period > max_size // 2:
                    end = start + last_period + 1
                    chunk = text[start:end]

            chunks.append(chunk.strip())
            start = end - overlap if overlap > 0 else end

        return chunks

    def _split_large_paragraph(self, text: str, max_size: int, overlap: int) -> list[str]:
        """Split a large paragraph into smaller chunks."""
        # Try to split by sentences first
        sentences = re.split(r"(?<=[.!?])\s+", text)

        if len(sentences) > 1:
            chunks = []
            current = []
            current_size = 0

            for sentence in sentences:
                if current_size + len(sentence) > max_size and current:
                    chunks.append(" ".join(current))
                    current = [sentence]
                    current_size = len(sentence)
                else:
                    current.append(sentence)
                    current_size += len(sentence)

            if current:
                chunks.append(" ".join(current))

            return chunks

        # Fall back to fixed-size if no sentences
        return self._chunk_naive(text, {"max_chunk_size": max_size, "chunk_overlap": overlap})

    def _chunk_table_aware(self, text: str, config: dict[str, Any]) -> list[str]:
        """
        Table-aware chunking that keeps Markdown table rows intact.

        Strategy:
        - Non-table sections that consist only of headings are NOT emitted as
          standalone chunks. Instead they are saved as section_context and
          prepended to every table chunk that follows (including split sub-chunks).
          This ensures "## Juni 2026" never gets lost as an isolated 12-char chunk.
        - Non-table sections with real content are emitted via _chunk_semantic.
        - Each contiguous table block is kept as one chunk if within max_chunk_size.
        - Oversized tables are split by rows with the column header row AND the
          section heading repeated in each sub-chunk so context is never lost.
        """
        max_size = config.get("max_chunk_size", 2048)

        TABLE_LINE = re.compile(r"^\s*\|")
        SEP_LINE = re.compile(r"^\s*\|[\s\-:|]+\|")
        HEADING_LINE = re.compile(r"^#{1,6}\s+.+$|^={2,}\s*.+\s*={2,}$")

        lines = text.split("\n")
        chunks: list[str] = []

        non_table_buf: list[str] = []
        table_buf: list[str] = []
        in_table = False
        section_context: str = ""  # last section heading, prepended to table chunks

        def flush_non_table() -> None:
            nonlocal section_context
            content_lines = [l for l in non_table_buf if l.strip()]
            non_table_buf.clear()
            if not content_lines:
                return

            # Pure heading block -> save as context prefix, skip standalone emission
            if all(HEADING_LINE.match(l.strip()) for l in content_lines):
                section_context = "\n".join(l.strip() for l in content_lines)
                return

            # Real content block: emit as chunk, update section_context from last heading
            block = "\n".join(content_lines).strip()
            for l in content_lines:
                if HEADING_LINE.match(l.strip()):
                    section_context = l.strip()
            chunks.extend(self._chunk_semantic(block, config))

        def flush_table() -> None:
            nonlocal section_context
            if not table_buf:
                return

            # Identify column-header lines (row 0) and separator (row 1 if it matches)
            header_lines: list[str] = []
            data_lines: list[str] = []
            for i, line in enumerate(table_buf):
                if i == 0:
                    header_lines.append(line)
                elif i == 1 and SEP_LINE.match(line):
                    header_lines.append(line)
                else:
                    data_lines.append(line)

            # Section prefix prepended to every chunk for retrieval context
            prefix = (section_context + "\n") if section_context else ""
            col_header = "\n".join(header_lines)

            full = prefix + "\n".join(table_buf)
            if len(full) <= max_size:
                chunks.append(full)
            else:
                base_size = len(prefix) + len(col_header)
                current: list[str] = list(header_lines)
                current_size = base_size

                for row in data_lines:
                    row_size = len(row) + 1  # +1 for newline
                    if current_size + row_size > max_size and len(current) > len(header_lines):
                        chunks.append(prefix + "\n".join(current))
                        current = list(header_lines)
                        current_size = base_size
                    current.append(row)
                    current_size += row_size

                if len(current) > len(header_lines):
                    chunks.append(prefix + "\n".join(current))

            section_context = ""
            table_buf.clear()

        for line in lines:
            if TABLE_LINE.match(line):
                if not in_table:
                    flush_non_table()
                    in_table = True
                table_buf.append(line)
            else:
                if in_table:
                    flush_table()
                    in_table = False
                non_table_buf.append(line)

        if in_table:
            flush_table()
        else:
            flush_non_table()

        return chunks if chunks else [text]

    def chunk_all(self, documents: list[Document]) -> list[Chunk]:
        """
        Chunk all documents.

        Args:
            documents: List of documents to chunk

        Returns:
            List of all chunks
        """
        all_chunks = []
        skipped = 0

        for doc in documents:
            chunks = self.chunk_document(doc)
            if chunks:
                all_chunks.extend(chunks)
            else:
                skipped += 1

        logger.info(
            f"Created {len(all_chunks)} chunks from {len(documents)} documents ({skipped} skipped)"
        )
        return all_chunks

    def get_stats(self, chunks: list[Chunk]) -> dict[str, Any]:
        """Get statistics about chunks."""
        if not chunks:
            return {"total": 0}

        chunk_sizes = [len(c.text) for c in chunks]

        by_collection = {}
        by_content_type = {}

        for chunk in chunks:
            by_collection[chunk.collection] = by_collection.get(chunk.collection, 0) + 1
            ct = chunk.content_type or "UNKNOWN"
            by_content_type[ct] = by_content_type.get(ct, 0) + 1

        return {
            "total": len(chunks),
            "by_collection": by_collection,
            "by_content_type": by_content_type,
            "avg_chunk_size": sum(chunk_sizes) / len(chunk_sizes),
            "min_chunk_size": min(chunk_sizes),
            "max_chunk_size": max(chunk_sizes),
            "total_chars": sum(chunk_sizes),
        }


# Test chunking
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    from document_loader import DocumentLoader

    loader = DocumentLoader()
    chunker = ContentAwareChunker()

    try:
        documents = loader.load_all(limit=5)
        chunks = chunker.chunk_all(documents)
        stats = chunker.get_stats(chunks)

        print(f"\nChunking statistics:")
        print(f"  Total chunks: {stats['total']}")
        print(f"  By collection: {stats['by_collection']}")
        print(f"  By content type: {stats['by_content_type']}")
        print(f"  Avg chunk size: {stats['avg_chunk_size']:.0f} chars")
        print(f"  Min/Max: {stats['min_chunk_size']}/{stats['max_chunk_size']} chars")

        if chunks:
            print(f"\nFirst chunk:")
            print(f"  ID: {chunks[0].chunk_id}")
            print(f"  Collection: {chunks[0].collection}")
            print(f"  Content type: {chunks[0].content_type}")
            print(f"  Size: {len(chunks[0].text)} chars")
            print(f"  Preview: {chunks[0].text[:200]}...")
    except FileNotFoundError as e:
        print(f"Error: {e}")
