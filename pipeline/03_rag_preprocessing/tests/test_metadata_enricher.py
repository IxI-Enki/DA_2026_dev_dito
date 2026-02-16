"""T068 + T007: Tests for MetadataEnricher -- schema fields, freshness, access."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
import yaml


class TestFreshnessScore:
    """T077: Tests for calculate_freshness_score method."""

    def test_fresh_within_30_days(self) -> None:
        from metadata_enricher import MetadataEnricher

        me = MetadataEnricher()
        recent = (datetime.now() - timedelta(days=10)).isoformat()
        assert me.calculate_freshness_score(recent) == "fresh"

    def test_recent_within_180_days(self) -> None:
        from metadata_enricher import MetadataEnricher

        me = MetadataEnricher()
        date = (datetime.now() - timedelta(days=90)).isoformat()
        assert me.calculate_freshness_score(date) == "recent"

    def test_outdated_within_365_days(self) -> None:
        from metadata_enricher import MetadataEnricher

        me = MetadataEnricher()
        date = (datetime.now() - timedelta(days=250)).isoformat()
        assert me.calculate_freshness_score(date) == "outdated"

    def test_archived_over_365_days(self) -> None:
        from metadata_enricher import MetadataEnricher

        me = MetadataEnricher()
        date = (datetime.now() - timedelta(days=400)).isoformat()
        assert me.calculate_freshness_score(date) == "archived"

    def test_invalid_date_returns_unknown(self) -> None:
        from metadata_enricher import MetadataEnricher

        me = MetadataEnricher()
        assert me.calculate_freshness_score("not-a-date") == "unknown"


class TestAccessLevel:
    """T078: Tests for determine_access_level method."""

    def test_teacher_namespace(self) -> None:
        from metadata_enricher import MetadataEnricher

        me = MetadataEnricher()
        assert me.determine_access_level("teacher:docs") == "teacher_only"

    def test_lehrer_namespace(self) -> None:
        from metadata_enricher import MetadataEnricher

        me = MetadataEnricher()
        assert me.determine_access_level("lehrer:material") == "teacher_only"

    def test_public_namespace(self) -> None:
        from metadata_enricher import MetadataEnricher

        me = MetadataEnricher()
        assert me.determine_access_level("departm:electronics") == "public"

    def test_empty_namespace(self) -> None:
        from metadata_enricher import MetadataEnricher

        me = MetadataEnricher()
        assert me.determine_access_level("") == "public"


class TestGenerateFrontmatter:
    """T007: Tests for generate_frontmatter() schema compliance."""

    def test_field_name_is_last_modified_not_modified_at(self) -> None:
        """Frontmatter must use 'last_modified', not 'modified_at'."""
        from metadata_enricher import MetadataEnricher

        me = MetadataEnricher(wiki_base_url="https://leowiki.htl-leonding.ac.at/doku.php?id=")
        raw_meta = {
            "page_info": {
                "last_modified": "2025-12-12T13:59:38",
                "author": "r.raschhofer",
                "permission": 1,
            }
        }
        fm_str = me.generate_frontmatter(
            page_id="exams:theses",
            title="Theses",
            raw_metadata=raw_meta,
        )
        fm = yaml.safe_load(fm_str.strip().strip("---").strip())
        assert "last_modified" in fm, "Field must be named 'last_modified'"
        assert "modified_at" not in fm, "Old field name 'modified_at' must not be present"

    def test_linked_from_populated_from_backlinks(self) -> None:
        """linked_from field must be populated when backlinks data is provided."""
        from metadata_enricher import MetadataEnricher

        me = MetadataEnricher(wiki_base_url="https://leowiki.htl-leonding.ac.at/doku.php?id=")
        fm_str = me.generate_frontmatter(
            page_id="exams:theses",
            title="Theses",
            backlinks=["start", "departm:electronics"],
        )
        fm = yaml.safe_load(fm_str.strip().strip("---").strip())
        assert "linked_from" in fm
        assert "start" in fm["linked_from"]
        assert "departm:electronics" in fm["linked_from"]

    def test_linked_from_empty_when_no_backlinks(self) -> None:
        """linked_from defaults to empty list when no backlinks provided."""
        from metadata_enricher import MetadataEnricher

        me = MetadataEnricher(wiki_base_url="https://leowiki.htl-leonding.ac.at/doku.php?id=")
        fm_str = me.generate_frontmatter(
            page_id="exams:theses",
            title="Theses",
        )
        fm = yaml.safe_load(fm_str.strip().strip("---").strip())
        assert "linked_from" in fm
        assert fm["linked_from"] == []

    def test_source_url_uses_wiki_base_url(self) -> None:
        """source field must use wiki_base_url + page_id."""
        from metadata_enricher import MetadataEnricher

        me = MetadataEnricher(wiki_base_url="https://leowiki.htl-leonding.ac.at/doku.php?id=")
        fm_str = me.generate_frontmatter(
            page_id="departm:electronics",
            title="Electronics",
        )
        fm = yaml.safe_load(fm_str.strip().strip("---").strip())
        assert fm["source"] == "https://leowiki.htl-leonding.ac.at/doku.php?id=departm:electronics"

    def test_frontmatter_has_links_to(self) -> None:
        """links_to field must be present in frontmatter."""
        from metadata_enricher import MetadataEnricher

        me = MetadataEnricher(wiki_base_url="https://leowiki.htl-leonding.ac.at/doku.php?id=")
        links_data = {
            "internal_links": [
                {"target": "departm:start"},
                {"target": "exams:overview"},
            ],
            "external_links": [],
            "media_links": [],
        }
        fm_str = me.generate_frontmatter(
            page_id="departm:electronics",
            title="Electronics",
            links_data=links_data,
        )
        fm = yaml.safe_load(fm_str.strip().strip("---").strip())
        assert "links_to" in fm
        assert "departm:start" in fm["links_to"]
