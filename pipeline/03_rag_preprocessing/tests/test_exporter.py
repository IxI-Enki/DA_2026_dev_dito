"""T066 + T006: Tests for Exporter -- Qdrant-Schema compliance."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml


@pytest.fixture()
def sample_pages() -> list[dict]:
    """Sample preprocessed page data with full Qdrant-schema fields."""
    return [
        {
            "page_id": "departm:electronics",
            "title": "Electronics",
            "namespace": "departm",
            "source": "https://leowiki.htl-leonding.ac.at/doku.php?id=departm:electronics",
            "access_level": "public",
            "content_type": "KNOWLEDGE",
            "freshness_score": 0.85,
            "freshness_category": "fresh",
            "chunking_method": "recursive_header",
            "last_modified": "2026-01-15T10:00:00",
            "author": "m.mueller",
            "links_to": ["departm:start"],
            "linked_from": ["start"],
            "content": "# Electronics\n\nWelcome to electronics.",
        },
        {
            "page_id": "competitions:start",
            "title": "Competitions",
            "namespace": "competitions",
            "source": "https://leowiki.htl-leonding.ac.at/doku.php?id=competitions:start",
            "access_level": "public",
            "content_type": "NEWS",
            "freshness_score": 1.0,
            "freshness_category": "fresh",
            "chunking_method": "naive",
            "last_modified": "2026-02-10T08:00:00",
            "author": "a.admin",
            "links_to": [],
            "linked_from": [],
            "content": "# Competitions\n\nLatest competition news.",
        },
    ]


@pytest.fixture()
def sample_media() -> list[dict]:
    """Sample media data with full Qdrant-schema fields."""
    return [
        {
            "media_id": "org:forms:anmeldung.pdf",
            "title": "Anmeldung",
            "namespace": "org:forms",
            "source": "https://leowiki.htl-leonding.ac.at/lib/exe/fetch.php?media=org:forms:anmeldung.pdf",
            "access_level": "public",
            "content_type": "FORM",
            "freshness_score": 0.55,
            "freshness_category": "recent",
            "chunking_method": "metadata_only",
            "last_modified": "2025-06-01T10:00:00",
            "author": "",
            "links_to": [],
            "linked_from": [],
            "content": "Anmeldung Formular Inhalt.",
        },
    ]


class TestExporterExport:
    """Test Exporter.export() with new API: export(pages, media, output_base)."""

    def test_export_returns_path(self, sample_pages: list[dict], tmp_path: Path) -> None:
        from exporter import Exporter

        exp = Exporter()
        result = exp.export(sample_pages, [], tmp_path)
        assert isinstance(result, Path)
        assert result.exists()

    def test_export_creates_timestamped_dir(self, sample_pages: list[dict], tmp_path: Path) -> None:
        from exporter import Exporter

        exp = Exporter()
        result = exp.export(sample_pages, [], tmp_path)
        assert result.name.startswith("preprocessed_at_")

    def test_export_creates_pages_subdir(self, sample_pages: list[dict], tmp_path: Path) -> None:
        from exporter import Exporter

        exp = Exporter()
        out_dir = exp.export(sample_pages, [], tmp_path)
        pages_dir = out_dir / "pages"
        assert pages_dir.is_dir()
        md_files = list(pages_dir.glob("*.md"))
        assert len(md_files) == len(sample_pages)

    def test_export_creates_media_subdir(
        self, sample_media: list[dict], tmp_path: Path
    ) -> None:
        from exporter import Exporter

        exp = Exporter()
        out_dir = exp.export([], sample_media, tmp_path)
        media_dir = out_dir / "media"
        assert media_dir.is_dir()
        md_files = list(media_dir.glob("*.md"))
        assert len(md_files) == len(sample_media)

    def test_media_output_has_md_extension_not_txt(
        self, sample_media: list[dict], tmp_path: Path
    ) -> None:
        from exporter import Exporter

        exp = Exporter()
        out_dir = exp.export([], sample_media, tmp_path)
        media_dir = out_dir / "media"
        txt_files = list(media_dir.glob("*.txt"))
        md_files = list(media_dir.glob("*.md"))
        assert len(txt_files) == 0, "Media files must use .md extension, not .txt"
        assert len(md_files) > 0

    def test_exported_file_has_yaml_frontmatter(
        self, sample_pages: list[dict], tmp_path: Path
    ) -> None:
        from exporter import Exporter

        exp = Exporter()
        out_dir = exp.export(sample_pages, [], tmp_path)
        md_files = list((out_dir / "pages").glob("*.md"))
        content = md_files[0].read_text(encoding="utf-8")
        assert content.startswith("---\n")
        assert "\n---\n" in content[4:]

    def test_export_empty_pages_returns_dir(self, tmp_path: Path) -> None:
        from exporter import Exporter

        exp = Exporter()
        result = exp.export([], [], tmp_path)
        assert result.exists()


class TestPageFrontmatter:
    """Test that page frontmatter contains all Qdrant-Schema fields."""

    def _get_frontmatter(self, pages: list[dict], tmp_path: Path) -> dict:
        from exporter import Exporter

        exp = Exporter()
        out_dir = exp.export(pages, [], tmp_path)
        md_file = list((out_dir / "pages").glob("*.md"))[0]
        content = md_file.read_text(encoding="utf-8")
        parts = content.split("---\n", 2)
        return yaml.safe_load(parts[1])

    def test_page_has_all_required_fields(
        self, sample_pages: list[dict], tmp_path: Path
    ) -> None:
        fm = self._get_frontmatter(sample_pages, tmp_path)
        required = {
            "title", "namespace", "source", "page_id", "access_level",
            "content_type", "freshness_score", "freshness_category",
            "chunking_method", "last_modified", "author", "content_hash",
            "links_to", "linked_from",
        }
        assert required.issubset(set(fm.keys())), f"Missing: {required - set(fm.keys())}"

    def test_content_hash_is_md5_of_body(
        self, sample_pages: list[dict], tmp_path: Path
    ) -> None:
        from exporter import Exporter

        exp = Exporter()
        out_dir = exp.export(sample_pages, [], tmp_path)
        md_file = list((out_dir / "pages").glob("*.md"))[0]
        content = md_file.read_text(encoding="utf-8")
        parts = content.split("---\n", 2)
        fm = yaml.safe_load(parts[1])
        body = parts[2].strip()

        expected = hashlib.md5(body.encode("utf-8")).hexdigest()
        assert fm["content_hash"] == expected
        assert len(fm["content_hash"]) == 32

    def test_freshness_score_is_float(
        self, sample_pages: list[dict], tmp_path: Path
    ) -> None:
        fm = self._get_frontmatter(sample_pages, tmp_path)
        assert isinstance(fm["freshness_score"], float)

    def test_links_to_is_list(
        self, sample_pages: list[dict], tmp_path: Path
    ) -> None:
        fm = self._get_frontmatter(sample_pages, tmp_path)
        assert isinstance(fm["links_to"], list)

    def test_linked_from_is_list(
        self, sample_pages: list[dict], tmp_path: Path
    ) -> None:
        fm = self._get_frontmatter(sample_pages, tmp_path)
        assert isinstance(fm["linked_from"], list)


class TestMediaFrontmatter:
    """Test that media frontmatter uses media_id not page_id."""

    def _get_frontmatter(self, media: list[dict], tmp_path: Path) -> dict:
        from exporter import Exporter

        exp = Exporter()
        out_dir = exp.export([], media, tmp_path)
        md_file = list((out_dir / "media").glob("*.md"))[0]
        content = md_file.read_text(encoding="utf-8")
        parts = content.split("---\n", 2)
        return yaml.safe_load(parts[1])

    def test_media_uses_media_id(
        self, sample_media: list[dict], tmp_path: Path
    ) -> None:
        fm = self._get_frontmatter(sample_media, tmp_path)
        assert "media_id" in fm
        assert "page_id" not in fm

    def test_media_has_all_required_fields(
        self, sample_media: list[dict], tmp_path: Path
    ) -> None:
        fm = self._get_frontmatter(sample_media, tmp_path)
        required = {
            "title", "namespace", "source", "media_id", "access_level",
            "content_type", "freshness_score", "freshness_category",
            "chunking_method", "last_modified", "author", "content_hash",
            "links_to", "linked_from",
        }
        assert required.issubset(set(fm.keys())), f"Missing: {required - set(fm.keys())}"
