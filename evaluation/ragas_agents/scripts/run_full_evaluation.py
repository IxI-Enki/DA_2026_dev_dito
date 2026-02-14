"""Run full RAGAS evaluation pipeline (all phases sequentially).

Phase 1: Data Curator (analyze, assess, select, preprocessing eval)
Phase 2: Ground Truth Engineer (generate questions, create answers, judge relevance, validate, optional augment)
Phase 3: RAG Evaluator (embedding eval, retrieval eval, llm judge, statistics, report)

Usage::
    python -m evaluation.ragas_agents.scripts.run_full_evaluation
    python -m evaluation.ragas_agents.scripts.run_full_evaluation --input-fetched <path> --skip-phase2
"""

from __future__ import annotations

import argparse
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


def run_script(name: str, *args: str, cwd: Path | None = None) -> int:
    """Run a script in this package; return exit code."""
    script = SCRIPT_DIR / f"{name}.py"
    if not script.exists():
        logger.warning("Script not found: %s", script)
        return 0
    cmd = [sys.executable, "-m", "evaluation.ragas_agents.scripts." + name.replace(".py", ""), *args]
    try:
        proc = subprocess.run(cmd, cwd=cwd or REPO_ROOT, timeout=600)
        return proc.returncode
    except Exception as e:
        logger.error("Failed to run %s: %s", name, e)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full RAGAS evaluation pipeline")
    parser.add_argument("--input-fetched", type=Path, default=None, help="Path to fetched_at_* directory (Phase 1)")
    parser.add_argument("--input-preprocessed", type=Path, default=None, help="Path to preprocessed directory (Phase 1)")
    parser.add_argument("--skip-phase1", action="store_true", help="Skip Data Curator phase")
    parser.add_argument("--skip-phase2", action="store_true", help="Skip Ground Truth Engineer phase")
    parser.add_argument("--skip-phase3", action="store_true", help="Skip RAG Evaluator phase")
    parser.add_argument("--config", type=Path, default=None, help="Path to ragas_config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    paths = config.get("paths", {})
    out_dir = paths.get("output_dir", REPO_ROOT / "evaluation" / "ragas_agents" / "output")
    out_dir = REPO_ROOT / out_dir if not Path(str(out_dir)).is_absolute() else Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    exit_code = 0

    # Phase 1: Data Curator
    if not args.skip_phase1 and args.input_fetched:
        logger.info("Phase 1: Data Curator")
        if run_script("analyze_scraped_data", "--input", str(args.input_fetched), "--output", str(out_dir)) != 0:
            exit_code = 1
        if args.input_preprocessed and run_script("assess_document_quality", "--input", str(args.input_preprocessed), "--output", str(out_dir / "document_quality_scores.json")) != 0:
            exit_code = 1
        # select_test_corpus needs pipeline_results; user may run manually
        logger.info("Phase 1 done (run select_test_corpus and run_preprocessing_eval with paths as needed)")

    # Phase 2: Ground Truth Engineer
    if not args.skip_phase2:
        logger.info("Phase 2: Ground Truth Engineer")
        manifest = out_dir / "test_corpus_manifest.json"
        if manifest.exists():
            if run_script("generate_questions", "--manifest", str(manifest), "--output", str(out_dir / "ground_truth" / "questions.json")) != 0:
                exit_code = 1
            qpath = out_dir / "ground_truth" / "questions.json"
            if qpath.exists():
                if run_script("create_answers", "--questions", str(qpath), "--output", str(out_dir / "ground_truth" / "answers.json")) != 0:
                    exit_code = 1
                if run_script("judge_relevance", "--questions", str(qpath), "--output", str(out_dir / "ground_truth" / "relevance_judgments.json")) != 0:
                    exit_code = 1
        else:
            logger.info("Skipping Phase 2 (no test_corpus_manifest.json); run Phase 1 or provide manifest")

    # Phase 3: RAG Evaluator
    if not args.skip_phase3:
        logger.info("Phase 3: RAG Evaluator")
        gt_path = out_dir / "ground_truth" / "ground_truth_dataset.json"
        if not gt_path.exists():
            gt_path = out_dir / "ground_truth" / "answers.json"
        if gt_path.exists():
            if run_script("evaluate_embeddings", "--ground-truth", str(gt_path), "--output", str(out_dir / "evaluation_results" / "evaluation_results_embeddings.json")) != 0:
                exit_code = 1
            if run_script("evaluate_retrieval", "--ground-truth", str(gt_path), "--output", str(out_dir / "evaluation_results" / "evaluation_results_retrieval.json")) != 0:
                exit_code = 1
            if run_script("llm_judge_responses", "--ground-truth", str(gt_path), "--output", str(out_dir / "evaluation_results" / "evaluation_results_llm_judge.json")) != 0:
                exit_code = 1
        eval_dir = out_dir / "evaluation_results"
        eval_dir.mkdir(parents=True, exist_ok=True)
        if run_script("analyze_statistics", "--results-dir", str(eval_dir), "--output", str(eval_dir / "statistical_analysis.json")) != 0:
            exit_code = 1
        if run_script("generate_report", "--results-dir", str(eval_dir), "--stats", str(eval_dir / "statistical_analysis.json"), "--output-dir", str(out_dir / "reports")) != 0:
            exit_code = 1
        logger.info("Phase 3 done; reports in %s/reports", out_dir)

    logger.info("Full evaluation pipeline finished with exit_code=%s", exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
