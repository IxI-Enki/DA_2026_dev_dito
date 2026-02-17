"""
RAG Readiness Checker - Eignung für RAG-Pipeline

Prüft:
- Chunking-Eignung (Struktur, Länge)
- Noise-Level (Wiki-Syntax, Boilerplate)
- Metadaten-Qualität
- Link-Integrität
"""

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Relative import für config
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import EvaluationConfig, get_config


@dataclass
class PageRAGReadiness:
    """RAG-Eignung einer einzelnen Seite."""

    page_id: str
    readiness_score: float  # 0.0 - 1.0
    chunking_score: float
    noise_score: float  # Lower is better (inverted for final score)
    metadata_score: float
    structure_score: float
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RAGReadinessResult:
    """Gesamtergebnis der RAG-Readiness-Analyse."""

    total_pages: int = 0
    avg_readiness_score: float = 0.0
    readiness_distribution: Dict[str, int] = field(default_factory=dict)
    common_issues: Dict[str, int] = field(default_factory=dict)
    noise_statistics: Dict[str, Any] = field(default_factory=dict)
    structure_statistics: Dict[str, Any] = field(default_factory=dict)
    pages: List[PageRAGReadiness] = field(default_factory=list)
    preprocessing_recommendations: List[str] = field(default_factory=list)


