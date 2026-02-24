"""Unit tests for ReportGenerator (T051-T054)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture()
def results_dir(tmp_path: Path) -> Path:
    """Create a temp results dir with two sample result JSONs."""
    d = tmp_path / "results"
    d.mkdir()
    baseline = {
        "experiment": {"name": "Baseline", "model": "bge-m3"},
        "config_hash": "sha256:abc123",
        "per_query": [
            {"rr": 0.5, "ndcg_at_10": 0.6, "p_at_5": 0.7, "difficulty": "easy"},
            {"rr": 0.4, "ndcg_at_10": 0.5, "p_at_5": 0.6, "difficulty": "medium"},
            {"rr": 0.6, "ndcg_at_10": 0.7, "p_at_5": 0.8, "difficulty": "easy"},
            {"rr": 0.3, "ndcg_at_10": 0.4, "p_at_5": 0.5, "difficulty": "hard"},
        ],
    }
    candidate = {
        "experiment": {"name": "Candidate", "model": "nomic-embed"},
        "config_hash": "sha256:def456",
        "per_query": [
            {"rr": 0.6, "ndcg_at_10": 0.7, "p_at_5": 0.8, "difficulty": "easy"},
            {"rr": 0.5, "ndcg_at_10": 0.6, "p_at_5": 0.7, "difficulty": "medium"},
            {"rr": 0.7, "ndcg_at_10": 0.8, "p_at_5": 0.9, "difficulty": "easy"},
            {"rr": 0.4, "ndcg_at_10": 0.5, "p_at_5": 0.6, "difficulty": "hard"},
        ],
    }
    (d / "baseline.json").write_text(json.dumps(baseline), encoding="utf-8")
    (d / "candidate.json").write_text(json.dumps(candidate), encoding="utf-8")
    return d


@pytest.fixture()
def ragas_scores() -> dict[str, float]:
    """Sample RAGAS scores."""
    return {"answer_correctness": 0.78, "faithfulness": 0.65, "context_precision": 0.72}


class TestReportStructure:
    """T051: Tests for report structure generation."""

    def test_generate_returns_markdown_and_json_paths(
        self, results_dir: Path, tmp_path: Path
    ) -> None:
        from evaluation.reports.generator import ReportGenerator

        gen = ReportGenerator(output_dir=tmp_path / "report")
        md_path, json_path = gen.generate(results_dir)
        assert md_path.exists()
        assert json_path.exists()
        assert md_path.suffix == ".md"
        assert json_path.suffix == ".json"

    def test_markdown_contains_required_sections(self, results_dir: Path, tmp_path: Path) -> None:
        from evaluation.reports.generator import ReportGenerator

        gen = ReportGenerator(output_dir=tmp_path / "report")
        md_path, _ = gen.generate(results_dir)
        content = md_path.read_text(encoding="utf-8")
        assert "# Evaluation Report" in content
        assert "## Executive Summary" in content
        assert "## Custom Metrics" in content

    def test_json_is_valid_and_has_sections(self, results_dir: Path, tmp_path: Path) -> None:
        from evaluation.reports.generator import ReportGenerator

        gen = ReportGenerator(output_dir=tmp_path / "report")
        _, json_path = gen.generate(results_dir)
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)
        assert "executive_summary" in data
        assert "custom_metrics" in data


class TestRAGASAndCustomMetricsTable:
    """T052: Tests for RAGAS + Custom metrics side-by-side table."""

    def test_custom_metrics_table_in_markdown(self, results_dir: Path, tmp_path: Path) -> None:
        from evaluation.reports.generator import ReportGenerator

        gen = ReportGenerator(output_dir=tmp_path / "report")
        md_path, _ = gen.generate(results_dir)
        content = md_path.read_text(encoding="utf-8")
        assert "rr" in content.lower() or "MRR" in content or "mrr" in content

    def test_ragas_section_in_markdown(self, results_dir: Path, tmp_path: Path) -> None:
        from evaluation.reports.generator import ReportGenerator

        gen = ReportGenerator(output_dir=tmp_path / "report")
        md_path, _ = gen.generate(results_dir, ragas_scores={"answer_correctness": 0.78})
        content = md_path.read_text(encoding="utf-8")
        assert "RAGAS" in content

    def test_ragas_scores_in_json(self, results_dir: Path, tmp_path: Path) -> None:
        from evaluation.reports.generator import ReportGenerator

        gen = ReportGenerator(output_dir=tmp_path / "report")
        _, json_path = gen.generate(results_dir, ragas_scores={"answer_correctness": 0.78})
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert "ragas_metrics" in data
        assert data["ragas_metrics"]["answer_correctness"] == 0.78


class TestNFR005Fields:
    """T053: Tests for NFR-005 fields (timestamp, config-hash, code-version)."""

    def test_json_contains_timestamp(self, results_dir: Path, tmp_path: Path) -> None:
        from evaluation.reports.generator import ReportGenerator

        gen = ReportGenerator(output_dir=tmp_path / "report")
        _, json_path = gen.generate(results_dir)
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert "timestamp" in data
        assert isinstance(data["timestamp"], str)

    def test_json_contains_config_hash(self, results_dir: Path, tmp_path: Path) -> None:
        from evaluation.reports.generator import ReportGenerator

        gen = ReportGenerator(output_dir=tmp_path / "report")
        _, json_path = gen.generate(results_dir)
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert "config_hashes" in data

    def test_json_contains_code_version(self, results_dir: Path, tmp_path: Path) -> None:
        from evaluation.reports.generator import ReportGenerator

        gen = ReportGenerator(output_dir=tmp_path / "report")
        _, json_path = gen.generate(results_dir)
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert "code_version" in data


class TestDifficultyBreakdown:
    """T054: Tests for difficulty breakdown table."""

    def test_difficulty_breakdown_in_markdown(self, results_dir: Path, tmp_path: Path) -> None:
        from evaluation.reports.generator import ReportGenerator

        gen = ReportGenerator(output_dir=tmp_path / "report")
        md_path, _ = gen.generate(results_dir)
        content = md_path.read_text(encoding="utf-8")
        assert "Difficulty" in content or "difficulty" in content

    def test_difficulty_breakdown_in_json(self, results_dir: Path, tmp_path: Path) -> None:
        from evaluation.reports.generator import ReportGenerator

        gen = ReportGenerator(output_dir=tmp_path / "report")
        _, json_path = gen.generate(results_dir)
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert "difficulty_breakdown" in data
        breakdown = data["difficulty_breakdown"]
        assert isinstance(breakdown, dict)
        assert len(breakdown) > 0
