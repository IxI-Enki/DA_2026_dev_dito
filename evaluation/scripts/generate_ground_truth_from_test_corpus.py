"""Generate ground-truth Q&A JSON from evaluation/test_corpus for retrieval metrics.

Reads preprocessed .md files, extracts page_id/media_id from YAML frontmatter,
and uses an LLM (via OpenAI-compatible API) to produce one high-quality Q&A pair
per document.  Output is compatible with eval_pipeline.py and
eval_keyword_baseline.py for computing MRR, NDCG@10, P@5, Recall@10, MAP,
Hit Rate.

The LLM receives document metadata (title, namespace, content_type) plus up to
6000 chars of body text INCLUDING tables, and returns structured JSON:
  {"frage": "...", "antwort": "...", "suchbegriffe": ["..."]}

Documents with <200 chars of body text are skipped (empty stubs).

Supports any OpenAI-compatible API: OpenAI, Ollama, LM Studio, etc.

Usage::
  # LM Studio (recommended -- load Qwen2.5-7B-Instruct first)
  python -m evaluation.scripts.generate_ground_truth_from_test_corpus \\
      --llm --llm-base-url http://localhost:1234/v1 --llm-model qwen2.5-7b-instruct

  # Ollama
  python -m evaluation.scripts.generate_ground_truth_from_test_corpus \\
      --llm --llm-base-url http://localhost:11434/v1 --llm-model llama3.2

  # OpenAI
  python -m evaluation.scripts.generate_ground_truth_from_test_corpus \\
      --llm --llm-model gpt-4o-mini

  # Template-only (no LLM, fallback)
  python -m evaluation.scripts.generate_ground_truth_from_test_corpus

  # Sample 50 from 70 usable docs
  python -m evaluation.scripts.generate_ground_truth_from_test_corpus \\
      --llm --max-questions 50 --llm-base-url http://localhost:1234/v1
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import UTC, datetime
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
DEFAULT_MAX_QUESTIONS = 0  # 0 = use all usable docs
LLM_CONTEXT_CHARS = 6000  # max chars of body sent to LLM (including tables!)
MIN_BODY_CHARS = 200  # skip documents shorter than this
LLM_DELAY_SEC = 0.3  # delay between LLM calls

TEACHER_NAMESPACE_PREFIX = "teacher"

# ---------------------------------------------------------------------------
# Prompt -- a single unified prompt with document context injected
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
Du bist ein Experte fuer Information Retrieval an einer oesterreichischen HTL \
(Hoehere Technische Lehranstalt). Deine Aufgabe ist es, aus einem Wiki-Dokument \
eine realistische deutsche Suchanfrage und eine kurze Antwort zu erzeugen.

REGELN:
1. Die Frage muss ein vollstaendiger deutscher Fragesatz sein (endet mit ?).
2. Die Frage muss durch den gegebenen Text DIREKT beantwortbar sein.
3. Die Antwort muss 1-3 Saetze lang sein und NUR Fakten aus dem Text verwenden.
4. Gib 3-5 deutsche Suchbegriffe an, die zum Auffinden dieses Dokuments nuetzlich waeren.
5. Antworte AUSSCHLIESSLICH mit einem JSON-Objekt, KEIN weiterer Text.

Antwortformat (exakt dieses JSON, nichts anderes):
{"frage": "...", "antwort": "...", "suchbegriffe": ["...", "...", "..."]}

SCHLECHTE Fragen (VERMEIDE diese):
- "Welche Informationen enthaelt die Seite zu ...?" (zu generisch)
- "Was steht in diesem Dokument?" (zu generisch)
- Fragen die nicht durch den Text beantwortbar sind

GUTE Fragen (SO sollen sie aussehen):
- "Wann beginnt das Schuljahr 2026/2027?"
- "Wie melde ich mich vom PH-Seminar ab?"
- "Welche Kleidungsvorschrift gilt bei der muendlichen Matura?"
- "Wo finde ich das Formular fuer Pflichtpraktikum?"
- "Was sind die Semesterkompetenzen in Kommunikation und Medientechnik im 3. Jahrgang?"\
"""


def _build_user_prompt(
    title: str,
    namespace: str,
    content_type: str,
    perspective: str,
    body_excerpt: str,
) -> str:
    """Build the user message with document context + body text."""
    role = (
        "eine Lehrperson (Lehrer-Namespace, nur fuer Lehrende zugaenglich)"
        if perspective == "teacher"
        else "eine Schuelerin / ein Schueler"
    )
    return (
        f"Dokument-Titel: {title}\n"
        f"Namespace: {namespace}\n"
        f"Inhaltstyp: {content_type}\n"
        f"Perspektive: Du bist {role} an der HTL Leonding und suchst "
        f"nach dieser Information im Schul-Wiki.\n"
        f"\n--- Dokumentinhalt ---\n{body_excerpt}\n--- Ende ---\n\n"
        f"Erzeuge jetzt das JSON-Objekt mit frage, antwort, suchbegriffe."
    )


