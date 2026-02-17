"""Keyword search baseline evaluation for thesis table FF1.

Runs all ground-truth questions against DokuWiki ``core.searchPages``
and computes MRR + Precision@5.  This establishes the keyword-search
baseline that semantic retrieval is compared against in FF1.

Usage::

    python -m evaluation.scripts.eval_keyword_baseline
    python -m evaluation.scripts.eval_keyword_baseline --config experiments/keyword_baseline.yaml
    python -m evaluation.scripts.eval_keyword_baseline --top-k 20

Thesis-ID: FF1
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml

# Resolve evaluation root for relative imports
EVAL_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = EVAL_ROOT.parent

sys.path.insert(0, str(EVAL_ROOT.parent))

from evaluation.config import (
    ExperimentConfig,
    load_experiment_config,
    load_ground_truth,
)
from evaluation.metrics.mrr import mean_reciprocal_rank, reciprocal_rank
from evaluation.metrics.precision_at_k import mean_precision_at_k, precision_at_k

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Source-file → page-ID mapping
# ---------------------------------------------------------------------------

def source_file_to_page_id(source_file: str) -> str:
    """Convert ground-truth ``source_file`` to a DokuWiki page ID.

    The fetcher stores pages as .txt; preprocessed test_corpus uses .md.
    DokuWiki namespace colons (``:``) are replaced with underscores (``_``).
    Hyphens remain as-is.  Examples:

    - ``exams_matura-tagesschule-if-it.txt``  -> ``exams:matura-tagesschule-if-it``
    - ``org_termine-2026.md``                 -> ``org:termine-2026``
    - ``archive_exams_semesterpruefungen.txt`` -> ``archive:exams:semesterpruefungen``

    Args:
        source_file: Filename from ground truth.

    Returns:
        DokuWiki page ID with colons as namespace separators.
    """
    name = source_file.removesuffix(".txt").removesuffix(".md")
    page_id = name.replace("_", ":")
    return page_id


# ---------------------------------------------------------------------------
# Lightweight DokuWiki search client
# ---------------------------------------------------------------------------

class WikiSearchClient:
    """Minimal DokuWiki JSON-RPC client for ``core.searchPages``.

    Reads connection settings from the central ``config/env.yaml``.
    Per Article VIII we use ``requests`` directly — no framework wrapper.
    Per Article VI secrets come from token files.
    """

    def __init__(self, env_yaml_path: Path | None = None) -> None:
        if env_yaml_path is None:
            env_yaml_path = REPO_ROOT / "config" / "env.yaml"

        if not env_yaml_path.exists():
            raise FileNotFoundError(
                f"Central config not found: {env_yaml_path}\n"
                f"Ensure config/env.yaml exists in the repository root."
            )

        with open(env_yaml_path, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)

        source_wiki = raw.get("SOURCE_WIKI", {})
        api_cfg = source_wiki.get("api", {})
        self._api_url: str = api_cfg.get("url", "")
        if not self._api_url:
            raise ValueError("SOURCE_WIKI.api.url is empty in env.yaml")

        # Load token from file (Article VI)
        auth = source_wiki.get("authentication", {})
        token_file_raw: str = auth.get("token_file", "")
        # Resolve ${secrets_dir} placeholder
        paths = raw.get("PATHS", {})
        root_dir = paths.get("root_dir", str(REPO_ROOT))
        config_dir = paths.get("config_dir", f"{root_dir}/config")
        secrets_dir = paths.get("secrets_dir", f"{config_dir}/secrets")
        token_file_path = token_file_raw.replace("${secrets_dir}", secrets_dir)
        token_file_path = token_file_path.replace("${config_dir}", config_dir)
        token_file_path = token_file_path.replace("${root_dir}", root_dir)

        token = ""
        tf = Path(token_file_path)
        if tf.exists():
            token = tf.read_text(encoding="utf-8").strip()
            if "=" in token and not token.startswith("eyJ"):
                parts = token.split("=", 1)
                if len(parts) == 2 and parts[0].isupper():
                    token = parts[1]

        # SSL certificate
        cert_raw: str = source_wiki.get("certificate", "")
        cert_path = cert_raw.replace("${secrets_dir}", secrets_dir)
        cert_path = cert_path.replace("${config_dir}", config_dir)
        cert_path = cert_path.replace("${root_dir}", root_dir)

        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        })
        cert_p = Path(cert_path)
        self._session.verify = str(cert_p) if cert_p.exists() else True
        self._request_id = 0

    def search_pages(self, query: str) -> list[dict]:
        """Call ``core.searchPages`` and return the result list.

        Args:
            query: Search query string.

        Returns:
            List of result dicts, each with at least ``id`` and ``score``.

        Raises:
            requests.RequestException: On connection errors.
        """
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": f"eval_{self._request_id}",
            "method": "core.searchPages",
            "params": {"query": query},
        }
        resp = self._session.post(self._api_url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            err = data["error"]
            raise RuntimeError(
                f"JSON-RPC error {err.get('code')}: {err.get('message')}"
            )

        return data.get("result", [])


# ---------------------------------------------------------------------------
# Evaluation runner
# ---------------------------------------------------------------------------

def _get_git_version() -> str:
    """Return short git hash or 'unknown'."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=5,
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def run_keyword_baseline(
    config: ExperimentConfig,
    *,
    top_k: int | None = None,
    verbose: bool = False,
) -> dict:
    """Execute the keyword-search baseline evaluation.

    Args:
        config: Experiment configuration.
        top_k: Override top_k from config.
        verbose: Print per-query results.

    Returns:
        Result dict ready for JSON serialisation.
    """
    k = top_k if top_k is not None else config.top_k

    # Load ground truth
    gt_path = EVAL_ROOT / config.ground_truth_file
    gt_data = load_ground_truth(gt_path)
    qa_pairs = gt_data["qa_pairs"]
    logger.info("Loaded %d ground-truth Q&A pairs", len(qa_pairs))

    # Connect to DokuWiki
    client = WikiSearchClient()
    logger.info("Connected to DokuWiki API")

    per_query_results: list[dict] = []
    mrr_inputs: list[tuple[list[str], set[str]]] = []
    p_at_5_inputs: list[tuple[list[str], set[str]]] = []

    for i, qa in enumerate(qa_pairs):
        question = qa["question"]
        expected_page = source_file_to_page_id(qa["source_file"])
        relevant = {expected_page}

        try:
            search_results = client.search_pages(question)
        except requests.RequestException as exc:
            logger.error("Query %d failed: %s", i + 1, exc)
            per_query_results.append({
                "id": qa["id"],
                "question": question,
                "expected_page": expected_page,
                "error": str(exc),
                "ranked_pages": [],
                "rr": 0.0,
                "p_at_5": 0.0,
            })
            mrr_inputs.append(([], relevant))
            p_at_5_inputs.append(([], relevant))
            continue

        # Extract ranked page IDs (top_k)
        ranked_pages = [r.get("id", "") for r in search_results[:k]]

        rr = reciprocal_rank(ranked_pages, relevant)
        p5 = precision_at_k(ranked_pages, relevant, k=5)

        mrr_inputs.append((ranked_pages, relevant))
        p_at_5_inputs.append((ranked_pages, relevant))

        entry = {
            "id": qa["id"],
            "question": question,
            "expected_page": expected_page,
            "ranked_pages": ranked_pages[:10],
            "rr": round(rr, 4),
            "p_at_5": round(p5, 4),
            "hit_in_top_k": expected_page in ranked_pages,
        }
        per_query_results.append(entry)

        if verbose:
            hit = "HIT" if entry["hit_in_top_k"] else "MISS"
            print(f"  [{i+1:2d}/{len(qa_pairs)}] RR={rr:.3f}  P@5={p5:.3f}  {hit}  {qa['id']}")

    # Aggregate metrics
    agg_mrr = mean_reciprocal_rank(mrr_inputs)
    agg_p5 = mean_precision_at_k(p_at_5_inputs, k=5)

    hits = sum(1 for q in per_query_results if q.get("hit_in_top_k", False))
    total = len(per_query_results)
    errors = sum(1 for q in per_query_results if "error" in q)

    result = {
        "experiment": {
            "name": config.name,
            "type": config.experiment_type,
            "thesis_id": config.thesis_id,
            "config_hash": config.config_hash,
            "code_version": _get_git_version(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "top_k": k,
        },
        "aggregate_metrics": {
            "mrr": round(agg_mrr, 4),
            "precision_at_5": round(agg_p5, 4),
            "hit_rate": round(hits / total, 4) if total else 0.0,
        },
        "summary": {
            "total_queries": total,
            "hits": hits,
            "misses": total - hits - errors,
            "errors": errors,
        },
        "per_query": per_query_results,
    }

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "FF1 Keyword Search Baseline — run ground-truth questions "
            "against DokuWiki core.searchPages and compute MRR + P@5."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m evaluation.scripts.eval_keyword_baseline\n"
            "  python -m evaluation.scripts.eval_keyword_baseline --top-k 20 --verbose\n"
            "  python -m evaluation.scripts.eval_keyword_baseline --config experiments/keyword_baseline.yaml\n"
        ),
    )
    parser.add_argument(
        "--config",
        default=str(EVAL_ROOT / "experiments" / "keyword_baseline.yaml"),
        help="Path to experiment YAML config (default: experiments/keyword_baseline.yaml)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=None,
        help="Override number of results to retrieve per query",
    )
    parser.add_argument(
        "--output-dir",
        default=str(EVAL_ROOT / "results"),
        help="Directory for result JSON files (default: evaluation/results/)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print per-query results to stdout",
    )
    return parser


