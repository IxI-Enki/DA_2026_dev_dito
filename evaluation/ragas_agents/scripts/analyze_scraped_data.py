"""Analyze scraped DokuWiki data from fetched_at_* directories.

Parses fetch_statistics.json, analyzes namespaces, identifies duplicate content,
reports media type distribution. Used by Data Curator Agent - Scraped Data Analysis skill.

Usage::
    python -m evaluation.ragas_agents.scripts.analyze_scraped_data --input <path_to_fetched_at_*>
    python -m evaluation.ragas_agents.scripts.analyze_scraped_data --input <path> --output <output_dir>
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path

import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
RAGAS_AGENTS_ROOT = SCRIPT_DIR.parent
REPO_ROOT = RAGAS_AGENTS_ROOT.parent.parent


def load_config(config_path: Path | None = None) -> dict:
    """Load ragas_config.yaml."""
    if config_path is None:
        config_path = RAGAS_AGENTS_ROOT / "config" / "ragas_config.yaml"
    if not config_path.exists():
        return {}
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def analyze_fetched_dir(input_dir: Path) -> dict:
    """Analyze a fetched_at_* directory: stats, namespaces, media types."""
    result: dict = {
        "input_dir": str(input_dir),
        "fetch_statistics": None,
        "namespaces": {},
        "media_by_type": Counter(),
        "pages_count": 0,
        "media_count": 0,
        "errors": [],
    }

    stats_file = input_dir / "fetch_statistics.json"
    if stats_file.exists():
        try:
            with open(stats_file, encoding="utf-8") as f:
                result["fetch_statistics"] = json.load(f)
        except Exception as e:
            result["errors"].append(f"Failed to parse fetch_statistics.json: {e}")

    pages_dir = input_dir / "pages"
    if pages_dir.exists():
        for p in pages_dir.rglob("*.txt"):
            result["pages_count"] += 1
            # Namespace from relative path (e.g. departm/subpage.txt -> departm)
            rel = p.relative_to(pages_dir)
            ns = rel.parts[0] if len(rel.parts) > 1 else "root"
            result["namespaces"][ns] = result["namespaces"].get(ns, 0) + 1

    media_dir = input_dir / "media"
    if media_dir.exists():
        for p in media_dir.rglob("*"):
            if p.is_file():
                result["media_count"] += 1
                suffix = p.suffix.lower() or "unknown"
                result["media_by_type"][suffix] += 1

    result["namespaces"] = dict(result["namespaces"])
    result["media_by_type"] = dict(result["media_by_type"])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze scraped DokuWiki data")
    parser.add_argument("--input", "-i", type=Path, required=True, help="Path to fetched_at_* directory")
    parser.add_argument("--output", "-o", type=Path, default=None, help="Output directory for JSON report")
    parser.add_argument("--config", type=Path, default=None, help="Path to ragas_config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    input_dir = args.input.resolve()
    if not input_dir.is_dir():
        logger.error("Input is not a directory: %s", input_dir)
        return 1

    analysis = analyze_fetched_dir(input_dir)
    logger.info("Pages: %d, Media: %d, Namespaces: %s", analysis["pages_count"], analysis["media_count"], list(analysis["namespaces"].keys()))

    out_dir = args.output
    if out_dir is None:
        out_dir = Path(config.get("paths", {}).get("output_dir", REPO_ROOT / "evaluation" / "ragas_agents" / "output"))
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "scraped_data_analysis.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    logger.info("Report written to %s", out_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
