"""Assess document quality for test corpus eligibility.

Computes content completeness, readability (Flesch), structure preservation
per preprocessed Markdown file. Used by Data Curator Agent - Document Quality Assessment skill.

Usage::
    python -m evaluation.ragas_agents.scripts.assess_document_quality --input <preprocessed_dir>
"""

from __future__ import annotations

import argparse
import json
import logging
import re
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


def flesch_reading_ease_de(text: str) -> float:
    """Approximate Flesch Reading Ease for German (syllables estimated by vowel groups)."""
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    words = re.findall(r"\b\w+\b", text)
    if not sentences or not words:
        return 0.0
    # Approximate syllables: count vowel groups per word
    syllables = 0
    for w in words:
        syl = max(1, len(re.findall(r"[aeiouAEIOUaeiouAEIOU]+", w)))
        syllables += syl
    asl = len(words) / len(sentences)
    asw = syllables / len(words) if words else 0
    # German Flesch: 180 - ASL - 58.5 * ASW (simplified)
    score = 180 - asl - 58.5 * asw
    return max(0.0, min(100.0, score))


def structure_score(text: str) -> float:
    """Ratio of structured content (headings, lists) to total lines."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return 0.0
    structured = sum(1 for l in lines if l.startswith("#") or l.startswith("-") or l.startswith("*") or re.match(r"^\d+\.", l))
    return structured / len(lines)


def assess_one(path: Path, config: dict) -> dict:
    """Assess a single Markdown file."""
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        return {"path": str(path), "error": str(e), "readability": 0.0, "structure": 0.0, "content_length": 0}

    q = config.get("document_quality", {})
    min_flesch = q.get("readability_min_flesch", 20)
    readability = flesch_reading_ease_de(content)
    structure = structure_score(content)
    passed = readability >= min_flesch and structure >= q.get("structure_preservation_min_ratio", 0.5)
    return {
        "path": str(path),
        "content_length": len(content),
        "readability": round(readability, 2),
        "structure": round(structure, 2),
        "readability_threshold": min_flesch,
        "passed": passed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Assess document quality of preprocessed Markdown")
    parser.add_argument("--input", "-i", type=Path, required=True, help="Preprocessed directory (e.g. preprocessed_at_* or for_qdrant/upload_at_*)")
    parser.add_argument("--output", "-o", type=Path, default=None, help="Output JSON path")
    parser.add_argument("--config", type=Path, default=None, help="Path to ragas_config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    input_dir = args.input.resolve()
    if not input_dir.is_dir():
        logger.error("Input is not a directory: %s", input_dir)
        return 1

    results = []
    for md in input_dir.rglob("*.md"):
        results.append(assess_one(md, config))

    aggregate = {
        "total": len(results),
        "passed": sum(1 for r in results if r.get("passed", False)),
        "avg_readability": round(sum(r.get("readability", 0) for r in results) / len(results), 2) if results else 0,
        "avg_structure": round(sum(r.get("structure", 0) for r in results) / len(results), 2) if results else 0,
    }

    out_path = args.output
    if out_path is None:
        out_dir = Path(config.get("paths", {}).get("output_dir", REPO_ROOT / "evaluation" / "ragas_agents" / "output"))
        out_dir = REPO_ROOT / out_dir if not Path(out_dir).is_absolute() else Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "document_quality_scores.json"
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"documents": results, "aggregate": aggregate}, f, indent=2, ensure_ascii=False)
    logger.info("Wrote %d document scores to %s", len(results), out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
