"""Augment ground truth dataset (paraphrase, negative sampling, edge cases).

Uses RAGAS TestsetGenerator (evolution: reasoning, multi_context, simple) when --corpus-dir
and OPENAI_API_KEY are set; otherwise duplicate+paraphrase placeholder.
RAGAS evolution is built into TestsetGenerator via distributions (simple, reasoning, multi_context).
Used by Ground Truth Engineer Agent - Synthetic Data Augmentation skill.

Usage::
    python -m evaluation.ragas_agents.scripts.augment_test_data --dataset <ground_truth_dataset.json> --num-extra 10
    python -m evaluation.ragas_agents.scripts.augment_test_data --dataset <path> --corpus-dir <path> --num-extra 10
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import sys
from pathlib import Path

import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
RAGAS_AGENTS_ROOT = SCRIPT_DIR.parent
REPO_ROOT = RAGAS_AGENTS_ROOT.parent.parent

# Optional RAGAS TestsetGenerator for synthetic augmentation
RAGAS_AUGMENT_AVAILABLE = False
try:
    from langchain_community.document_loaders import DirectoryLoader
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.testset import TestsetGenerator

    RAGAS_AUGMENT_AVAILABLE = True
except ImportError:
    pass


def load_config(config_path: Path | None = None) -> dict:
    if config_path is None:
        config_path = RAGAS_AGENTS_ROOT / "config" / "ragas_config.yaml"
    if not config_path.exists():
        return {}
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def augment_with_ragas(corpus_dir: Path, num_extra: int, seed: int) -> list[dict] | None:
    """Generate num_extra synthetic samples via RAGAS TestsetGenerator (evolution: reasoning, multi_context)."""
    if not RAGAS_AUGMENT_AVAILABLE or not corpus_dir.is_dir() or not os.environ.get("OPENAI_API_KEY"):
        return None
    try:
        from langchain_community.document_loaders import DirectoryLoader
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from ragas.llms import LangchainLLMWrapper
        from ragas.testset import TestsetGenerator

        loader = DirectoryLoader(str(corpus_dir), glob="**/*.md", show_progress=False)
        docs = loader.load()
        if not docs:
            return None
        docs = docs[: min(50, len(docs))]
        generator_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini"))
        generator_embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings(model="text-embedding-3-small"))
        generator = TestsetGenerator(llm=generator_llm, embedding_model=generator_embeddings)
        test_size = min(num_extra, 15)
        try:
            testset = generator.generate_with_langchain_docs(docs, testset_size=test_size)
        except TypeError:
            testset = generator.generate_with_langchain_docs(docs, test_size=test_size)  # type: ignore[call-arg]
        extra: list[dict] = []
        to_pandas_fn = getattr(testset, "to_pandas", None)
        if callable(to_pandas_fn):
            df = to_pandas_fn()
            iterrows_fn = getattr(df, "iterrows", None) if df is not None else None
            if callable(iterrows_fn):
                for i, (_, row) in enumerate(iterrows_fn(), start=1):  # type: ignore[arg-type]
                    q_text = str(row.get("user_input", row.get("question", "")))
                    if not q_text:
                        continue
                    extra.append({
                        "question_id": f"q_aug_{seed}_{i}",
                        "question_text": q_text,
                        "reference_answer": str(row.get("reference", row.get("ground_truth", ""))),
                        "query_type": "multi_hop" if i % 2 else "single_hop",
                        "source_doc_ids": [],
                    })
        if not extra:
            samples = getattr(testset, "samples", None)
            if samples:
                for i, s in enumerate(samples):
                    q_text = getattr(s, "user_input", None) or getattr(s, "question", "") or ""
                    if not q_text:
                        continue
                    extra.append({
                        "question_id": f"q_aug_{seed}_{i+1}",
                        "question_text": q_text,
                        "reference_answer": getattr(s, "reference", "") or "",
                        "query_type": "multi_hop" if i % 2 else "single_hop",
                        "source_doc_ids": [],
                    })
        return extra if extra else None
    except Exception as e:
        logger.warning("RAGAS augmentation failed: %s; falling back to placeholder", e)
        return None


def augment_placeholder(dataset: dict, num_extra: int, seed: int) -> dict:
    """Duplicate and suffix question_id (paraphrase-style)."""
    qa = dataset.get("qa_pairs", dataset.get("questions", []))
    if not isinstance(qa, list):
        qa = []
    rng = random.Random(seed)
    extra = []
    for i in range(num_extra):
        if not qa:
            break
        item = dict(rng.choice(qa))
        item["question_id"] = str(item.get("question_id", f"q_{i}")) + f"_aug_{i}"
        item["question_text"] = "(Augmented) " + str(item.get("question_text", ""))
        if "reference_answer" not in item and "reference" in item:
            item["reference_answer"] = item["reference"]
        extra.append(item)
    return {"qa_pairs": qa + extra, "augmented_count": len(extra), "original_count": len(qa)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Augment ground truth dataset")
    parser.add_argument("--dataset", type=Path, required=True, help="Path to ground_truth_dataset.json")
    parser.add_argument("--corpus-dir", type=Path, default=None, help="Path to corpus (for RAGAS synthetic augmentation)")
    parser.add_argument("--num-extra", type=int, default=10, help="Number of extra examples")
    parser.add_argument("--output", "-o", type=Path, default=None, help="Output path")
    parser.add_argument("--config", type=Path, default=None, help="Path to ragas_config.yaml")
    parser.add_argument("--no-ragas", action="store_true", help="Force placeholder (skip RAGAS)")
    args = parser.parse_args()

    config = load_config(args.config)
    aug = config.get("augmentation", {})
    num_extra = args.num_extra or aug.get("num_extra", 10)
    seed = aug.get("random_seed", 42)

    dataset_path = args.dataset.resolve()
    if not dataset_path.exists():
        logger.error("Dataset not found: %s", dataset_path)
        return 1
    with open(dataset_path, encoding="utf-8") as f:
        dataset = json.load(f)

    qa = dataset.get("qa_pairs", dataset.get("questions", []))
    if not isinstance(qa, list):
        qa = []

    extra_from_ragas = None
    if not args.no_ragas and args.corpus_dir and args.corpus_dir.is_dir() and RAGAS_AUGMENT_AVAILABLE and os.environ.get("OPENAI_API_KEY"):
        extra_from_ragas = augment_with_ragas(args.corpus_dir.resolve(), num_extra, seed)

    if extra_from_ragas:
        merged_qa = qa + extra_from_ragas
        augmented = {"qa_pairs": merged_qa, "augmented_count": len(extra_from_ragas), "original_count": len(qa)}
        logger.info("RAGAS synthetic augmentation: %d original + %d new", len(qa), len(extra_from_ragas))
    else:
        augmented = augment_placeholder(dataset, num_extra, seed)

    out_path = args.output
    if out_path is None:
        out_dir = config.get("paths", {}).get("ground_truth_dir", REPO_ROOT / "evaluation" / "ragas_agents" / "output" / "ground_truth")
        out_dir = REPO_ROOT / out_dir if not Path(str(out_dir)).is_absolute() else Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "ground_truth_dataset_augmented.json"
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(augmented, f, indent=2, ensure_ascii=False)
    logger.info("Augmented dataset: %d original + %d extra -> %s", augmented["original_count"], augmented["augmented_count"], out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
