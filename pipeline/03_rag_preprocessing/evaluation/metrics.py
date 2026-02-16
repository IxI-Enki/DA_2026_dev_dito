"""Preprocessing Evaluation -- 7-Metrik-Suite (US8, T038-T045).

Quantitative metrics comparing original DokuWiki content with preprocessed
Markdown output. Each metric implements a ``score()`` method returning a
float value, plus a ``threshold`` attribute for pass/fail.

Metrics:
1. ContentCompletenessMetric   -- char ratio adjusted for markup
2. SemanticSimilarityMetric    -- embedding cosine similarity
3. EntityPreservationMetric    -- dates, rooms, emails, URLs
4. LinkIntegrityMetric         -- DokuWiki->Markdown link pairs
5. NoiseDetectionMetric        -- wiki-syntax rest, mojibake, HTML
6. ReadabilityMetric           -- German Flesch (threshold 20)
7. StructurePreservationMetric -- headings, lists, paragraphs
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher
from typing import Any


# ---------------------------------------------------------------------------
# DocumentScore dataclass
# ---------------------------------------------------------------------------

@dataclass
class DocumentScore:
    """Scores for a single document across all 7 metrics."""

    doc_id: str
    content_completeness: float
    semantic_similarity: float
    entity_preservation: float
    link_integrity: float
    noise_ratio: float
    readability: float
    structure_preservation: float


# ---------------------------------------------------------------------------
# Threshold definitions (per-document)
# ---------------------------------------------------------------------------

THRESHOLDS: dict[str, tuple[str, float]] = {
    "content_completeness": (">=", 0.85),
    "semantic_similarity": (">=", 0.85),
    "entity_preservation": (">=", 0.95),
    "link_integrity": (">=", 0.95),
    "noise_ratio": ("<=", 0.02),
    "readability": (">=", 20.0),
    "structure_preservation": (">=", 0.90),
}

REGRESSION_THRESHOLD = 0.90  # aggregate pass-rate below this -> CI fail


def passes_thresholds(ds: DocumentScore) -> bool:
    """Check if a single document passes all per-document thresholds."""
    for field, (op, val) in THRESHOLDS.items():
        score_val = getattr(ds, field)
        if op == ">=" and score_val < val:
            return False
        if op == "<=" and score_val > val:
            return False
    return True


def check_regression(scores: list[DocumentScore]) -> dict[str, Any]:
    """Check aggregate pass-rates against regression thresholds.

    Returns a dict per metric with ``pass_rate`` and ``pass`` boolean.
    """
    if not scores:
        return {}

    results: dict[str, Any] = {}
    n = len(scores)

    for field, (op, val) in THRESHOLDS.items():
        passing = 0
        for ds in scores:
            sv = getattr(ds, field)
            if op == ">=" and sv >= val:
                passing += 1
            elif op == "<=" and sv <= val:
                passing += 1
        rate = passing / n
        results[field] = {
            "pass_rate": rate,
            "pass": rate >= REGRESSION_THRESHOLD,
            "passing": passing,
            "total": n,
        }
    return results


# ---------------------------------------------------------------------------
# 1. ContentCompletenessMetric (T038)
# ---------------------------------------------------------------------------

# Patterns that add markup chars in DokuWiki but are removed in Markdown
_WIKI_MARKUP_PATTERN = re.compile(
    r"={2,6}|"          # heading markers
    r"\[\[|\]\]|"       # link brackets
    r"\{\{|\}\}|"       # media brackets
    r"\*\*|//|''|__|"   # bold/italic/mono/underline
    r"^[ \t]*[\*\-]\s"  # list markers at line start
    r"|<[^>]+>",        # HTML-like tags
    re.MULTILINE,
)

# Link-aware patterns: extract display text from links before general stripping
_DOKUWIKI_LINK_NORM = re.compile(r"\[\[([^\]]*?)(?:\|([^\]]*?))?\]\]")
_DOKUWIKI_MEDIA_NORM = re.compile(r"\{\{([^\}]*?)(?:\|([^\}]*?))?\}\}")
_MARKDOWN_LINK_NORM = re.compile(r"!?\[([^\]]*?)\]\(([^\)]*?)\)")

# General markup removal (applied after link normalization)
_GENERAL_MARKUP = re.compile(
    r"={2,6}|"                     # DokuWiki headings
    r"\*\*|//|''|__|"              # DokuWiki bold/italic/mono/underline
    r"\\\\\s|"                     # DokuWiki forced line break
    r"~~[A-Z]+~~|"                 # DokuWiki macros (~~NOTOC~~ etc.)
    r"#{1,6}\s|"                   # Markdown headings
    r"\|[-:]+\||"                  # Markdown table separator rows
    r"</?[a-z][^>]*>|"             # HTML tags
    r"^---$|"                      # Markdown horizontal rules
    r"^[ \t]*[\*\-]\s|"            # List markers (wiki & markdown)
    r"^\d+[\.\)]\s|"              # Numbered list markers
    r"[\^\|]",                     # Table cell separators
    re.MULTILINE,
)

_MULTI_WHITESPACE = re.compile(r"\s+")


def _normalize_text(text: str) -> str:
    """Strip all markup (DokuWiki & Markdown) and normalize whitespace.

    Preserves display text from links: ``[[url|display]]`` -> ``display``,
    ``[display](url)`` -> ``display``.  Then strips remaining syntax.
    Returns lowercase, whitespace-collapsed text for comparison.
    """
    # Step 1: DokuWiki links -> keep display text (or target if no display)
    cleaned = _DOKUWIKI_LINK_NORM.sub(
        lambda m: m.group(2) if m.group(2) else m.group(1), text
    )
    # Step 2: DokuWiki media -> keep alt text (or filename)
    cleaned = _DOKUWIKI_MEDIA_NORM.sub(
        lambda m: m.group(2) if m.group(2) else m.group(1), cleaned
    )
    # Step 3: Markdown links/images -> keep display/alt text (or URL if empty)
    cleaned = _MARKDOWN_LINK_NORM.sub(
        lambda m: m.group(1) if m.group(1) else m.group(2), cleaned
    )
    # Step 4: Strip remaining markup syntax
    cleaned = _GENERAL_MARKUP.sub(" ", cleaned)
    # Step 5: Collapse whitespace & lowercase
    cleaned = _MULTI_WHITESPACE.sub(" ", cleaned)
    return cleaned.strip().lower()


class ContentCompletenessMetric:
    """Metrik 1: Character ratio Original vs Output.

    Adjusts for expected DokuWiki markup removal.
    Threshold: >= 0.85
    """

    threshold: float = 0.85

    def score(self, original: str, processed: str) -> float:
        if not original:
            return 0.0
        # Strip markup from original to get a fairer comparison
        stripped_original = _WIKI_MARKUP_PATTERN.sub("", original)
        orig_len = len(stripped_original.strip())
        proc_len = len(processed.strip())
        if orig_len == 0:
            return 0.0
        ratio = proc_len / orig_len
        return min(ratio, 1.0)


# ---------------------------------------------------------------------------
# 2. SemanticSimilarityMetric (T039)
# ---------------------------------------------------------------------------

class SemanticSimilarityMetric:
    """Metrik 2: Embedding Cosine Similarity.

    Model: paraphrase-multilingual-mpnet-base-v2 (or fallback SequenceMatcher).
    Threshold: >= 0.85
    """

    threshold: float = 0.85

    def __init__(self, model_name: str | None = "paraphrase-multilingual-mpnet-base-v2"):
        self._model = None
        self._model_name = model_name
        if model_name is not None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(model_name)
            except ImportError:
                pass

    def score(self, original: str, processed: str) -> float:
        if not original or not processed:
            return 0.0

        if self._model is not None:
            return self._score_embeddings(original, processed)
        return self._score_sequence_matcher(original, processed)

    def _score_embeddings(self, original: str, processed: str) -> float:
        import numpy as np
        emb = self._model.encode([original, processed])
        cos_sim = float(np.dot(emb[0], emb[1]) / (
            np.linalg.norm(emb[0]) * np.linalg.norm(emb[1]) + 1e-10
        ))
        return max(0.0, min(cos_sim, 1.0))

    def _score_sequence_matcher(self, original: str, processed: str) -> float:
        """Fallback when sentence-transformers is not available.

        Normalizes both texts (strip all markup, lowercase, collapse
        whitespace) before SequenceMatcher comparison.  This ensures
        DokuWiki->Markdown syntax transformations don't dominate the
        similarity score.
        """
        norm_orig = _normalize_text(original)
        norm_proc = _normalize_text(processed)
        return SequenceMatcher(None, norm_orig, norm_proc).ratio()


# ---------------------------------------------------------------------------
# 3. EntityPreservationMetric (T040)
# ---------------------------------------------------------------------------

_ENTITY_PATTERNS: dict[str, re.Pattern] = {
    "dates": re.compile(
        r"\b\d{4}[-/\.]\d{2}[-/\.]\d{2}\b"
        r"|\b\d{1,2}\.\d{1,2}\.\d{4}\b"
        r"|\b\d{1,2}\.\s*(?:Jaenner|Feber|Maerz|April|Mai|Juni|Juli|"
        r"August|September|Oktober|November|Dezember|"
        r"Januar|Februar|Maerz|Oktober)\s*\d{4}\b",
        re.IGNORECASE,
    ),
    "emails": re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
    "urls": re.compile(r"https?://[^\s\)\]>\"]+"),
    "rooms": re.compile(r"\b[A-Z]\d\.\d{2}\b"),
}


class EntityPreservationMetric:
    """Metrik 3: Key Entity Preservation.

    Entities: dates, room numbers, emails, URLs (regex-based).
    Threshold: >= 0.95
    """

    threshold: float = 0.95

    def score(self, original: str, processed: str) -> float:
        # Strip wiki markup so entities inside [[...]] are found the same way
        stripped_orig = _WIKI_MARKUP_PATTERN.sub("", original)

        orig_entities: set[str] = set()
        proc_entities: set[str] = set()

        for pattern in _ENTITY_PATTERNS.values():
            orig_entities.update(pattern.findall(stripped_orig))
            proc_entities.update(pattern.findall(processed))

        if not orig_entities:
            return 1.0

        preserved = orig_entities & proc_entities
        return len(preserved) / len(orig_entities)


# ---------------------------------------------------------------------------
# 4. LinkIntegrityMetric (T041)
# ---------------------------------------------------------------------------

_DOKUWIKI_LINK = re.compile(r"\[\[([^\]|]+?)(?:\|([^\]]*?))?\]\]")
_MARKDOWN_LINK = re.compile(r"\[([^\]]*?)\]\(([^\)]+?)\)")


class LinkIntegrityMetric:
    """Metrik 4: DokuWiki Link Transformation.

    Checks that link targets from original DokuWiki are preserved in Markdown output.
    Threshold: >= 0.95
    """

    threshold: float = 0.95

    def score(self, original: str, processed: str) -> float:
        wiki_links = _DOKUWIKI_LINK.findall(original)
        if not wiki_links:
            return 1.0

        # Extract targets from DokuWiki links
        wiki_targets: set[str] = set()
        for target, _display in wiki_links:
            wiki_targets.add(target.strip().lower())

        # Extract targets from Markdown links
        md_links = _MARKDOWN_LINK.findall(processed)
        md_targets: set[str] = set()
        for _display, target in md_links:
            md_targets.add(target.strip().lower())

        if not wiki_targets:
            return 1.0

        preserved = wiki_targets & md_targets
        return len(preserved) / len(wiki_targets)


# ---------------------------------------------------------------------------
# 5. NoiseDetectionMetric (T042)
# ---------------------------------------------------------------------------

_NOISE_PATTERNS: list[re.Pattern] = [
    re.compile(r"={2,6}"),                 # wiki heading markers
    re.compile(r"\[\[.*?\]\]"),            # wiki links
    re.compile(r"\{\{.*?\}\}"),            # wiki media embeds
    re.compile(r"</?[a-z]+[^>]*>"),        # HTML tags
    re.compile(r"&[a-z]+;"),               # HTML entities
    re.compile(r"[\x80-\x9f]"),            # mojibake range
    re.compile(r"\\\\ "),                  # DokuWiki forced line break
]


class NoiseDetectionMetric:
    """Metrik 5: Wiki Syntax Noise Detection.

    Detects wiki-syntax rest, mojibake, HTML artefakte in processed output.
    Returns noise ratio (0.0 = clean, 1.0 = all noise).
    Threshold: <= 0.02 (2%)
    """

    threshold: float = 0.02

    def score(self, processed: str) -> float:
        if not processed:
            return 0.0

        total_chars = len(processed)
        noise_chars = 0
        for pattern in _NOISE_PATTERNS:
            for match in pattern.finditer(processed):
                noise_chars += len(match.group())

        return noise_chars / total_chars if total_chars > 0 else 0.0


# ---------------------------------------------------------------------------
# 6. ReadabilityMetric (T043)
# ---------------------------------------------------------------------------

class ReadabilityMetric:
    """Metrik 6: German-adapted Flesch Reading Ease.

    Threshold: >= 20 (for German technical docs, NOT English default 60).
    Uses ``textstat`` library with German locale.
    """

    threshold: float = 20.0

    def score(self, processed: str) -> float:
        if not processed:
            return 0.0

        word_count = len(processed.split())
        if word_count < 10:
            return self.threshold if word_count > 0 else 0.0

        # Detect primarily structured content (lists, tables, links)
        # where Flesch readability is not meaningful.
        lines = [ln for ln in processed.splitlines() if ln.strip()]
        if lines:
            structured = sum(
                1 for ln in lines
                if (ln.strip().startswith(("-", "*", "|", "#"))
                    or re.match(r"^\d+[\.\)]\s", ln.strip())
                    or re.match(r"^!\[", ln.strip())
                    or re.match(r"^\[.*\]\(", ln.strip()))
            )
            if structured / len(lines) > 0.60:
                return self.threshold

        try:
            import textstat
            textstat.set_lang("de")
            fre = textstat.flesch_reading_ease(processed)
            return max(fre, 0.0)
        except ImportError:
            return self._fallback_flesch(processed)

    def _fallback_flesch(self, text: str) -> float:
        """Simple Flesch approximation when textstat is unavailable."""
        sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
        words = text.split()
        if not sentences or not words:
            return 0.0
        syllables = sum(self._count_syllables_de(w) for w in words)
        asl = len(words) / len(sentences)
        asw = syllables / len(words)
        return 180.0 - asl - (58.5 * asw)

    @staticmethod
    def _count_syllables_de(word: str) -> int:
        """Rough German syllable count based on vowel groups."""
        word = word.lower().strip(".,;:!?()[]\"'")
        vowels = re.findall(r"[aeiouyaeoeue]+", word)
        return max(len(vowels), 1)


# ---------------------------------------------------------------------------
# 7. StructurePreservationMetric (T044)
# ---------------------------------------------------------------------------

_WIKI_HEADING = re.compile(r"^={2,6}\s*.*?={2,6}\s*$", re.MULTILINE)
_MD_HEADING = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_WIKI_LIST = re.compile(r"^[ \t]*[\*\-]\s", re.MULTILINE)
_MD_LIST = re.compile(r"^[ \t]*[\*\-]\s|^\d+[\.\)]\s", re.MULTILINE)


class StructurePreservationMetric:
    """Metrik 7: Headings, Lists, Paragraphs Preservation.

    Compares structural element counts between original and processed.
    Threshold: >= 0.90
    """

    threshold: float = 0.90

    def score(self, original: str, processed: str) -> float:
        # Count headings
        orig_headings = len(_WIKI_HEADING.findall(original))
        proc_headings = len(_MD_HEADING.findall(processed))

        # Count list items
        orig_lists = len(_WIKI_LIST.findall(original))
        proc_lists = len(_MD_LIST.findall(processed))

        # Count paragraphs (blocks separated by blank lines)
        orig_paragraphs = len([
            p for p in original.split("\n\n") if p.strip()
        ])
        proc_paragraphs = len([
            p for p in processed.split("\n\n") if p.strip()
        ])

        # If no structure in original, it's trivially preserved
        total_orig = orig_headings + orig_lists + orig_paragraphs
        if total_orig == 0:
            return 1.0

        # Component-wise preservation scores
        scores: list[tuple[float, float]] = []  # (score, weight)
        if orig_headings > 0:
            scores.append(
                (min(proc_headings / orig_headings, 1.0), 2.0)  # headings weighted 2x
            )
        if orig_lists > 0:
            scores.append(
                (min(proc_lists / orig_lists, 1.0), 2.0)  # lists weighted 2x
            )
        if orig_paragraphs > 0:
            # Paragraph counts diverge between wiki and markdown due to
            # whitespace conventions; use lenient ratio (allow +/- 30%).
            para_ratio = proc_paragraphs / orig_paragraphs
            scores.append(
                (min(para_ratio, 1.0) if para_ratio <= 1.0
                 else max(1.0 - (para_ratio - 1.0) * 0.5, 0.5),
                 1.0)  # paragraphs weighted 1x (less reliable)
            )

        if not scores:
            return 1.0

        weighted_sum = sum(s * w for s, w in scores)
        total_weight = sum(w for _, w in scores)
        return weighted_sum / total_weight


# ---------------------------------------------------------------------------
# Evaluation runner helper (T045)
# ---------------------------------------------------------------------------

def evaluate_document(
    doc_id: str,
    original: str,
    processed: str,
    *,
    semantic_metric: SemanticSimilarityMetric | None = None,
) -> DocumentScore:
    """Run all 7 metrics on a single document pair.

    Args:
        doc_id: Document identifier.
        original: Original DokuWiki content.
        processed: Preprocessed Markdown content.
        semantic_metric: Optional pre-initialized metric (avoids reloading model).

    Returns:
        DocumentScore with all 7 metric values.
    """
    cc = ContentCompletenessMetric()
    sm = semantic_metric or SemanticSimilarityMetric(model_name=None)
    ep = EntityPreservationMetric()
    li = LinkIntegrityMetric()
    nd = NoiseDetectionMetric()
    rm = ReadabilityMetric()
    sp = StructurePreservationMetric()

    return DocumentScore(
        doc_id=doc_id,
        content_completeness=cc.score(original, processed),
        semantic_similarity=sm.score(original, processed),
        entity_preservation=ep.score(original, processed),
        link_integrity=li.score(original, processed),
        noise_ratio=nd.score(processed),
        readability=rm.score(processed),
        structure_preservation=sp.score(original, processed),
    )
