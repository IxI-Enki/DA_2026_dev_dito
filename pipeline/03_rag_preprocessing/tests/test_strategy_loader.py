"""T064: Tests for StrategyLoader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture()
def evaluated_dir(tmp_path: Path) -> Path:
    """Create a minimal evaluated dir with per-page JSONs."""
    d = tmp_path / "evaluated"
    d.mkdir()
    # Page evaluation results (from Deep Evaluation)
    pages = [
        {
            "page_id": "departm:electronics",
            "content_type": "knowledge",
            "rag_readiness": 0.85,
            "recommended_chunk_size": 512,
            "noise_level": "low",
        },
        {
            "page_id": "competitions:start",
            "content_type": "news",
            "rag_readiness": 0.4,
            "recommended_chunk_size": 256,
            "noise_level": "high",
        },
        {
            "page_id": "start",
            "content_type": "portal",
            "rag_readiness": 0.2,
            "recommended_chunk_size": 128,
            "noise_level": "medium",
        },
    ]
    results_file = d / "page_strategies.json"
    results_file.write_text(json.dumps(pages), encoding="utf-8")
    return d


class TestStrategyLoaderLoad:
    """Test StrategyLoader.load()."""

    def test_load_returns_dict(self, evaluated_dir: Path) -> None:
        from strategy_loader import StrategyLoader

        loader = StrategyLoader()
        strategies = loader.load(evaluated_dir)
        assert isinstance(strategies, dict)

    def test_load_has_correct_page_ids(self, evaluated_dir: Path) -> None:
        from strategy_loader import StrategyLoader

        loader = StrategyLoader()
        strategies = loader.load(evaluated_dir)
        assert "departm:electronics" in strategies

    def test_load_page_strategy_fields(self, evaluated_dir: Path) -> None:
        from strategy_loader import StrategyLoader

        loader = StrategyLoader()
        strategies = loader.load(evaluated_dir)
        s = strategies["departm:electronics"]
        assert s.page_id == "departm:electronics"
        assert s.rag_readiness == 0.85
        assert s.recommended_chunk_size == 512

    def test_load_empty_dir_returns_empty(self, tmp_path: Path) -> None:
        from strategy_loader import StrategyLoader

        empty = tmp_path / "empty"
        empty.mkdir()
        loader = StrategyLoader()
        strategies = loader.load(empty)
        assert strategies == {}


class TestStrategyLoaderGetStrategy:
    """Test StrategyLoader.get_strategy()."""

    def test_get_existing(self, evaluated_dir: Path) -> None:
        from strategy_loader import StrategyLoader

        loader = StrategyLoader()
        loader.load(evaluated_dir)
        s = loader.get_strategy("departm:electronics")
        assert s.page_id == "departm:electronics"

    def test_get_missing_returns_default(self, evaluated_dir: Path) -> None:
        from strategy_loader import StrategyLoader

        loader = StrategyLoader()
        loader.load(evaluated_dir)
        s = loader.get_strategy("nonexistent:page")
        assert s.page_id == "nonexistent:page"
        # Default should be knowledge with sensible defaults
        assert s.recommended_chunk_size > 0


class TestContentType:
    """Test ContentType enum values."""

    def test_all_types_exist(self) -> None:
        from strategy_loader import ContentType

        expected = {"knowledge", "news", "portal", "form", "archived"}
        actual = {ct.value for ct in ContentType}
        assert expected == actual
