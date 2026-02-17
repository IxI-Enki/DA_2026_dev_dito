#!/usr/bin/env python3
"""
Qdrant Embeddings Creator - Run Entry Point
===========================================
Creates optimized embeddings for Qdrant based on Deep Evaluation strategies.

Usage:
    python pipeline/04_embeddings_creator/run_embeddings.py              # Process all documents
    python pipeline/04_embeddings_creator/run_embeddings.py --limit 10   # Process first 10 (testing)
    python pipeline/04_embeddings_creator/run_embeddings.py --config path.yaml

Environment:
    OPENAI_API_KEY: Required - OpenAI API key for embeddings
"""

import sys
import argparse
from pathlib import Path

# Add script directory to path for imports
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))
# Shared CLI utilities (color, sigint, --no-color)
sys.path.insert(0, str(script_dir.parent / "shared"))
from cli_utils import (
    add_no_color_arg,
    apply_color_from_args,
    enable_windows_ansi,
    print_help_banner,
    register_sigint,
    set_use_color,
    style,
)

from config import get_config, reload_config, ConfigError
from pipeline import EmbeddingPipeline


def main() -> int:
    """Run embedding pipeline."""
    if "-h" in sys.argv or "--help" in sys.argv:
        set_use_color("--no-color" not in sys.argv)
        enable_windows_ansi()
        print_help_banner(
            what="Creates embeddings for Qdrant from preprocessed Markdown (Stage 3). \nUses content-aware chunking and OpenAI text-embedding-3-large. Writes JSONL to data/embeddings/embedded_at_<timestamp>/.",
            usage="python run_embeddings.py [OPTIONS]",
            parameters="(none)",
            options=(
                "-h, --help         Show this help and exit.\n"
                "-l, --limit N      Limit number of documents (for testing).\n"
                "-c, --config PATH  Custom env.yaml path.\n"
                "--no-color         Disable colored output."
            ),
            examples=(
                "# Process all documents (latest preprocessed_at_*)\n"
                "python run_embeddings.py\n"
                "# Process first 10 documents only\n"
                "python run_embeddings.py --limit 10\n"
                "# Use custom config\n"
                "python run_embeddings.py --config path/to/env.yaml"
            ),
            configuration="pipeline/04_embeddings_creator/env.yaml (PATHS, OPENAI, CHUNKING, OUTPUT).",
            output="data/embeddings/embedded_at_<timestamp>/embedded_chunks.jsonl, embedding_statistics.json.",
            exit_codes="0   Success.\n1   Config error, missing API key, or no input.\n130 Interrupted (Ctrl+C).",
        )
        sys.exit(0)

    parser = argparse.ArgumentParser(description="Create Qdrant embeddings from preprocessed documents")
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=None,
        help="Limit number of documents to process (for testing)",
    )

    parser.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help="Path to custom configuration file",
    )
    add_no_color_arg(parser)

    args = parser.parse_args()
    apply_color_from_args(args)
    enable_windows_ansi()
    register_sigint("run_embeddings")

    # Load configuration
    try:
        if args.config:
            reload_config(args.config)
        config = get_config()
    except ConfigError as e:
        print(f"Configuration error: {e}")
        return 1

    # Check for API key
    try:
        config.get_api_key()
    except ConfigError as e:
        print(f"Error: {e}")
        print("\nPlease set the OPENAI_API_KEY environment variable:")
        print("  PowerShell: $env:OPENAI_API_KEY = 'your-key-here'")
        print("  CMD: set OPENAI_API_KEY=your-key-here")
        return 1

    # Run pipeline
    try:
        pipeline = EmbeddingPipeline()
        stats = pipeline.run(limit=args.limit)

        print("\n[OK] Pipeline completed successfully!")
        print(f"  Output: {stats['output']['file']}")
        print(f"  Records: {stats['output']['records']}")
        print(f"  Cost: ${stats['embedding']['total_cost']:.4f}")
        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("\nMake sure preprocessed documents exist. Run the preprocessing pipeline first:")
        print("  python pipeline/03_rag_preprocessing/run_preprocessing.py")
        return 1

    except Exception as e:
        print(f"Pipeline failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
