"""Evaluate RAG responses with LLM-as-Judge (RAGAS metrics).

Uses ragas.evaluate() with AnswerCorrectness, AnswerRelevancy, Faithfulness, ContextPrecision.
Falls back to placeholder if ragas is not installed or OPENAI_API_KEY is missing.

Usage::
    python -m evaluation.ragas_agents.scripts.llm_judge_responses --ground-truth <ground_truth_dataset.json> --rag-responses <rag_responses.json>

Requires: ragas, openai API key (OPENAI_API_KEY) for evaluator LLM.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
RAGAS_AGENTS_ROOT = SCRIPT_DIR.parent
REPO_ROOT = RAGAS_AGENTS_ROOT.parent.parent

# Optional RAGAS imports (lazy: only when running real evaluation)
RAGAS_AVAILABLE = False
evaluate = None
EvaluationDataset = None
SingleTurnSample = None
_answer_correctness = None
_answer_relevancy = None
_context_precision = None
_faithfulness = None


def _ensure_ragas():
    global RAGAS_AVAILABLE, evaluate, EvaluationDataset, SingleTurnSample
    global _answer_correctness, _answer_relevancy, _context_precision, _faithfulness
    if RAGAS_AVAILABLE:
        return True
    try:
        from ragas import EvaluationDataset, SingleTurnSample, evaluate
        from ragas.metrics import answer_correctness, answer_relevancy, context_precision, faithfulness
        EvaluationDataset = EvaluationDataset
        SingleTurnSample = SingleTurnSample
        evaluate = evaluate
        _answer_correctness = answer_correctness
        _answer_relevancy = answer_relevancy
        _context_precision = context_precision
        _faithfulness = faithfulness
        RAGAS_AVAILABLE = True
        return True
    except ImportError:
        return False


def load_config(config_path: Path | None = None) -> dict:
    if config_path is None:
        config_path = RAGAS_AGENTS_ROOT / "config" / "ragas_config.yaml"
    if not config_path.exists():
        return {}
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _build_ragas_samples(ground_truth: dict) -> list:
    """Build list of SingleTurnSample from ground_truth (qa_pairs or questions+answers)."""
    qa = ground_truth.get("qa_pairs")
    if not qa:
        questions = ground_truth.get("questions", [])
        answers = ground_truth.get("answers", [])
        if isinstance(answers, list) and len(answers) >= len(questions):
            qa = [
                {
                    "question_text": q.get("question_text", ""),
                    "reference_answer": a.get("reference_answer", a.get("reference", "")),
                    "response": a.get("response", ""),
                    "retrieved_contexts": a.get("retrieved_contexts", []),
                }
                for q, a in zip(questions, answers, strict=False)
            ]
        else:
            qa = [
                {
                    "question_text": q.get("question_text", ""),
                    "reference_answer": q.get("reference", ""),
                    "response": q.get("response", ""),
                    "retrieved_contexts": q.get("retrieved_contexts", []),
                }
                for q in questions
            ]
    if SingleTurnSample is None:
        return []
    samples = []
    for item in qa:
        user_input = item.get("question_text", item.get("user_input", ""))
        reference = item.get("reference_answer", item.get("reference", item.get("ground_truth", "")))
        response = item.get("response", "")
        contexts = item.get("retrieved_contexts", item.get("contexts", []))
        if not isinstance(contexts, list):
            contexts = [contexts] if contexts else []
        if not user_input and not response:
            continue
        samples.append(
            SingleTurnSample(
                user_input=user_input,
                reference=reference or "",
                response=response or "",
                retrieved_contexts=contexts,
            )
        )
    return samples


def run_ragas_evaluate(ground_truth: dict, metric_names: list[str]) -> dict:
    """Run ragas.evaluate() and return metrics dict. Uses OPENAI_API_KEY."""
    if not _ensure_ragas() or evaluate is None or SingleTurnSample is None or EvaluationDataset is None:
        return {}

    samples = _build_ragas_samples(ground_truth)
    if not samples:
        logger.warning("No valid samples for RAGAS evaluation")
        return {}

    # Map config metric names to ragas metric objects (lazy-loaded)
    name_to_metric = {
        "answer_correctness": _answer_correctness,
        "answer_relevancy": _answer_relevancy,
        "faithfulness": _faithfulness,
        "context_precision": _context_precision,
    }
    metrics_list = []
    for name in metric_names:
        m = name_to_metric.get(name)
        if m is not None:
            metrics_list.append(m)
    if not metrics_list:
        metrics_list = [m for m in (_faithfulness, _answer_relevancy, _context_precision) if m is not None]
        if _answer_correctness is not None:
            metrics_list.insert(0, _answer_correctness)

    try:
        dataset = EvaluationDataset(samples=samples)
        result = evaluate(dataset, metrics=metrics_list, show_progress=True)
        # result may be EvaluationResult or Executor; extract scores defensively
        scores: dict[str, float] = {}
        result_scores = getattr(result, "scores", None)
        if result_scores and isinstance(result_scores, dict):
            for k, v in result_scores.items():
                if isinstance(v, (int, float)):
                    scores[k] = float(v)
                elif hasattr(v, "__iter__") and not isinstance(v, str):
                    try:
                        scores[k] = sum(v) / len(v) if v else 0.0
                    except TypeError:
                        scores[k] = 0.0
        to_pandas_fn = getattr(result, "to_pandas", None)
        if callable(to_pandas_fn):
            df = to_pandas_fn()
            cols = getattr(df, "columns", None) if df is not None else None
            empty = getattr(df, "empty", True) if df is not None else True
            if df is not None and cols is not None and not empty:
                for col in cols:
                    if col not in scores:
                        try:
                            col_series = getattr(df, col, None)
                            if col_series is not None and hasattr(col_series, "mean"):
                                scores[col] = float(col_series.mean())
                        except (TypeError, ValueError):
                            pass
        return {
            "metrics": scores,
            "num_samples": len(samples),
            "_message": "RAGAS evaluation completed",
        }
    except Exception as e:
        logger.exception("RAGAS evaluate failed: %s", e)
        return {}


def llm_judge_placeholder(ground_truth: dict, rag_responses: list, metric_names: list[str]) -> dict:
    """Fallback when RAGAS is not available."""
    scores: dict[str, float] = {m: 0.0 for m in metric_names}
    return {
        "metrics": scores,
        "num_samples": len(rag_responses) if rag_responses else 0,
        "_message": "Placeholder; install ragas and set OPENAI_API_KEY for real LLM-as-Judge evaluation",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="LLM Judge RAG responses (RAGAS metrics)")
    parser.add_argument("--ground-truth", type=Path, required=True, help="Path to ground_truth_dataset.json")
    parser.add_argument("--rag-responses", type=Path, default=None, help="Path to rag_responses.json (optional)")
    parser.add_argument("--metrics", nargs="+", default=["answer_correctness", "answer_relevancy", "faithfulness", "context_precision"])
    parser.add_argument("--output", "-o", type=Path, default=None, help="Output evaluation_results_llm_judge.json path")
    parser.add_argument("--config", type=Path, default=None, help="Path to ragas_config.yaml")
    parser.add_argument("--no-ragas", action="store_true", help="Force placeholder (skip RAGAS even if installed)")
    args = parser.parse_args()

    config = load_config(args.config)
    metrics = args.metrics or config.get("llm_judge", {}).get("metrics", ["answer_correctness", "answer_relevancy", "faithfulness", "context_precision"])

    gt_path = args.ground_truth.resolve()
    if not gt_path.exists():
        logger.error("Ground truth not found: %s", gt_path)
        return 1
    with open(gt_path, encoding="utf-8") as f:
        ground_truth = json.load(f)

    rag_responses = []
    if args.rag_responses and args.rag_responses.exists():
        with open(args.rag_responses, encoding="utf-8") as f:
            rag_responses = json.load(f)
    elif isinstance(ground_truth.get("qa_pairs"), list):
        rag_responses = [p.get("response", "") for p in ground_truth["qa_pairs"]]

    if not args.no_ragas and os.environ.get("OPENAI_API_KEY"):
        _ensure_ragas()
    if not args.no_ragas and RAGAS_AVAILABLE and os.environ.get("OPENAI_API_KEY"):
        results = run_ragas_evaluate(ground_truth, metrics)
        if not results:
            results = llm_judge_placeholder(ground_truth, rag_responses, metrics)
    else:
        if not RAGAS_AVAILABLE and not args.no_ragas:
            logger.info("RAGAS not installed; using placeholder. Install with: pip install ragas datasets")
        elif not os.environ.get("OPENAI_API_KEY") and not args.no_ragas:
            logger.info("OPENAI_API_KEY not set; using placeholder")
        results = llm_judge_placeholder(ground_truth, rag_responses, metrics)

    results["ground_truth_path"] = str(gt_path)

    out_path = args.output
    if out_path is None:
        out_dir = config.get("paths", {}).get("evaluation_results_dir", REPO_ROOT / "evaluation" / "ragas_agents" / "output" / "evaluation_results")
        out_dir = REPO_ROOT / out_dir if not Path(str(out_dir)).is_absolute() else Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "evaluation_results_llm_judge.json"
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info("LLM Judge results written to %s", out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
