"""Generate a ground-truth JSON from evaluation/test_corpus for retrieval metrics.

Reads preprocessed .md files from test_corpus, extracts page_id from YAML frontmatter
(or derives from filename), and produces one Q&A pair per document. Output format
matches leowiki_qa_50_verified.json so the eval pipeline and all metrics (MRR, NDCG@10,
P@5, Recall@10, MAP, Hit Rate) work without RAGAS.

With --llm: questions are generated from two perspectives:
  - Teacher perspective: documents in namespace "teacher" (internal teacher-only content).
  - Student perspective: documents NOT in teacher namespace (student-accessible content).
Each qa_pair includes "perspective": "teacher" | "student".

Use this ground truth with:
  - evaluation/scripts/eval_pipeline.py (--skip ragas)
  - evaluation/experiments/*.yaml (set ground_truth.file to the output JSON)
  - Embedding model comparison (FF3, J2), chunk size (J4), hybrid vs dense (J6).

Usage::
  python -m evaluation.scripts.generate_ground_truth_from_test_corpus
  python -m evaluation.scripts.generate_ground_truth_from_test_corpus --max-questions 50
  python -m evaluation.scripts.generate_ground_truth_from_test_corpus --llm
  python -m evaluation.scripts.generate_ground_truth_from_test_corpus --llm --llm-provider ollama --llm-model llama3.2
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
EVAL_ROOT = SCRIPT_DIR.parent
REPO_ROOT = EVAL_ROOT.parent

DEFAULT_CORPUS = EVAL_ROOT / "test_corpus"
DEFAULT_OUTPUT = EVAL_ROOT / "ground_truth" / "test_corpus_qa.json"
DEFAULT_MAX_QUESTIONS = 0  # 0 = use all docs
EXCERPT_CHARS = 600  # chars of body for template question / optional ground_truth
EXCERPT_CHARS_LLM = 1200  # chars sent to LLM for question generation
LLM_DELAY_SEC = 0.15  # delay between LLM calls to avoid rate limits

# First line of page_id or namespace "teacher" (and teacher:*) = teacher-only content
TEACHER_NAMESPACE_PREFIX = "teacher"

LLM_PROMPT_TEACHER = """Du bist eine Lehrperson an der HTL Leonding. Der folgende Text stammt aus einem internen Wiki-Dokument aus dem Lehrer-Bereich (Namespace "teacher").

Aufgabe: Formuliere genau EINE kurze deutsche Suchanfrage, die eine Lehrperson eingeben wuerde, um genau DIESE Information im Wiki zu finden. Die Frage muss durch den gegebenen Text direkt beantwortbar sein. Sie muss ein vollstaendiger Fragesatz sein (endet mit ?). Keine Stichwoerter, keine Erklaerung, keine Anführungszeichen.

Beispiele fuer Lehrer-Fragen: "Wie melde ich mich vom Seminar ab?", "Wo finde ich das Formular fuer die Aufstiegsklausel?", "Wann ist Abgabefrist fuer die Diplomarbeit?"

Text:
"""

LLM_PROMPT_STUDENT = """Du bist eine Schuelerin oder ein Schueler an der HTL Leonding. Der folgende Text stammt aus einem Wiki-Dokument, das fuer Schueler zugaenglich ist (NICHT aus dem Lehrer-Namespace).

Aufgabe: Formuliere genau EINE kurze deutsche Suchanfrage, die eine Schuelerin oder ein Schueler eingeben wuerde, um genau DIESE Information im Wiki zu finden. Die Frage muss durch den gegebenen Text direkt beantwortbar sein. Sie muss ein vollstaendiger Fragesatz sein (endet mit ?). Keine Stichwoerter, keine Erklaerung, keine Anführungszeichen.

Beispiele fuer Schueler-Fragen: "Wann ist Schulbeginn?", "Wo finde ich die Termine fuer das Schuljahr?", "Wie richte ich meine Studenten-Mail ein?"

Text:
"""


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Split YAML frontmatter and body. Returns (frontmatter_dict, body)."""
    if not content.strip().startswith("---"):
        return {}, content
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        return {}, content
    fm_str, body = match.group(1), match.group(2)
    try:
        fm = yaml.safe_load(fm_str) or {}
    except Exception:
        fm = {}
    return fm, body


def _page_id_from_filename(basename: str) -> str:
    """Derive page_id from preprocessed filename (e.g. org_termine-2026.md -> org:termine-2026)."""
    stem = basename.removesuffix(".md")
    return stem.replace("_", ":")


