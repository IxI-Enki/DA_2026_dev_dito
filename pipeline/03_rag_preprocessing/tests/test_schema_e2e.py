"""T005: End-to-End schema test.

Exporter output -> DocumentLoader roundtrip.
Verifies all 14 required frontmatter fields are present and correctly typed.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest
import yaml

# Ensure both preprocessing and embeddings_creator are importable
_preproc = Path(__file__).resolve().parent.parent
_embeddings = _preproc.parent / "04_embeddings_creator"
for p in [_preproc, _embeddings]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


# --- Fixtures ---


@pytest.fixture()
def sample_page() -> dict:
    """A complete page dict with all Qdrant-schema fields."""
    return {
        "page_id": "exams:da-inf-it:theses",
        "title": "Diplomarbeit Thesen",
        "namespace": "exams:da-inf-it",
        "source": "https://leowiki.htl-leonding.ac.at/doku.php?id=exams:da-inf-it:theses",
        "access_level": "public",
        "content_type": "KNOWLEDGE",
        "freshness_score": 0.7,
        "freshness_category": "recent",
        "chunking_method": "recursive_header",
        "last_modified": "2025-12-12T13:59:38",
        "author": "r.raschhofer",
        "links_to": ["page:id:1"],
        "linked_from": ["page:id:2"],
        "content": "# Diplomarbeit\n\nHier sind die Thesen.",
    }


@pytest.fixture()
def sample_media() -> dict:
    """A complete media dict with all Qdrant-schema fields."""
    return {
        "media_id": "org:forms:schulabmeldung.pdf",
        "title": "Schulabmeldung",
        "namespace": "org:forms",
        "source": "https://leowiki.htl-leonding.ac.at/lib/exe/fetch.php?media=org:forms:schulabmeldung.pdf",
        "access_level": "public",
        "content_type": "FORM",
        "freshness_score": 0.35,
        "freshness_category": "outdated",
        "chunking_method": "metadata_only",
        "last_modified": "2024-05-10T10:00:00",
        "author": "",
        "links_to": [],
        "linked_from": [],
        "content": "Schulabmeldung Formular Text extrahiert aus PDF.",
    }


# --- E2E Tests ---


class TestSchemaE2E:
    """Exporter -> DocumentLoader roundtrip."""

    def test_page_roundtrip_all_fields_present(
        self, sample_page: dict, tmp_path: Path
    ) -> None:
        """Exported page can be loaded by DocumentLoader with all 14 fields."""
        from exporter import Exporter

        exp = Exporter()
        out_dir = exp.export([sample_page], [], tmp_path)

        # Find the exported file
        pages_dir = out_dir / "pages"
        assert pages_dir.exists(), "pages/ subdirectory must exist"
        md_files = list(pages_dir.glob("*.md"))
        assert len(md_files) == 1

        # Parse the file manually (same logic as DocumentLoader.extract_frontmatter)
        content = md_files[0].read_text(encoding="utf-8")
        assert content.startswith("---\n")

        # Extract frontmatter
        parts = content.split("---\n", 2)
        assert len(parts) >= 3, "File must have ---\\n<yaml>\\n---\\n<body>"
        fm = yaml.safe_load(parts[1])
        body = parts[2].strip()

        # Verify all 14 required fields
        assert fm["title"] == "Diplomarbeit Thesen"
        assert fm["namespace"] == "exams:da-inf-it"
        assert fm["source"].startswith("https://")
        assert fm["page_id"] == "exams:da-inf-it:theses"
        assert fm["access_level"] == "public"
        assert fm["content_type"] == "KNOWLEDGE"
        assert isinstance(fm["freshness_score"], float)
        assert fm["freshness_category"] in {"fresh", "recent", "outdated", "archived"}
        assert isinstance(fm["chunking_method"], str)
        assert fm["last_modified"] == "2025-12-12T13:59:38"
        assert isinstance(fm["author"], str)
        assert fm["content_hash"] == hashlib.md5(body.encode("utf-8")).hexdigest()
        assert isinstance(fm["links_to"], list)
        assert isinstance(fm["linked_from"], list)

    def test_media_roundtrip_uses_media_id(
        self, sample_media: dict, tmp_path: Path
    ) -> None:
        """Exported media uses media_id (not page_id) and has all fields."""
        from exporter import Exporter

        exp = Exporter()
        out_dir = exp.export([], [sample_media], tmp_path)

        media_dir = out_dir / "media"
        assert media_dir.exists(), "media/ subdirectory must exist"
        md_files = list(media_dir.glob("*.md"))
        assert len(md_files) == 1

        content = md_files[0].read_text(encoding="utf-8")
        parts = content.split("---\n", 2)
        fm = yaml.safe_load(parts[1])

        assert "media_id" in fm
        assert "page_id" not in fm
        assert fm["media_id"] == "org:forms:schulabmeldung.pdf"
        assert fm["content_type"] == "FORM"
        assert isinstance(fm["freshness_score"], float)
        assert isinstance(fm["content_hash"], str)
        assert len(fm["content_hash"]) == 32  # MD5 hex

    def test_content_hash_is_md5_of_body_without_frontmatter(
        self, sample_page: dict, tmp_path: Path
    ) -> None:
        """content_hash must be MD5 of body content only (no frontmatter)."""
        from exporter import Exporter

        exp = Exporter()
        out_dir = exp.export([sample_page], [], tmp_path)

        md_file = list((out_dir / "pages").glob("*.md"))[0]
        content = md_file.read_text(encoding="utf-8")
        parts = content.split("---\n", 2)
        fm = yaml.safe_load(parts[1])
        body = parts[2].strip()

        expected_hash = hashlib.md5(body.encode("utf-8")).hexdigest()
        assert fm["content_hash"] == expected_hash

    def test_output_has_pages_and_media_subdirs(
        self, sample_page: dict, sample_media: dict, tmp_path: Path
    ) -> None:
        """Output directory has pages/ and media/ subdirectories."""
        from exporter import Exporter

        exp = Exporter()
        out_dir = exp.export([sample_page], [sample_media], tmp_path)

        assert (out_dir / "pages").is_dir()
        assert (out_dir / "media").is_dir()

    def test_manifest_json_created(
        self, sample_page: dict, tmp_path: Path
    ) -> None:
        """Export creates a manifest.json."""
        import json
        from exporter import Exporter

        exp = Exporter()
        out_dir = exp.export([sample_page], [], tmp_path)

        manifest_path = out_dir / "manifest.json"
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert "pages_count" in manifest
        assert "media_count" in manifest
