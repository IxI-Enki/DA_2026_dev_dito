"""
Strategy Generation Runner

Führt die Strategie-Generierung auf Basis der letzten Deep Evaluation aus.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from generators.strategy_generator import StrategyGenerator
from config import get_config

def main():
    config = get_config()
    results_root = config.results_dir
    
    if not results_root:
        # Fallback to script_dir/results if results_dir is not set
        if config.script_dir:
            results_root = config.script_dir.parent / "results"
        else:
            results_root = Path("results")
    
    if not results_root.exists():
        print(f"Results directory not found: {results_root}")
        return
    
    # Find latest eval directory
    eval_dirs = sorted([d for d in results_root.iterdir() if d.is_dir() and d.name.startswith("deep_eval_")], 
                       key=lambda x: x.name, reverse=True)
                       
    if not eval_dirs:
        print("No evaluation results found.")
        return

    latest_eval = eval_dirs[0]
    json_path = latest_eval / "deep_analysis_results.json"
    
    print(f"Generating strategies from: {json_path}")
    
    generator = StrategyGenerator(json_path)
    output_path = generator.generate_strategies(latest_eval)
    
    print(f"\nStrategies generated successfully!")
    print(f"Path: {output_path}")

if __name__ == "__main__":
    main()
