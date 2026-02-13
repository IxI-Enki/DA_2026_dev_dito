"""Tests for the model comparison evaluation script.

Covers the simple_chunk function and the evaluation runner
with mocked Qdrant and embedding provider.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from evaluation.scripts.eval_model_comparison import (
    simple_chunk,
    calculate_relevance_score,
    load_corpus_for_ground_truth,
    run_model_evaluation,
)


# ---------------------------------------------------------------------------
# simple_chunk
# ---------------------------------------------------------------------------


class TestSimpleChunk:
    def test_empty_text(self) -> None:
        assert simple_chunk("") == []

    def test_short_text_single_chunk(self) -> None:
        result = simple_chunk("Hello world.", chunk_size=100)
        assert len(result) == 1
        assert result[0] == "Hello world."

    def test_respects_chunk_size(self) -> None:
        text = "A" * 200 + "\n\n" + "B" * 200 + "\n\n" + "C" * 200
        chunks = simple_chunk(text, chunk_size=250, overlap=0)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk) <= 300  # Some tolerance for boundary effects

    def test_multiple_paragraphs(self) -> None:
        text = "Para one.\n\nPara two.\n\nPara three."
        chunks = simple_chunk(text, chunk_size=1000)
        assert len(chunks) == 1  # All fit in one chunk

    def test_large_paragraph_split_by_sentences(self) -> None:
        long_para = "Sentence one. " * 50  # ~750 chars
        chunks = simple_chunk(long_para, chunk_size=200, overlap=0)
        assert len(chunks) >= 2


# ---------------------------------------------------------------------------
# calculate_relevance_score
# ---------------------------------------------------------------------------


class TestRelevanceScore:
    def test_high_overlap(self) -> None:
        score = calculate_relevance_score(
            "Die Reife und Diplomprüfungen bestehen aus 3 Säulen",
            "Die Reife- und Diplomprüfungen bestehen aus 3 Säulen",
        )
        assert score > 0.3

    def test_no_overlap(self) -> None:
        score = calculate_relevance_score("unrelated text about weather", "Matura Prüfung")
        assert score < 0.2

    def test_keyword_boost(self) -> None:
        base = calculate_relevance_score("Text about diplomarbeit", "Answer text")
        boosted = calculate_relevance_score(
            "Text about diplomarbeit",
            "Answer text",
            context_keywords=["diplomarbeit"],
        )
        assert boosted > base


# ---------------------------------------------------------------------------
# load_corpus_for_ground_truth
# ---------------------------------------------------------------------------


class TestLoadCorpus:
    def test_loads_from_fetched_dir(self, tmp_path) -> None:
        """Verify corpus loading with mock fetched directory."""
        # Create mock fetched data structure
        fetched = tmp_path / "data" / "fetched" / "fetched_at_20260101_000000"
        content_dir = fetched / "page_content"
        content_dir.mkdir(parents=True)

        (content_dir / "ns_page-one.txt").write_text("Content for page one.", encoding="utf-8")

        gt = {
            "metadata": {},
            "qa_pairs": [
                {
                    "id": "q1",
                    "question": "Q?",
                    "ground_truth": "A.",
                    "source_file": "ns_page-one.txt",
                    "context_keywords": [],
                    "difficulty": "easy",
                },
            ],
        }

        with patch(
            "evaluation.scripts.eval_model_comparison._find_fetched_dir",
            return_value=fetched,
        ):
            chunks = load_corpus_for_ground_truth(gt, chunk_size=1000)

        assert len(chunks) >= 1
        assert chunks[0]["page_id"] == "ns:page-one"
        assert "Content for page one" in chunks[0]["text"]


# ---------------------------------------------------------------------------
# run_model_evaluation (fully mocked)
# ---------------------------------------------------------------------------


class TestRunModelEvaluation:
    @pytest.fixture()
    def mock_config(self, tmp_path):
        from evaluation.config import ExperimentConfig

        gt = {
            "metadata": {"version": "test"},
            "qa_pairs": [
                {
                    "id": "t1",
                    "question": "What is X?",
                    "ground_truth": "X is Y.",
                    "source_file": "ns_page-one.txt",
                    "context_keywords": ["x"],
                    "difficulty": "easy",
                },
            ],
        }
        gt_file = tmp_path / "gt.json"
        gt_file.write_text(json.dumps(gt), encoding="utf-8")

        return ExperimentConfig(
            name="test-model",
            experiment_type="model_comparison",
            thesis_id="FF3",
            provider="ollama",
            model="test-model",
            dimensions=4,
            chunk_size=512,
            chunk_overlap=50,
            retrieval_mode="dense",
            top_k=10,
            collection_prefix="eval_test_",
            ground_truth_file=str(gt_file),
            metrics=("mrr", "ndcg_at_10"),
            config_hash="sha256:test",
        )

    def test_full_pipeline_mocked(self, mock_config, tmp_path):
        """Test the evaluation runner with all external calls mocked."""
        # Mock corpus loading
        mock_chunks = [
            {"page_id": "ns:page-one", "chunk_index": 0, "text": "Content about X."},
            {"page_id": "ns:page-two", "chunk_index": 0, "text": "Irrelevant content."},
        ]

        # Mock provider — embed returns one vector per input text
        mock_provider = MagicMock()
        mock_provider.embed.side_effect = lambda texts: [[0.1, 0.2, 0.3, 0.4]] * len(texts)
        type(mock_provider).model_name = PropertyMock(return_value="test-model")
        type(mock_provider).dimensions = PropertyMock(return_value=4)

        # Mock Qdrant
        mock_qdrant = MagicMock()
        mock_hit = MagicMock()
        mock_hit.payload = {"page_id": "ns:page-one", "chunk_index": 0, "text": "Content about X is Y."}
        mock_qdrant.search.return_value = [mock_hit]

        with (
            patch(
                "evaluation.scripts.eval_model_comparison.load_corpus_for_ground_truth",
                return_value=mock_chunks,
            ),
            patch(
                "evaluation.scripts.eval_model_comparison.create_provider",
                return_value=mock_provider,
            ),
            patch(
                "evaluation.scripts.eval_model_comparison._get_qdrant_client",
                return_value=mock_qdrant,
            ),
        ):
            result = run_model_evaluation(mock_config)

        assert result["aggregate_metrics"]["mrr"]["mean"] == 1.0
        assert result["experiment"]["config_hash"] == "sha256:test"
        assert result["experiment"]["model"] == "test-model"
        assert "timestamp" in result["experiment"]
        assert "code_version" in result["experiment"]
        assert "by_difficulty" in result

        # Verify cleanup was called
        mock_qdrant.delete_collection.assert_called_once()

    def test_cleanup_on_error(self, mock_config, tmp_path):
        """Verify Qdrant collection is deleted even if evaluation fails."""
        mock_qdrant = MagicMock()
        mock_qdrant.search.side_effect = RuntimeError("Search failed")

        with (
            patch(
                "evaluation.scripts.eval_model_comparison.load_corpus_for_ground_truth",
                return_value=[{"page_id": "p", "chunk_index": 0, "text": "t"}],
            ),
            patch(
                "evaluation.scripts.eval_model_comparison.create_provider",
                return_value=MagicMock(
                    embed=MagicMock(return_value=[[0.1, 0.2, 0.3, 0.4]]),
                    model_name="m",
                    dimensions=4,
                ),
            ),
            patch(
                "evaluation.scripts.eval_model_comparison._get_qdrant_client",
                return_value=mock_qdrant,
            ),
            pytest.raises(RuntimeError, match="Search failed"),
        ):
            run_model_evaluation(mock_config)

        # Cleanup should still have been called
        mock_qdrant.delete_collection.assert_called_once()
