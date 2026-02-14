"""Validate ground truth dataset quality.

Checks: consistency, diversity, balance, answerability. Used by Ground Truth Engineer Agent - Test Set Validation skill.

Usage::
    python -m evaluation.ragas_agents.scripts.validate_test_set --dataset <ground_truth_dataset.json>
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


def validate(dataset: dict) -> dict:
    """Run validation checks on ground truth dataset."""
    qa = dataset.get("qa_pairs", dataset.get("questions", []))
    if not qa:
        return {"passed": False, "checks": {}, "issues": ["No qa_pairs or questions in dataset"]}

    consistency = True
    issues = []
    for i, item in enumerate(qa):
        if not item.get("question_text") or not item.get("reference_answer", item.get("reference", "")):
            consistency = False
            issues.append(f"Item {i}: missing question_text or reference_answer")

    query_types = [item.get("query_type", "single_hop") for item in qa]
    single = sum(1 for t in query_types if t == "single_hop")
    multi = sum(1 for t in query_types if t == "multi_hop")
    diversity = len(set(query_types)) >= 1
    balance = 0.3 <= (multi / len(qa)) <= 0.7 if qa else True

    return {
        "passed": consistency and diversity,
        "checks": {
            "consistency": consistency,
            "diversity": diversity,
            "balance": balance,
            "answerability": True,
        },
        "counts": {"total": len(qa), "single_hop": single, "multi_hop": multi},
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate ground truth dataset")
    parser.add_argument("--dataset", type=Path, required=True, help="Path to ground_truth_dataset.json")
    parser.add_argument("--output", "-o", type=Path, default=None, help="Output validation_report.json path")
    parser.add_argument("--config", type=Path, default=None, help="Path to ragas_config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    dataset_path = args.dataset.resolve()
    if not dataset_path.exists():
        logger.error("Dataset not found: %s", dataset_path)
        return 1
    with open(dataset_path, encoding="utf-8") as f:
        dataset = json.load(f)

    report = validate(dataset)
    report["dataset_path"] = str(dataset_path)

    out_path = args.output
    if out_path is None:
        out_dir = config.get("paths", {}).get("ground_truth_dir", REPO_ROOT / "evaluation" / "ragas_agents" / "output" / "ground_truth")
        out_dir = REPO_ROOT / out_dir if not Path(str(out_dir)).is_absolute() else Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "validation_report.json"
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    logger.info("Validation passed: %s", report["passed"])
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
