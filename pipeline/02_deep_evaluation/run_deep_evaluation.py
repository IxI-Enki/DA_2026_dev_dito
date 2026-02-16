#!/usr/bin/env python3
"""
Deep Evaluation Runner - Orchestriert die Tiefenanalyse

Führt sequenziell Wiki-, Dokumenten- und Medien-Analyse durch und generiert den Strategie-Report.
Alle Einstellungen werden aus config/env.yaml geladen - KEINE hardcoded Werte!

Usage:
    python run_deep_evaluation.py               # Vollständige Deep Evaluation
    python run_deep_evaluation.py --show-config # Zeigt aktuelle Konfiguration
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Set

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Shared CLI utilities
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shared"))
from cli_utils import add_no_color_arg, apply_color_from_args, register_sigint, style

from config import get_config, EvaluationConfig
from analyzers.wiki_deep_analyzer import WikiDeepAnalyzer
from analyzers.document_deep_analyzer import DocumentDeepAnalyzer
from analyzers.media_deep_analyzer import MediaDeepAnalyzer
from report_generator import ReportGenerator
from generators.strategy_generator import StrategyGenerator


def setup_logging(config: EvaluationConfig) -> logging.Logger:
    """
    Konfiguriert Logging basierend auf env.yaml.
    
    Args:
        config: EvaluationConfig Instanz
        
    Returns:
        Konfigurierter Logger
    """
    log_cfg = config.raw_config.get('LOGGING', {})
    
    # Get log file path
    if config.results_dir:
        default_log = str(config.results_dir / 'deep_evaluation.log')
    else:
        default_log = 'deep_evaluation.log'
    log_file = log_cfg.get('deep_eval_log', default_log)
    
    # Create log directory if needed
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure logging
    handlers: List[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    
    logging.basicConfig(
        level=getattr(logging, log_cfg.get('level', 'INFO')),
        format=log_cfg.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
        handlers=handlers,
        force=True
    )
    
    logger = logging.getLogger("DeepEval")
    logger.info(f"Logging configured. Log file: {log_file}")
    return logger


def get_file_extensions_from_config(config: EvaluationConfig) -> dict:
    """
    Lädt Dateiendungen aus config/env.yaml.
    
    Args:
        config: EvaluationConfig Instanz
        
    Returns:
        Dictionary mit extensions für pages, documents, images
    """
    format_cfg = config.raw_config.get('FORMAT_ANALYSIS', {}).get('supported_formats', {})
    
    # Page extensions
    page_exts = set(format_cfg.get('pages', {}).get('extensions', ['.txt', '.md']))
    
    # Document extensions (PDF + Office)
    doc_exts = set()
    if 'documents' in format_cfg:
        docs_cfg = format_cfg['documents']
        if 'pdf' in docs_cfg:
            doc_exts.update(docs_cfg['pdf'].get('extensions', ['.pdf']))
        if 'office' in docs_cfg:
            for office_type in docs_cfg['office'].values():
                doc_exts.update(office_type.get('extensions', []))
    
    # Image extensions
    img_exts = set(format_cfg.get('images', {}).get('extensions', ['.jpg', '.jpeg', '.png', '.svg']))
    
    return {
        'pages': page_exts,
        'documents': doc_exts,
        'images': img_exts
    }


def validate_paths(config: EvaluationConfig, logger: logging.Logger) -> bool:
    """
    Validiert dass alle benötigten Pfade existieren.
    
    Args:
        config: EvaluationConfig Instanz
        logger: Logger Instanz
        
    Returns:
        True wenn alle Pfade gültig sind, False sonst
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
    logger: logging.Logger
) -> List[dict]:
    """
    Analysiert alle Wiki-Seiten.
    
    Args:
        config: EvaluationConfig Instanz
        wiki_analyzer: WikiDeepAnalyzer Instanz
        extensions: Set von Dateiendungen
        logger: Logger Instanz
        
    Returns:
        Liste von Analyse-Ergebnissen
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
            content = page_file.read_text(encoding='utf-8')
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
    logger: logging.Logger
) -> List[dict]:
    """
    Analysiert alle Dokumente (PDF, Office) in Media-Ordnern.
    
    Args:
        config: EvaluationConfig Instanz
        doc_analyzer: DocumentDeepAnalyzer Instanz
        extensions: Set von Dateiendungen
        logger: Logger Instanz
        
    Returns:
        Liste von Analyse-Ergebnissen
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
    logger: logging.Logger
) -> List[dict]:
    """
    Analysiert alle Bilder mit Vision AI.
    
    Args:
        config: EvaluationConfig Instanz
        media_analyzer: MediaDeepAnalyzer Instanz
        extensions: Set von Dateiendungen
        logger: Logger Instanz
        
    Returns:
        Liste von Analyse-Ergebnissen
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
    """Hauptfunktion für Deep Evaluation."""
    import argparse
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
    
    # Get file extensions from config
    extensions = get_file_extensions_from_config(config)
    logger.info(f"Configured extensions - Pages: {extensions['pages']}, "
                f"Documents: {extensions['documents']}, Images: {extensions['images']}")
    
    # Initialize Analyzers
    logger.info("Initializing analyzers...")
    wiki_analyzer = WikiDeepAnalyzer(config)
    doc_analyzer = DocumentDeepAnalyzer(config)
    media_analyzer = MediaDeepAnalyzer(config)
    
    # Timestamp für diesen Run (vollständig: YYYYMMDD_HHMMSS)
    now = datetime.now()
    timestamp_full = now.strftime('%Y%m%d_%H%M%S')
    
    results = {
        "timestamp": timestamp_full,
        "timestamp_iso": now.isoformat(),
        "wiki_pages": [],
        "documents": [],
        "media": []
    }
    
    # 1. Analyze Wiki Pages
    logger.info("\n" + "=" * 70)
    logger.info("  STEP 1: WIKI PAGES ANALYSIS")
    logger.info("=" * 70)
    results["wiki_pages"] = analyze_wiki_pages(
        config, wiki_analyzer, extensions['pages'], logger
    )
    
    # 2. Analyze Documents
    logger.info("\n" + "=" * 70)
    logger.info("  STEP 2: DOCUMENTS ANALYSIS")
    logger.info("=" * 70)
    results["documents"] = analyze_documents(
        config, doc_analyzer, extensions['documents'], logger
    )
    
    # 3. Analyze Images
    logger.info("\n" + "=" * 70)
    logger.info("  STEP 3: IMAGES ANALYSIS")
    logger.info("=" * 70)
    results["media"] = analyze_images(
        config, media_analyzer, extensions['images'], logger
    )
    
    # 4. Save Raw Results
    logger.info("\n" + "=" * 70)
    logger.info("  STEP 4: SAVING RESULTS")
    logger.info("=" * 70)
    if not config.results_dir:
        logger.error("Results directory not configured!")
        sys.exit(1)
    output_dir = config.results_dir / f"deep_eval_{timestamp_full}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    json_path = output_dir / "deep_analysis_results.json"
    with open(json_path, "w", encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Raw results saved to: {json_path}")
    
    # 5. Generate Preprocessing Strategies
    logger.info("\n" + "=" * 70)
    logger.info("  STEP 5: GENERATING PREPROCESSING STRATEGIES")
    logger.info("=" * 70)
    try:
        strategy_gen = StrategyGenerator(json_path)
        strategy_path = strategy_gen.generate_strategies(output_dir)
        logger.info(f"Preprocessing strategies saved to: {strategy_path}")
    except Exception as e:
        logger.error(f"Failed to generate preprocessing strategies: {e}")
        if not config.continue_on_error:
            raise
    
    # 6. Generate Comprehensive Markdown Report
    logger.info("\n" + "=" * 70)
    logger.info("  STEP 6: GENERATING REPORT")
    logger.info("=" * 70)
    try:
        report_gen = ReportGenerator(config=config)
        report_path = report_gen.generate_deep_analysis_report(output_dir, results)
        logger.info(f"Deep analysis report saved to: {report_path}")
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        if not config.continue_on_error:
            raise
    
    # Summary -- logged as a single cohesive block (AC3)
    sep = "=" * 70
    summary = (
        f"\n{sep}\n"
        f"  DEEP EVALUATION COMPLETE\n"
        f"{sep}\n"
        f"  Wiki Pages:    {len(results['wiki_pages'])}\n"
        f"  Documents:     {len(results['documents'])}\n"
        f"  Images:        {len(results['media'])}\n"
        f"  Output Dir:    {output_dir}\n"
        f"{sep}"
    )
    logger.info(summary)


if __name__ == "__main__":
    main()
