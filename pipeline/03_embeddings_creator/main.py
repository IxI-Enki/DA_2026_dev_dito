#!/usr/bin/env python3
"""
Qdrant Embeddings Creator - Main Entry Point
=============================================
Creates optimized embeddings for Qdrant based on Deep Evaluation strategies.

Usage:
    python main.py                    # Process all documents
    python main.py --limit 10         # Process first 10 documents (testing)
    python main.py --config path.yaml # Use custom config file

Environment:
    OPENAI_API_KEY: Required - OpenAI API key for embeddings
"""

import sys
import argparse
from pathlib import Path

# Add script directory to path for imports
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from config import get_config, reload_config, ConfigError
from pipeline import EmbeddingPipeline


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Create Qdrant embeddings from preprocessed documents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py                      # Process all documents
    python main.py --limit 10           # Process 10 documents (for testing)
    python main.py --config custom.yaml # Use custom configuration
    
Environment Variables:
    OPENAI_API_KEY: Your OpenAI API key (required)
        """
    )
    
    parser.add_argument(
        '--limit', '-l',
        type=int,
        default=None,
        help='Limit number of documents to process (for testing)'
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        default=None,
        help='Path to custom configuration file'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        if args.config:
            reload_config(args.config)
        config = get_config()
    except ConfigError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
    
    # Check for API key
    try:
        config.get_api_key()
    except ConfigError as e:
        print(f"Error: {e}")
        print("\nPlease set the OPENAI_API_KEY environment variable:")
        print("  PowerShell: $env:OPENAI_API_KEY = 'your-key-here'")
        print("  CMD: set OPENAI_API_KEY=your-key-here")
        sys.exit(1)
    
    # Run pipeline
    try:
        pipeline = EmbeddingPipeline()
        stats = pipeline.run(limit=args.limit)
        
        print(f"\n✓ Pipeline completed successfully!")
        print(f"  Output: {stats['output']['file']}")
        print(f"  Records: {stats['output']['records']}")
        print(f"  Cost: ${stats['embedding']['total_cost']:.4f}")
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("\nMake sure preprocessed documents exist. Run the preprocessing pipeline first:")
        print("  cd ragflow/test_suite_rag_preprocessing")
        print("  python script/main.py")
        sys.exit(1)
        
    except Exception as e:
        print(f"Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
