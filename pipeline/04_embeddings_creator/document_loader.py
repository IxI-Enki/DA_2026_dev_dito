"""
Document Loader
===============
Loads Markdown documents with YAML frontmatter from preprocessed output.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from config import get_config, get_latest_timestamped_path

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """Represents a loaded document with frontmatter and content."""

    file_path: Path
    collection: str  # 'pages' or 'media'
    frontmatter: dict[str, Any]
    content: str

    # Extracted from frontmatter for convenience
    title: str = ""
    source: str = ""
    namespace: str = ""
    page_id: str = ""
    media_id: str = ""
    access_level: str = "public"
    content_type: str = ""

    def __post_init__(self):
        """Extract common fields from frontmatter."""
        self.title = self.frontmatter.get("title", "")
        self.source = self.frontmatter.get("source", "")
        self.namespace = self.frontmatter.get("namespace", "")
        self.page_id = self.frontmatter.get("page_id", "")
        self.media_id = self.frontmatter.get("media_id", "")
        self.access_level = self.frontmatter.get("access_level", "public")
        self.content_type = self.frontmatter.get("content_type", "")

    @property
    def doc_id(self) -> str:
        """Get document ID (page_id or media_id)."""
        return self.page_id or self.media_id or self.file_path.stem


class DocumentLoader:
    """Loads and parses Markdown documents with YAML frontmatter."""

    # YAML frontmatter pattern
    FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

    def __init__(self):
        self.config = get_config()
        self.encoding = self.config.text_prep.get("encoding", "utf-8")
        self.fallback_encodings = self.config.text_prep.get("fallback_encodings", [])

    def find_input_directory(self) -> Path:
        """
        Find the input directory with preprocessed documents.

        Returns:
            Path to the latest preprocessed_at_* directory (from Stage 3 RAG Preprocessing)
        """
        # Try primary input directory (data/preprocessed)
        input_dir = Path(self.config.paths.input_dir)
        if input_dir.exists():
            # Look for preprocessed_at_* directories (Stage 3 output)
            latest = get_latest_timestamped_path(str(input_dir), "preprocessed_at")
            if latest:
                logger.info(f"Using preprocessed directory: {latest}")
                return latest

            # Legacy: upload_at_* directories in same base
            latest = get_latest_timestamped_path(str(input_dir), "upload_at")
            if latest:
                logger.info(f"Using legacy upload directory: {latest}")
                return latest

        raise FileNotFoundError(
            f"No input directory found. Checked:\n"
            f"  - {input_dir} (preprocessed_at_* or upload_at_*)"
        )

    def read_file(self, file_path: Path) -> str | None:
        """Read file with encoding fallbacks."""
        for enc in [self.encoding] + self.fallback_encodings:
            try:
                with open(file_path, encoding=enc) as f:
                    return f.read()
            except (UnicodeDecodeError, LookupError):
                continue

        logger.error(f"Could not read file {file_path} with any encoding")
        return None

    def extract_frontmatter(self, content: str) -> tuple[dict[str, Any], str]:
        """
        Extract YAML frontmatter from Markdown content.

        Args:
            content: Full document content

        Returns:
            Tuple of (frontmatter dict, content without frontmatter)
        """
        match = self.FRONTMATTER_PATTERN.match(content)

        if match:
            frontmatter_str = match.group(1)
            content_body = content[match.end() :]

            try:
                frontmatter = yaml.safe_load(frontmatter_str)
                if frontmatter is None:
                    frontmatter = {}
                return frontmatter, content_body
            except yaml.YAMLError as e:
                logger.warning(f"Invalid YAML frontmatter: {e}")
                return {}, content

        return {}, content

    def load_document(self, file_path: Path, collection: str) -> Document | None:
        """
        Load a single document.

        Args:
            file_path: Path to the Markdown file
            collection: 'pages' or 'media'

        Returns:
            Document object or None if loading failed
        """
        content = self.read_file(file_path)
        if content is None:
            return None

        frontmatter, body = self.extract_frontmatter(content)

        # Skip empty documents
        if not body.strip() and not frontmatter:
            logger.warning(f"Empty document: {file_path.name}")
            return None

        return Document(
            file_path=file_path,
            collection=collection,
            frontmatter=frontmatter,
            content=body.strip(),
        )

    def load_collection(
        self, base_dir: Path, collection: str, limit: int | None = None
    ) -> list[Document]:
        """
        Load all documents from a collection directory.

        Args:
            base_dir: Base directory containing 'pages' and 'media' subdirs
            collection: 'pages' or 'media'
            limit: Maximum number of documents to load

        Returns:
            List of Document objects
        """
        collection_dir = base_dir / collection
        if not collection_dir.exists():
            logger.warning(f"Collection directory not found: {collection_dir}")
            return []

        # Support both .md and .txt files
        files = sorted(list(collection_dir.glob("*.md")) + list(collection_dir.glob("*.txt")))

        if limit:
            files = files[:limit]

        logger.info(f"Loading {len(files)} documents from {collection}")

        documents = []
        for file_path in files:
            doc = self.load_document(file_path, collection)
            if doc:
                documents.append(doc)

        logger.info(f"Loaded {len(documents)} documents from {collection}")
        return documents

    def load_all(self, limit: int | None = None) -> list[Document]:
        """
        Load all documents from pages and media collections.

        Args:
            limit: Maximum number of documents per collection

        Returns:
            List of all Document objects
        """
        input_dir = self.find_input_directory()

        documents = []

        # Load pages
        pages = self.load_collection(input_dir, "pages", limit)
        documents.extend(pages)

        # Load media
        media = self.load_collection(input_dir, "media", limit)
        documents.extend(media)

        logger.info(f"Total documents loaded: {len(documents)}")
        return documents

    def get_stats(self, documents: list[Document]) -> dict[str, Any]:
        """Get statistics about loaded documents."""
        pages = [d for d in documents if d.collection == "pages"]
        media = [d for d in documents if d.collection == "media"]

        content_types = {}
        access_levels = {"public": 0, "teacher_only": 0}

        for doc in documents:
            ct = doc.content_type or "UNKNOWN"
            content_types[ct] = content_types.get(ct, 0) + 1

            al = doc.access_level
            if al in access_levels:
                access_levels[al] += 1

        return {
            "total": len(documents),
            "pages": len(pages),
            "media": len(media),
            "content_types": content_types,
            "access_levels": access_levels,
            "avg_content_length": (
                sum(len(d.content) for d in documents) / len(documents) if documents else 0
            ),
        }


# Test document loading
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    loader = DocumentLoader()

    try:
        documents = loader.load_all(limit=5)
        stats = loader.get_stats(documents)

        print(f"\nLoaded {stats['total']} documents:")
        print(f"  Pages: {stats['pages']}")
        print(f"  Media: {stats['media']}")
        print(f"  Avg content length: {stats['avg_content_length']:.0f} chars")
        print(f"\nContent types: {stats['content_types']}")
        print(f"Access levels: {stats['access_levels']}")

        if documents:
            print(f"\nFirst document:")
            doc = documents[0]
            print(f"  Title: {doc.title}")
            print(f"  Source: {doc.source}")
            print(f"  Content type: {doc.content_type}")
            print(f"  Content preview: {doc.content[:200]}...")
    except FileNotFoundError as e:
        print(f"Error: {e}")
