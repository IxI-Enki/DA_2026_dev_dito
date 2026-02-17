"""
Content Classifier - Kategorisierung der Wiki-Inhalte

Analysiert und klassifiziert:
- Namespaces (teacher/public)
- Inhaltstypen (organizational, educational, etc.)
- Seitentypen (form, procedure, reference, news)
"""

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# Relative import für config
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import EvaluationConfig, get_config


@dataclass
class PageClassification:
    """Klassifizierung einer einzelnen Seite."""

    page_id: str
    namespace: str
    is_teacher_restricted: bool
    content_type: str
    page_type: str
    char_count: int
    word_count: int
    has_media: bool
    media_count: int
    link_count: int
    is_archived: bool


@dataclass
class ClassificationResult:
    """Gesamtergebnis der Content-Klassifizierung."""

    total_pages: int = 0
    pages_by_namespace: Dict[str, int] = field(default_factory=dict)
    pages_by_content_type: Dict[str, int] = field(default_factory=dict)
    pages_by_page_type: Dict[str, int] = field(default_factory=dict)
    teacher_restricted_count: int = 0
    public_count: int = 0
    archived_count: int = 0
    pages: List[PageClassification] = field(default_factory=list)
    namespace_details: Dict[str, Dict] = field(default_factory=dict)


