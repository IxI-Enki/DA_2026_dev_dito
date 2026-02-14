"""Evaluate retrieval strategies (J6: Dense, BM25, Hybrid).

Computes Precision@5, NDCG@10, Recall@k. Used by RAG Evaluator Agent - Retrieval Quality skill.

Usage::
    python -m evaluation.ragas_agents.scripts.evaluate_retrieval --ground-truth <ground_truth_dataset.json>
    python -m evaluation.scripts.eval_hybrid_vs_dense  # existing thesis script
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
RAGAS_AGENTS_ROOT = SCRIPT_DIR.parent
REPO_ROOT = RAGAS_AGENTS_ROOT.parent.parent


def load_config(config_path: Path | None = None) -> dict:
    if config_path is None:
        config_path = RAGAS_AGENTS_ROOT / "config" / "ragas_config.yaml"
    if not config_path.exists():
        return {}
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def evaluate_retrieval_placeholder(ground_truth: dict, strategies: list[str]) -> dict:
    """Placeholder: return dummy scores per strategy. Full impl: use evaluation.scripts.eval_hybrid_vs_dense or Qdrant + BM25."""
    results = {}
    for s in strategies:
        results[s] = {
            "precision_at_5": 0.0,
            "ndcg_at_10": 0.0,
            "recall_at_10": 0.0,
            "message": "Placeholder; run evaluation.scripts.eval_hybrid_vs_dense for real metrics",
        }
    return {"strategies": results}


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate retrieval strategies (J6)")
    parser.add_argument("--ground-truth", type=Path, default=None, help="Path to ground_truth_dataset.json")
    parser.add_argument("--qdrant-url", type=str, default=None, help="Qdrant URL (for full evaluation)")
    parser.add_argument("--strategies", nargs="+", default=["dense", "bm25", "hybrid"], help="Strategies to evaluate")
    parser.add_argument("--output", "-o", type=Path, default=None, help="Output evaluation_results_retrieval.json path")
    parser.add_argument("--config", type=Path, default=None, help="Path to ragas_config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    strategies = args.strategies or config.get("retrieval_evaluation", {}).get("strategies", ["dense", "bm25", "hybrid"])

    ground_truth = {}
    if args.ground_truth and args.ground_truth.exists():
        with open(args.ground_truth, encoding="utf-8") as f:
            ground_truth = json.load(f)

    results = evaluate_retrieval_placeholder(ground_truth, strategies)

    out_path = args.output
    if out_path is None:
        out_dir = config.get("paths", {}).get("evaluation_results_dir", REPO_ROOT / "evaluation" / "ragas_agents" / "output" / "evaluation_results")
        out_dir = REPO_ROOT / out_dir if not Path(str(out_dir)).is_absolute() else Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "evaluation_results_retrieval.json"
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info("Retrieval evaluation results written to %s", out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
