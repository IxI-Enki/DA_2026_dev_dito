"""Exporter (T074-T075)

Exports preprocessed content to timestamped directories.
Each page becomes a ``.md`` file with YAML frontmatter.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class Exporter:
    """Exports preprocessed pages to ``data/preprocessed/preprocessed_at_{timestamp}/``.

    Each page is written as a Markdown file with YAML frontmatter containing
    the page's metadata.
    """

    def export(self, pages: list[dict[str, Any]], output_base: Path) -> Path:
        """Export pages to a timestamped directory.

        Args:
            pages: List of page dicts. Each must have at least
                ``page_id``, ``content``, and optionally ``title``,
                ``namespace``, ``metadata``.
            output_base: Base directory (e.g. ``data/preprocessed/``).

        Returns:
            Path to the created output directory.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out_dir = output_base / f"preprocessed_at_{timestamp}"
        out_dir.mkdir(parents=True, exist_ok=True)

        for page in pages:
            page_id: str = page.get("page_id", "unknown")
            safe_name = page_id.replace(":", "_").replace("/", "_")
            content = page.get("content", "")
            metadata = dict(page.get("metadata", {}))

            # Core frontmatter
            metadata.setdefault("page_id", page_id)
            metadata.setdefault("title", page.get("title", ""))
            metadata.setdefault("namespace", page.get("namespace", ""))
            metadata["exported_at"] = datetime.now(timezone.utc).isoformat()

            fm = yaml.dump(
                metadata,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )
            file_content = f"---\n{fm}---\n\n{content}\n"

            out_file = out_dir / f"{safe_name}.md"
            out_file.write_text(file_content, encoding="utf-8")

        logger.info("Exported %d pages to %s", len(pages), out_dir)
        return out_dir