def _title_from_body(body: str) -> str:
    """Extract first # heading as title, or first line, or placeholder."""
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
        if line and not line.startswith("|") and not line.startswith("-"):
            return line[:80].strip() if len(line) > 80 else line
    return "Dokument"


def _excerpt(body: str, max_chars: int = EXCERPT_CHARS) -> str:
    """First max_chars of body, one line if possible."""
    body = body.strip()
    if len(body) <= max_chars:
        return body
    truncated = body[:max_chars].rsplit("\n", 1)[0] if "\n" in body[:max_chars] else body[:max_chars]
    return truncated.rstrip() + " ..."


def _template_question(title: str, basename: str) -> str:
    """Generate a short German question from title/filename (no LLM). Fallback only."""
    if title and title != "Dokument":
        return "Welche Informationen enthaelt die Seite zu: " + title + "?"
    stem = basename.removesuffix(".md").replace("_", " ").replace("-", " ")
    return "Welche Informationen enthaelt das Dokument zu " + stem + "?"


def _excerpt_for_llm(body: str, max_chars: int = EXCERPT_CHARS_LLM) -> str:
    """Excerpt for LLM: skip tables/markup-heavy start, take first meaningful chunk."""
    body = body.strip()
    lines = body.splitlines()
    chunk: list[str] = []
    n = 0
    for line in lines:
        if n >= max_chars:
            break
        stripped = line.strip()
        if stripped.startswith("|") and "|" in stripped:
            continue
        if stripped.startswith("<!--"):
            continue
        chunk.append(line)
        n += len(line) + 1
    text = "\n".join(chunk)
    if len(text) > max_chars:
        text = text[:max_chars].rsplit("\n", 1)[0] + " ..."
    return text or body[:max_chars]


def _namespace_from_doc(fm: dict, page_id: str) -> str:
    """Return top-level namespace (e.g. teacher, org, class). Used for perspective."""
    ns = fm.get("namespace")
    if ns and isinstance(ns, str):
        return ns.split(":")[0].strip().lower()
    if page_id and ":" in page_id:
        return page_id.split(":")[0].strip().lower()
    return ""


def _is_teacher_namespace(namespace: str) -> bool:
    """True if document is in teacher-only namespace (teachers have access, students do not)."""
    return namespace.startswith(TEACHER_NAMESPACE_PREFIX) if namespace else False


def _normalize_llm_question(raw: str) -> str | None:
    """Ensure output is a single question: ends with ?, one line, no quotes. Returns None if invalid."""
    raw = (raw or "").strip().strip('"\'').strip()
    if "\n" in raw:
        raw = raw.split("\n")[0].strip()
    if not raw or len(raw) < 10:
        return None
    if not raw.endswith("?"):
        raw = raw + "?"
    return raw if 10 <= len(raw) <= 200 else None


def _generate_question_with_llm(
    excerpt: str,
    perspective: str,
    provider: str,
    model: str,
    base_url: str | None,
) -> str | None:
    """Call OpenAI or Ollama to generate one short German question (teacher or student perspective). Returns None on failure."""
    if not excerpt.strip():
        return None
    prompt = (LLM_PROMPT_TEACHER if perspective == "teacher" else LLM_PROMPT_STUDENT) + excerpt
    try:
        from openai import OpenAI

        if provider == "ollama":
            client = OpenAI(base_url=base_url or "http://localhost:11434/v1", api_key="ollama")
        else:
            if not os.environ.get("OPENAI_API_KEY"):
                logger.warning("OPENAI_API_KEY not set; cannot use OpenAI")
                return None
            client = OpenAI()
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=120,
        )
        choice = resp.choices[0] if resp.choices else None
        if not choice or not getattr(choice, "message", None):
            return None
        raw = (choice.message.content or "").strip()
        return _normalize_llm_question(raw)
    except Exception as e:
        logger.debug("LLM question generation failed: %s", e)
        return None


