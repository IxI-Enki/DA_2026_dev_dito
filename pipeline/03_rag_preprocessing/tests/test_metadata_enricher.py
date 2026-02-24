"""T068 + T007 + T017: Tests for MetadataEnricher -- schema fields, freshness, access."""

from __future__ import annotations

from datetime import datetime, timedelta

import yaml


class TestFreshnessHybridFormula:
    """T017: Tests for loosened freshness formula (school-wiki content longevity).

    Thresholds:
        < 90 days:    score=1.00, category="fresh"
        < 365 days:   score=0.85, category="fresh"
        < 730 days:   score=0.70, category="recent"
        < 1460 days:  score=0.50, category="outdated"
        >= 1460 days: score=0.30, category="stale"
    Archive namespace: always 0.20, "archived".
    """

    def test_26_day_old_returns_fresh_1_0(self) -> None:
        """26 days -> score=1.0, category='fresh'."""
        from metadata_enricher import MetadataEnricher

        me = MetadataEnricher()
        date = (datetime.now() - timedelta(days=26)).isoformat()
        result = me.calculate_freshness(date)
        assert result.score == 1.0
        assert result.category == "fresh"

    def test_60_day_old_returns_fresh_1_0(self) -> None:
        """60 days (< 90) -> score=1.0, category='fresh'."""
        from metadata_enricher import MetadataEnricher

        me = MetadataEnricher()
        date = (datetime.now() - timedelta(days=60)).isoformat()
        result = me.calculate_freshness(date)
        assert result.score == 1.0
        assert result.category == "fresh"

    def test_120_day_old_returns_fresh_0_85(self) -> None:
        """120 days (< 365) -> score=0.85, category='fresh'."""
        from metadata_enricher import MetadataEnricher

        me = MetadataEnricher()
        date = (datetime.now() - timedelta(days=120)).isoformat()
        result = me.calculate_freshness(date)
        assert result.score == 0.85
        assert result.category == "fresh"

    def test_300_day_old_returns_fresh_0_85(self) -> None:
        """300 days (< 365) -> score=0.85, category='fresh'."""
        from metadata_enricher import MetadataEnricher

        me = MetadataEnricher()
        date = (datetime.now() - timedelta(days=300)).isoformat()
        result = me.calculate_freshness(date)
        assert result.score == 0.85
        assert result.category == "fresh"

    def test_650_day_old_returns_recent_0_70(self) -> None:
        """650 days (< 730) -> score=0.70, category='recent'."""
        from metadata_enricher import MetadataEnricher

        me = MetadataEnricher()
        date = (datetime.now() - timedelta(days=650)).isoformat()
        result = me.calculate_freshness(date)
        assert result.score == 0.70
        assert result.category == "recent"

    def test_800_day_old_returns_outdated_0_50(self) -> None:
        """800 days (730-1460) -> score=0.50, category='outdated'."""
        from metadata_enricher import MetadataEnricher

        me = MetadataEnricher()
        date = (datetime.now() - timedelta(days=800)).isoformat()
        result = me.calculate_freshness(date)
        assert result.score == 0.50
        assert result.category == "outdated"

    def test_1500_day_old_returns_stale_0_30(self) -> None:
        """Non-archive namespace: ~1500 days -> score=0.30, category='stale'."""
        from metadata_enricher import MetadataEnricher

        me = MetadataEnricher()
        date = (datetime.now() - timedelta(days=1500)).isoformat()
        result = me.calculate_freshness(date, namespace="class")
        assert result.score == 0.30
        assert result.category == "stale"

    def test_archive_namespace_always_archived(self) -> None:
        """Archive namespace: always category='archived' regardless of date."""
        from metadata_enricher import MetadataEnricher

        me = MetadataEnricher()
        recent = (datetime.now() - timedelta(days=10)).isoformat()
        result = me.calculate_freshness(recent, namespace="archive:old")
        assert result.score == 0.20
        assert result.category == "archived"

    def test_invalid_date_returns_default(self) -> None:
        """Invalid date string -> default score=0.5, category='unknown'."""
        from metadata_enricher import MetadataEnricher

        me = MetadataEnricher()
        result = me.calculate_freshness("not-a-date")
        assert result.score == 0.5
        assert result.category == "unknown"

    def test_freshness_result_has_score_and_category(self) -> None:
        """FreshnessResult dataclass has both score (float) and category (str)."""
        from metadata_enricher import FreshnessResult

        fr = FreshnessResult(score=0.85, category="fresh")
        assert isinstance(fr.score, float)
        assert isinstance(fr.category, str)


class TestFreshnessScore:
    """T077: Tests for calculate_freshness_score (loosened thresholds)."""

    def test_fresh_within_90_days(self) -> None:
        from metadata_enricher import MetadataEnricher

        me = MetadataEnricher()
        recent = (datetime.now() - timedelta(days=10)).isoformat()
        assert me.calculate_freshness_score(recent) == "fresh"

    def test_recent_365_to_730_days(self) -> None:
        from metadata_enricher import MetadataEnricher

        me = MetadataEnricher()
        date = (datetime.now() - timedelta(days=400)).isoformat()
        assert me.calculate_freshness_score(date) == "recent"

    def test_outdated_730_to_1460_days(self) -> None:
        from metadata_enricher import MetadataEnricher

        me = MetadataEnricher()
        date = (datetime.now() - timedelta(days=800)).isoformat()
        assert me.calculate_freshness_score(date) == "outdated"

    def test_archived_over_1460_days(self) -> None:
        from metadata_enricher import MetadataEnricher

        me = MetadataEnricher()
        date = (datetime.now() - timedelta(days=1500)).isoformat()
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
