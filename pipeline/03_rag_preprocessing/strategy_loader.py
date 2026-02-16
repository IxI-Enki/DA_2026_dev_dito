"""Strategy Loader -- loads preprocessing strategies from Stage 2 output.

Supports two formats:
1. ``preprocessing_strategies.yaml`` (preferred, from strategy_generator.py)
2. ``page_strategies.json`` (legacy fallback)

The YAML format is category-based with ``include_ids`` lists.
The loader builds an inverted per-ID index for fast lookup.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """Page content type classification."""

    KNOWLEDGE = "KNOWLEDGE"
    NEWS = "NEWS"
    PORTAL = "PORTAL"
    FORM = "FORM"
    ARCHIVED = "ARCHIVED"
    IGNORED = "IGNORED"


@dataclass(frozen=True)
class PageStrategy:
    """Processing strategy for a single wiki page."""

    page_id: str
    content_type: ContentType
    chunking_method: str
    chunk_size: int
    action: str  # "process" | "skip" | "metadata_only"


@dataclass(frozen=True)
class MediaStrategy:
    """Strategy for a single media file (document or image)."""

    file_name: str
    content_type: str  # "DOCUMENT" | "IMAGE" | "KNOWLEDGE" | "FORM"
    action: str  # "process" | "caption_and_index" | "skip" | "index_metadata_only"
    parser: str  # "pdf_standard" | "pdf_scientific" | "pdf_form_fields" | ...
    chunk_size: int


# Wiki page category -> (ContentType, chunking_method, action) mapping
_WIKI_CATEGORY_MAP: dict[str, tuple[ContentType, str, str]] = {
    "knowledge_articles": (ContentType.KNOWLEDGE, "recursive_header", "process"),
    "portals": (ContentType.PORTAL, "parent_context", "process"),
    "forms": (ContentType.FORM, "table_row", "process"),
    "news": (ContentType.NEWS, "naive", "process"),
    "ignored": (ContentType.IGNORED, "none", "skip"),
}

# Document category -> (content_type_str, default_parser, default_action) mapping
_DOC_CATEGORY_MAP: dict[str, tuple[str, str, str]] = {
    "theses": ("KNOWLEDGE", "pdf_scientific", "process"),
    "forms": ("FORM", "pdf_form_fields", "index_metadata_only"),
    "standard_docs": ("DOCUMENT", "pdf_standard", "process"),
    "presentations": ("DOCUMENT", "pptx_slide", "summarize_slides"),
}


class StrategyLoader:
    """Loads preprocessing strategies from Stage 2 Deep Evaluation output.

    YAML structure (from strategy_generator.py)::

        PIPELINE_STRATEGIES:
          wiki_pages:
            knowledge_articles: { include_ids: [...], chunking: "recursive_header" }
            portals:            { include_ids: [...], action: "index_as_context_only" }
            ignored:            { include_ids: [...], action: "skip" }
          documents:
            theses:   { files: [...], parser: "pdf_scientific" }
            forms:    { files: [...], action: "index_metadata_only" }
          media:
            informative_images: { files: [...], action: "caption_and_index" }
            decorative:         { files: [...], action: "skip" }
    """

    def __init__(self) -> None:
        self._page_strategies: dict[str, PageStrategy] = {}
        self._media_strategies: dict[str, MediaStrategy] = {}

    def load(self, evaluated_dir: Path) -> None:
        """Load strategies from evaluated directory.

        Prefers ``preprocessing_strategies.yaml`` over ``page_strategies.json``.
        """
        yaml_file = evaluated_dir / "preprocessing_strategies.yaml"
        if yaml_file.exists():
            self._load_yaml(yaml_file)
            return

        # Fallback: legacy JSON
        json_file = evaluated_dir / "page_strategies.json"
        if json_file.exists():
            self._load_legacy_json(json_file)
            return

        logger.warning("No strategy file found in %s", evaluated_dir)

    def get_strategy(self, page_id: str) -> PageStrategy:
        """Get strategy for a page. Returns sensible default if unknown."""
        if page_id in self._page_strategies:
            return self._page_strategies[page_id]
        return PageStrategy(
            page_id=page_id,
            content_type=ContentType.KNOWLEDGE,
            chunking_method="semantic",
            chunk_size=512,
            action="process",
        )

    def get_media_strategy(self, file_name: str) -> MediaStrategy:
        """Get strategy for a media file. Returns default if unknown."""
        if file_name in self._media_strategies:
            return self._media_strategies[file_name]
        return MediaStrategy(
            file_name=file_name,
            content_type="DOCUMENT",
            action="process",
            parser="pdf_standard",
            chunk_size=1024,
        )

    def is_ignored(self, page_id: str) -> bool:
        """Check if a page should be skipped."""
        strategy = self.get_strategy(page_id)
        return strategy.action == "skip"

    def _load_yaml(self, path: Path) -> None:
        """Parse preprocessing_strategies.yaml and build inverted index."""
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except (yaml.YAMLError, OSError) as e:
            logger.error("Failed to load YAML strategies: %s", e)
            return

        strategies = data.get("PIPELINE_STRATEGIES", {})

        # Wiki pages: category-based with include_ids
        wiki_pages = strategies.get("wiki_pages", {})
        for category, info in wiki_pages.items():
            if not isinstance(info, dict):
                continue
            ct, chunking, action = _WIKI_CATEGORY_MAP.get(
                category, (ContentType.KNOWLEDGE, "semantic", "process")
            )
            # Override chunking from YAML if present
            chunking = info.get("chunking", chunking)
            chunk_size = info.get("chunk_size", 512)
            # Override action from YAML if present
            if info.get("action") == "skip":
                action = "skip"

            for raw_id in info.get("include_ids", []):
                # YAML uses underscores, convert to colons for page_id
                page_id = raw_id.replace("_", ":")
                self._page_strategies[page_id] = PageStrategy(
                    page_id=page_id,
                    content_type=ct,
                    chunking_method=chunking,
                    chunk_size=chunk_size,
                    action=action,
                )

        # Documents: category-based with files lists
        documents = strategies.get("documents", {})
        for category, info in documents.items():
            if not isinstance(info, dict):
                continue
            ct_str, parser, action = _DOC_CATEGORY_MAP.get(
                category, ("DOCUMENT", "pdf_standard", "process")
            )
            # Override action from YAML
            if info.get("action") == "index_metadata_only":
                action = "index_metadata_only"
            chunk_size = info.get("chunk_size", 1024)
            parser = info.get("parser", parser)

            for file_name in info.get("files", []):
                self._media_strategies[file_name] = MediaStrategy(
                    file_name=file_name,
                    content_type=ct_str,
                    action=action,
                    parser=parser,
                    chunk_size=chunk_size,
                )

        # Media (images): action-based
        media = strategies.get("media", {})
        for category, info in media.items():
            if not isinstance(info, dict):
                continue
            action = info.get("action", "process")
            for file_name in info.get("files", []):
                self._media_strategies[file_name] = MediaStrategy(
                    file_name=file_name,
                    content_type="IMAGE",
                    action=action,
                    parser="image",
                    chunk_size=0,
                )

        logger.info(
            "Loaded YAML strategies: %d pages, %d media/docs",
            len(self._page_strategies),
            len(self._media_strategies),
        )

    def _load_legacy_json(self, path: Path) -> None:
        """Parse page_strategies.json (backwards compatibility)."""
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to load JSON strategies: %s", e)
            return

        if not isinstance(data, list):
            logger.error("page_strategies.json must be a JSON array")
            return

        for entry in data:
            page_id = entry.get("page_id", "")
            if not page_id:
                continue
            try:
                ct = ContentType(entry.get("content_type", "KNOWLEDGE").upper())
            except ValueError:
                ct = ContentType.KNOWLEDGE
            self._page_strategies[page_id] = PageStrategy(
                page_id=page_id,
                content_type=ct,
                chunking_method="semantic",
                chunk_size=int(entry.get("recommended_chunk_size", 512)),
                action="process",
            )

        logger.info("Loaded %d legacy JSON strategies", len(self._page_strategies))
