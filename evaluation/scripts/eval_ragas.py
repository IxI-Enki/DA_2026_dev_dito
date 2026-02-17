"""Run RAGAS LLM-as-Judge evaluation against ground truth (Ollama).

Loads experiment config for llm_base_url and model, ground truth Q&A,
and optionally a result file with contexts/answer per query. Discovers
Ollama by testing the config URL, then localhost:11434 and 127.0.0.1:11434.
Writes RAGAS metric scores to stdout and optionally to a JSON file.

Usage:
  python -m evaluation.scripts.eval_ragas --config evaluation/experiments/full_eval.yaml
  python -m evaluation.scripts.eval_ragas --ollama-url http://localhost:11434/v1   # override URL
  python -m evaluation.scripts.eval_ragas --config full_eval.yaml --result results/run1.json --output ragas_scores.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

import requests

from evaluation.config import (
    EVAL_ROOT,
    load_experiment_config,
    load_ground_truth,
)
from evaluation.ragas import RAGASEvaluator

logger = logging.getLogger(__name__)

OLLAMA_DEFAULT_PORT = 11434
OLLAMA_HEALTH_PATH = "/api/tags"
OLLAMA_CHECK_TIMEOUT = 3.0


def _normalize_ollama_base_url(url: str) -> str:
    """Ensure URL ends with /v1 for OpenAI-compatible API."""
    url = (url or "").strip().rstrip("/")
    if not url:
        return f"http://localhost:{OLLAMA_DEFAULT_PORT}/v1"
    if not url.endswith("/v1"):
        url = f"{url}/v1"
    return url


def _check_ollama_reachable(base_url: str, timeout: float = OLLAMA_CHECK_TIMEOUT) -> bool:
    """Return True if Ollama responds at base_url (GET /api/tags). base_url should end with /v1."""
    root = base_url.rstrip("/").removesuffix("/v1") if base_url else ""
    if not root:
        return False
    health_url = f"{root}{OLLAMA_HEALTH_PATH}"
    try:
        r = requests.get(health_url, timeout=timeout)
        return r.status_code == 200
    except requests.RequestException:
        return False


def _discover_ollama_url(config_url: str, timeout: float = OLLAMA_CHECK_TIMEOUT) -> str | None:
    """Try localhost, 127.0.0.1, then config_url; return first reachable base URL (with /v1) or None."""
    candidates = [
        f"http://localhost:{OLLAMA_DEFAULT_PORT}/v1",
        f"http://127.0.0.1:{OLLAMA_DEFAULT_PORT}/v1",
    ]
    config_normalized = _normalize_ollama_base_url(config_url) if config_url else None
    if config_normalized and config_normalized not in candidates:
        candidates.append(config_normalized)
    for url in candidates:
        if _check_ollama_reachable(url, timeout):
            return url
    return None


def _get_ollama_models(base_url: str, timeout: float = OLLAMA_CHECK_TIMEOUT) -> list[str]:
    """Return list of model names from Ollama /api/tags. base_url should end with /v1."""
    root = base_url.rstrip("/").removesuffix("/v1") if base_url else ""
    if not root:
        return []
    try:
        r = requests.get(f"{root}{OLLAMA_HEALTH_PATH}", timeout=timeout)
        if r.status_code != 200:
            return []
        data = r.json()
        names = []
        for m in data.get("models", []):
            n = m.get("name")
            if n:
                names.append(n)
        return names
    except (requests.RequestException, ValueError, KeyError):
        return []


def _resolve_ollama_model(configured: str, available: list[str]) -> str | None:
    """Exact match, or first available model whose name starts with configured (e.g. llama3.2 -> llama3.2:latest)."""
    if not configured or not available:
        return configured or None
    configured = configured.strip()
    if configured in available:
        return configured
    matches = [n for n in available if n == configured or n.startswith(configured + ":")]
    if not matches:
        return None
    # Prefer :latest if present
    for n in matches:
        if n.endswith(":latest"):
            return n
    return matches[0]


def _build_data(gt: dict, result_data: dict | None) -> list[dict]:
    """Build list of { question, ground_truth, contexts, answer } from GT and optional result."""
    qa_pairs = gt.get("qa_pairs", [])
    if not qa_pairs:
        return []
    per_query = (result_data or {}).get("per_query", [])
    data = []
    for i, qa in enumerate(qa_pairs):
        question = qa.get("question", "")
        ground_truth = qa.get("ground_truth", "")
        contexts = []
        answer = ground_truth
        if per_query and i < len(per_query):
            row = per_query[i]
            contexts = row.get("contexts", row.get("retrieved_contexts", []))
            if not isinstance(contexts, list):
                contexts = [contexts] if contexts else []
            answer = row.get("answer", row.get("response", ground_truth))
        data.append(
            {
                "question": question,
                "ground_truth": ground_truth,
                "contexts": contexts,
                "answer": answer,
            }
        )
    return data


def main() -> int:
    """Entry point for RAGAS evaluation."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    # Reduce noise: OpenAI retries WARNING; ragas.executor OutputParserException at ERROR -> CRITICAL so per-job parse failures don't flood output
    for name in ("openai", "openai._base_client", "ragas", "httpx"):
        logging.getLogger(name).setLevel(logging.WARNING)
    logging.getLogger("ragas.executor").setLevel(logging.CRITICAL)

    parser = argparse.ArgumentParser(
        description="RAGAS LLM-as-Judge evaluation (Ollama) against ground truth",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=EVAL_ROOT / "experiments" / "full_eval.yaml",
        help="Path to experiment YAML (default: evaluation/experiments/full_eval.yaml)",
    )
    parser.add_argument(
        "--ground-truth",
        type=Path,
        default=None,
        help="Override ground truth JSON path (default: from config)",
    )
    parser.add_argument(
        "--result",
        type=Path,
        default=None,
        help="Optional result JSON with per_query contexts/answer for RAG run",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write RAGAS scores to this JSON file",
    )
    parser.add_argument(
        "--ollama-url",
        type=str,
        default=os.environ.get("OLLAMA_BASE_URL", ""),
        help="Ollama API base URL (e.g. http://localhost:11434/v1). Overrides config. Set if Ollama runs locally.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=os.environ.get("OLLAMA_MODEL", ""),
        help="Ollama model name (e.g. llama3.2:latest). Overrides config. Use if config model not found.",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = (Path.cwd() / config_path).resolve()
    if not config_path.exists():
        logger.error("Config not found: %s", config_path)
        return 1

    try:
        config = load_experiment_config(config_path)
    except (FileNotFoundError, ValueError) as e:
        logger.error("Failed to load config: %s", e)
        return 1

    gt_path = args.ground_truth or (EVAL_ROOT / config.ground_truth_file)
    if not gt_path.is_absolute():
        gt_path = EVAL_ROOT / gt_path
    if not gt_path.exists():
        logger.error("Ground truth not found: %s", gt_path)
        return 1

    try:
        gt = load_ground_truth(gt_path)
    except FileNotFoundError as e:
        logger.error("%s", e)
        return 1

    result_data = None
    if args.result and args.result.exists():
        with open(args.result, encoding="utf-8") as f:
            result_data = json.load(f)

    data = _build_data(gt, result_data)
    if not data:
        logger.error("No Q&A pairs to evaluate")
        return 1

    if args.ollama_url:
        llm_base_url = _normalize_ollama_base_url(args.ollama_url)
        if not _check_ollama_reachable(llm_base_url):
            logger.error(
                "Ollama not reachable at %s. Start Ollama or check --ollama-url.", llm_base_url
            )
            return 1
        logger.info("Ollama base URL: %s", llm_base_url)
    else:
        config_url = _normalize_ollama_base_url(config.llm_base_url)
        llm_base_url = _discover_ollama_url(config_url)
        if not llm_base_url:
            logger.error(
                "Ollama not reachable at localhost:%s or at %s. Start Ollama or set --ollama-url.",
                OLLAMA_DEFAULT_PORT,
                config_url,
            )
            return 1
        logger.info("Ollama base URL: %s", llm_base_url)

    # Resolve model: CLI/env override, or config model matched to Ollama's available list (exact or tag prefix)
    configured_model = (args.model or config.llm_model or "").strip()
    available_models = _get_ollama_models(llm_base_url)
    if args.model:
        llm_model = configured_model
    else:
        resolved = _resolve_ollama_model(configured_model, available_models)
        if not resolved:
            logger.error(
                "Model %r not found in Ollama. Available: %s. Use --model <name> or set OLLAMA_MODEL.",
                configured_model,
                ", ".join(available_models) if available_models else "(none)",
            )
            return 1
        llm_model = resolved
        if llm_model != configured_model:
            logger.info("Using model %r (config had %r)", llm_model, configured_model)

    evaluator = RAGASEvaluator(
        llm_base_url=llm_base_url,
        model=llm_model,
        temperature=config.ragas_temperature,
    )
    n_samples = len(data)
    logger.info(
        "Running RAGAS evaluation on %d samples (this may take several minutes)...", n_samples
    )
    sys.stdout.flush()
    sys.stderr.flush()
    try:
        scores = evaluator.evaluate(data)
    except KeyboardInterrupt:
        logger.info("Interrupted by user (Ctrl+C).")
        return 130
    except asyncio.CancelledError:
        logger.info("Interrupted.")
        return 130
    logger.info("RAGAS evaluation completed.")
    if not scores:
        logger.warning("RAGAS returned no scores (check Ollama and ragas install)")
        return 0

    print("RAGAS scores:")
    for k, v in sorted(scores.items()):
        print(f"  {k}: {v:.4f}")

    if args.output:
        out_path = Path(args.output)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(scores, f, indent=2)
        logger.info("Wrote scores to %s", out_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
