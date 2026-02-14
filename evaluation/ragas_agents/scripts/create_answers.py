"""Create reference answers for generated questions.

Methods: extractive, abstractive, hybrid. Used by Ground Truth Engineer Agent - Answer Creation skill.

Usage::
    python -m evaluation.ragas_agents.scripts.create_answers --questions <questions.json> --corpus-dir <test_corpus_dir>
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


def create_answers_extractive(questions: list[dict], corpus_dir: Path) -> list[dict]:
    """Placeholder: use first 200 chars of first source doc as reference. Full impl would use LLM or extractive QA."""
    result = []
    for q in questions:
        ref = "Referenz-Antwort (Platzhalter). Fuer echte Antworten LLM oder Extractive QA nutzen."
        doc_ids = q.get("source_doc_ids", [])
        if doc_ids and corpus_dir.exists():
            for rel in corpus_dir.rglob("*.md"):
                if any(d in str(rel) for d in doc_ids):
                    ref = rel.read_text(encoding="utf-8")[:500].strip()
                    break
        result.append({
            **q,
            "reference_answer": ref,
            "method_used": "extractive",
        })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Create reference answers for questions")
    parser.add_argument("--questions", type=Path, required=True, help="Path to questions.json")
    parser.add_argument("--corpus-dir", type=Path, default=None, help="Path to test corpus directory")
    parser.add_argument("--method", choices=["extractive", "abstractive", "hybrid"], default="extractive")
    parser.add_argument("--output", "-o", type=Path, default=None, help="Output path (default: ground_truth/answers.json)")
    parser.add_argument("--config", type=Path, default=None, help="Path to ragas_config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
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
    answers = create_answers_extractive(questions, corpus_dir)

    out_path = args.output
    if out_path is None:
        out_dir = config.get("paths", {}).get("ground_truth_dir", REPO_ROOT / "evaluation" / "ragas_agents" / "output" / "ground_truth")
        out_dir = REPO_ROOT / out_dir if not Path(str(out_dir)).is_absolute() else Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "answers.json"
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"questions": questions, "answers": answers}, f, indent=2, ensure_ascii=False)
    logger.info("Wrote answers for %d questions to %s", len(answers), out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
