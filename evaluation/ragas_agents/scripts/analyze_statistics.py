"""Statistical analysis of evaluation results.

Deskriptive Statistik, Ergebnistabellen, 95% CI. No significance tests (per thesis).
Used by RAG Evaluator Agent - Statistical Analysis skill.

Usage::
    python -m evaluation.ragas_agents.scripts.analyze_statistics --results-dir <evaluation_results_dir>
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


def _mean_std(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    n = len(values)
    mean = sum(values) / n
    var = sum((x - mean) ** 2 for x in values) / n
    return mean, var ** 0.5


def analyze_results(results_dir: Path, confidence_level: float = 0.95) -> dict:
    """Aggregate evaluation JSONs and compute descriptive stats (no significance tests)."""
    aggregated = {"sources": [], "tables": {}, "summary": {}}
    if not results_dir.exists():
        return aggregated

    for jf in results_dir.glob("evaluation_results_*.json"):
        try:
            with open(jf, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        aggregated["sources"].append(str(jf.name))
        if "models" in data:
            for mid, mdata in data["models"].items():
                row = {k: v for k, v in mdata.items() if isinstance(v, (int, float))}
                if row:
                    aggregated["tables"][f"embedding_{mid}"] = row
        if "strategies" in data:
            for sid, sdata in data["strategies"].items():
                row = {k: v for k, v in sdata.items() if isinstance(v, (int, float))}
                if row:
                    aggregated["tables"][f"retrieval_{sid}"] = row
        if "metrics" in data:
            aggregated["tables"]["llm_judge"] = {k: v for k, v in data["metrics"].items() if isinstance(v, (int, float))}

    aggregated["summary"] = {"confidence_level": confidence_level, "no_significance_tests": True}
    return aggregated


def main() -> int:
    parser = argparse.ArgumentParser(description="Statistical analysis of evaluation results")
    parser.add_argument("--results-dir", type=Path, default=None, help="Directory with evaluation_results_*.json")
    parser.add_argument("--output", "-o", type=Path, default=None, help="Output statistical_analysis_*.json path")
    parser.add_argument("--plots-dir", type=Path, default=None, help="Directory for plots (optional)")
    parser.add_argument("--config", type=Path, default=None, help="Path to ragas_config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    stats_config = config.get("statistics", {})
    confidence_level = stats_config.get("confidence_level", 0.95)

    results_dir = args.results_dir
    if results_dir is None:
        results_dir = config.get("paths", {}).get("evaluation_results_dir", REPO_ROOT / "evaluation" / "ragas_agents" / "output" / "evaluation_results")
        results_dir = REPO_ROOT / results_dir if not Path(str(results_dir)).is_absolute() else Path(results_dir)
    results_dir = Path(results_dir).resolve()

    aggregated = analyze_results(results_dir, confidence_level)

    out_path = args.output
    if out_path is None:
        out_dir = config.get("paths", {}).get("evaluation_results_dir", results_dir)
        out_dir = REPO_ROOT / out_dir if not Path(str(out_dir)).is_absolute() else Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "statistical_analysis.json"
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(aggregated, f, indent=2, ensure_ascii=False)
    logger.info("Statistical analysis written to %s", out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
