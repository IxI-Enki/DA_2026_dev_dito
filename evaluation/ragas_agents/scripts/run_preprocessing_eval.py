"""Run preprocessing evaluation (techstack/ragflow/preprocessing_evaluation or inline).

Used by Data Curator Agent - Preprocessing Evaluation skill.
If techstack path is set in config, delegates to that framework; otherwise runs a minimal inline check.

Usage::
    python -m evaluation.ragas_agents.scripts.run_preprocessing_eval --original-dir <fetched_dir> --preprocessed-dir <preprocessed_dir>
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
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


def run_external_eval(original_dir: Path, preprocessed_dir: Path, config_root: Path) -> dict:
    """Run techstack preprocessing_evaluation if available."""
    run_script = config_root / "script" / "run_evaluation.py"
    if not run_script.exists():
        return {"delegated": False, "error": f"run_evaluation.py not found: {run_script}"}
    try:
        proc = subprocess.run(
            [sys.executable, str(run_script), "--original-dir", str(original_dir), "--preprocessed-dir", str(preprocessed_dir)],
            capture_output=True,
            text=True,
            cwd=str(config_root),
            timeout=300,
        )
        return {
            "delegated": True,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-2000:] if proc.stdout else "",
            "stderr": proc.stderr[-1000:] if proc.stderr else "",
        }
    except Exception as e:
        return {"delegated": True, "error": str(e)}


def inline_preprocessing_check(original_dir: Path, preprocessed_dir: Path) -> dict:
    """Minimal inline check: file counts and presence."""
    orig_pages = list((original_dir / "pages").rglob("*.txt")) if (original_dir / "pages").exists() else []
    prep_md = list(preprocessed_dir.rglob("*.md")) if preprocessed_dir.exists() else []
    return {
        "original_pages": len(orig_pages),
        "preprocessed_md": len(prep_md),
        "passed": len(prep_md) >= len(orig_pages) * 0.9 if orig_pages else True,
        "message": "Inline count check only; use techstack preprocessing_evaluation for full metrics.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run preprocessing evaluation")
    parser.add_argument("--original-dir", type=Path, required=True, help="Original fetched_at_* directory")
    parser.add_argument("--preprocessed-dir", type=Path, required=True, help="Preprocessed output directory")
    parser.add_argument("--config-root", type=Path, default=None, help="Path to techstack/ragflow/preprocessing_evaluation")
    parser.add_argument("--output", "-o", type=Path, default=None, help="Output JSON path")
    parser.add_argument("--config", type=Path, default=None, help="Path to ragas_config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    techstack_root = args.config_root or config.get("techstack", {}).get("preprocessing_evaluation_root")
    original_dir = args.original_dir.resolve()
    preprocessed_dir = args.preprocessed_dir.resolve()

    if not original_dir.is_dir():
        logger.error("Original dir not found: %s", original_dir)
        return 1
    if not preprocessed_dir.is_dir():
        logger.error("Preprocessed dir not found: %s", preprocessed_dir)
        return 1

    result: dict = {"original_dir": str(original_dir), "preprocessed_dir": str(preprocessed_dir)}
    if techstack_root:
        config_root = Path(techstack_root).resolve()
        result["external"] = run_external_eval(original_dir, preprocessed_dir, config_root)
    result["inline"] = inline_preprocessing_check(original_dir, preprocessed_dir)

    out_path = args.output
    if out_path is None:
        out_dir = config.get("paths", {}).get("output_dir", REPO_ROOT / "evaluation" / "ragas_agents" / "output")
        out_dir = REPO_ROOT / out_dir if not Path(str(out_dir)).is_absolute() else Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "preprocessing_eval_result.json"
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    logger.info("Preprocessing eval result written to %s", out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
