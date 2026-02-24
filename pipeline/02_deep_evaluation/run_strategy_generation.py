"""Strategy Generation Runner

Fuehrt die Strategie-Generierung auf Basis der letzten Deep Evaluation aus.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Shared CLI utilities
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shared"))
from cli_utils import add_no_color_arg, apply_color_from_args, register_sigint, style
from generators.strategy_generator import StrategyGenerator

from config import get_config


def main():
    parser = argparse.ArgumentParser(description="Strategy Generation Runner")
    add_no_color_arg(parser)
    args = parser.parse_args()
    apply_color_from_args(args)
    register_sigint("run_strategy_generation")

    config = get_config()
    results_root = config.results_dir

    if not results_root:
        if config.script_dir:
            results_root = config.script_dir.parent / "results"
        else:
            results_root = Path("results")

    if not results_root.exists():
        print(f"Results directory not found: {results_root}")
        return

    eval_dirs = sorted(
        [d for d in results_root.iterdir() if d.is_dir() and d.name.startswith("deep_eval_")],
        key=lambda x: x.name,
        reverse=True,
    )

    if not eval_dirs:
        print("No evaluation results found.")
        return

    latest_eval = eval_dirs[0]
    json_path = latest_eval / "deep_analysis_results.json"

    print(style(f"Generating strategies from: {json_path}", "cyan"))

    generator = StrategyGenerator(json_path)
    output_path = generator.generate_strategies(latest_eval)

    print(style("\nStrategies generated successfully!", "bright_green", "bold"))
    print(f"Path: {output_path}")


if __name__ == "__main__":
    main()
