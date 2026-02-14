"""T068: Tests for MetadataEnricher freshness_score and access_level."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest


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