def main() -> None:
    """Entry point for keyword baseline evaluation."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = _build_parser()
    args = parser.parse_args()

    # Load experiment config
    config = load_experiment_config(args.config)
    logger.info("Experiment: %s (thesis_id=%s)", config.name, config.thesis_id)

    try:
        result = run_keyword_baseline(
            config,
            top_k=args.top_k,
            verbose=args.verbose,
        )
    except FileNotFoundError as exc:
        logger.error("File not found: %s", exc)
        sys.exit(1)
    except requests.ConnectionError as exc:
        logger.error(
            "Cannot connect to DokuWiki API. Is the wiki reachable?\n  %s", exc
        )
        sys.exit(2)
    except RuntimeError as exc:
        logger.error("API error: %s", exc)
        sys.exit(3)

    # Write result JSON
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"keyword_baseline_{timestamp}.json"

    with open(output_file, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)

    logger.info("Results written to %s", output_file)

    # Print summary
    agg = result["aggregate_metrics"]
    summary = result["summary"]
    print("\n" + "=" * 50)
    print(f"  FF1 Keyword Baseline — {config.name}")
    print("=" * 50)
    print(f"  MRR:          {agg['mrr']:.4f}")
    print(f"  Precision@5:  {agg['precision_at_5']:.4f}")
    print(f"  Hit Rate:     {agg['hit_rate']:.1%}")
    print(f"  Queries:      {summary['total_queries']} total, "
          f"{summary['hits']} hits, {summary['errors']} errors")
    print(f"  Output:       {output_file}")
    print("=" * 50)


if __name__ == "__main__":
    main()
