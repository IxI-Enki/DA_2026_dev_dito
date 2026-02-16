"""Preprocessing Evaluation CLI (US8, T047).

Pairs original DokuWiki content from ``data/fetched/`` with preprocessed
Markdown from ``data/preprocessed/``, runs the 7-Metrik-Suite per document,
and generates a JSON + Markdown evaluation report.

Usage:
    python run_eval_preprocessing.py
    python run_eval_preprocessing.py --fetched-dir data/fetched/fetched_at_20260201_120240
    python run_eval_preprocessing.py --preprocessed-dir data/preprocessed/preprocessed_at_20260201
    python run_eval_preprocessing.py --help
"""

from __future__ import annotations

import argparse
import logging
import sys
import yaml
from pathlib import Path
from typing import Any, Optional

# Ensure package is importable
_here = Path(__file__).resolve().parent
_module_root = _here.parent
if str(_module_root) not in sys.path:
    sys.path.insert(0, str(_module_root))
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

from config import get_config, get_latest_fetch_dir
from evaluation.metrics import (
    DocumentScore,
    SemanticSimilarityMetric,
    evaluate_document,
    check_regression,
    passes_thresholds,
    REGRESSION_THRESHOLD,
)
from evaluation.report import generate_report

logger = logging.getLogger(__name__)


def _find_latest_preprocessed(base: Path) -> Optional[Path]:
    """Find the latest preprocessed_at_* directory."""
    if not base.exists():
        return None
    dirs = sorted(
        [d for d in base.iterdir() if d.is_dir() and d.name.startswith("preprocessed_at_")],
        key=lambda x: x.name,
        reverse=True,
    )
    return dirs[0] if dirs else None


def _pair_documents(
    fetched_dir: Path,
    preprocessed_dir: Path,
) -> list[dict[str, Any]]:
    """Pair original DokuWiki pages with their preprocessed Markdown output.

    Returns list of {doc_id, original_path, processed_path}.
    """
    page_content_dir = fetched_dir / "page_content"
    pages_dir = preprocessed_dir / "pages"

    pairs: list[dict[str, Any]] = []

    if not page_content_dir.exists():
        logger.warning("No page_content/ in fetched dir: %s", fetched_dir)
        return pairs

    if not pages_dir.exists():
        logger.warning("No pages/ in preprocessed dir: %s", preprocessed_dir)
        return pairs

    for original_file in sorted(page_content_dir.glob("*.txt")):
        stem = original_file.stem
        processed_file = pages_dir / f"{stem}.md"

        if processed_file.exists():
            page_id = stem.replace("_", ":")
            pairs.append({
                "doc_id": page_id,
                "original_path": original_file,
                "processed_path": processed_file,
            })

    logger.info("Paired %d documents for evaluation", len(pairs))
    return pairs


def _extract_body(md_path: Path) -> str:
    """Extract body content from a Markdown file, stripping YAML frontmatter."""
    text = md_path.read_text(encoding="utf-8", errors="replace")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return text.strip()


def run_evaluation(
    fetched_dir: Path,
    preprocessed_dir: Path,
    output_dir: Optional[Path] = None,
    *,
    use_embeddings: bool = False,
) -> list[DocumentScore]:
    """Run the full 7-metric evaluation.

    Args:
        fetched_dir: Directory with original fetched DokuWiki content.
        preprocessed_dir: Directory with preprocessed Markdown output.
        output_dir: Directory to write reports into (defaults to preprocessed_dir).
        use_embeddings: If True, use sentence-transformers for semantic similarity.

    Returns:
        List of DocumentScore results.
    """
    pairs = _pair_documents(fetched_dir, preprocessed_dir)
    if not pairs:
        logger.error("No document pairs found for evaluation")
        return []

    # Initialize semantic metric once (expensive model load)
    model_name = "paraphrase-multilingual-mpnet-base-v2" if use_embeddings else None
    semantic_metric = SemanticSimilarityMetric(model_name=model_name)

    scores: list[DocumentScore] = []
    for i, pair in enumerate(pairs, 1):
        original = pair["original_path"].read_text(encoding="utf-8", errors="replace")
        processed = _extract_body(pair["processed_path"])

        ds = evaluate_document(
            doc_id=pair["doc_id"],
            original=original,
            processed=processed,
            semantic_metric=semantic_metric,
        )
        scores.append(ds)

        if i % 50 == 0 or i == len(pairs):
            logger.info("Evaluated %d/%d documents", i, len(pairs))

    # Generate reports
    if output_dir is None:
        output_dir = preprocessed_dir

    json_path = generate_report(
        scores,
        output_dir,
        fetched_dir=str(fetched_dir),
        preprocessed_dir=str(preprocessed_dir),
    )

    # Print summary
    _print_summary(scores, json_path)

    return scores


def _print_summary(scores: list[DocumentScore], report_path: Path) -> None:
    """Print evaluation summary to stdout."""
    n = len(scores)
    passing = sum(1 for ds in scores if passes_thresholds(ds))
    regression = check_regression(scores)

    sep = "=" * 60
    print(f"\n{sep}")
    print("PREPROCESSING EVALUATION COMPLETE")
    print(sep)
    print(f"Documents evaluated:  {n}")
    print(f"All thresholds pass:  {passing}/{n} ({passing/n:.1%})" if n else "")

    # Regression status
    reg_pass = all(r["pass"] for r in regression.values()) if regression else True
    print(f"Regression check:     {'PASS' if reg_pass else 'FAIL'}")
    print(f"Report: {report_path}")
    print(sep)


def main() -> int:
    """CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Preprocessing Evaluation -- 7-Metrik-Suite",
    )
    parser.add_argument("--fetched-dir", type=Path, default=None,
                        help="Fetched data directory (auto-detect if omitted)")
    parser.add_argument("--preprocessed-dir", type=Path, default=None,
                        help="Preprocessed output directory (auto-detect if omitted)")
    parser.add_argument("--output-dir", type=Path, default=None,
                        help="Report output directory (defaults to preprocessed dir)")
    parser.add_argument("--config", type=Path, default=None,
                        help="Config file (env.yaml)")
    parser.add_argument("--use-embeddings", action="store_true",
                        help="Use sentence-transformers for semantic similarity (slower)")
    args = parser.parse_args()

    cfg = get_config(args.config)

    # Resolve fetched dir
    fetched_dir = args.fetched_dir
    if fetched_dir is None:
        fetched_dir = get_latest_fetch_dir(cfg.fetched_dir)
        if fetched_dir is None:
            logger.error("No fetched data found in %s", cfg.fetched_dir)
            return 1
    logger.info("Fetched:      %s", fetched_dir)

    # Resolve preprocessed dir
    preprocessed_dir = args.preprocessed_dir
    if preprocessed_dir is None:
        preprocessed_dir = _find_latest_preprocessed(cfg.output_dir)
        if preprocessed_dir is None:
            logger.error("No preprocessed data found in %s", cfg.output_dir)
            return 1
    logger.info("Preprocessed: %s", preprocessed_dir)

    try:
        scores = run_evaluation(
            fetched_dir=fetched_dir,
            preprocessed_dir=preprocessed_dir,
            output_dir=args.output_dir,
            use_embeddings=args.use_embeddings,
        )

        if not scores:
            return 1

        # Check regression for exit code
        regression = check_regression(scores)
        if any(not r["pass"] for r in regression.values()):
            logger.warning("Regression check FAILED")
            return 2

    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
        return 130
    except Exception as e:
        logger.error("Evaluation failed: %s", e)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
