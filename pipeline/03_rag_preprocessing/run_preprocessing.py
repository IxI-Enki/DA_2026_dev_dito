"""RAG Preprocessing Orchestrator

Runs the complete preprocessing pipeline:
  DokuWiki fetched data -> Strategy routing -> Markdown + YAML frontmatter -> Export

Usage:
  python pipeline/03_rag_preprocessing/run_preprocessing.py
  python pipeline/03_rag_preprocessing/run_preprocessing.py --input-dir data/fetched/fetched_at_20260201
  python pipeline/03_rag_preprocessing/run_preprocessing.py --evaluated-dir data/evaluated
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Ensure parent is importable
_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

from config import get_config, get_latest_fetch_dir, get_latest_evaluation
from exporter import Exporter
from media_processor import MediaProcessor
from metadata_enricher import MetadataEnricher
from page_processor import PageProcessor
from strategy_loader import StrategyLoader

logger = logging.getLogger(__name__)


def _load_backlinks(input_dir: Path) -> dict[str, list[str]]:
    """Load backlinks from page_backlinks/*.json into a lookup dict.

    Returns:
        Dict mapping page_id -> list of page_ids that link TO this page.
    """
    backlinks: dict[str, list[str]] = {}
    backlinks_dir = input_dir / "page_backlinks"
    if not backlinks_dir.exists():
        logger.info("No page_backlinks/ directory found, linked_from will be empty")
        return backlinks

    for f in backlinks_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            page_id = f.stem.replace("_", ":")
            # data is typically a list of page_ids that link to this page
            if isinstance(data, list):
                backlinks[page_id] = data
            elif isinstance(data, dict):
                backlinks[page_id] = data.get("backlinks", [])
        except Exception as e:
            logger.warning("Failed to load backlinks from %s: %s", f, e)

    logger.info("Loaded backlinks for %d pages", len(backlinks))
    return backlinks


def run(
    input_dir: Optional[Path] = None,
    evaluated_dir: Optional[Path] = None,
    output_base: Optional[Path] = None,
    config_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Execute the full preprocessing pipeline.

    Args:
        input_dir: Fetched data directory (auto-detect if None).
        evaluated_dir: Directory with preprocessing_strategies.yaml.
        output_base: Base output directory.
        config_path: YAML config file path.

    Returns:
        Statistics dict.
    """
    cfg = get_config(config_path)

    # Resolve input
    if input_dir is None:
        input_dir = get_latest_fetch_dir(cfg.fetched_dir)
        if input_dir is None:
            raise FileNotFoundError(f"No fetched data found in {cfg.fetched_dir}")
    logger.info("Input:    %s", input_dir)

    # Resolve evaluation
    if evaluated_dir is None:
        eval_file = get_latest_evaluation(cfg.evaluated_dir)
        if eval_file:
            evaluated_dir = eval_file.parent
    if evaluated_dir:
        logger.info("Eval dir: %s", evaluated_dir)

    if output_base is None:
        output_base = cfg.output_dir
    logger.info("Output:   %s", output_base)

    # Init components
    strategy_loader = StrategyLoader()
    if evaluated_dir:
        strategy_loader.load(evaluated_dir)

    page_proc = PageProcessor(cfg.wiki_base_url)
    meta_enricher = MetadataEnricher(cfg.wiki_base_url)
    media_proc = MediaProcessor(
        tesseract_path=cfg.media.get("tesseract_path", ""),
        ocr_language=cfg.media.get("ocr", {}).get("language", "deu+eng"),
    )
    exporter = Exporter()

    # T011a: Load backlinks
    backlinks_lookup = _load_backlinks(input_dir)

    # Process pages
    page_content_dir = input_dir / "page_content"
    raw_json_dir = input_dir / "raw_json"
    page_links_dir = input_dir / "page_links"

    pages: list[dict[str, Any]] = []
    media: list[dict[str, Any]] = []
    stats = {"pages_total": 0, "pages_ok": 0, "pages_fail": 0, "media_processed": 0}

    # T011b: Process pages with full Qdrant-schema metadata
    if page_content_dir.exists():
        for f in sorted(page_content_dir.glob("*.txt")):
            stats["pages_total"] += 1
            page_id = f.stem.replace("_", ":")
            wiki = f.read_text(encoding="utf-8", errors="replace")
            if not wiki.strip():
                continue

            strategy = strategy_loader.get_strategy(page_id)
            result = page_proc.process_with_strategy(
                {"content": wiki, "page_id": page_id}, strategy
            )

            # Load raw metadata if available
            raw_meta_file = raw_json_dir / f"{f.stem}_complete.json"
            raw_meta = None
            if raw_meta_file.exists():
                try:
                    raw_meta = json.loads(raw_meta_file.read_text(encoding="utf-8"))
                except Exception:
                    pass

            # Extract metadata fields
            page_info = raw_meta.get("page_info", {}) if raw_meta else {}
            last_mod = page_info.get("last_modified", "")
            author = page_info.get("author", "")
            namespace = page_id.rsplit(":", 1)[0] if ":" in page_id else ""

            # Freshness + access
            freshness = meta_enricher.calculate_freshness_score(last_mod) if last_mod else "unknown"
            access = meta_enricher.determine_access_level(namespace)

            # Links
            links_to: list[str] = []
            links_file = page_links_dir / f"{f.stem}_links.json" if page_links_dir.exists() else None
            if links_file and links_file.exists():
                try:
                    links_data = json.loads(links_file.read_text(encoding="utf-8"))
                    links_to = [
                        link.get("target", "")
                        for link in links_data.get("internal_links", [])
                        if link.get("target")
                    ]
                except Exception:
                    pass

            # Backlinks
            linked_from = backlinks_lookup.get(page_id, [])

            # Build page dict with Qdrant-schema fields
            pages.append({
                "page_id": page_id,
                "title": result.get("title", ""),
                "namespace": namespace,
                "source": f"{cfg.wiki_base_url}{page_id.replace('_', ':')}",
                "access_level": access,
                "content_type": result.get("content_type", "KNOWLEDGE"),
                "freshness_score": 0.5,  # Placeholder until US5 Freshness-Scoring
                "freshness_category": freshness,
                "chunking_method": result.get("chunking_method", "semantic"),
                "last_modified": last_mod,
                "author": author,
                "links_to": links_to,
                "linked_from": linked_from,
                "content": result.get("markdown", ""),
            })
            stats["pages_ok"] += 1

    stats["pages_fail"] = stats["pages_total"] - stats["pages_ok"]

    # T011c: Process media with full Qdrant-schema metadata
    media_dir = input_dir / "media"
    if media_dir.exists():
        media_results = media_proc.process_media_directory(media_dir)
        for mr in media_results:
            file_path = mr.get("file_path", Path())
            if isinstance(file_path, str):
                file_path = Path(file_path)
            media_id = mr.get("media_id", file_path.name if file_path else "unknown")

            media.append({
                "media_id": media_id,
                "title": file_path.stem.replace("_", " ").title() if file_path else "",
                "namespace": media_id.rsplit(":", 1)[0] if ":" in media_id else "",
                "source": f"{cfg.wiki_base_url}lib/exe/fetch.php?media={media_id}" if cfg.wiki_base_url else "",
                "access_level": "public",
                "content_type": mr.get("content_type", "DOCUMENT"),
                "freshness_score": 0.5,
                "freshness_category": "recent",
                "chunking_method": "metadata_only",
                "last_modified": "",
                "author": "",
                "links_to": [],
                "linked_from": [],
                "content": mr.get("text", ""),
            })
        stats["media_processed"] = len(media)

    # T011d: Export with new API
    out_dir = exporter.export(pages, media, output_base)
    logger.info("Exported to %s", out_dir)
    logger.info("Stats: %s", stats)
    return stats


def main() -> int:
    """CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="RAG Preprocessing Pipeline")
    parser.add_argument("--input-dir", type=Path, default=None)
    parser.add_argument("--evaluated-dir", type=Path, default=None)
    parser.add_argument("--output-base", type=Path, default=None)
    parser.add_argument("--config", type=Path, default=None)
    args = parser.parse_args()

    try:
        run(
            input_dir=args.input_dir,
            evaluated_dir=args.evaluated_dir,
            output_base=args.output_base,
            config_path=args.config,
        )
    except FileNotFoundError as e:
        logger.error("%s", e)
        return 1
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
