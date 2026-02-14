"""T066: Tests for Exporter."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def sample_pages() -> list[dict]:
    """Sample preprocessed page data."""
    return [
        {
            "page_id": "departm:electronics",
            "title": "Electronics",
            "namespace": "departm",
            "content": "# Electronics\n\nWelcome to electronics.",
            "metadata": {"access_level": "public", "content_type": "KNOWLEDGE"},
        },
        {
            "page_id": "competitions:start",
            "title": "Competitions",
            "namespace": "competitions",
            "content": "# Competitions\n\nLatest competition news.",
            "metadata": {"access_level": "public", "content_type": "NEWS"},
        },
    ]


class TestExporterExport:
    """Test Exporter.export()."""

    def test_export_returns_path(self, sample_pages: list[dict], tmp_path: Path) -> None:
        from exporter import Exporter

        exp = Exporter()
        result = exp.export(sample_pages, tmp_path)
        assert isinstance(result, Path)
        assert result.exists()

    def test_export_creates_timestamped_dir(self, sample_pages: list[dict], tmp_path: Path) -> None:
        from exporter import Exporter

        exp = Exporter()
        result = exp.export(sample_pages, tmp_path)
        assert result.name.startswith("preprocessed_at_")

    def test_export_creates_md_files(self, sample_pages: list[dict], tmp_path: Path) -> None:
        from exporter import Exporter

        exp = Exporter()
        out_dir = exp.export(sample_pages, tmp_path)
        md_files = list(out_dir.glob("*.md"))
        assert len(md_files) == len(sample_pages)

    def test_exported_file_has_yaml_frontmatter(self, sample_pages: list[dict], tmp_path: Path) -> None:
        from exporter import Exporter

        exp = Exporter()
        out_dir = exp.export(sample_pages, tmp_path)
        md_files = list(out_dir.glob("*.md"))
        content = md_files[0].read_text(encoding="utf-8")
        assert content.startswith("---\n")
        assert "\n---\n" in content[4:]  # Closing frontmatter marker

    def test_export_empty_pages_returns_dir(self, tmp_path: Path) -> None:
        from exporter import Exporter

        exp = Exporter()
        result = exp.export([], tmp_path)
        assert result.exists()
