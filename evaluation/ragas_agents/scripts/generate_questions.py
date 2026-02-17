"""Generate 20-30 test questions from selected corpus (J1).

Uses RAGAS TestsetGenerator when ragas + OPENAI_API_KEY available; otherwise template-based.
Used by Ground Truth Engineer Agent - Question Generation skill.

Based on: https://docs.ragas.io/en/stable/getstarted/rag_testset_generation/
          https://docs.ragas.io/en/stable/howtos/customizations/testgenerator/_testgen-custom-single-hop/
          https://docs.ragas.io/en/stable/howtos/customizations/testgenerator/_persona_generator/
          https://docs.ragas.io/en/stable/howtos/llm-adapters/
          https://docs.ragas.io/en/stable/concepts/test_data_generation/rag/

Usage::
    python -m evaluation.ragas_agents.scripts.generate_questions \
        --corpus-dir data/preprocessed/preprocessed_at_20260216_192955/pages \
        --num-questions 30
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path

import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
RAGAS_AGENTS_ROOT = SCRIPT_DIR.parent
REPO_ROOT = RAGAS_AGENTS_ROOT.parent.parent

# Optional RAGAS TestsetGenerator (synthetic question generation)
RAGAS_AVAILABLE = False
try:
    from langchain_core.documents import Document

    RAGAS_AVAILABLE = True
except ImportError:
    Document = None  # type: ignore[misc, assignment]

# German context instruction for RAGAS LLM — steers question generation language
# without fragile adapt_prompts() which corrupts synthesizer state.
GERMAN_LLM_CONTEXT = (
    "Du generierst Testfragen fuer ein deutschsprachiges Schulwiki (HTL Leonding). "
    "Alle Fragen und Antworten muessen auf Deutsch formuliert sein. "
    "Verwende klare, praezise Sprache."
)


def load_docs_from_corpus_dir(corpus_dir: Path, max_docs: int = 10) -> list:
    """Load preprocessed .md files, strip YAML frontmatter, return LangChain Documents."""
    if Document is None:
        return []
    import random

    docs: list = []
    md_files = sorted(corpus_dir.glob("**/*.md"))
    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8", errors="replace")
        # Strip YAML frontmatter so RAGAS sees clean markdown content
        content = re.sub(r"^---\n.*?\n---\n*", "", content, count=1, flags=re.DOTALL)
        content = content.strip()
        if len(content) < 100:
            continue
        # Truncate to ~4000 tokens (~16000 chars) to stay within embedding model limits (8192 tokens)
        # RAGAS generates summaries that can double the token count
        if len(content) > 16000:
            content = content[:16000]
        docs.append(
            Document(
                page_content=content,
                metadata={"source": str(md_file), "doc_id": md_file.stem},
            )
        )
    if len(docs) > max_docs:
        random.seed(42)
        docs = random.sample(docs, max_docs)
    logger.info("Loaded %d documents from %s (frontmatter stripped, random sample)", len(docs), corpus_dir)
    return docs


def load_config(config_path: Path | None = None) -> dict:
    if config_path is None:
        config_path = RAGAS_AGENTS_ROOT / "config" / "ragas_config.yaml"
    if not config_path.exists():
        return {}
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def generate_with_ragas(corpus_dir: Path, num_questions: int) -> list[dict] | None:
    """Generate questions using RAGAS TestsetGenerator with single-hop queries.

    Uses llm_factory() (modern RAGAS API) and SingleHopSpecificQuerySynthesizer only.
    Multi-hop synthesizers require keyphrases_overlap relationships which our
    CosineSimilarityBuilder doesn't produce — they fail silently and RAGAS returns
    np.nan, crashing the sample iteration loop (RAGAS 0.4.x bug).
    """
    if not RAGAS_AVAILABLE or not os.environ.get("OPENAI_API_KEY"):
        return None

    docs = load_docs_from_corpus_dir(corpus_dir)
    if not docs:
        logger.warning("No documents loaded from corpus dir")
        return None

    try:
        from openai import OpenAI
        from ragas.embeddings import OpenAIEmbeddings as RagasOpenAIEmbeddings
        from ragas.llms import llm_factory
        from ragas.testset import TestsetGenerator
        from ragas.testset.persona import Persona
        from ragas.testset.synthesizers.single_hop.specific import (
            SingleHopSpecificQuerySynthesizer,
        )
        from ragas.testset.transforms.extractors.llm_based import NERExtractor
        from ragas.testset.transforms.extractors import (
            EmbeddingExtractor,
            SummaryExtractor,
            KeyphrasesExtractor,
        )
        from ragas.testset.transforms.relationship_builders import (
            CosineSimilarityBuilder,
        )

        # Modern RAGAS API: llm_factory + OpenAIEmbeddings
        # (docs: https://docs.ragas.io/en/stable/howtos/llm-adapters/)
        openai_client = OpenAI()
        generator_llm = llm_factory(
            "gpt-4o-mini",
            client=openai_client,
        )
        generator_embeddings = RagasOpenAIEmbeddings(
            client=openai_client,
            model="text-embedding-3-small",
        )

        # Custom transforms: skip HeadlinesExtractor/HeadlineSplitter entirely
        # (docs: https://docs.ragas.io/en/stable/howtos/customizations/testgenerator/_testgen-custom-single-hop/)
        transforms = [
            NERExtractor(llm=generator_llm),
            SummaryExtractor(llm=generator_llm),
            KeyphrasesExtractor(llm=generator_llm),
            EmbeddingExtractor(embedding_model=generator_embeddings),
            CosineSimilarityBuilder(threshold=0.6),
        ]

        # German-adapted personas for LeoWiki context
        personas = [
            Persona(
                name="HTL Schueler",
                role_description="Ein Schueler der HTL Leonding, der Informationen zu Pruefungen, Unterricht und Schulorganisation sucht.",
            ),
            Persona(
                name="Lehrer",
                role_description="Ein Lehrer der HTL Leonding, der Informationen zu Abteilungen, Raeumen und organisatorischen Ablaeufen sucht.",
            ),
            Persona(
                name="Elternteil",
                role_description="Ein Elternteil, der allgemeine Informationen ueber die Schule, Termine und Kontaktdaten sucht.",
            ),
        ]

        generator = TestsetGenerator(
            llm=generator_llm,
            embedding_model=generator_embeddings,
            persona_list=personas,
            llm_context=GERMAN_LLM_CONTEXT,
        )

        # Single-hop only — multi-hop requires keyphrases_overlap relationships
        # which CosineSimilarityBuilder doesn't produce, causing RAGAS to crash
        # with 'float' object is not iterable (np.nan from failed Executor jobs).
        distribution = [
            (SingleHopSpecificQuerySynthesizer(llm=generator_llm, llm_context=GERMAN_LLM_CONTEXT), 1.0),
        ]

        logger.info("Generating %d questions with RAGAS (single-hop, German context)...", num_questions)

        testset = generator.generate_with_langchain_docs(
            docs,
            testset_size=min(num_questions, 30),
            transforms=transforms,
            query_distribution=distribution,
            raise_exceptions=True,
            with_debugging_logs=True,
        )

        # Convert RAGAS testset to our format
        questions: list[dict] = []
        samples = getattr(testset, "samples", None)
        if samples:
            for i, sample in enumerate(samples, start=1):
                user_input = getattr(sample, "user_input", None) or ""
                reference = getattr(sample, "reference", None) or ""
                ref_contexts = getattr(sample, "reference_contexts", None) or []
                synth_name = getattr(sample, "synthesizer_name", "unknown")

                questions.append({
                    "question_id": f"ragas_{i}",
                    "question_text": user_input,
                    "ground_truth": reference,
                    "query_type": "single_hop",
                    "reference_contexts": list(ref_contexts)[:3],
                    "synthesizer": synth_name,
                })

        # Fallback: try to_pandas if samples didn't work
        if not questions:
            to_pandas_fn = getattr(testset, "to_pandas", None)
            if callable(to_pandas_fn):
                df = to_pandas_fn()
                if df is not None and hasattr(df, "iterrows"):
                    for i, (_, row) in enumerate(df.iterrows(), start=1):
                        questions.append({
                            "question_id": f"ragas_{i}",
                            "question_text": str(row.get("user_input", row.get("question", ""))),
                            "ground_truth": str(row.get("reference", row.get("ground_truth", ""))),
                            "query_type": "single_hop",
                            "reference_contexts": [],
                            "synthesizer": "unknown",
                        })

        logger.info("RAGAS generated %d questions", len(questions))
        return questions if questions else None

    except Exception as e:
        logger.warning("RAGAS TestsetGenerator failed: %s", e, exc_info=True)
        return None


def generate_questions_template(corpus_dir: Path, num_questions: int) -> list[dict]:
    """Generate placeholder questions from corpus dir (no LLM). Last resort fallback."""
    questions = []
    templates = [
        "Was steht in diesem Dokument ueber {topic}?",
        "Welche Informationen enthaelt das Dokument zu {topic}?",
        "Beschreibe die wichtigsten Punkte zu {topic}.",
    ]
    md_files = sorted(corpus_dir.glob("**/*.md"))[:num_questions]
    for i, md_file in enumerate(md_files):
        if i >= num_questions:
            break
        q = {
            "question_id": f"tmpl_{i+1}",
            "question_text": templates[i % len(templates)].format(topic=md_file.stem),
            "ground_truth": "",
            "query_type": "single_hop",
            "reference_contexts": [],
            "synthesizer": "template",
        }
        questions.append(q)
    return questions


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate test questions from corpus")
    parser.add_argument("--corpus-dir", type=Path, required=True, help="Path to preprocessed pages directory")
    parser.add_argument("--num-questions", type=int, default=30, help="Number of questions to generate")
    parser.add_argument("--output", "-o", type=Path, default=None, help="Output questions.json path")
    parser.add_argument("--config", type=Path, default=None, help="Path to ragas_config.yaml")
    parser.add_argument("--no-ragas", action="store_true", help="Force template (skip RAGAS TestsetGenerator)")
    parser.add_argument("--manifest", type=Path, default=None, help="(deprecated) Path to test_corpus_manifest.json")
    args = parser.parse_args()

    config = load_config(args.config)
    q_config = config.get("questions", {})
    num_questions = args.num_questions or q_config.get("num_questions", 30)

    corpus_dir = args.corpus_dir.resolve()
    if not corpus_dir.is_dir():
        logger.error("Corpus dir not found: %s", corpus_dir)
        return 1

    questions = None
    if not args.no_ragas and RAGAS_AVAILABLE and os.environ.get("OPENAI_API_KEY"):
        questions = generate_with_ragas(corpus_dir, num_questions)

    if questions is None:
        questions = generate_questions_template(corpus_dir, num_questions)
        logger.warning("Fell back to template-based generation (RAGAS failed or unavailable)")

    out = {
        "generator": "ragas" if questions and questions[0].get("synthesizer") != "template" else "template",
        "corpus_dir": str(corpus_dir),
        "num_questions": len(questions),
        "questions": questions,
    }

    out_path = args.output
    if out_path is None:
        out_dir = REPO_ROOT / "evaluation" / "ragas_agents" / "output" / "ground_truth"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "questions_ragas.json"
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    logger.info("Wrote %d questions to %s", len(questions), out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
