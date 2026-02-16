"""Exporter -- Qdrant-compatible schema output.

Exports preprocessed content to timestamped directories with YAML frontmatter
matching the fields expected by pipeline/03_embeddings_creator/document_loader.py.

Output layout::

    preprocessed_at_{timestamp}/
    ├── pages/
    │   └── *.md
    ├── media/
    │   └── *.md
    └── manifest.json
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class Exporter:
    """Exports preprocessed pages and media in Qdrant-compatible schema.

    Every output file is ``.md`` with YAML frontmatter matching the
    ``Document`` dataclass in ``document_loader.py``.
    """

    def export(
        self,
        pages: list[dict[str, Any]],
        media: list[dict[str, Any]],
        output_base: Path,
    ) -> Path:
        """Export pages AND media to timestamped directory.

        Args:
            pages: List of page dicts with Qdrant-schema fields + ``content``.
            media: List of media dicts with Qdrant-schema fields + ``content``.
            output_base: Base directory (e.g. ``data/preprocessed/``).

        Returns:
            Path to the created output directory.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out_dir = output_base / f"preprocessed_at_{timestamp}"
        pages_dir = out_dir / "pages"
        media_dir = out_dir / "media"
        pages_dir.mkdir(parents=True, exist_ok=True)
        media_dir.mkdir(parents=True, exist_ok=True)

        # Export pages
        for page in pages:
            page_id: str = page.get("page_id", "unknown")
            safe_name = page_id.replace(":", "_").replace("/", "_")
            body = page.get("content", "")
            fm = self._build_page_frontmatter(page, body)
            self._write_md(pages_dir / f"{safe_name}.md", fm, body)

        # Export media
        for item in media:
            media_id: str = item.get("media_id", "unknown")
            safe_name = media_id.replace(":", "_").replace("/", "_")
            body = item.get("content", "")
            fm = self._build_media_frontmatter(item, body)
            self._write_md(media_dir / f"{safe_name}.md", fm, body)

        # Write manifest
        self._write_manifest(out_dir, len(pages), len(media))

        logger.info(
            "Exported %d pages + %d media to %s", len(pages), len(media), out_dir
        )
        return out_dir

    def _build_page_frontmatter(
        self, page: dict[str, Any], body: str
    ) -> dict[str, Any]:
        """Build Qdrant-compatible frontmatter for a wiki page.

        Required fields (per document_loader.py Document dataclass):
        - title, namespace, source, page_id, access_level, content_type
        - freshness_score (float), freshness_category (str)
        - chunking_method (str), last_modified (ISO timestamp)
        - author, content_hash, links_to, linked_from
        """
        return {
            "title": page.get("title", ""),
            "namespace": page.get("namespace", ""),
            "source": page.get("source", ""),
            "page_id": page.get("page_id", ""),
            "access_level": page.get("access_level", "public"),
            "content_type": page.get("content_type", "KNOWLEDGE"),
            "freshness_score": float(page.get("freshness_score", 0.5)),
            "freshness_category": page.get("freshness_category", "recent"),
            "chunking_method": page.get("chunking_method", "semantic"),
            "last_modified": page.get("last_modified", ""),
            "author": page.get("author", ""),
            "content_hash": hashlib.md5(body.encode("utf-8")).hexdigest(),
            "links_to": page.get("links_to", []),
            "linked_from": page.get("linked_from", []),
        }

    def _build_media_frontmatter(
        self, media_item: dict[str, Any], body: str
    ) -> dict[str, Any]:
        """Build Qdrant-compatible frontmatter for a media file.

        Uses ``media_id`` instead of ``page_id``, otherwise identical schema.
        """
        return {
            "title": media_item.get("title", ""),
            "namespace": media_item.get("namespace", ""),
            "source": media_item.get("source", ""),
            "media_id": media_item.get("media_id", ""),
            "access_level": media_item.get("access_level", "public"),
            "content_type": media_item.get("content_type", "DOCUMENT"),
            "freshness_score": float(media_item.get("freshness_score", 0.5)),
            "freshness_category": media_item.get("freshness_category", "recent"),
            "chunking_method": media_item.get("chunking_method", "metadata_only"),
            "last_modified": media_item.get("last_modified", ""),
            "author": media_item.get("author", ""),
            "content_hash": hashlib.md5(body.encode("utf-8")).hexdigest(),
            "links_to": [],
            "linked_from": [],
        }

    def _write_md(
        self, path: Path, frontmatter: dict[str, Any], body: str
    ) -> None:
        """Write a Markdown file with YAML frontmatter."""
        fm_str = yaml.dump(
            frontmatter,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
        file_content = f"---\n{fm_str}---\n\n{body}\n"
        path.write_text(file_content, encoding="utf-8")

    def _write_manifest(
        self, out_dir: Path, pages_count: int, media_count: int
    ) -> None:
        """Write manifest.json with export metadata."""
        manifest = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "pages_count": pages_count,
            "media_count": media_count,
            "total_count": pages_count + media_count,
            "schema_version": "2.0",
        }
        (out_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