class ContentClassifier:
    """Klassifiziert Wiki-Inhalte nach verschiedenen Kriterien."""

    def __init__(self, config: Optional[EvaluationConfig] = None):
        """
        Initialisiert den ContentClassifier.

        Args:
            config: EvaluationConfig Instanz
        """
        self.config = config or get_config()
        self.raw_config = self.config.raw_config

        # Load classification settings
        content_cfg = self.raw_config.get("CONTENT_CLASSIFICATION", {})
        self.teacher_namespaces = content_cfg.get("namespaces", {}).get(
            "teacher_restricted", ["teacher"]
        )
        self.public_namespaces = content_cfg.get("namespaces", {}).get("public", [])
        self.content_types = content_cfg.get("content_types", {})
        self.page_type_patterns = content_cfg.get("page_type_patterns", {})

        # Results
        self.result = ClassificationResult()

    def analyze(self) -> ClassificationResult:
        """
        Führt die vollständige Content-Klassifizierung durch.

        Returns:
            ClassificationResult mit allen Klassifizierungen
        """
        print("\n[ContentClassifier] Starte Analyse...")

        # Load all pages
        pages = self._load_pages()
        print(f"  Gefunden: {len(pages)} Seiten")

        # Classify each page
        for page_data in pages:
            classification = self._classify_page(page_data)
            self._update_stats(classification)

        print(f"  Teacher-restricted: {self.result.teacher_restricted_count}")
        print(f"  Public: {self.result.public_count}")
        print(f"  Archived: {self.result.archived_count}")
        print(f"  Namespaces: {len(self.result.pages_by_namespace)}")

        return self.result

    def _load_pages(self) -> List[Dict[str, Any]]:
        """Lädt alle Seiten mit Content und Metadaten."""
        pages = []

        content_dir = self.config.page_content_dir
        metadata_dir = self.config.page_metadata_dir
        links_dir = self.config.page_links_dir

        if not content_dir or not content_dir.exists():
            print(f"  WARNUNG: Content-Verzeichnis nicht gefunden: {content_dir}")
            return pages

        # Iterate through all content files
        for content_file in content_dir.glob("*.txt"):
            page_id = content_file.stem

            # Load content
            try:
                with open(content_file, encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                print(f"  WARNUNG: Konnte {page_id} nicht lesen: {e}")
                continue

            # Load metadata if available
            metadata = {}
            if metadata_dir:
                meta_file = metadata_dir / f"{page_id}_info.json"
                if meta_file.exists():
                    try:
                        with open(meta_file, encoding="utf-8") as f:
                            metadata = json.load(f)
                    except Exception:
                        pass

            # Use real page ID from metadata if available, else fallback to filename
            real_page_id = metadata.get("id", page_id)

            # Load links if available
            links = []
            if links_dir:
                links_file = links_dir / f"{page_id}_links.json"
                if links_file.exists():
                    try:
                        with open(links_file, encoding="utf-8") as f:
                            links_data = json.load(f)
                            links = links_data.get("internal", []) + links_data.get("external", [])
                    except Exception:
                        pass

            pages.append(
                {"page_id": real_page_id, "content": content, "metadata": metadata, "links": links}
            )

        return pages

    def _classify_page(self, page_data: Dict[str, Any]) -> PageClassification:
        """
        Klassifiziert eine einzelne Seite.

        Args:
            page_data: Dict mit page_id, content, metadata, links

        Returns:
            PageClassification Objekt
        """
        page_id = page_data["page_id"]
        content = page_data["content"]
        page_data["metadata"]
        links = page_data["links"]

        # Extract namespace from page_id (format: namespace:subns:page or namespace:page)
        namespace = self._extract_namespace(page_id)

        # Determine access level
        is_teacher_restricted = namespace in self.teacher_namespaces

        # Determine content type
        content_type = self._determine_content_type(namespace)

        # Determine page type
        page_type = self._determine_page_type(page_id, content)

        # Count content
        char_count = len(content)
        word_count = len(content.split())

        # Check for media references
        media_refs = self._count_media_refs(content)

        # Check if archived
        is_archived = namespace == "archive" or page_id.startswith("archive:")

        return PageClassification(
            page_id=page_id,
            namespace=namespace,
            is_teacher_restricted=is_teacher_restricted,
            content_type=content_type,
            page_type=page_type,
            char_count=char_count,
            word_count=word_count,
            has_media=media_refs > 0,
            media_count=media_refs,
            link_count=len(links),
            is_archived=is_archived,
        )

    def _extract_namespace(self, page_id: str) -> str:
        """Extrahiert den Top-Level Namespace aus der Page-ID."""
        # Handle different formats:
        # "namespace:page" -> "namespace"
        # "namespace:subns:page" -> "namespace"
        # "page" -> "root"

        if ":" in page_id:
            return page_id.split(":")[0]
        return "root"

    def _determine_content_type(self, namespace: str) -> str:
        """Bestimmt den Inhaltstyp basierend auf dem Namespace."""
        for content_type, namespaces in self.content_types.items():
            if namespace in namespaces:
                return content_type
        return "other"

    def _determine_page_type(self, page_id: str, content: str) -> str:
        """Bestimmt den Seitentyp basierend auf Patterns."""
        page_id_lower = page_id.lower()
        content_lower = content[:1000].lower()  # Nur Anfang prüfen

        for page_type, config in self.page_type_patterns.items():
            patterns = config.get("patterns", [])
            for pattern in patterns:
                if re.search(pattern, page_id_lower) or re.search(pattern, content_lower):
                    return page_type

        return "general"

    def _count_media_refs(self, content: str) -> int:
        """Zählt Media-Referenzen im Content."""
        # DokuWiki media syntax: {{media:file.ext}} or {{:media:file.ext}}
        pattern = r"\{\{[^}]+\}\}"
        matches = re.findall(pattern, content)
        return len(matches)

    def _update_stats(self, classification: PageClassification):
        """Aktualisiert die Statistiken mit einer neuen Klassifizierung."""
        self.result.total_pages += 1
        self.result.pages.append(classification)

        # Namespace stats
        ns = classification.namespace
        self.result.pages_by_namespace[ns] = self.result.pages_by_namespace.get(ns, 0) + 1

        # Content type stats
        ct = classification.content_type
        self.result.pages_by_content_type[ct] = self.result.pages_by_content_type.get(ct, 0) + 1

        # Page type stats
        pt = classification.page_type
        self.result.pages_by_page_type[pt] = self.result.pages_by_page_type.get(pt, 0) + 1

        # Access level
        if classification.is_teacher_restricted:
            self.result.teacher_restricted_count += 1
        else:
            self.result.public_count += 1

        # Archived
        if classification.is_archived:
            self.result.archived_count += 1

        # Namespace details
        if ns not in self.result.namespace_details:
            self.result.namespace_details[ns] = {
                "page_count": 0,
                "total_chars": 0,
                "total_words": 0,
                "media_refs": 0,
                "avg_chars": 0,
                "is_restricted": classification.is_teacher_restricted,
            }

        details = self.result.namespace_details[ns]
        details["page_count"] += 1
        details["total_chars"] += classification.char_count
        details["total_words"] += classification.word_count
        details["media_refs"] += classification.media_count
        details["avg_chars"] = details["total_chars"] // details["page_count"]

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert Ergebnisse zu Dictionary für JSON-Export."""
        return {
            "summary": {
                "total_pages": self.result.total_pages,
                "teacher_restricted": self.result.teacher_restricted_count,
                "public": self.result.public_count,
                "archived": self.result.archived_count,
                "namespaces": len(self.result.pages_by_namespace),
            },
            "by_namespace": self.result.pages_by_namespace,
            "by_content_type": self.result.pages_by_content_type,
            "by_page_type": self.result.pages_by_page_type,
            "namespace_details": self.result.namespace_details,
            "pages": [
                {
                    "page_id": p.page_id,
                    "namespace": p.namespace,
                    "is_teacher_restricted": p.is_teacher_restricted,
                    "content_type": p.content_type,
                    "page_type": p.page_type,
                    "char_count": p.char_count,
                    "word_count": p.word_count,
                    "has_media": p.has_media,
                    "media_count": p.media_count,
                    "is_archived": p.is_archived,
                }
                for p in self.result.pages
            ],
        }


# =============================================================================
# Test
# =============================================================================

if __name__ == "__main__":
    classifier = ContentClassifier()
    result = classifier.analyze()

    print("\n" + "=" * 60)
    print("  CLASSIFICATION RESULTS")
    print("=" * 60)
    print(f"\n  Total Pages: {result.total_pages}")
    print(f"\n  By Namespace:")
    for ns, count in sorted(result.pages_by_namespace.items(), key=lambda x: -x[1]):
        restricted = " [TEACHER]" if ns in classifier.teacher_namespaces else ""
        print(f"    {ns}: {count}{restricted}")

    print(f"\n  By Content Type:")
    for ct, count in sorted(result.pages_by_content_type.items(), key=lambda x: -x[1]):
        print(f"    {ct}: {count}")

    print(f"\n  By Page Type:")
    for pt, count in sorted(result.pages_by_page_type.items(), key=lambda x: -x[1]):
        print(f"    {pt}: {count}")
