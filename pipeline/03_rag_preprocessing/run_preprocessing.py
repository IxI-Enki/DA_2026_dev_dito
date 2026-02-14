"""RAG Preprocessing Orchestrator (T079)

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


def run(
    input_dir: Optional[Path] = None,
    evaluated_dir: Optional[Path] = None,
    output_base: Optional[Path] = None,
    config_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Execute the full preprocessing pipeline.

    Args:
        input_dir: Fetched data directory (auto-detect if None).
        evaluated_dir: Directory with page_strategies.json.
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

    # Process pages
    page_content_dir = input_dir / "page_content"
    raw_json_dir = input_dir / "raw_json"

    pages: list[dict[str, Any]] = []
    stats = {"pages_total": 0, "pages_ok": 0, "pages_fail": 0, "media_processed": 0}

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

            # Compute freshness + access
            last_mod = ""
            if raw_meta:
                last_mod = raw_meta.get("page_info", {}).get("last_modified", "")
            freshness = meta_enricher.calculate_freshness_score(last_mod) if last_mod else "unknown"
            namespace = page_id.rsplit(":", 1)[0] if ":" in page_id else ""
            access = meta_enricher.determine_access_level(namespace)

            pages.append({
                "page_id": page_id,
                "title": result.get("title", ""),
                "namespace": namespace,
                "content": result.get("markdown", ""),
                "metadata": {
                    "content_type": result.get("content_type", "knowledge"),
                    "priority": result.get("priority", "normal"),
                    "rag_readiness": result.get("rag_readiness", 0.5),
                    "chunk_size": result.get("chunk_size", 512),
                    "freshness": freshness,
                    "access_level": access,
                },
            })
            stats["pages_ok"] += 1

    stats["pages_fail"] = stats["pages_total"] - stats["pages_ok"]

    # Process media
    media_dir = input_dir / "media"
    if media_dir.exists():
        media_results = media_proc.process_media_directory(media_dir)
        stats["media_processed"] = len(media_results)

    # Export
    out_dir = exporter.export(pages, output_base)
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
