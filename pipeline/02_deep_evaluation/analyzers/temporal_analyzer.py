"""
Temporal Analyzer - Zeitliche Aspekte und Aktualität

Analysiert:
- Aktualität der Inhalte (Freshness)
- Archivierte Inhalte
- Jahreszahlen-Referenzen
- Zeitkritische Inhalte
"""

import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Relative import für config
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import EvaluationConfig, get_config


@dataclass
class PageTemporalInfo:
    """Zeitliche Informationen einer Seite."""

    page_id: str
    last_modified: Optional[datetime]
    freshness_category: str  # current, recent, outdated, archived
    freshness_score: float  # 0.0 - 1.0
    is_archived: bool
    is_time_sensitive: bool
    year_references: List[int]
    oldest_year_ref: Optional[int]
    newest_year_ref: Optional[int]
    has_outdated_refs: bool
    rag_weight: float  # Empfohlene Gewichtung für RAG


@dataclass
class TemporalAnalysisResult:
    """Gesamtergebnis der zeitlichen Analyse."""

    total_pages: int = 0
    analysis_date: datetime = field(default_factory=datetime.now)
    freshness_distribution: Dict[str, int] = field(default_factory=dict)
    archived_count: int = 0
    time_sensitive_count: int = 0
    pages_with_outdated_refs: int = 0
    year_distribution: Dict[int, int] = field(default_factory=dict)
    avg_freshness_score: float = 0.0
    pages: List[PageTemporalInfo] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class TemporalAnalyzer:
    """Analysiert zeitliche Aspekte von Wiki-Inhalten."""

    def __init__(self, config: Optional[EvaluationConfig] = None):
        """
        Initialisiert den TemporalAnalyzer.

        Args:
            config: EvaluationConfig Instanz
        """
        self.config = config or get_config()
        self.raw_config = self.config.raw_config

        # Load temporal settings
        temporal_cfg = self.raw_config.get("TEMPORAL_ANALYSIS", {})
        self.archive_cfg = temporal_cfg.get("archive", {})
        self.freshness_cfg = temporal_cfg.get("freshness", {})
        self.year_cfg = temporal_cfg.get("year_detection", {})
        self.rag_cfg = temporal_cfg.get("rag_recommendations", {})

        # Current year
        self.current_year = self.year_cfg.get("current_year", datetime.now().year)

        # Freshness thresholds (in days)
        self.current_days = self.freshness_cfg.get("current_days", 90)
        self.recent_days = self.freshness_cfg.get("recent_days", 365)
        self.outdated_days = self.freshness_cfg.get("outdated_days", 730)

        # Time-sensitive patterns
        self.time_sensitive_patterns = [
            re.compile(p, re.IGNORECASE)
            for p in self.freshness_cfg.get("time_sensitive_patterns", [])
        ]

        # Year patterns
        self.year_patterns = [
            re.compile(p) for p in self.year_cfg.get("patterns", [r"\b20[0-9]{2}\b"])
        ]

        # RAG weights
        self.rag_weights = {
            "current": self.rag_cfg.get("current_weight", 1.0),
            "recent": self.rag_cfg.get("recent_weight", 0.9),
            "archived": self.rag_cfg.get("archived_weight", 0.5),
            "outdated": self.rag_cfg.get("outdated_weight", 0.3),
        }

        # Results
        self.result = TemporalAnalysisResult()

    def analyze(self) -> TemporalAnalysisResult:
        """
        Führt die vollständige zeitliche Analyse durch.

        Returns:
            TemporalAnalysisResult mit allen Analysen
        """
        print("\n[TemporalAnalyzer] Starte Analyse...")

        # Load all pages with metadata
        pages = self._load_pages()
        print(f"  Analysiere {len(pages)} Seiten...")

        for page_data in pages:
            temporal_info = self._analyze_page(page_data)
            self.result.pages.append(temporal_info)
            self._update_stats(temporal_info)

        # Calculate summary
        self._calculate_summary()

        # Generate recommendations
        self._generate_recommendations()

        print(f"  Current: {self.result.freshness_distribution.get('current', 0)}")
        print(f"  Recent: {self.result.freshness_distribution.get('recent', 0)}")
        print(f"  Outdated: {self.result.freshness_distribution.get('outdated', 0)}")
        print(f"  Archived: {self.result.archived_count}")

        return self.result

    def _load_pages(self) -> List[Dict[str, Any]]:
        """Lädt alle Seiten mit Metadaten und Inhalt."""
        pages = []
        content_dir = self.config.page_content_dir
        metadata_dir = self.config.page_metadata_dir

        if not content_dir or not content_dir.exists():
            return pages

        for content_file in content_dir.glob("*.txt"):
            page_id = content_file.stem

            try:
                content = content_file.read_text(encoding="utf-8")
            except Exception:
                continue

            # Load metadata
            metadata = {}
            if metadata_dir:
                meta_file = metadata_dir / f"{page_id}_info.json"
                if meta_file.exists():
                    try:
                        metadata = json.loads(meta_file.read_text(encoding="utf-8"))
                    except Exception:
                        pass

            # Use real page ID from metadata if available
            real_page_id = metadata.get("id", page_id)

            pages.append({"page_id": real_page_id, "content": content, "metadata": metadata})

        return pages

    def _analyze_page(self, page_data: Dict[str, Any]) -> PageTemporalInfo:
        """
        Analysiert die zeitlichen Aspekte einer Seite.

        Args:
            page_data: Dict mit page_id, content, metadata

        Returns:
            PageTemporalInfo Objekt
        """
        page_id = page_data["page_id"]
        content = page_data["content"]
        metadata = page_data["metadata"]

        # Extract last modified
        last_modified = self._parse_last_modified(metadata)

        # Check if archived
        is_archived = self._is_archived(page_id)

        # Check if time-sensitive
        is_time_sensitive = self._is_time_sensitive(page_id, content)

        # Find year references
        year_refs = self._find_year_references(content)
        oldest_ref = min(year_refs) if year_refs else None
        newest_ref = max(year_refs) if year_refs else None

        # Check for outdated references
        has_outdated_refs = self._has_outdated_references(year_refs)

        # Determine freshness category and score
        freshness_category, freshness_score = self._calculate_freshness(
            last_modified, is_archived, year_refs
        )

        # Determine RAG weight
        rag_weight = self._calculate_rag_weight(freshness_category, is_archived, has_outdated_refs)

        return PageTemporalInfo(
            page_id=page_id,
            last_modified=last_modified,
            freshness_category=freshness_category,
            freshness_score=freshness_score,
            is_archived=is_archived,
            is_time_sensitive=is_time_sensitive,
            year_references=year_refs,
            oldest_year_ref=oldest_ref,
            newest_year_ref=newest_ref,
            has_outdated_refs=has_outdated_refs,
            rag_weight=rag_weight,
        )

    def _parse_last_modified(self, metadata: Dict) -> Optional[datetime]:
        """Parst das Änderungsdatum aus den Metadaten."""
        # Try different field names
        for field_name in ["last_modified", "lastModified", "modified", "date"]:
            if field_name in metadata:
                try:
                    value = metadata[field_name]
                    if isinstance(value, (int, float)):
                        # Unix timestamp
                        return datetime.fromtimestamp(value)
                    elif isinstance(value, str):
                        # Try common formats
                        for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d.%m.%Y"]:
                            try:
                                return datetime.strptime(value[:19], fmt)
                            except ValueError:
                                continue
                except Exception:
                    pass
        return None

    def _is_archived(self, page_id: str) -> bool:
        """Prüft ob eine Seite archiviert ist."""
        archive_namespace = self.archive_cfg.get("namespace", "archive")
        return page_id.startswith(f"{archive_namespace}:")

    def _is_time_sensitive(self, page_id: str, content: str) -> bool:
        """Prüft ob eine Seite zeitkritische Inhalte hat."""
        # Check page_id
        page_id_lower = page_id.lower()
        for pattern in self.time_sensitive_patterns:
            if pattern.search(page_id_lower):
                return True

        # Check content (first 500 chars)
        content_start = content[:500].lower()
        return any(pattern.search(content_start) for pattern in self.time_sensitive_patterns)

    def _find_year_references(self, content: str) -> List[int]:
        """Findet alle Jahreszahlen im Inhalt."""
        years = set()

        for pattern in self.year_patterns:
            matches = pattern.findall(content)
            for match in matches:
                try:
                    # Handle different match formats
                    if isinstance(match, tuple):
                        match = match[0]

                    # Extract year from various formats
                    year_str = re.search(r"20[0-9]{2}", str(match))
                    if year_str:
                        year = int(year_str.group())
                        if 2000 <= year <= 2100:  # Plausibility check
                            years.add(year)
                except (ValueError, AttributeError):
                    pass

        return sorted(years)

    def _has_outdated_references(self, years: List[int]) -> bool:
        """Prüft ob veraltete Jahresreferenzen vorhanden sind."""
        if not years:
            return False

        # Consider references more than 2 years old as potentially outdated
        outdated_threshold = self.current_year - 2

        return any(year < outdated_threshold for year in years)

    def _calculate_freshness(
        self, last_modified: Optional[datetime], is_archived: bool, year_refs: List[int]
    ) -> Tuple[str, float]:
        """Berechnet Freshness-Kategorie und Score."""
        now = datetime.now()

        # Archived content
        if is_archived:
            return "archived", 0.3

        # Based on last modified date
        if last_modified:
            age_days = (now - last_modified).days

            if age_days <= self.current_days:
                return "current", 1.0
            elif age_days <= self.recent_days:
                # Linear interpolation between 1.0 and 0.7
                score = (
                    1.0
                    - (age_days - self.current_days) / (self.recent_days - self.current_days) * 0.3
                )
                return "recent", score
            elif age_days <= self.outdated_days:
                # Linear interpolation between 0.7 and 0.4
                score = (
                    0.7
                    - (age_days - self.recent_days) / (self.outdated_days - self.recent_days) * 0.3
                )
                return "outdated", score
            else:
                return "outdated", 0.3

        # Fallback: use year references
        if year_refs:
            newest = max(year_refs)
            if newest >= self.current_year:
                return "current", 0.8
            elif newest >= self.current_year - 1:
                return "recent", 0.6
            else:
                return "outdated", 0.4

        # No temporal information
        return "unknown", 0.5

    def _calculate_rag_weight(
        self, freshness_category: str, is_archived: bool, has_outdated_refs: bool
    ) -> float:
        """Berechnet die empfohlene RAG-Gewichtung."""
        base_weight = self.rag_weights.get(freshness_category, 0.5)

        # Reduce weight for archived content
        if is_archived:
            base_weight = min(base_weight, self.rag_weights.get("archived", 0.5))

        # Reduce weight for outdated references
        if has_outdated_refs:
            base_weight *= 0.9

        return round(base_weight, 2)

    def _update_stats(self, info: PageTemporalInfo):
        """Aktualisiert globale Statistiken."""
        self.result.total_pages += 1

        # Freshness distribution
        cat = info.freshness_category
        self.result.freshness_distribution[cat] = self.result.freshness_distribution.get(cat, 0) + 1

        # Archived
        if info.is_archived:
            self.result.archived_count += 1

        # Time sensitive
        if info.is_time_sensitive:
            self.result.time_sensitive_count += 1

        # Outdated refs
        if info.has_outdated_refs:
            self.result.pages_with_outdated_refs += 1

        # Year distribution
        for year in info.year_references:
            self.result.year_distribution[year] = self.result.year_distribution.get(year, 0) + 1

    def _calculate_summary(self):
        """Berechnet Zusammenfassungsstatistiken."""
        if not self.result.pages:
            return

        # Average freshness
        total_score = sum(p.freshness_score for p in self.result.pages)
        self.result.avg_freshness_score = total_score / len(self.result.pages)

    def _generate_recommendations(self):
        """Generiert Empfehlungen basierend auf der Analyse."""
        recommendations = []

        # Archived content
        archived_pct = (self.result.archived_count / max(self.result.total_pages, 1)) * 100
        if archived_pct > 5:
            recommendations.append(
                f"Archivierte Inhalte ({archived_pct:.1f}%): "
                "Separates Dataset oder niedrigere Gewichtung empfohlen"
            )

        # Outdated content
        outdated = self.result.freshness_distribution.get("outdated", 0)
        if outdated > 20:
            recommendations.append(
                f"Veraltete Inhalte ({outdated} Seiten): "
                "Prüfen ob Aktualisierung nötig oder Gewichtung anpassen"
            )

        # Time-sensitive content
        if self.result.time_sensitive_count > 10:
            recommendations.append(
                f"Zeitkritische Inhalte ({self.result.time_sensitive_count} Seiten): "
                "Regelmäßige Re-Indexierung empfohlen"
            )

        # Old year references
        outdated_refs = self.result.pages_with_outdated_refs
        if outdated_refs > self.result.total_pages * 0.2:
            recommendations.append(
                f"Veraltete Jahresreferenzen ({outdated_refs} Seiten): "
                "Metadata-Enrichment mit Freshness-Tag empfohlen"
            )

        self.result.recommendations = recommendations

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert Ergebnisse zu Dictionary für JSON-Export."""
        return {
            "summary": {
                "total_pages": self.result.total_pages,
                "analysis_date": self.result.analysis_date.isoformat(),
                "avg_freshness_score": round(self.result.avg_freshness_score, 3),
                "archived_count": self.result.archived_count,
                "time_sensitive_count": self.result.time_sensitive_count,
                "pages_with_outdated_refs": self.result.pages_with_outdated_refs,
            },
            "freshness_distribution": self.result.freshness_distribution,
            "year_distribution": dict(
                sorted(self.result.year_distribution.items(), key=lambda x: x[0], reverse=True)
            ),
            "recommendations": self.result.recommendations,
            "archived_pages": [
                {
                    "page_id": p.page_id,
                    "freshness_score": round(p.freshness_score, 2),
                    "rag_weight": p.rag_weight,
                }
                for p in self.result.pages
                if p.is_archived
            ],
            "outdated_pages": [
                {
                    "page_id": p.page_id,
                    "freshness_score": round(p.freshness_score, 2),
                    "oldest_year": p.oldest_year_ref,
                    "rag_weight": p.rag_weight,
                }
                for p in sorted(self.result.pages, key=lambda x: x.freshness_score)
                if p.freshness_category == "outdated"
            ][:20],
            "time_sensitive_pages": [p.page_id for p in self.result.pages if p.is_time_sensitive],
        }


# =============================================================================
# Test
# =============================================================================

if __name__ == "__main__":
    analyzer = TemporalAnalyzer()
    result = analyzer.analyze()

    print("\n" + "=" * 60)
    print("  TEMPORAL ANALYSIS RESULTS")
    print("=" * 60)
    print(f"\n  Total Pages: {result.total_pages}")
    print(f"  Avg Freshness: {result.avg_freshness_score:.2f}")

    print(f"\n  Freshness Distribution:")
    for cat, count in result.freshness_distribution.items():
        pct = (count / result.total_pages * 100) if result.total_pages else 0
        print(f"    {cat}: {count} ({pct:.1f}%)")

    print(f"\n  Year References (Top 5):")
    for year, count in sorted(result.year_distribution.items(), key=lambda x: -x[1])[:5]:
        print(f"    {year}: {count} references")

    print(f"\n  Recommendations:")
    for rec in result.recommendations:
        print(f"    - {rec}")
