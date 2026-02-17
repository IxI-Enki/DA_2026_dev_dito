"""RAG Preprocessing Orchestrator (single entry point, US9)

Runs the complete preprocessing pipeline:
  DokuWiki fetched data -> Strategy routing -> Markdown + YAML frontmatter -> Export

Usage:
  python pipeline/03_rag_preprocessing/run_preprocessing.py
  python pipeline/03_rag_preprocessing/run_preprocessing.py --input-dir data/fetched/fetched_at_20260201
  python pipeline/03_rag_preprocessing/run_preprocessing.py --evaluated-dir data/evaluated
  python pipeline/03_rag_preprocessing/run_preprocessing.py --help
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

# Ensure parent is importable
_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

from exporter import Exporter
from image_captioner import CAPTIONABLE_EXTENSIONS, ImageCaptioner
from media_processor import DOCUMENT_EXTENSIONS, MediaProcessor
from metadata_enricher import MetadataEnricher
from page_processor import PageProcessor
from strategy_loader import StrategyLoader

from config import get_config, get_latest_evaluation, get_latest_fetch_dir

# Shared CLI utilities
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shared"))
from cli_utils import (
    add_no_color_arg,
    apply_color_from_args,
    enable_windows_ansi,
    print_help_banner,
    register_sigint,
    set_use_color,
    style,
)

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
            # Primary: use page_id from the JSON (e.g. "page_id": "start")
            page_id = data.get("page_id", "") if isinstance(data, dict) else ""
            if not page_id:
                # Fallback: strip _backlinks suffix, then convert _ to :
                stem = f.stem
                if stem.endswith("_backlinks"):
                    stem = stem[:-10]  # len("_backlinks") == 10
                page_id = stem.replace("_", ":")
            # data is typically a list of page_ids that link to this page
            if isinstance(data, list):
                backlinks[page_id] = data
            elif isinstance(data, dict):
                backlinks[page_id] = data.get("backlinks", [])
        except Exception as e:
            logger.warning("Failed to load backlinks from %s: %s", f, e)

    logger.info("Loaded backlinks for %d pages", len(backlinks))
    return backlinks


def _load_media_metadata(input_dir: Path) -> dict[str, dict[str, Any]]:
    """Load media metadata from media_metadata/*_info.json.

    Returns:
        Dict keyed by media id (from JSON) with keys last_modified (ISO),
        author, and optionally revision (unix).
    """
    result: dict[str, dict[str, Any]] = {}
    meta_dir = input_dir / "media_metadata"
    if not meta_dir.exists():
        logger.info("No media_metadata/ directory found")
        return result

    for path in meta_dir.glob("*_info.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            mid = data.get("id")
            if not mid:
                continue
            orig = data.get("original_metadata") or {}
            rev = orig.get("revision")
            last_mod = ""
            if rev is not None:
                try:
                    dt = datetime.fromtimestamp(int(rev), tz=UTC)
                    last_mod = dt.isoformat()
                except (ValueError, OSError):
                    pass
            result[mid] = {
                "last_modified": last_mod,
                "author": orig.get("author") or "",
            }
        except Exception as e:
            logger.warning("Failed to load media metadata from %s: %s", path.name, e)

    logger.info("Loaded media metadata for %d files", len(result))
    return result


def _load_media_usage(input_dir: Path) -> dict[str, list[str]]:
    """Load media_usage_index.json for linked_from (which pages reference each media).

    Returns:
        Dict mapping media_id -> list of page_ids that reference it.
    """
    result: dict[str, list[str]] = {}
    usage_file = input_dir / "media_usage_index.json"
    if not usage_file.exists():
        logger.info("No media_usage_index.json found, media linked_from will be empty")
        return result
    try:
        data = json.loads(usage_file.read_text(encoding="utf-8"))
        usage = data.get("media_usage") or {}
        for mid, info in usage.items():
            refs = info.get("referenced_by")
            if isinstance(refs, list):
                result[mid] = refs
        logger.info("Loaded media usage for %d media (linked_from)", len(result))
    except Exception as e:
        logger.warning("Failed to load media_usage_index.json: %s", e)
    return result


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

    # Resolve evaluation directory
    if evaluated_dir is None:
        eval_result = get_latest_evaluation(cfg.evaluated_dir)
        if eval_result:
            # get_latest_evaluation returns a directory (deep_eval_*) or file
            evaluated_dir = eval_result if eval_result.is_dir() else eval_result.parent
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

    # US6: Vision-LLM Image Captioner
    vlm_cfg = cfg.vision_llm
    captioner = ImageCaptioner(
        api_base=vlm_cfg.get("api_base", "http://192.168.8.3:1234/v1"),
        model=vlm_cfg.get("model", "qwen2.5-vl"),
        timeout=vlm_cfg.get("timeout", 60),
        max_image_size=vlm_cfg.get("max_image_size", 1024),
    )
    captioner_available = captioner.is_available()
    if captioner_available:
        logger.info("Vision-LLM available at %s", vlm_cfg.get("api_base"))
    else:
        logger.warning("Vision-LLM not available -- images will be skipped")

    # T011a: Load backlinks
    backlinks_lookup = _load_backlinks(input_dir)
    # Load media metadata for last_modified, author, freshness
    media_metadata_lookup = _load_media_metadata(input_dir)
    # Load media usage for linked_from (which pages reference each media)
    media_usage_lookup = _load_media_usage(input_dir)

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

            # Strategy-based routing (US4)
            strategy = strategy_loader.get_strategy(page_id)
            if strategy_loader.is_ignored(page_id):
                logger.debug("Skipping ignored page: %s", page_id)
                continue

            result = page_proc.process_with_strategy(
                {"content": wiki, "page_id": page_id}, strategy
            )
            title = result.get("title", "") or page_id.split(":")[-1].replace("_", " ").title()

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

            # Freshness (US5: 6-tier hybrid formula) + access; namespace used for archived vs stale
            freshness = meta_enricher.calculate_freshness(last_mod, namespace) if last_mod else None
            access = meta_enricher.determine_access_level(namespace)

            # Links
            links_to: list[str] = []
            links_file = (
                page_links_dir / f"{f.stem}_links.json" if page_links_dir.exists() else None
            )
            if links_file and links_file.exists():
                try:
                    links_data = json.loads(links_file.read_text(encoding="utf-8"))
                    links_to = [
                        link.get("target", "")
                        for link in links_data.get("internal_links", [])
                        if link.get("target")
                    ]
                    # Include media embeds
                    for ml in links_data.get("media_links", []):
                        mid = ml.get("media_id", "")
                        if mid:
                            links_to.append(mid)
                except Exception:
                    pass

            # Backlinks
            linked_from = backlinks_lookup.get(page_id, [])

            # Build page dict with Qdrant-schema fields
            # Strategy provides content_type and chunking_method (US4)
            pages.append(
                {
                    "page_id": page_id,
                    "title": title,
                    "namespace": namespace,
                    "source": f"{cfg.wiki_base_url}{page_id.replace('_', ':')}",
                    "access_level": access,
                    "content_type": strategy.content_type.value,
                    "freshness_score": freshness.score if freshness else 0.5,
                    "freshness_category": freshness.category if freshness else "unknown",
                    "chunking_method": strategy.chunking_method,
                    "last_modified": last_mod,
                    "author": author,
                    "links_to": links_to,
                    "linked_from": linked_from,
                    "content": result.get("markdown", ""),
                }
            )
            stats["pages_ok"] += 1

    stats["pages_fail"] = stats["pages_total"] - stats["pages_ok"]

    # T011c + US6: Process media with full Qdrant-schema metadata + Vision-LLM
    media_dir = input_dir / "media"
    stats["images_captioned"] = 0
    if media_dir.exists():
        for f in sorted(media_dir.rglob("*")):
            if not f.is_file():
                continue

            ext = f.suffix.lower()
            # Resolve metadata from media_metadata/*_info.json
            try:
                rel = f.relative_to(media_dir)
            except ValueError:
                rel = Path(f.name)
            meta_key = rel.as_posix().replace("/", ":")
            media_id = meta_key  # e.g. "class:docker_kollision.jpg"
            ms = strategy_loader.get_media_strategy(f.name)
            meta = media_metadata_lookup.get(meta_key) or media_metadata_lookup.get(f.name)
            last_mod = (meta.get("last_modified", "") or "") if meta else ""
            author = (meta.get("author", "") or "") if meta else ""
            media_namespace = meta_key.split(":")[0] if ":" in meta_key else ""
            freshness = (
                meta_enricher.calculate_freshness(last_mod, media_namespace) if last_mod else None
            )
            freshness_score = freshness.score if freshness else 0.5
            freshness_category = freshness.category if freshness else "recent"
            linked_from = media_usage_lookup.get(meta_key) or media_usage_lookup.get(f.name) or []

            # Skip decorative images / skipped media
            if ms.action == "skip":
                logger.debug("Skipping media (strategy=skip): %s", f.name)
                continue

            # Captionable images (US6): use Vision-LLM
            if ext in CAPTIONABLE_EXTENSIONS:
                if ms.action == "caption_and_index" and captioner_available:
                    description = captioner.caption(f)
                    if description:
                        media.append(
                            {
                                "media_id": media_id,
                                "title": f.stem.replace("_", " ").title(),
                                "namespace": media_id.rsplit(":", 1)[0] if ":" in media_id else "",
                                "source": (
                                    f"{cfg.wiki_base_url}lib/exe/fetch.php?media={media_id}"
                                    if cfg.wiki_base_url
                                    else ""
                                ),
                                "access_level": "public",
                                "content_type": "IMAGE",
                                "freshness_score": freshness_score,
                                "freshness_category": freshness_category,
                                "chunking_method": "metadata_only",
                                "last_modified": last_mod,
                                "author": author,
                                "links_to": [],
                                "linked_from": linked_from,
                                "content": description,
                            }
                        )
                        stats["images_captioned"] += 1
                continue  # images are either captioned or skipped

            # Documents (PDF, DOCX, XLSX, PPTX): extract text
            text = ""
            if ext == ".pdf":
                text = media_proc.process_pdf(f)
            elif ext == ".docx":
                text = media_proc.process_docx(f)
            elif ext == ".xlsx":
                text = media_proc.process_xlsx(f)
            elif ext == ".pptx":
                text = media_proc.process_pptx(f)
            elif ext not in DOCUMENT_EXTENSIONS:
                continue

            media.append(
                {
                    "media_id": media_id,
                    "title": f.stem.replace("_", " ").title(),
                    "namespace": media_id.rsplit(":", 1)[0] if ":" in media_id else "",
                    "source": (
                        f"{cfg.wiki_base_url}lib/exe/fetch.php?media={media_id}"
                        if cfg.wiki_base_url
                        else ""
                    ),
                    "access_level": "public",
                    "content_type": ms.content_type,
                    "freshness_score": freshness_score,
                    "freshness_category": freshness_category,
                    "chunking_method": ms.parser if ms.parser != "image" else "metadata_only",
                    "last_modified": last_mod,
                    "author": author,
                    "links_to": [],
                    "linked_from": linked_from,
                    "content": text,
                }
            )
        stats["media_processed"] = len(media)

    # T011d: Export with new API (NFR-005: manifest has timestamp, config_hash, code_version)
    code_version = "1.0.0"
    config_hash = "n/a"
    out_dir = exporter.export(
        pages,
        media,
        output_base,
        config_hash=config_hash,
        code_version=code_version,
    )
    logger.info("Exported to %s", out_dir)
    logger.info("Stats: %s", stats)

    _print_summary(stats, out_dir)
    return stats


def _print_summary(stats: dict[str, Any], out_dir: Path) -> None:
    """Print human-readable processing summary to stdout."""
    sep = style("=" * 60, "cyan")
    print(f"\n{sep}")
    print(style("RAG PREPROCESSING COMPLETE", "bold", "bright_green"))
    print(sep)
    print(f"Pages total:      {stats.get('pages_total', 0)}")
    print(f"  - OK:           {stats.get('pages_ok', 0)}")
    print(f"  - Failed:       {stats.get('pages_fail', 0)}")
    print(f"Media processed:  {stats.get('media_processed', 0)}")
    print(f"  - Captioned:    {stats.get('images_captioned', 0)}")
    print(f"Output directory:  {out_dir}")
    print(sep)


def main() -> int:
    """CLI entry point."""
    if "-h" in sys.argv or "--help" in sys.argv:
        set_use_color("--no-color" not in sys.argv)
        enable_windows_ansi()
        print_help_banner(
            what="Transforms fetched DokuWiki content into RAG-optimized Markdown with YAML frontmatter. Uses strategies from Stage 2, runs PDF/OCR and image captioning. Single entry point (US9).",
            usage="python run_preprocessing.py [OPTIONS]",
            parameters="(none)",
            options="-h, --help         Show this help and exit.\n--input-dir DIR      Fetched data directory (auto-detect latest if omitted).\n--evaluated-dir DIR  Evaluation dir with strategies (auto-detect if omitted).\n--output-base DIR    Base output directory (default from config).\n--config PATH        Config file (env.yaml).\n--no-color           Disable colored output.",
            examples="# Run with auto-detected latest fetch and evaluation\npython run_preprocessing.py\n# Specify fetch and eval dirs\npython run_preprocessing.py --input-dir data/fetched/fetched_at_20260216 --evaluated-dir data/evaluated",
            configuration="pipeline/03_rag_preprocessing/env.yaml (PATHS, MEDIA, VISION_LLM, OUTPUT, etc.).",
            output="data/preprocessed/preprocessed_at_<timestamp>/: pages/, media/, manifest.json.",
            exit_codes="0   Success.\n1   FileNotFoundError or config error.\n130 Interrupted (Ctrl+C).",
        )
        sys.exit(0)

    parser = argparse.ArgumentParser(description="RAG Preprocessing Pipeline")
    parser.add_argument("--input-dir", type=Path, default=None)
    parser.add_argument("--evaluated-dir", type=Path, default=None)
    parser.add_argument("--output-base", type=Path, default=None)
    parser.add_argument("--config", type=Path, default=None)
    add_no_color_arg(parser)
    args = parser.parse_args()
    apply_color_from_args(args)
    register_sigint("run_preprocessing")

    cfg = get_config(args.config)
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    handlers: list = [logging.StreamHandler()]
    log_file = cfg.log_dir / "preprocessing.log"
    cfg.log_dir.mkdir(parents=True, exist_ok=True)
    handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=handlers,
        force=True,
    )

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
