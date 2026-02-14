"""Generate 20-30 test questions from selected corpus (J1).

Uses RAGAS TestsetGenerator when ragas + OPENAI_API_KEY available; otherwise template-based.
Used by Ground Truth Engineer Agent - Question Generation skill.

Usage::
    python -m evaluation.ragas_agents.scripts.generate_questions --manifest <test_corpus_manifest.json> --corpus-dir <test_corpus_dir>
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

# Optional RAGAS TestsetGenerator (synthetic question generation)
RAGAS_GENERATOR_AVAILABLE = False
try:
    from langchain_community.document_loaders import DirectoryLoader
    from langchain_core.documents import Document
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.testset import TestsetGenerator

    RAGAS_GENERATOR_AVAILABLE = True
except ImportError:
    Document = None  # type: ignore[misc, assignment]


def load_documents_from_manifest(manifest: dict) -> list:
    """Build Langchain Documents from test_corpus_manifest paths (e.g. page_content/<id>.txt)."""
    if not RAGAS_GENERATOR_AVAILABLE or Document is None:
        return []
    docs: list = []
    for d in manifest.get("documents", []):
        path = d.get("path")
        if not path:
            continue
        p = Path(path)
        if not p.is_file():
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        docs.append(
            Document(
                page_content=content,
                metadata={
                    "doc_id": d.get("doc_id", ""),
                    "namespace": d.get("namespace", ""),
                    "source": path,
                },
            )
        )
    return docs


def load_config(config_path: Path | None = None) -> dict:
    if config_path is None:
        config_path = RAGAS_AGENTS_ROOT / "config" / "ragas_config.yaml"
    if not config_path.exists():
        return {}
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def generate_with_ragas(manifest: dict | None, corpus_dir: Path | None, num_questions: int) -> list[dict] | None:
    """Generate questions using RAGAS TestsetGenerator. Prefers docs from test_corpus_manifest paths."""
    if not RAGAS_GENERATOR_AVAILABLE or not os.environ.get("OPENAI_API_KEY"):
        return None
    docs: list = []
    if manifest and manifest.get("documents"):
        docs = load_documents_from_manifest(manifest)
        if docs:
            logger.info("Loaded %d documents from test_corpus_manifest paths", len(docs))
    if not docs and corpus_dir and corpus_dir.is_dir():
        try:
            from langchain_community.document_loaders import DirectoryLoader

            loader = DirectoryLoader(str(corpus_dir), glob="**/*.md", show_progress=False)
            docs = loader.load()
        except Exception:
            docs = []
    if not docs:
        logger.warning("No documents from manifest or corpus dir")
        return None
    try:
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from ragas.llms import LangchainLLMWrapper
        from ragas.testset import TestsetGenerator

        # Limit docs for faster generation; ragas builds knowledge graph from them
        docs = docs[: min(100, len(docs))]

        generator_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini"))
        generator_embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings(model="text-embedding-3-small"))
        generator = TestsetGenerator(llm=generator_llm, embedding_model=generator_embeddings)

        # testset_size or test_size depending on ragas version
        test_size = min(num_questions, 30)
        try:
            testset = generator.generate_with_langchain_docs(docs, testset_size=test_size)
        except TypeError:
            testset = generator.generate_with_langchain_docs(docs, test_size=test_size)  # type: ignore[call-arg]

        # Convert ragas testset to our questions format
        questions: list[dict] = []
        to_pandas_fn = getattr(testset, "to_pandas", None)
        if callable(to_pandas_fn):
            df = to_pandas_fn()
            iterrows_fn = getattr(df, "iterrows", None) if df is not None else None
            if callable(iterrows_fn):
                for i, (_, row) in enumerate(iterrows_fn(), start=1):  # type: ignore[arg-type]
                    q = {
                        "question_id": f"q_{i}",
                        "question_text": str(row.get("user_input", row.get("question", ""))),
                        "query_type": "single_hop" if i % 2 == 0 else "multi_hop",
                        "source_doc_ids": [],
                    }
                    ref_ctx = row.get("reference_contexts")
                    if ref_ctx is not None and not (hasattr(ref_ctx, "__len__") and len(ref_ctx) == 0):
                        q["source_doc_ids"] = list(ref_ctx)[:5] if hasattr(ref_ctx, "__iter__") else []
                    questions.append(q)
        if not questions:
            samples = getattr(testset, "samples", None)
            if samples:
                for i, s in enumerate(samples):
                    q = {
                        "question_id": f"q_{i+1}",
                        "question_text": getattr(s, "user_input", None) or getattr(s, "question", "") or "",
                        "query_type": "single_hop" if i % 2 == 0 else "multi_hop",
                        "source_doc_ids": [],
                    }
                    questions.append(q)
        return questions if questions else None
    except Exception as e:
        logger.warning("RAGAS TestsetGenerator failed: %s; falling back to template", e)
        return None


def generate_questions_template(manifest: dict, corpus_dir: Path, num_questions: int) -> list[dict]:
    """Generate placeholder questions from manifest (no LLM)."""
    docs = manifest.get("documents", [])[: max(num_questions, 30)]
    questions = []
    templates = [
        "Was steht in diesem Dokument ueber {topic}?",
        "Welche Informationen enthaelt das Dokument zu {topic}?",
        "Beschreibe die wichtigsten Punkte zu {topic}.",
    ]
    for i, doc in enumerate(docs):
        if i >= num_questions:
            break
        ns = doc.get("namespace", "doc")
        q = {
            "question_id": f"q_{i+1}",
            "question_text": templates[i % len(templates)].format(topic=ns),
            "query_type": "single_hop" if i % 2 == 0 else "multi_hop",
            "source_doc_ids": [doc.get("doc_id", f"doc_{i}")],
        }
        questions.append(q)
    return questions


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate test questions from corpus")
    parser.add_argument("--manifest", type=Path, required=True, help="Path to test_corpus_manifest.json")
    parser.add_argument("--corpus-dir", type=Path, default=None, help="Path to test corpus directory (optional; RAGAS uses manifest paths first)")
    parser.add_argument("--num-questions", type=int, default=25, help="Number of questions to generate")
    parser.add_argument("--output", "-o", type=Path, default=None, help="Output questions.json path")
    parser.add_argument("--config", type=Path, default=None, help="Path to ragas_config.yaml")
    parser.add_argument("--no-ragas", action="store_true", help="Force template (skip RAGAS TestsetGenerator)")
    args = parser.parse_args()

    config = load_config(args.config)
    q_config = config.get("questions", {})
    num_questions = args.num_questions or q_config.get("num_questions", 25)

    manifest_path = args.manifest.resolve()
    if not manifest_path.exists():
        logger.error("Manifest not found: %s", manifest_path)
        return 1
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    corpus_dir = args.corpus_dir.resolve() if args.corpus_dir else Path()

    questions = None
    if not args.no_ragas and RAGAS_GENERATOR_AVAILABLE and os.environ.get("OPENAI_API_KEY"):
        questions = generate_with_ragas(manifest, corpus_dir if corpus_dir else None, num_questions)
    if questions is None:
        questions = generate_questions_template(manifest, corpus_dir, num_questions)
        logger.info("Using template-based question generation (no RAGAS or OPENAI_API_KEY)")

    out = {"manifest_path": str(manifest_path), "num_questions": len(questions), "questions": questions}

    out_path = args.output
    if out_path is None:
        out_dir = config.get("paths", {}).get("ground_truth_dir", REPO_ROOT / "evaluation" / "ragas_agents" / "output" / "ground_truth")
        out_dir = REPO_ROOT / out_dir if not Path(str(out_dir)).is_absolute() else Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "questions.json"
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    logger.info("Wrote %d questions to %s", len(questions), out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
