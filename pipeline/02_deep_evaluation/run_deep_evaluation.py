#!/usr/bin/env python3
"""
Deep Evaluation Runner - orchestrates the in-depth analysis

Sequentially runs wiki, document, and media analysis and generates the strategy report.
All settings are loaded from config/env.yaml - NO hardcoded values!

Usage:
    python run_deep_evaluation.py               # Full deep evaluation
    python run_deep_evaluation.py --show-config # Shows the current configuration
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Set

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Shared CLI utilities
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shared"))
from analyzers.document_deep_analyzer import DocumentDeepAnalyzer
from analyzers.media_deep_analyzer import MediaDeepAnalyzer
from analyzers.wiki_deep_analyzer import WikiDeepAnalyzer
from cli_utils import (
    add_no_color_arg,
    apply_color_from_args,
    enable_windows_ansi,
    print_help_banner,
    register_sigint,
    set_use_color,
    style,
)
from generators.strategy_generator import StrategyGenerator
from report_generator import ReportGenerator

from config import EvaluationConfig, get_config


def setup_logging(config: EvaluationConfig) -> logging.Logger:
    """
    Configures logging based on env.yaml.

    Args:
        config: EvaluationConfig instance

    Returns:
        Configured logger
    """
    log_cfg = config.raw_config.get("LOGGING", {})

    # Get log file path (result-dir log)
    if config.results_dir:
        default_log = str(config.results_dir / "deep_evaluation.log")
    else:
        default_log = "deep_evaluation.log"
    log_file = log_cfg.get("deep_eval_log", default_log)

    # Central log under data/logs (alongside other pipeline stages)
    central_log_dir = config.results_dir.parent / "logs" if config.results_dir else None
    central_log_file = str(central_log_dir / "deep_evaluation.log") if central_log_dir else None

    # Create log directories if needed
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    if central_log_file:
        Path(central_log_file).parent.mkdir(parents=True, exist_ok=True)

    # Configure logging
    handlers: List[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    if central_log_file and central_log_file != log_file:
        handlers.append(logging.FileHandler(central_log_file, encoding="utf-8"))

    logging.basicConfig(
        level=getattr(logging, log_cfg.get("level", "INFO")),
        format=log_cfg.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
        handlers=handlers,
        force=True,
    )

    logger = logging.getLogger("DeepEval")
    log_targets = [log_file]
    if central_log_file and central_log_file != log_file:
        log_targets.append(central_log_file)
    logger.info("Logging configured. Log file(s): %s", ", ".join(log_targets))
    return logger


def get_file_extensions_from_config(config: EvaluationConfig) -> dict:
    """
    Loads file extensions from config/env.yaml.

    Args:
        config: EvaluationConfig instance

    Returns:
        Dictionary with extensions for pages, documents, images
    """
    format_cfg = config.raw_config.get("FORMAT_ANALYSIS", {}).get("supported_formats", {})

    # Page extensions
    page_exts = set(format_cfg.get("pages", {}).get("extensions", [".txt", ".md"]))

    # Document extensions (PDF + Office)
    doc_exts = set()
    if "documents" in format_cfg:
        docs_cfg = format_cfg["documents"]
        if "pdf" in docs_cfg:
            doc_exts.update(docs_cfg["pdf"].get("extensions", [".pdf"]))
        if "office" in docs_cfg:
            for office_type in docs_cfg["office"].values():
                doc_exts.update(office_type.get("extensions", []))

    # Image extensions
    img_exts = set(
        format_cfg.get("images", {}).get("extensions", [".jpg", ".jpeg", ".png", ".svg"])
    )

    return {"pages": page_exts, "documents": doc_exts, "images": img_exts}


def validate_paths(config: EvaluationConfig, logger: logging.Logger) -> bool:
    """
    Validates that all required paths exist.

    Args:
        config: EvaluationConfig instance
        logger: Logger instance

    Returns:
        True if all paths are valid, False otherwise
    """
    errors = []

    if not config.page_content_dir or not config.page_content_dir.exists():
        errors.append(f"Page content directory not found: {config.page_content_dir}")

    if not config.media_dir or not config.media_dir.exists():
        errors.append(f"Media directory not found: {config.media_dir}")

    if not config.results_dir:
        errors.append("Results directory not configured")

    if errors:
        for error in errors:
            logger.error(error)
        return False

    return True


def analyze_wiki_pages(
    config: EvaluationConfig,
    wiki_analyzer: WikiDeepAnalyzer,
    extensions: Set[str],
    logger: logging.Logger,
) -> List[dict]:
    """
    Analyzes all wiki pages.

    Args:
        config: EvaluationConfig instance
        wiki_analyzer: WikiDeepAnalyzer instance
        extensions: Set of file extensions
        logger: Logger instance

    Returns:
        List of analysis results
    """
    results = []
    content_dir = config.page_content_dir

    if not content_dir or not content_dir.exists():
        logger.error(f"Page content directory not found: {content_dir}")
        return results

    logger.info(f"Analyzing Wiki Pages in {content_dir}...")

    # Find all page files with configured extensions
    pages: List[Path] = []
    for ext in extensions:
        pages.extend(content_dir.glob(f"*{ext}"))

    total_pages = len(pages)
    logger.info(f"Found {total_pages} page files")

    if total_pages == 0:
        logger.warning("No page files found!")
        return results

    # Process pages
    continue_on_error = config.continue_on_error
    show_progress = config.show_progress

    for i, page_file in enumerate(pages):
        if show_progress and (i % 10 == 0 or i == total_pages - 1):
            logger.info(f"Processing Page {i+1}/{total_pages}: {page_file.name}")

        try:
            content = page_file.read_text(encoding="utf-8")
            res = wiki_analyzer.analyze_page(page_file.stem, content)
            results.append(res)
        except Exception as e:
            error_msg = f"Error processing {page_file.name}: {e}"
            logger.error(error_msg)
            if not continue_on_error:
                raise

    logger.info(f"Successfully analyzed {len(results)}/{total_pages} pages")
    return results


def analyze_documents(
    config: EvaluationConfig,
    doc_analyzer: DocumentDeepAnalyzer,
    extensions: Set[str],
    logger: logging.Logger,
) -> List[dict]:
    """
    Analyzes all documents (PDF, Office) in the media folders.

    Args:
        config: EvaluationConfig instance
        doc_analyzer: DocumentDeepAnalyzer instance
        extensions: Set of file extensions
        logger: Logger instance

    Returns:
        List of analysis results
    """
    results = []
    media_dir = config.media_dir

    if not media_dir or not media_dir.exists():
        logger.error(f"Media directory not found: {media_dir}")
        return results

    logger.info(f"Analyzing Documents in {media_dir}...")

    # Recursive search for documents (set-based dedup for case-insensitive FS)
    doc_files_set: Set[Path] = set()
    for ext in extensions:
        doc_files_set.update(media_dir.rglob(f"*{ext}"))
        doc_files_set.update(media_dir.rglob(f"*{ext.upper()}"))
    doc_files = sorted(doc_files_set)

    total_docs = len(doc_files)
    logger.info(f"Found {total_docs} document files")

    if total_docs == 0:
        logger.warning("No document files found!")
        return results

    # Process documents
    continue_on_error = config.continue_on_error
    show_progress = config.show_progress

    for i, doc_file in enumerate(doc_files):
        if show_progress and (i % 5 == 0 or i == total_docs - 1):
            logger.info(f"Processing Document {i+1}/{total_docs}: {doc_file.name}")

        try:
            res = doc_analyzer.analyze_document(doc_file)
            results.append(res)
        except Exception as e:
            error_msg = f"Error processing doc {doc_file.name}: {e}"
            logger.error(error_msg)
            if not continue_on_error:
                raise

    logger.info(f"Successfully analyzed {len(results)}/{total_docs} documents")
    return results


def analyze_images(
    config: EvaluationConfig,
    media_analyzer: MediaDeepAnalyzer,
    extensions: Set[str],
    logger: logging.Logger,
) -> List[dict]:
    """
    Analyzes all images with vision AI.

    Args:
        config: EvaluationConfig instance
        media_analyzer: MediaDeepAnalyzer instance
        extensions: Set of file extensions
        logger: Logger instance

    Returns:
        List of analysis results
    """
    results = []
    media_dir = config.media_dir

    if not media_dir or not media_dir.exists():
        logger.error(f"Media directory not found: {media_dir}")
        return results

    logger.info(f"Analyzing Images in {media_dir}...")

    # Recursive search for images (set-based dedup for case-insensitive FS)
    img_files_set: Set[Path] = set()
    for ext in extensions:
        img_files_set.update(media_dir.rglob(f"*{ext}"))
        img_files_set.update(media_dir.rglob(f"*{ext.upper()}"))
    img_files = sorted(img_files_set)

    total_imgs = len(img_files)
    logger.info(f"Found {total_imgs} image files")

    if total_imgs == 0:
        logger.warning("No image files found!")
        return results

    # Process images
    continue_on_error = config.continue_on_error
    show_progress = config.show_progress

    for i, img_file in enumerate(img_files):
        if show_progress and (i % 5 == 0 or i == total_imgs - 1):
            logger.info(f"Processing Image {i+1}/{total_imgs}: {img_file.name}")

        try:
            res = media_analyzer.analyze_image(img_file)
            results.append(res)
        except Exception as e:
            error_msg = f"Error processing img {img_file.name}: {e}"
            logger.error(error_msg)
            if not continue_on_error:
                raise

    logger.info(f"Successfully analyzed {len(results)}/{total_imgs} images")
    return results


def main():
    """Main entry point for the deep evaluation."""
    import argparse

    if "-h" in sys.argv or "--help" in sys.argv:
        set_use_color("--no-color" not in sys.argv)
        enable_windows_ansi()
        print_help_banner(
            what="Runs deep analysis of fetched DokuWiki data: wiki pages, documents, images. Generates preprocessing strategies and reports. All settings from config/env.yaml.",
            usage="python run_deep_evaluation.py [OPTIONS]",
            parameters="(none)",
            options="-h, --help       Show this help and exit.\n--show-config     Show current config and exit.\n--no-color        Disable colored output.",
            examples="# Full deep evaluation\npython run_deep_evaluation.py\n# Show config\npython run_deep_evaluation.py --show-config",
            configuration="pipeline/02_deep_evaluation/env.yaml (PATHS, LOGGING, LLM, etc.). If fetched_data_dir does not exist, latest fetched_at_* is used automatically.",
            output="data/evaluated/deep_eval_<YYYYMMDD_HHMMSS>/: deep_analysis_results.json, preprocessing_strategies.yaml, report.",
            exit_codes="0   Success.\n1   Path validation or config error.",
        )
        sys.exit(0)

    parser = argparse.ArgumentParser(description="Deep Content Evaluation")
    parser.add_argument("--show-config", action="store_true", help="Show current config")
    add_no_color_arg(parser)
    args = parser.parse_args()
    apply_color_from_args(args)
    register_sigint("run_deep_evaluation")

    # Load configuration
    config = get_config()

    # Setup logging
    logger = setup_logging(config)
    logger.info(style("=" * 70, "cyan"))
    logger.info(style("  DEEP CONTENT EVALUATION", "bold", "bright_cyan"))
    logger.info(style("=" * 70, "cyan"))

    # Validate paths
    if not validate_paths(config, logger):
        logger.error("Path validation failed. Please check your config/env.yaml")
        sys.exit(1)

    if config.fetched_data_dir:
        logger.info("Using fetched data dir: %s", config.fetched_data_dir)

    # Get file extensions from config
    extensions = get_file_extensions_from_config(config)
    logger.info(
        f"Configured extensions - Pages: {extensions['pages']}, "
        f"Documents: {extensions['documents']}, Images: {extensions['images']}"
    )

    # Initialize Analyzers
    logger.info("Initializing analyzers...")
    wiki_analyzer = WikiDeepAnalyzer(config)
    doc_analyzer = DocumentDeepAnalyzer(config)
    media_analyzer = MediaDeepAnalyzer(config)

    # Timestamp for this run (full: YYYYMMDD_HHMMSS)
    now = datetime.now()
    timestamp_full = now.strftime("%Y%m%d_%H%M%S")

    results = {
        "timestamp": timestamp_full,
        "timestamp_iso": now.isoformat(),
        "wiki_pages": [],
        "documents": [],
        "media": [],
    }

    # 1. Analyze Wiki Pages
    sep = "=" * 70
    logger.info(style(sep, "cyan"))
    logger.info(style("  STEP 1: WIKI PAGES ANALYSIS", "bold", "bright_cyan"))
    logger.info(style(sep, "cyan"))
    results["wiki_pages"] = analyze_wiki_pages(config, wiki_analyzer, extensions["pages"], logger)

    # 2. Analyze Documents
    logger.info(style(sep, "cyan"))
    logger.info(style("  STEP 2: DOCUMENTS ANALYSIS", "bold", "bright_cyan"))
    logger.info(style(sep, "cyan"))
    results["documents"] = analyze_documents(config, doc_analyzer, extensions["documents"], logger)

    # 3. Analyze Images
    logger.info(style(sep, "cyan"))
    logger.info(style("  STEP 3: IMAGES ANALYSIS", "bold", "bright_cyan"))
    logger.info(style(sep, "cyan"))
    results["media"] = analyze_images(config, media_analyzer, extensions["images"], logger)

    # 4. Save Raw Results
    logger.info(style(sep, "cyan"))
    logger.info(style("  STEP 4: SAVING RESULTS", "bold", "bright_cyan"))
    logger.info(style(sep, "cyan"))
    if not config.results_dir:
        logger.error("Results directory not configured!")
        sys.exit(1)
    output_dir = config.results_dir / f"deep_eval_{timestamp_full}"
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "deep_analysis_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logger.info(f"Raw results saved to: {json_path}")

    # 5. Generate Preprocessing Strategies
    logger.info(style(sep, "cyan"))
    logger.info(style("  STEP 5: GENERATING PREPROCESSING STRATEGIES", "bold", "bright_cyan"))
    logger.info(style(sep, "cyan"))
    try:
        strategy_gen = StrategyGenerator(json_path)
        strategy_path = strategy_gen.generate_strategies(output_dir)
        logger.info(f"Preprocessing strategies saved to: {strategy_path}")
    except Exception as e:
        logger.error(f"Failed to generate preprocessing strategies: {e}")
        if not config.continue_on_error:
            raise

    # 6. Generate Comprehensive Markdown Report
    logger.info(style(sep, "cyan"))
    logger.info(style("  STEP 6: GENERATING REPORT", "bold", "bright_cyan"))
    logger.info(style(sep, "cyan"))
    try:
        report_gen = ReportGenerator(config=config)
        report_path = report_gen.generate_deep_analysis_report(output_dir, results)
        logger.info(f"Deep analysis report saved to: {report_path}")
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        if not config.continue_on_error:
            raise

    # Summary -- logged as a single cohesive block (AC3), with styled banner
    summary = (
        "\n"
        + style(sep, "cyan")
        + "\n"
        + style("  DEEP EVALUATION COMPLETE", "bold", "bright_cyan")
        + "\n"
        + style(sep, "cyan")
        + "\n"
        + f"  Wiki Pages:    {len(results['wiki_pages'])}\n"
        + f"  Documents:     {len(results['documents'])}\n"
        + f"  Images:        {len(results['media'])}\n"
        + f"  Output Dir:    {output_dir}\n"
        + style(sep, "cyan")
    )
    logger.info(summary)


if __name__ == "__main__":
    main()
