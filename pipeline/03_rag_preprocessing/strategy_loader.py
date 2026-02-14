"""Strategy Loader (T069-T070)

Loads per-page processing strategies from Deep Evaluation output.
Each page gets a ContentType classification and processing parameters.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """Page content type classification."""

    KNOWLEDGE = "knowledge"
    NEWS = "news"
    PORTAL = "portal"
    FORM = "form"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class PageStrategy:
    """Processing strategy for a single page.

    Attributes:
        page_id: DokuWiki page identifier (namespace:page).
        content_type: Classification of content type.
        rag_readiness: Score 0.0-1.0 for RAG suitability.
        recommended_chunk_size: Optimal chunk size in tokens.
        noise_level: Noise classification (low / medium / high).
    """

    page_id: str
    content_type: ContentType
    rag_readiness: float
    recommended_chunk_size: int
    noise_level: str


# Default strategy for pages without evaluation data
_DEFAULT_STRATEGY = dict(
    content_type=ContentType.KNOWLEDGE,
    rag_readiness=0.5,
    recommended_chunk_size=512,
    noise_level="medium",
)


class StrategyLoader:
    """Loads per-page processing strategies from Deep Evaluation output."""

    def __init__(self) -> None:
        self._strategies: dict[str, PageStrategy] = {}

    def load(self, evaluated_dir: Path) -> dict[str, PageStrategy]:
        """Load page strategies from an evaluated directory.

        Looks for ``page_strategies.json`` (a list of per-page dicts).

        Args:
            evaluated_dir: Directory containing evaluation output.

        Returns:
            Dict mapping page_id -> PageStrategy.
        """
        strategies_file = evaluated_dir / "page_strategies.json"
        if not strategies_file.exists():
            logger.warning("No page_strategies.json in %s", evaluated_dir)
            return {}

        try:
            with open(strategies_file, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to load strategies: %s", e)
            return {}

        if not isinstance(data, list):
            logger.error("page_strategies.json must be a JSON array")
            return {}

        for entry in data:
            page_id = entry.get("page_id", "")
            if not page_id:
                continue
            try:
                ct = ContentType(entry.get("content_type", "knowledge"))
            except ValueError:
                ct = ContentType.KNOWLEDGE
            strategy = PageStrategy(
                page_id=page_id,
                content_type=ct,
                rag_readiness=float(entry.get("rag_readiness", 0.5)),
                recommended_chunk_size=int(entry.get("recommended_chunk_size", 512)),
                noise_level=str(entry.get("noise_level", "medium")),
            )
            self._strategies[page_id] = strategy

        logger.info("Loaded %d page strategies", len(self._strategies))
        return dict(self._strategies)

    def get_strategy(self, page_id: str) -> PageStrategy:
        """Get strategy for a page, returning a sensible default if unknown."""
        if page_id in self._strategies:
            return self._strategies[page_id]
        return PageStrategy(page_id=page_id, **_DEFAULT_STRATEGY)
