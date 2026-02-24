"""Tests for the keyword baseline evaluation script.

Covers source_file → page_id mapping and the evaluation runner
with mocked DokuWiki API calls.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from evaluation.scripts.eval_keyword_baseline import (
    run_keyword_baseline,
    source_file_to_page_id,
)

# ---------------------------------------------------------------------------
# source_file_to_page_id
# ---------------------------------------------------------------------------


class TestSourceFileToPageId:
    """Verify all ground-truth filename patterns map correctly."""

    def test_single_namespace(self) -> None:
        assert (
            source_file_to_page_id("exams_matura-tagesschule-if-it.txt")
            == "exams:matura-tagesschule-if-it"
        )

    def test_double_namespace(self) -> None:
        assert (
            source_file_to_page_id("archive_exams_semesterpruefungen.txt")
            == "archive:exams:semesterpruefungen"
        )

    def test_triple_namespace(self) -> None:
        assert (
            source_file_to_page_id("it_studentmail2023_android_gmail.txt")
            == "it:studentmail2023:android:gmail"
        )

    def test_no_namespace(self) -> None:
        assert source_file_to_page_id("start.txt") == "start"

    def test_hyphens_preserved(self) -> None:
        assert source_file_to_page_id("exams_da-inf-it.txt") == "exams:da-inf-it"

    def test_all_ground_truth_sources(self) -> None:
        """Spot-check that known source files produce valid page IDs (no .txt, colons present)."""
        sources = [
            "class_notebooks-inf-it.txt",
            "class_verhaltensnoten.txt",
            "competitions_listewettbewerbe.txt",
            "departm_elektr.txt",
            "org_brandschutz.txt",
            "org_forms_exkursion.txt",
            "org_hausordnung.txt",
            "werkstaette_luftcheck.txt",
        ]
        for src in sources:
            pid = source_file_to_page_id(src)
            assert not pid.endswith(".txt"), f"{src} still has .txt suffix"
            assert ":" in pid, f"{src} has no namespace separator"


# ---------------------------------------------------------------------------
# run_keyword_baseline (mocked API)
# ---------------------------------------------------------------------------


class TestRunKeywordBaseline:
    """Test the evaluation runner with a mocked WikiSearchClient."""

    @pytest.fixture()
    def small_ground_truth(self, tmp_path):
        """Create a minimal ground truth file."""
        gt = {
            "metadata": {"version": "test"},
            "qa_pairs": [
                {
                    "id": "test-01",
                    "question": "What is X?",
                    "ground_truth": "X is Y.",
                    "source_file": "ns_page-one.txt",
                    "context_keywords": ["x"],
                    "difficulty": "easy",
                },
                {
                    "id": "test-02",
                    "question": "What is Z?",
                    "ground_truth": "Z is W.",
                    "source_file": "ns_page-two.txt",
                    "context_keywords": ["z"],
                    "difficulty": "easy",
                },
            ],
        }
        gt_file = tmp_path / "gt.json"
        gt_file.write_text(json.dumps(gt), encoding="utf-8")
        return gt_file

    @pytest.fixture()
    def mock_config(self, small_ground_truth):
        """Create a minimal ExperimentConfig pointing at the small ground truth."""
        from evaluation.config import ExperimentConfig

        return ExperimentConfig(
            name="test-keyword",
            experiment_type="keyword_baseline",
            thesis_id="FF1",
            provider="ollama",
            model="none",
            dimensions=0,
            chunk_size=0,
            chunk_overlap=0,
            retrieval_mode="dense",
            top_k=10,
            collection_prefix="n/a",
            ground_truth_file=str(small_ground_truth),
            metrics=("mrr", "precision_at_5"),
            config_hash="sha256:test",
        )

    def test_perfect_hits(self, mock_config):
        """When the API returns the expected page first, MRR and P@5 should be 1.0."""
        mock_client = MagicMock()
        mock_client.search_pages.side_effect = [
            [{"id": "ns:page-one", "score": 100}],
            [{"id": "ns:page-two", "score": 100}],
        ]

        with patch(
            "evaluation.scripts.eval_keyword_baseline.WikiSearchClient",
            return_value=mock_client,
        ):
            result = run_keyword_baseline(mock_config)

        assert result["aggregate_metrics"]["mrr"] == 1.0
        assert result["aggregate_metrics"]["precision_at_5"] == pytest.approx(0.2)
        assert result["summary"]["hits"] == 2
        assert result["summary"]["errors"] == 0

    def test_no_hits(self, mock_config):
        """When the API returns irrelevant pages, MRR should be 0.0."""
        mock_client = MagicMock()
        mock_client.search_pages.return_value = [
            {"id": "other:page", "score": 50},
        ]

        with patch(
            "evaluation.scripts.eval_keyword_baseline.WikiSearchClient",
            return_value=mock_client,
        ):
            result = run_keyword_baseline(mock_config)

        assert result["aggregate_metrics"]["mrr"] == 0.0
        assert result["summary"]["hits"] == 0

    def test_result_has_nfr005_fields(self, mock_config):
        """Result must include timestamp, config_hash, code_version (NFR-005)."""
        mock_client = MagicMock()
        mock_client.search_pages.return_value = []

        with patch(
            "evaluation.scripts.eval_keyword_baseline.WikiSearchClient",
            return_value=mock_client,
        ):
            result = run_keyword_baseline(mock_config)

        exp = result["experiment"]
        assert "timestamp" in exp
        assert exp["config_hash"] == "sha256:test"
        assert "code_version" in exp