# ---------------------------------------------------------------------------
# Frontmatter and text helpers
# ---------------------------------------------------------------------------


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


def _page_id_from_frontmatter(fm: dict, filename: str) -> str:
    """Get page_id or media_id from frontmatter; fall back to filename derivation."""
    pid = fm.get("page_id") or fm.get("media_id")
    if pid and isinstance(pid, str):
        return pid.strip()
    stem = filename.removesuffix(".md")
    return stem.replace("_", ":")


def _clean_body(body: str) -> str:
    """Strip HTML comments but keep everything else (including tables)."""
    return re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL).strip()


def _body_excerpt(body: str, max_chars: int = LLM_CONTEXT_CHARS) -> str:
    """First max_chars of body for the LLM. Includes tables, headings, everything."""
    body = _clean_body(body)
    if len(body) <= max_chars:
        return body
    truncated = body[:max_chars]
    last_nl = truncated.rfind("\n")
    if last_nl > max_chars * 0.7:
        truncated = truncated[:last_nl]
    return truncated.rstrip() + "\n[...]"


def _title_from_body(body: str) -> str:
    """Extract first # heading as title, or first non-table line, or placeholder."""
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
        if (
            line
            and not line.startswith("|")
            and not line.startswith("-")
            and not line.startswith("<!--")
        ):
            return line[:80].strip() if len(line) > 80 else line
    return "Dokument"


def _namespace_from_doc(fm: dict, page_id: str) -> str:
    """Return full namespace string (e.g. 'teacher:neulehrerinnenhandbuch')."""
    ns = fm.get("namespace")
    if ns and isinstance(ns, str):
        return ns.strip().lower()
    if page_id and ":" in page_id:
        parts = page_id.split(":")
        return ":".join(parts[:-1]).lower() if len(parts) > 1 else parts[0].lower()
    return ""


def _top_namespace(namespace: str) -> str:
    """Top-level namespace (before first colon)."""
    return namespace.split(":")[0] if namespace else ""


def _is_teacher_namespace(namespace: str) -> bool:
    """True if document is in teacher-only namespace."""
    return _top_namespace(namespace).startswith(TEACHER_NAMESPACE_PREFIX)


# ---------------------------------------------------------------------------
# LLM interaction
# ---------------------------------------------------------------------------


def _create_llm_client(base_url: str | None) -> Any:
    """Create an OpenAI client (works with OpenAI, Ollama, LM Studio)."""
    from openai import OpenAI

    if base_url:
        return OpenAI(base_url=base_url, api_key=os.environ.get("OPENAI_API_KEY", "lm-studio"))
    if not os.environ.get("OPENAI_API_KEY"):
        logger.error("No --llm-base-url and no OPENAI_API_KEY set.")
        return None
    return OpenAI()


def _call_llm(
    client: Any,
    model: str,
    system: str,
    user: str,
    temperature: float = 0.3,
    max_tokens: int = 400,
) -> str | None:
    """Send a chat completion request and return the raw response text."""
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choice = resp.choices[0] if resp.choices else None
        if not choice or not getattr(choice, "message", None):
            return None
        return (choice.message.content or "").strip()
    except Exception as e:
        logger.warning("LLM call failed: %s", e)
        return None