class RAGReadinessChecker:
    """Prüft die Eignung von Inhalten für RAG-Pipelines."""

    def __init__(self, config: EvaluationConfig | None = None):
        """
        Initialisiert den RAGReadinessChecker.

        Args:
            config: EvaluationConfig Instanz
        """
        self.config = config or get_config()
        self.raw_config = self.config.raw_config

        # Load RAG readiness settings
        rag_cfg = self.raw_config.get("RAG_READINESS", {})
        self.chunking_cfg = rag_cfg.get("chunking", {})
        self.noise_cfg = rag_cfg.get("noise_detection", {})
        self.metadata_cfg = rag_cfg.get("metadata_requirements", {})
        self.link_cfg = rag_cfg.get("link_quality", {})

        # Compile patterns
        self._compile_patterns()

        # Results
        self.result = RAGReadinessResult()

    def _compile_patterns(self):
        """Kompiliert Regex-Patterns für Performance."""
        # Removable syntax patterns
        removable = self.noise_cfg.get("removable_syntax", [])
        self.removable_patterns = [re.compile(p, re.IGNORECASE) for p in removable]

        # Boilerplate patterns
        boilerplate = self.noise_cfg.get("boilerplate_patterns", [])
        self.boilerplate_patterns = [re.compile(p, re.MULTILINE) for p in boilerplate]

        # Structure indicators (DokuWiki syntax)
        self.headline_pattern = re.compile(r"^={2,6}.+={2,6}$", re.MULTILINE)
        self.list_pattern = re.compile(r"^[\s]*[\*\-]\s+", re.MULTILINE)
        self.table_pattern = re.compile(r"^\|.*\|$", re.MULTILINE)
        self.link_pattern = re.compile(r"\[\[([^\]]+)\]\]")
        self.media_pattern = re.compile(r"\{\{([^}]+)\}\}")
        self.code_block_pattern = re.compile(r"<code.*?>.*?</code>", re.DOTALL)

    def analyze(self) -> RAGReadinessResult:
        """
        Führt die vollständige RAG-Readiness-Analyse durch.

        Returns:
            RAGReadinessResult mit allen Analysen
        """
        print("\n[RAGReadinessChecker] Starte Analyse...")

        # Load and analyze all pages
        pages = self._load_pages()
        print(f"  Analysiere {len(pages)} Seiten...")

        for page_data in pages:
            readiness = self._analyze_page(page_data)
            self.result.pages.append(readiness)
            self._update_stats(readiness)

        # Calculate summary
        self._calculate_summary()

        # Generate preprocessing recommendations
        self._generate_recommendations()

        print(f"  Durchschnittliche Readiness: {self.result.avg_readiness_score:.2f}")
        print(f"  High Readiness: {self.result.readiness_distribution.get('high', 0)}")
        print(f"  Low Readiness: {self.result.readiness_distribution.get('low', 0)}")

        return self.result

    def _load_pages(self) -> List[Dict[str, Any]]:
        """Lädt alle Seiten für die Analyse."""
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

    def _analyze_page(self, page_data: Dict[str, Any]) -> PageRAGReadiness:
        """
        Analysiert die RAG-Eignung einer Seite.

        Args:
            page_data: Dict mit page_id, content, metadata

        Returns:
            PageRAGReadiness Objekt
        """
        page_id = page_data["page_id"]
        content = page_data["content"]
        metadata = page_data["metadata"]

        issues = []
        recommendations = []

        # Analyze structure
        structure_score, structure_stats = self._analyze_structure(content)

        # Analyze noise
        noise_score, noise_stats = self._analyze_noise(content)

        # Analyze chunking suitability
        chunking_score, chunking_stats = self._analyze_chunking(content, structure_stats)

        # Analyze metadata
        metadata_score, meta_issues = self._analyze_metadata(metadata)

        # Collect issues
        if structure_score < 0.5:
            issues.append("Wenig Struktur (keine Überschriften)")
            recommendations.append("Manuelle Strukturierung oder Absatz-Chunking")

        if noise_score > 0.3:
            issues.append(f"Hoher Noise-Anteil ({noise_score:.0%})")
            recommendations.append("Wiki-Syntax bereinigen vor Indexierung")

        if chunking_score < 0.5:
            issues.append("Chunking-Herausforderung")
            recommendations.append("Angepasste Chunk-Größe empfohlen")

        if meta_issues:
            issues.extend(meta_issues)

        # Calculate overall readiness score
        # Noise is inverted (high noise = low score)
        adjusted_noise = 1.0 - noise_score
        readiness_score = (
            structure_score * 0.25
            + adjusted_noise * 0.30
            + chunking_score * 0.30
            + metadata_score * 0.15
        )

        return PageRAGReadiness(
            page_id=page_id,
            readiness_score=readiness_score,
            chunking_score=chunking_score,
            noise_score=noise_score,
            metadata_score=metadata_score,
            structure_score=structure_score,
            issues=issues,
            recommendations=recommendations,
            stats={"structure": structure_stats, "noise": noise_stats, "chunking": chunking_stats},
        )

    def _analyze_structure(self, content: str) -> Tuple[float, Dict]:
        """Analysiert die Struktur des Inhalts."""
        stats = {
            "headlines": len(self.headline_pattern.findall(content)),
            "lists": len(self.list_pattern.findall(content)),
            "tables": len(self.table_pattern.findall(content)),
            "links": len(self.link_pattern.findall(content)),
            "media_refs": len(self.media_pattern.findall(content)),
            "code_blocks": len(self.code_block_pattern.findall(content)),
            "paragraphs": content.count("\n\n") + 1,
            "char_count": len(content),
            "line_count": content.count("\n") + 1,
        }

        # Score calculation
        score = 0.0

        # Headlines are good for chunking
        if stats["headlines"] > 0:
            score += 0.4
        elif stats["paragraphs"] > 3:
            score += 0.2

        # Lists indicate structured content
        if stats["lists"] > 0:
            score += 0.2

        # Reasonable length
        if 500 <= stats["char_count"] <= 10000:
            score += 0.3
        elif stats["char_count"] > 100:
            score += 0.2

        # Tables can be tricky but indicate data
        if stats["tables"] > 0:
            score += 0.1

        return min(score, 1.0), stats

    def _analyze_noise(self, content: str) -> Tuple[float, Dict]:
        """Analysiert den Noise-Anteil im Inhalt."""
        stats = {
            "removable_matches": 0,
            "boilerplate_matches": 0,
            "empty_lines_ratio": 0.0,
            "short_lines_ratio": 0.0,
            "wiki_syntax_chars": 0,
        }

        original_len = len(content)
        if original_len == 0:
            return 0.0, stats

        # Count removable patterns
        for pattern in self.removable_patterns:
            matches = pattern.findall(content)
            stats["removable_matches"] += len(matches)

        # Count boilerplate
        for pattern in self.boilerplate_patterns:
            matches = pattern.findall(content)
            stats["boilerplate_matches"] += len(matches)

        # Count wiki syntax characters
        wiki_chars = content.count("{{") + content.count("}}")
        wiki_chars += content.count("[[") + content.count("]]")
        wiki_chars += content.count("====") + content.count("===")
        wiki_chars += content.count("<code") + content.count("</code>")
        wiki_chars += content.count("<wrap") + content.count("</wrap>")
        stats["wiki_syntax_chars"] = wiki_chars

        # Analyze lines
        lines = content.split("\n")
        non_empty = [l for l in lines if l.strip()]
        if lines:
            stats["empty_lines_ratio"] = 1 - (len(non_empty) / len(lines))

        short_lines = [l for l in non_empty if len(l.strip()) < 20]
        if non_empty:
            stats["short_lines_ratio"] = len(short_lines) / len(non_empty)

        # Calculate noise score
        noise_score = 0.0

        # Removable content
        noise_score += min(stats["removable_matches"] * 0.05, 0.2)

        # Empty lines ratio
        if stats["empty_lines_ratio"] > 0.3:
            noise_score += 0.1

        # Short lines ratio
        if stats["short_lines_ratio"] > 0.5:
            noise_score += 0.1

        # Wiki syntax density
        syntax_ratio = wiki_chars / max(original_len, 1)
        noise_score += min(syntax_ratio * 2, 0.3)

        return min(noise_score, 1.0), stats

    def _analyze_chunking(self, content: str, structure_stats: Dict) -> Tuple[float, Dict]:
        """Analysiert die Chunking-Eignung."""
        ideal_min = self.chunking_cfg.get("ideal_paragraph_length", {}).get("min", 100)
        ideal_max = self.chunking_cfg.get("ideal_paragraph_length", {}).get("max", 500)

        # Split by double newlines (paragraphs)
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

        stats = {
            "paragraph_count": len(paragraphs),
            "avg_paragraph_length": 0,
            "paragraphs_in_ideal_range": 0,
            "too_short": 0,
            "too_long": 0,
            "has_natural_breaks": structure_stats.get("headlines", 0) > 0,
        }

        if paragraphs:
            lengths = [len(p) for p in paragraphs]
            stats["avg_paragraph_length"] = sum(lengths) / len(lengths)

            for length in lengths:
                if ideal_min <= length <= ideal_max:
                    stats["paragraphs_in_ideal_range"] += 1
                elif length < ideal_min:
                    stats["too_short"] += 1
                else:
                    stats["too_long"] += 1

        # Score calculation
        score = 0.0

        # Natural breaks (headlines)
        if stats["has_natural_breaks"]:
            score += 0.4

        # Ideal paragraph distribution
        if stats["paragraph_count"] > 0:
            ideal_ratio = stats["paragraphs_in_ideal_range"] / stats["paragraph_count"]
            score += ideal_ratio * 0.4

        # Reasonable paragraph count
        if 3 <= stats["paragraph_count"] <= 20:
            score += 0.2
        elif stats["paragraph_count"] > 0:
            score += 0.1

        return min(score, 1.0), stats

    def _analyze_metadata(self, metadata: Dict) -> Tuple[float, List[str]]:
        """Analysiert die Metadaten-Qualität."""
        required = self.metadata_cfg.get("required", ["title", "namespace", "last_modified"])
        optional = self.metadata_cfg.get("optional", ["author", "revision"])

        issues = []
        score = 0.0

        # Check required fields
        required_found = 0
        for field_name in required:
            if field_name in metadata and metadata[field_name]:
                required_found += 1
            else:
                issues.append(f"Fehlendes Metadatum: {field_name}")

        if required:
            score += (required_found / len(required)) * 0.7

        # Check optional fields
        optional_found = sum(1 for f in optional if f in metadata and metadata[f])
        if optional:
            score += (optional_found / len(optional)) * 0.3

        return score, issues

    def _update_stats(self, readiness: PageRAGReadiness):
        """Aktualisiert globale Statistiken."""
        self.result.total_pages += 1

        # Track common issues
        for issue in readiness.issues:
            # Simplify issue for grouping
            simplified = issue.split("(")[0].strip()
            self.result.common_issues[simplified] = self.result.common_issues.get(simplified, 0) + 1

    def _calculate_summary(self):
        """Berechnet Zusammenfassungsstatistiken."""
        if not self.result.pages:
            return

        # Average readiness
        total_score = sum(p.readiness_score for p in self.result.pages)
        self.result.avg_readiness_score = total_score / len(self.result.pages)

        # Distribution
        for page in self.result.pages:
            if page.readiness_score >= 0.7:
                bucket = "high"
            elif page.readiness_score >= 0.4:
                bucket = "medium"
            else:
                bucket = "low"
            self.result.readiness_distribution[bucket] = (
                self.result.readiness_distribution.get(bucket, 0) + 1
            )

        # Aggregate noise stats
        all_noise = [p.noise_score for p in self.result.pages]
        self.result.noise_statistics = {
            "avg_noise": sum(all_noise) / len(all_noise) if all_noise else 0,
            "max_noise": max(all_noise) if all_noise else 0,
            "pages_with_high_noise": sum(1 for n in all_noise if n > 0.3),
        }

        # Aggregate structure stats
        all_headlines = [
            p.stats.get("structure", {}).get("headlines", 0) for p in self.result.pages
        ]
        self.result.structure_statistics = {
            "pages_with_headlines": sum(1 for h in all_headlines if h > 0),
            "avg_headlines": sum(all_headlines) / len(all_headlines) if all_headlines else 0,
        }

    def _generate_recommendations(self):
        """Generiert globale Preprocessing-Empfehlungen."""
        recommendations = []

        # Noise recommendations
        if self.result.noise_statistics.get("pages_with_high_noise", 0) > 10:
            recommendations.append(
                "Wiki-Syntax-Bereinigung empfohlen: "
                f"{self.result.noise_statistics['pages_with_high_noise']} Seiten mit hohem Noise"
            )

        # Structure recommendations
        pages_without_headlines = self.result.total_pages - self.result.structure_statistics.get(
            "pages_with_headlines", 0
        )
        if pages_without_headlines > self.result.total_pages * 0.3:
            recommendations.append(
                f"Absatz-basiertes Chunking für {pages_without_headlines} Seiten ohne Überschriften"
            )

        # Common issues recommendations
        for issue, count in sorted(self.result.common_issues.items(), key=lambda x: -x[1])[:5]:
            if count > 5:
                recommendations.append(f"Häufiges Problem ({count}x): {issue}")

        self.result.preprocessing_recommendations = recommendations

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert Ergebnisse zu Dictionary für JSON-Export."""
        return {
            "summary": {
                "total_pages": self.result.total_pages,
                "avg_readiness_score": round(self.result.avg_readiness_score, 3),
                "readiness_distribution": self.result.readiness_distribution,
            },
            "noise_statistics": self.result.noise_statistics,
            "structure_statistics": self.result.structure_statistics,
            "common_issues": dict(
                sorted(self.result.common_issues.items(), key=lambda x: -x[1])[:10]
            ),
            "preprocessing_recommendations": self.result.preprocessing_recommendations,
            "low_readiness_pages": [
                {
                    "page_id": p.page_id,
                    "readiness_score": round(p.readiness_score, 2),
                    "issues": p.issues,
                    "recommendations": p.recommendations,
                }
                for p in sorted(self.result.pages, key=lambda x: x.readiness_score)[:20]
            ],
            "high_readiness_pages": [
                {"page_id": p.page_id, "readiness_score": round(p.readiness_score, 2)}
                for p in sorted(self.result.pages, key=lambda x: -x.readiness_score)[:10]
            ],
        }


# =============================================================================
# Test
# =============================================================================

if __name__ == "__main__":
    checker = RAGReadinessChecker()
    result = checker.analyze()

    print("\n" + "=" * 60)
    print("  RAG READINESS RESULTS")
    print("=" * 60)
    print(f"\n  Total Pages: {result.total_pages}")
    print(f"  Avg Readiness: {result.avg_readiness_score:.2f}")

    print(f"\n  Readiness Distribution:")
    for level, count in result.readiness_distribution.items():
        pct = (count / result.total_pages * 100) if result.total_pages else 0
        print(f"    {level}: {count} ({pct:.1f}%)")

    print(f"\n  Common Issues:")
    for issue, count in sorted(result.common_issues.items(), key=lambda x: -x[1])[:5]:
        print(f"    - {issue}: {count}")

    print(f"\n  Recommendations:")
    for rec in result.preprocessing_recommendations:
        print(f"    - {rec}")
