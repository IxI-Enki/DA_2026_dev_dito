#!/usr/bin/env python3
"""
Fetched Data Evaluation Pipeline - CLI Runner
==============================================

Runs a full evaluation of the fetched DokuWiki data.
All settings are loaded from config/env.yaml.

Usage:
    python run_evaluation.py                    # Full evaluation
    python run_evaluation.py --quick            # Quick test without LLM queries
    python run_evaluation.py --show-config      # Shows the current configuration
    python run_evaluation.py --no-queries       # Without query generation

Examples:
    # Full evaluation
    python run_evaluation.py

    # Content and format analysis only (fast)
    python run_evaluation.py --quick

    # With a custom output directory
    python run_evaluation.py --output-dir ../results/custom_eval
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from analyzers import (
    ContentClassifier,
    FormatQualityAnalyzer,
    QueryGenerator,
    RAGReadinessChecker,
    TemporalAnalyzer,
)
from report_generator import ReportGenerator

from config import EvaluationConfig, get_config

# Shared CLI utilities
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shared"))
from cli_utils import add_no_color_arg, apply_color_from_args, register_sigint


def parse_args():
    parser = argparse.ArgumentParser(
        description="Fetched Data Evaluation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Config options
    parser.add_argument(
        "--config", "-c", type=str, default=None, help="Pfad zu alternativer env.yaml"
    )
    parser.add_argument(
        "--show-config", action="store_true", help="Zeigt aktuelle Konfiguration und beendet"
    )

    # Output options
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default=None,
        help="Ueberschreibt Output-Verzeichnis aus config",
    )
    parser.add_argument(
        "--run-name", "-n", type=str, default=None, help="Name fuer diesen Evaluationslauf"
    )

    # Evaluation options
    parser.add_argument(
        "--quick", action="store_true", help="Schnellmodus: Ueberspringt LLM-Queries"
    )
    parser.add_argument("--no-queries", action="store_true", help="Query-Generierung ueberspringen")
    parser.add_argument("--no-report", action="store_true", help="Report-Generierung ueberspringen")
    parser.add_argument(
        "--query-limit", type=int, default=None, help="Maximale Anzahl generierter Queries"
    )

    # Verbosity
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimale Ausgabe")
    parser.add_argument("--verbose", "-v", action="store_true", help="Ausfuehrliche Ausgabe")

    add_no_color_arg(parser)
    return parser.parse_args()


def show_config(config: EvaluationConfig):
    """Shows the current configuration."""
    print("=" * 70)
    print("  CURRENT CONFIGURATION")
    print("=" * 70)
    print(f"\n  Fetched Data: {config.fetched_data_dir}")
    print(f"  Results Dir:  {config.results_dir}")
    print(f"  Page Content: {config.page_content_dir}")
    print(f"  Media Dir:    {config.media_dir}")
    print(f"\n  Teacher Namespaces: {config.teacher_namespaces}")
    print(f"  Public Namespaces:  {len(config.public_namespaces)}")
    print(f"\n  Query Generation:")
    print(f"    Enabled:    {config.query_generation.enabled}")
    print(f"    LLM Model:  {config.query_generation.llm.model}")
    print(f"    LLM URL:    {config.query_generation.llm.base_url}")
    print(f"\n  Diploma Thesis Files: {len(config.diploma_thesis.files)}")
    for f in config.diploma_thesis.files:
        print(f"    - {f}")
    print("=" * 70)


def main():
    args = parse_args()
    apply_color_from_args(args)
    register_sigint("run_evaluation")

    # Load configuration
    config_path = Path(args.config) if args.config else None

    if config_path:
        config = EvaluationConfig.from_yaml(config_path)
    else:
        config = get_config()

    # Show config if requested
    if args.show_config:
        show_config(config)
        sys.exit(0)

    # Generate run name and output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = args.run_name or f"eval_{timestamp}"

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        # Use results_dir if available, otherwise fallback to script_dir/results
        if config.results_dir:
            output_dir = config.results_dir / run_name
        elif config.script_dir:
            output_dir = config.script_dir.parent / "results" / run_name
        else:
            output_dir = Path("results") / run_name

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("  FETCHED DATA EVALUATION PIPELINE")
    print("=" * 70)
    print(f"\n  Run Name:     {run_name}")
    print(f"  Output:       {output_dir}")
    print(f"  Source:       {config.fetched_data_dir}")
    print(f"  Quick Mode:   {args.quick}")
    print("=" * 70)

    # Initialize results
    results = {
        "run_name": run_name,
        "timestamp": timestamp,
        "source": str(config.fetched_data_dir),
        "output_dir": str(output_dir),
    }

    # Step 1: Content Classification
    print("\n[1/5] Content Classification...")
    classifier = ContentClassifier(config)
    classification_result = classifier.analyze()
    results["content_classification"] = classifier.to_dict()

    # Step 2: Format & Quality Analysis
    print("\n[2/5] Format & Quality Analysis...")
    format_analyzer = FormatQualityAnalyzer(config)
    format_result = format_analyzer.analyze()
    results["format_quality"] = format_analyzer.to_dict()

    # Step 3: RAG Readiness Check
    print("\n[3/5] RAG Readiness Check...")
    rag_checker = RAGReadinessChecker(config)
    rag_result = rag_checker.analyze()
    results["rag_readiness"] = rag_checker.to_dict()

    # Step 4: Temporal Analysis
    print("\n[4/5] Temporal Analysis...")
    temporal_analyzer = TemporalAnalyzer(config)
    temporal_result = temporal_analyzer.analyze()
    results["temporal_analysis"] = temporal_analyzer.to_dict()

    # Step 5: Query Generation (unless skipped)
    if not args.quick and not args.no_queries:
        print("\n[5/5] Query Generation...")
        query_gen = QueryGenerator(config)
        query_gen.generate(sample_size=args.query_limit)
        results["query_generation"] = query_gen.to_dict()

        # Save RAGAS-compatible queries
        ragas_queries = query_gen.to_ragas_format()
        ragas_path = output_dir / "synthetic_queries_ragas.json"
        with open(ragas_path, "w", encoding="utf-8") as f:
            json.dump(ragas_queries, f, ensure_ascii=False, indent=2)
        print(f"  RAGAS-Queries gespeichert: {ragas_path}")
    else:
        print("\n[5/5] Query Generation... ÜBERSPRUNGEN")
        results["query_generation"] = {"skipped": True}

    # Generate summary
    results["summary"] = {
        "total_pages": classification_result.total_pages,
        "total_media_files": format_result.total_files,
        "teacher_restricted_pages": classification_result.teacher_restricted_count,
        "archived_pages": temporal_result.archived_count,
        "avg_rag_readiness": round(rag_result.avg_readiness_score, 3),
        "avg_freshness": round(temporal_result.avg_freshness_score, 3),
        "files_needing_ocr": format_result.files_needing_ocr,
        "diploma_thesis_pdfs": len(format_result.diploma_thesis_files),
    }

    # Collect all recommendations
    all_recommendations = []
    all_recommendations.extend(rag_result.preprocessing_recommendations)
    all_recommendations.extend(temporal_result.recommendations)
    results["recommendations"] = all_recommendations

    # Save full results
    results_path = output_dir / f"{run_name}_full_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    # Generate report
    if not args.no_report:
        print("\n[Report] Generiere Report...")
        report_gen = ReportGenerator(config, results)
        report_path = report_gen.generate(output_dir)
        print(f"  Report gespeichert: {report_path}")

    # Print summary
    print("\n" + "=" * 70)
    print("  EVALUATION COMPLETE")
    print("=" * 70)
    print(f"\n  Total Pages:          {results['summary']['total_pages']}")
    print(f"  Total Media Files:    {results['summary']['total_media_files']}")
    print(f"  Teacher-Restricted:   {results['summary']['teacher_restricted_pages']}")
    print(f"  Archived:             {results['summary']['archived_pages']}")
    print(f"  Avg RAG Readiness:    {results['summary']['avg_rag_readiness']:.2f}")
    print(f"  Avg Freshness:        {results['summary']['avg_freshness']:.2f}")
    print(f"  Files Needing OCR:    {results['summary']['files_needing_ocr']}")
    print(f"  Diploma Thesis PDFs:  {results['summary']['diploma_thesis_pdfs']}")

    print(f"\n  Key Recommendations:")
    for rec in all_recommendations[:5]:
        print(f"    - {rec}")

    print(f"\n  Results saved to: {output_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
