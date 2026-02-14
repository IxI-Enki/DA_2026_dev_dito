"""Judge relevance of documents per question (0-3 scale) for NDCG@10.

Used by Ground Truth Engineer Agent - Relevance Judgment skill.
Output: relevance_judgments.json.

Usage::
    python -m evaluation.ragas_agents.scripts.judge_relevance --questions <questions.json> --corpus-dir <test_corpus_dir>
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


def judge_relevance_placeholder(questions: list[dict], corpus_dir: Path, scale_max: int = 3) -> list[dict]:
    """Placeholder: source_doc_ids get relevance 3, others 0. Full impl: LLM or human review."""
    judgments = []
    for q in questions:
        qid = q.get("question_id", "")
        source_ids = q.get("source_doc_ids", [])
        for doc_id in source_ids:
            judgments.append({"question_id": qid, "document_id": doc_id, "relevance_score": scale_max})
    return judgments


def main() -> int:
    parser = argparse.ArgumentParser(description="Judge relevance of documents per question")
    parser.add_argument("--questions", type=Path, required=True, help="Path to questions.json")
    parser.add_argument("--corpus-dir", type=Path, default=None, help="Path to test corpus directory")
    parser.add_argument("--output", "-o", type=Path, default=None, help="Output relevance_judgments.json path")
    parser.add_argument("--config", type=Path, default=None, help="Path to ragas_config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    scale = config.get("relevance_judgment", {}).get("scale_max", 3)

    questions_path = args.questions.resolve()
    if not questions_path.exists():
        logger.error("Questions file not found: %s", questions_path)
        return 1
    with open(questions_path, encoding="utf-8") as f:
        data = json.load(f)
    questions = data.get("questions", data) if isinstance(data, dict) else data
    if not isinstance(questions, list):
        questions = []

    corpus_dir = args.corpus_dir.resolve() if args.corpus_dir else Path()
    judgments = judge_relevance_placeholder(questions, corpus_dir, scale_max=scale)

    out_path = args.output
    if out_path is None:
        out_dir = config.get("paths", {}).get("ground_truth_dir", REPO_ROOT / "evaluation" / "ragas_agents" / "output" / "ground_truth")
        out_dir = REPO_ROOT / out_dir if not Path(str(out_dir)).is_absolute() else Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "relevance_judgments.json"
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"judgments": judgments, "scale_max": scale}, f, indent=2, ensure_ascii=False)
    logger.info("Wrote %d relevance judgments to %s", len(judgments), out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
