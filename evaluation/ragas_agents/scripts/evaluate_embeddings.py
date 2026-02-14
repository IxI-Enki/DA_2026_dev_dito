"""Evaluate embedding models (J2, FF3).

Computes NDCG@10, MRR, Precision@5. Can integrate with existing evaluation module and RAGAS.
Used by RAG Evaluator Agent - Embedding Evaluation skill.

Usage::
    python -m evaluation.ragas_agents.scripts.evaluate_embeddings --ground-truth <ground_truth_dataset.json>
    python -m evaluation.scripts.eval_model_comparison --compare-all  # existing thesis script
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


def evaluate_embeddings_placeholder(ground_truth: dict, models: list[dict]) -> dict:
    """Placeholder: return dummy scores per model. Full impl: use evaluation.scripts.eval_model_comparison or RAGAS."""
    results = {}
    for m in models:
        mid = m.get("id", m.get("name", "unknown"))
        results[mid] = {
            "ndcg_at_10": 0.0,
            "mrr": 0.0,
            "precision_at_5": 0.0,
            "message": "Placeholder; run evaluation.scripts.eval_model_comparison for real metrics",
        }
    return {"models": results, "ground_truth_path": None}


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate embedding models (J2, FF3)")
    parser.add_argument("--ground-truth", type=Path, default=None, help="Path to ground_truth_dataset.json")
    parser.add_argument("--embeddings-dir", type=Path, default=None, help="Path to embedded_chunks or embedding dir")
    parser.add_argument("--output", "-o", type=Path, default=None, help="Output evaluation_results_embeddings.json path")
    parser.add_argument("--config", type=Path, default=None, help="Path to ragas_config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    models = config.get("embedding_evaluation", {}).get("models", [
        {"id": "mxbai", "name": "deepset/mxbai-embed-de-large-v1"},
        {"id": "bge-m3", "name": "BAAI/bge-m3"},
        {"id": "e5", "name": "multilingual-e5-large-instruct"},
    ])

    ground_truth = {}
    if args.ground_truth and args.ground_truth.exists():
        with open(args.ground_truth, encoding="utf-8") as f:
            ground_truth = json.load(f)

    results = evaluate_embeddings_placeholder(ground_truth, models)
    if args.ground_truth:
        results["ground_truth_path"] = str(args.ground_truth.resolve())

    out_path = args.output
    if out_path is None:
        out_dir = config.get("paths", {}).get("evaluation_results_dir", REPO_ROOT / "evaluation" / "ragas_agents" / "output" / "evaluation_results")
        out_dir = REPO_ROOT / out_dir if not Path(str(out_dir)).is_absolute() else Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "evaluation_results_embeddings.json"
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info("Embedding evaluation results written to %s", out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