def build_qa_pairs(
    corpus_dir: Path,
    max_questions: int,
    seed: int,
    llm_kwargs: dict[str, Any] | None = None,
) -> list[dict]:
    """Build one Q&A pair per document: question, sources (page_id), ground_truth excerpt, etc."""
    import random

    md_files = sorted(corpus_dir.glob("*.md"))
    if not md_files:
        logger.warning("No .md files in %s", corpus_dir)
        return []

    if max_questions > 0 and len(md_files) > max_questions:
        rng = random.Random(seed)
        md_files = rng.sample(md_files, max_questions)

    qa_pairs: list[dict] = []
    for i, path in enumerate(md_files):
        content = path.read_text(encoding="utf-8", errors="replace")
        fm, body = _parse_frontmatter(content)
        page_id = fm.get("page_id") or fm.get("media_id") or _page_id_from_filename(path.name)
        title = fm.get("title") or _title_from_body(body)
        excerpt = _excerpt(body)
        namespace = _namespace_from_doc(fm, page_id)
        perspective = "teacher" if _is_teacher_namespace(namespace) else "student"

        question: str
        if llm_kwargs:
            excerpt_llm = _excerpt_for_llm(body)
            q = _generate_question_with_llm(
                excerpt_llm,
                perspective,
                llm_kwargs.get("provider", "openai"),
                llm_kwargs.get("model", "gpt-4o-mini"),
                llm_kwargs.get("base_url"),
            )
            if q:
                question = q
            else:
                question = _template_question(title, path.name)
                logger.debug("Fallback to template for %s (perspective=%s)", path.name, perspective)
            if i < len(md_files) - 1 and llm_kwargs:
                time.sleep(LLM_DELAY_SEC)
        else:
            question = _template_question(title, path.name)

        qa_pairs.append({
            "id": "tc-%03d" % (i + 1),
            "question": question,
            "ground_truth": excerpt,
            "sources": [page_id],
            "source_file": path.name,
            "perspective": perspective,
            "difficulty": "medium",
        })

    return qa_pairs


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate ground-truth JSON from evaluation/test_corpus for retrieval metrics"
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        default=DEFAULT_CORPUS,
        help="Directory containing preprocessed .md files (default: evaluation/test_corpus)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output JSON path (default: evaluation/ground_truth/test_corpus_qa.json)",
    )
    parser.add_argument(
        "--max-questions",
        type=int,
        default=DEFAULT_MAX_QUESTIONS,
        help="Max number of Q&A pairs (0 = use all docs)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20260217,
        help="Random seed when subsampling with --max-questions",
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Use LLM to generate realistic search-style questions (OpenAI or Ollama)",
    )
    parser.add_argument(
        "--llm-provider",
        choices=("openai", "ollama"),
        default=None,
        help="LLM provider: openai (needs OPENAI_API_KEY) or ollama (local). Default: openai if OPENAI_API_KEY set else ollama",
    )
    parser.add_argument(
        "--llm-model",
        type=str,
        default=None,
        help="Model name (e.g. gpt-4o-mini for OpenAI, llama3.2 for Ollama)",
    )
    parser.add_argument(
        "--llm-base-url",
        type=str,
        default=None,
        help="Ollama base URL (default: http://localhost:11434/v1)",
    )
    args = parser.parse_args()

    corpus_dir = Path(args.corpus).resolve()
    if not corpus_dir.is_dir():
        logger.error("Corpus directory not found: %s", corpus_dir)
        return 1

    llm_kwargs: dict[str, Any] | None = None
    if args.llm:
        provider = args.llm_provider
        if provider is None:
            provider = "openai" if os.environ.get("OPENAI_API_KEY") else "ollama"
        model = args.llm_model or ("gpt-4o-mini" if provider == "openai" else "llama3.2")
        llm_kwargs = {
            "provider": provider,
            "model": model,
            "base_url": args.llm_base_url or (None if provider == "openai" else "http://localhost:11434/v1"),
        }
        logger.info("Using LLM: provider=%s model=%s", provider, model)

    qa_pairs = build_qa_pairs(corpus_dir, args.max_questions, args.seed, llm_kwargs)
    if not qa_pairs:
        logger.error("No Q&A pairs generated")
        return 1

    out_path = Path(args.output).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    verification = (
        "LLM-generated questions from teacher vs student perspective (OpenAI/Ollama); sources from YAML frontmatter."
        if llm_kwargs
        else "Template from document title/filename; sources from YAML frontmatter page_id."
    )
    payload = {
        "metadata": {
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "version": "1.0",
            "description": "Ground-truth Q&A from evaluation/test_corpus for retrieval metrics (MRR, NDCG@10, P@5, Recall@10, MAP, Hit Rate). One question per document; sources = page_id from frontmatter.",
            "source": str(corpus_dir),
            "author": "generate_ground_truth_from_test_corpus.py",
            "verification_method": verification,
        },
        "qa_pairs": qa_pairs,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    logger.info("Wrote %d qa_pairs to %s", len(qa_pairs), out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
