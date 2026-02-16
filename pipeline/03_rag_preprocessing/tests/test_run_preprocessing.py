"""Tests for run_preprocessing helpers (backlinks, etc.)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_here = Path(__file__).resolve().parent.parent
if str(_here) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(_here))

from run_preprocessing import _load_backlinks


class TestLoadBacklinks:
    """_load_backlinks must use page_id from JSON, not stem.replace('_', ':')."""

    def test_backlinks_use_page_id_from_json(self, tmp_path: Path) -> None:
        """Files named start_backlinks.json must yield key 'start', not 'start:backlinks'."""
        backlinks_dir = tmp_path / "page_backlinks"
        backlinks_dir.mkdir()
        (backlinks_dir / "start_backlinks.json").write_text(
            json.dumps({"page_id": "start", "backlinks": ["wiki:welcome"]}, ensure_ascii=False),
            encoding="utf-8",
        )
        (backlinks_dir / "org_forms_backlinks.json").write_text(
            json.dumps({"page_id": "org:forms", "backlinks": ["start"]}, ensure_ascii=False),
            encoding="utf-8",
        )
        result = _load_backlinks(tmp_path)
        assert "start" in result
        assert result["start"] == ["wiki:welcome"]
        assert "org:forms" in result
        assert result["org:forms"] == ["start"]
        assert "start:backlinks" not in result
        assert "org:forms:backlinks" not in result

    def test_backlinks_fallback_stem_when_no_page_id(self, tmp_path: Path) -> None:
        """When JSON has no page_id, fall back to stripping _backlinks and replacing _ with :."""
        backlinks_dir = tmp_path / "page_backlinks"
        backlinks_dir.mkdir()
        (backlinks_dir / "start_backlinks.json").write_text(
            json.dumps({"backlinks": ["wiki:welcome"]}, ensure_ascii=False),
            encoding="utf-8",
        )
        result = _load_backlinks(tmp_path)
        assert "start" in result
        assert result["start"] == ["wiki:welcome"]

    def test_backlinks_empty_dir(self, tmp_path: Path) -> None:
        """Missing page_backlinks dir returns empty dict."""
        result = _load_backlinks(tmp_path)
        assert result == {}