def _parse_llm_json(raw: str | None) -> dict | None:
    """Extract and parse JSON from LLM response (tolerant of markdown fences)."""
    if not raw:
        return None
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        json_lines = []
        inside = False
        for line in lines:
            if line.strip().startswith("```") and not inside:
                inside = True
                continue
            if line.strip().startswith("```") and inside:
                break
            if inside:
                json_lines.append(line)
        text = "\n".join(json_lines).strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and "frage" in obj:
            return obj
    except json.JSONDecodeError:
        pass
    # Try to find JSON object in the text
    match = re.search(r'\{[^{}]*"frage"[^{}]*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

GENERIC_PATTERNS = [
    "welche informationen enthaelt",
    "welche informationen enthält",
    "was steht in diesem dokument",
    "was steht auf dieser seite",
    "was beinhaltet",
]


def _validate_qa(frage: str, antwort: str, suchbegriffe: list, body: str) -> str | None:
    """Validate a generated Q&A pair. Returns error message or None if valid."""
    if not frage or not isinstance(frage, str):
        return "frage is empty or not a string"
    frage_clean = frage.strip().strip("\"'").strip()
    if len(frage_clean) < 15:
        return f"frage too short ({len(frage_clean)} chars)"
    if len(frage_clean) > 200:
        return f"frage too long ({len(frage_clean)} chars)"
    if not frage_clean.endswith("?"):
        return "frage does not end with ?"

    frage_lower = frage_clean.lower()
    for pat in GENERIC_PATTERNS:
        if pat in frage_lower:
            return f"frage matches generic pattern: {pat}"

    if not antwort or not isinstance(antwort, str) or len(antwort.strip()) < 10:
        return "antwort is empty or too short"

    body_lower = body.lower()
    antwort_words = set(w for w in re.findall(r"\b\w+\b", antwort.lower()) if len(w) > 4)
    overlap = sum(1 for w in antwort_words if w in body_lower)
    if overlap < 2 and len(antwort_words) >= 2:
        return f"antwort shares only {overlap} significant words with document"

    return None


def _template_question(title: str, namespace: str) -> str:
    """Last-resort template question (only used when LLM fails entirely)."""
    if title and title != "Dokument":
        return f"Was muss ich ueber {title} wissen?"
    return f"Was findet man im Wiki unter {namespace}?"


def _template_answer(body: str) -> str:
    """Short excerpt as answer fallback."""
    clean = _clean_body(body)
    lines = [l.strip() for l in clean.splitlines() if l.strip() and not l.strip().startswith("|")]
    text = " ".join(lines[:5])
    if len(text) > 300:
        text = text[:297] + "..."
    return text or clean[:200]


# ---------------------------------------------------------------------------
# Main Q&A builder
# ---------------------------------------------------------------------------


def build_qa_pairs(
    corpus_dir: Path,
    max_questions: int,
    seed: int,
    llm_kwargs: dict[str, Any] | None = None,
) -> list[dict]:
    """Build one Q&A pair per usable document.

    Skips documents with < MIN_BODY_CHARS of body text.
    With --llm: uses LLM for question+answer generation with structured JSON.
    Without --llm: uses template questions (low quality, fallback only).
    """
    import random

    md_files = sorted(corpus_dir.glob("*.md"))
    if not md_files:
        logger.warning("No .md files in %s", corpus_dir)
        return []

    # Parse all files and filter out stubs
    docs: list[dict] = []
    skipped = 0
    for path in md_files:
        content = path.read_text(encoding="utf-8", errors="replace")
        fm, body = _parse_frontmatter(content)
        clean = _clean_body(body)
        if len(clean) < MIN_BODY_CHARS:
            skipped += 1
            logger.debug("Skipped (too short: %d chars): %s", len(clean), path.name)
            continue
        page_id = _page_id_from_frontmatter(fm, path.name)
        namespace = _namespace_from_doc(fm, page_id)
        docs.append(
            {
                "path": path,
                "fm": fm,
                "body": body,
                "page_id": page_id,
                "namespace": namespace,
                "title": fm.get("title") or _title_from_body(body),
                "content_type": fm.get("content_type", "UNKNOWN"),
            }
        )

    if skipped:
        logger.info("Skipped %d documents with <%d chars body text", skipped, MIN_BODY_CHARS)
    logger.info("Usable documents: %d", len(docs))

    if max_questions > 0 and len(docs) > max_questions:
        rng = random.Random(seed)
        docs = rng.sample(docs, max_questions)
        logger.info("Sampled %d documents (seed=%d)", len(docs), seed)

    # Create LLM client once (reuse for all documents)
    client = None
    if llm_kwargs:
        client = _create_llm_client(llm_kwargs.get("base_url"))
        if not client:
            logger.error("Failed to create LLM client")
            return []

    qa_pairs: list[dict] = []
    llm_success = 0
    llm_fallback = 0

    for i, doc in enumerate(docs):
        perspective = "teacher" if _is_teacher_namespace(doc["namespace"]) else "student"
        path: Path = doc["path"]

        question: str
        answer: str
        keywords: list[str] = []
        difficulty = "medium"

        if client and llm_kwargs:
            excerpt = _body_excerpt(doc["body"])
            user_msg = _build_user_prompt(
                title=doc["title"],
                namespace=doc["namespace"],
                content_type=doc["content_type"],
                perspective=perspective,
                body_excerpt=excerpt,
            )
            raw = _call_llm(
                client,
                llm_kwargs["model"],
                SYSTEM_PROMPT,
                user_msg,
            )
            parsed = _parse_llm_json(raw)

            if parsed:
                frage = parsed.get("frage", "").strip().strip("\"'")
                antwort = parsed.get("antwort", "").strip()
                suchbegriffe = parsed.get("suchbegriffe", [])
                if not isinstance(suchbegriffe, list):
                    suchbegriffe = []

                err = _validate_qa(frage, antwort, suchbegriffe, doc["body"])
                if err is None:
                    question = frage if frage.endswith("?") else frage + "?"
                    answer = antwort
                    keywords = [str(s) for s in suchbegriffe[:5]]
                    llm_success += 1
                else:
                    logger.warning(
                        "[VALIDATION FAILED] %s: %s (raw frage: %s)",
                        path.name,
                        err,
                        frage[:60] if frage else "N/A",
                    )
                    question = _template_question(doc["title"], doc["namespace"])
                    answer = _template_answer(doc["body"])
                    llm_fallback += 1
            else:
                logger.warning(
                    "[PARSE FAILED] %s: could not parse LLM JSON (raw: %s)",
                    path.name,
                    (raw or "")[:80],
                )
                question = _template_question(doc["title"], doc["namespace"])
                answer = _template_answer(doc["body"])
                llm_fallback += 1

            if i < len(docs) - 1:
                time.sleep(LLM_DELAY_SEC)
        else:
            question = _template_question(doc["title"], doc["namespace"])
            answer = _template_answer(doc["body"])

        qa_pairs.append(
            {
                "id": f"tc-{i + 1:03d}",
                "question": question,
                "ground_truth": answer,
                "sources": [doc["page_id"]],
                "source_file": path.name,
                "perspective": perspective,
                "context_keywords": keywords,
                "difficulty": difficulty,
            }
        )

    if llm_kwargs:
        logger.info("LLM results: %d success, %d fallback to template", llm_success, llm_fallback)

    return qa_pairs


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate ground-truth Q&A JSON from test_corpus for retrieval metrics"
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
        help="Max Q&A pairs (0 = all usable docs). Randomly samples if corpus has more.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20260217,
        help="Random seed for sampling with --max-questions",
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Use LLM for question+answer generation (requires --llm-base-url or OPENAI_API_KEY)",
    )
    parser.add_argument(
        "--llm-model",
        type=str,
        default=None,
        help="Model name (e.g. qwen2.5-7b-instruct for LM Studio, gpt-4o-mini for OpenAI)",
    )
    parser.add_argument(
        "--llm-base-url",
        type=str,
        default=None,
        help="OpenAI-compatible API URL (e.g. http://localhost:1234/v1 for LM Studio)",
    )
    args = parser.parse_args()

    corpus_dir = Path(args.corpus).resolve()
    if not corpus_dir.is_dir():
        logger.error("Corpus directory not found: %s", corpus_dir)
        return 1

    llm_kwargs: dict[str, Any] | None = None
    if args.llm:
        model = args.llm_model
        if not model:
            if args.llm_base_url:
                model = "qwen2.5-7b-instruct"
            elif os.environ.get("OPENAI_API_KEY"):
                model = "gpt-4o-mini"
            else:
                logger.error("--llm requires either --llm-base-url or OPENAI_API_KEY")
                return 1
        llm_kwargs = {"model": model, "base_url": args.llm_base_url}
        logger.info("LLM: model=%s base_url=%s", model, args.llm_base_url or "OpenAI default")

    qa_pairs = build_qa_pairs(corpus_dir, args.max_questions, args.seed, llm_kwargs)
    if not qa_pairs:
        logger.error("No Q&A pairs generated")
        return 1

    out_path = Path(args.output).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    verification = (
        f"LLM-generated (model={llm_kwargs['model']}) with structured JSON prompt; "
        f"sources from YAML frontmatter page_id/media_id."
        if llm_kwargs
        else "Template from document title; sources from YAML frontmatter page_id/media_id."
    )
    payload = {
        "metadata": {
            "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "version": "2.0",
            "description": (
                "Ground-truth Q&A from evaluation/test_corpus for retrieval metrics "
                "(MRR, NDCG@10, P@5, Recall@10, MAP, Hit Rate). "
                "One Q&A per document; sources from YAML frontmatter."
            ),
            "source": str(corpus_dir),
            "author": "generate_ground_truth_from_test_corpus.py",
            "verification_method": verification,
            "total_pairs": len(qa_pairs),
        },
        "qa_pairs": qa_pairs,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    logger.info("Wrote %d qa_pairs to %s", len(qa_pairs), out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
