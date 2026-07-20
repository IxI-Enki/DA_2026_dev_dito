"""Tests for US8 -- Preprocessing Evaluation 7-Metrik-Suite (T037).

Covers:
1. ContentCompletenessMetric  -- char ratio adjusted for markup removal
2. SemanticSimilarityMetric   -- cosine similarity (mocked model)
3. EntityPreservationMetric   -- dates, emails, URLs, rooms preserved
4. LinkIntegrityMetric        -- DokuWiki->Markdown link pairs
5. NoiseDetectionMetric       -- wiki-syntax rest, mojibake, HTML
6. ReadabilityMetric          -- German threshold 20 (not English 60)
7. StructurePreservationMetric -- headings, lists, paragraphs
+ DocumentScore dataclass
+ Regression: completeness <0.90 -> fail
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_here = Path(__file__).resolve().parent.parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))


# ---------------------------------------------------------------------------
# 1. ContentCompletenessMetric
# ---------------------------------------------------------------------------
class TestContentCompletenessMetric:
    """Char ratio original vs processed, adjusted for markup removal."""

    def test_identical_text_returns_1(self):
        from evaluation.metrics import ContentCompletenessMetric

        m = ContentCompletenessMetric()
        assert m.score("hello world", "hello world") == pytest.approx(1.0, abs=0.05)

    def test_half_content_returns_low(self):
        from evaluation.metrics import ContentCompletenessMetric

        m = ContentCompletenessMetric()
        original = "a" * 200
        processed = "a" * 80
        s = m.score(original, processed)
        assert s < 0.85

    def test_markup_removed_still_passes(self):
        """DokuWiki markup removal reduces char count but should be adjusted."""
        from evaluation.metrics import ContentCompletenessMetric

        m = ContentCompletenessMetric()
        original = "====== Title ======\nSome **bold** text with [[link|display]]."
        processed = "# Title\nSome **bold** text with [display](link)."
        s = m.score(original, processed)
        assert s >= 0.70  # adjusted for markup

    def test_empty_original_returns_0(self):
        from evaluation.metrics import ContentCompletenessMetric

        m = ContentCompletenessMetric()
        assert m.score("", "anything") == 0.0

    def test_threshold_is_085(self):
        from evaluation.metrics import ContentCompletenessMetric

        m = ContentCompletenessMetric()
        assert m.threshold == pytest.approx(0.85)


# ---------------------------------------------------------------------------
# 2. SemanticSimilarityMetric
# ---------------------------------------------------------------------------
class TestSemanticSimilarityMetric:
    """Embedding cosine similarity."""

    def test_identical_texts_high_score(self):
        from evaluation.metrics import SemanticSimilarityMetric

        m = SemanticSimilarityMetric(model_name=None)
        s = m.score("identical text", "identical text")
        assert s >= 0.95

    def test_different_texts_lower_score(self):
        from evaluation.metrics import SemanticSimilarityMetric

        m = SemanticSimilarityMetric(model_name=None)
        s = m.score("The quick brown fox", "Apfelstrudel mit Sahne")
        assert s < 0.85

    def test_empty_text_returns_0(self):
        from evaluation.metrics import SemanticSimilarityMetric

        m = SemanticSimilarityMetric(model_name=None)
        assert m.score("", "text") == 0.0

    def test_threshold_is_085(self):
        from evaluation.metrics import SemanticSimilarityMetric

        m = SemanticSimilarityMetric(model_name=None)
        assert m.threshold == pytest.approx(0.85)


# ---------------------------------------------------------------------------
# 3. EntityPreservationMetric
# ---------------------------------------------------------------------------
class TestEntityPreservationMetric:
    """Regex-based extraction of dates, rooms, emails, URLs."""

    def test_all_entities_preserved(self):
        from evaluation.metrics import EntityPreservationMetric

        m = EntityPreservationMetric()
        text = "Meeting am 2026-01-15 in Raum A3.04, email: test@example.org, see https://htl.at"
        s = m.score(text, text)
        assert s == pytest.approx(1.0)

    def test_entity_lost_reduces_score(self):
        from evaluation.metrics import EntityPreservationMetric

        m = EntityPreservationMetric()
        original = "Meeting am 2026-01-15, email: test@example.org, URL: https://htl.at"
        processed = "Meeting am 2026-01-15, URL: https://htl.at"
        s = m.score(original, processed)
        assert s < 1.0
        assert s >= 0.5

    def test_no_entities_returns_1(self):
        """If no entities in original, nothing to lose."""
        from evaluation.metrics import EntityPreservationMetric

        m = EntityPreservationMetric()
        s = m.score("plain text no entities", "plain text no entities")
        assert s == pytest.approx(1.0)

    def test_threshold_is_095(self):
        from evaluation.metrics import EntityPreservationMetric

        m = EntityPreservationMetric()
        assert m.threshold == pytest.approx(0.95)


# ---------------------------------------------------------------------------
# 4. LinkIntegrityMetric
# ---------------------------------------------------------------------------
class TestLinkIntegrityMetric:
    """DokuWiki->Markdown link text + target preservation."""

    def test_links_preserved(self):
        from evaluation.metrics import LinkIntegrityMetric

        m = LinkIntegrityMetric()
        original = "Visit [[start|Startseite]] and [[news:2026|News]]"
        processed = "Visit [Startseite](start) and [News](news:2026)"
        s = m.score(original, processed)
        assert s >= 0.90

    def test_link_lost_reduces_score(self):
        from evaluation.metrics import LinkIntegrityMetric

        m = LinkIntegrityMetric()
        original = "Links: [[a|A]] [[b|B]] [[c|C]] [[d|D]]"
        processed = "Links: [A](a) [B](b)"
        s = m.score(original, processed)
        assert s < 1.0

    def test_no_links_returns_1(self):
        from evaluation.metrics import LinkIntegrityMetric

        m = LinkIntegrityMetric()
        assert m.score("no links here", "no links here") == pytest.approx(1.0)

    def test_threshold_is_095(self):
        from evaluation.metrics import LinkIntegrityMetric

        m = LinkIntegrityMetric()
        assert m.threshold == pytest.approx(0.95)


# ---------------------------------------------------------------------------
# 5. NoiseDetectionMetric
# ---------------------------------------------------------------------------
class TestNoiseDetectionMetric:
    """Detects wiki-syntax rest, mojibake, HTML artefakte."""

    def test_clean_text_low_noise(self):
        from evaluation.metrics import NoiseDetectionMetric

        m = NoiseDetectionMetric()
        s = m.score("This is clean Markdown text with no artifacts.")
        assert s <= 0.02

    def test_wiki_syntax_detected(self):
        from evaluation.metrics import NoiseDetectionMetric

        m = NoiseDetectionMetric()
        noisy = "Normal text ====== heading ====== with [[wiki:link]] and **bold** {{image.png}}"
        s = m.score(noisy)
        assert s > 0.02

    def test_html_artifacts_detected(self):
        from evaluation.metrics import NoiseDetectionMetric

        m = NoiseDetectionMetric()
        noisy = "Text with <div>html</div> and &amp; entities"
        s = m.score(noisy)
        assert s > 0.0

    def test_empty_text_returns_0(self):
        from evaluation.metrics import NoiseDetectionMetric

        m = NoiseDetectionMetric()
        assert m.score("") == 0.0

    def test_threshold_is_002(self):
        from evaluation.metrics import NoiseDetectionMetric

        m = NoiseDetectionMetric()
        assert m.threshold == pytest.approx(0.02)


# ---------------------------------------------------------------------------
# 6. ReadabilityMetric
# ---------------------------------------------------------------------------
class TestReadabilityMetric:
    """German-adapted Flesch Reading Ease, threshold 20."""

    def test_simple_text_readable(self):
        from evaluation.metrics import ReadabilityMetric

        m = ReadabilityMetric()
        text = (
            "Die Schule ist gross. "
            "Die Lehrer sind nett. "
            "Wir lernen viel. "
            "Das Essen schmeckt gut."
        )
        s = m.score(text)
        assert s >= 20

    def test_threshold_is_20_not_60(self):
        """German technical docs have lower readability than English threshold 60."""
        from evaluation.metrics import ReadabilityMetric

        m = ReadabilityMetric()
        assert m.threshold == pytest.approx(20.0)

    def test_empty_text_returns_0(self):
        from evaluation.metrics import ReadabilityMetric

        m = ReadabilityMetric()
        assert m.score("") == 0.0


# ---------------------------------------------------------------------------
# 7. StructurePreservationMetric
# ---------------------------------------------------------------------------
class TestStructurePreservationMetric:
    """Headings, lists, paragraphs preserved."""

    def test_structure_fully_preserved(self):
        from evaluation.metrics import StructurePreservationMetric

        m = StructurePreservationMetric()
        original = "====== H1 ======\nText\n  * item1\n  * item2\n\nParagraph two."
        processed = "# H1\nText\n- item1\n- item2\n\nParagraph two."
        s = m.score(original, processed)
        assert s >= 0.80

    def test_missing_heading_reduces_score(self):
        from evaluation.metrics import StructurePreservationMetric

        m = StructurePreservationMetric()
        original = "====== H1 ======\n===== H2 =====\nText"
        processed = "Text"
        s = m.score(original, processed)
        assert s < 0.90

    def test_no_structure_returns_1(self):
        from evaluation.metrics import StructurePreservationMetric

        m = StructurePreservationMetric()
        s = m.score("plain text", "plain text")
        assert s == pytest.approx(1.0)

    def test_threshold_is_090(self):
        from evaluation.metrics import StructurePreservationMetric

        m = StructurePreservationMetric()
        assert m.threshold == pytest.approx(0.90)


# ---------------------------------------------------------------------------
# DocumentScore dataclass
# ---------------------------------------------------------------------------
class TestDocumentScore:
    """Verify DocumentScore has all 7 metric fields."""

    def test_has_all_fields(self):
        from evaluation.metrics import DocumentScore

        ds = DocumentScore(
            doc_id="test:page",
            content_completeness=0.95,
            semantic_similarity=0.90,
            entity_preservation=0.98,
            link_integrity=0.99,
            noise_ratio=0.01,
            readability=45.0,
            structure_preservation=0.92,
        )
        assert ds.doc_id == "test:page"
        assert ds.content_completeness == 0.95
        assert ds.semantic_similarity == 0.90
        assert ds.entity_preservation == 0.98
        assert ds.link_integrity == 0.99
        assert ds.noise_ratio == 0.01
        assert ds.readability == 45.0
        assert ds.structure_preservation == 0.92

    def test_passes_thresholds(self):
        """A good document score should pass all thresholds."""
        from evaluation.metrics import DocumentScore, passes_thresholds

        ds = DocumentScore(
            doc_id="good",
            content_completeness=0.95,
            semantic_similarity=0.90,
            entity_preservation=0.98,
            link_integrity=0.99,
            noise_ratio=0.01,
            readability=45.0,
            structure_preservation=0.92,
        )
        assert passes_thresholds(ds) is True

    def test_fails_thresholds_low_completeness(self):
        from evaluation.metrics import DocumentScore, passes_thresholds

        ds = DocumentScore(
            doc_id="bad",
            content_completeness=0.50,
            semantic_similarity=0.90,
            entity_preservation=0.98,
            link_integrity=0.99,
            noise_ratio=0.01,
            readability=45.0,
            structure_preservation=0.92,
        )
        assert passes_thresholds(ds) is False


# ---------------------------------------------------------------------------
# Regression test
# ---------------------------------------------------------------------------
class TestRegressionCheck:
    """Regression: completeness aggregate pass-rate <0.90 -> fail."""

    def test_regression_fails_below_90_percent(self):
        from evaluation.metrics import DocumentScore, check_regression

        scores = []
        for i in range(100):
            scores.append(
                DocumentScore(
                    doc_id=f"page:{i}",
                    content_completeness=0.50 if i < 15 else 0.95,
                    semantic_similarity=0.90,
                    entity_preservation=0.98,
                    link_integrity=0.99,
                    noise_ratio=0.01,
                    readability=45.0,
                    structure_preservation=0.92,
                )
            )
        result = check_regression(scores)
        assert result["content_completeness"]["pass"] is False
        assert result["content_completeness"]["pass_rate"] < 0.90

    def test_regression_passes_above_90_percent(self):
        from evaluation.metrics import DocumentScore, check_regression

        scores = []
        for i in range(100):
            scores.append(
                DocumentScore(
                    doc_id=f"page:{i}",
                    content_completeness=0.95,
                    semantic_similarity=0.90,
                    entity_preservation=0.98,
                    link_integrity=0.99,
                    noise_ratio=0.01,
                    readability=45.0,
                    structure_preservation=0.92,
                )
            )
        result = check_regression(scores)
        assert result["content_completeness"]["pass"] is True
        assert result["content_completeness"]["pass_rate"] >= 0.90
