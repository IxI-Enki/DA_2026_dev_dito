"""
Format & Quality Analyzer - Qualitätsanalyse der Dateiformate

Analysiert:
- PDF-Textqualität (Text-Layer, OCR-Eignung)
- Bildauflösung und OCR-Eignung
- Office-Dokumente (Struktur, Tabellen)
- Seiteninhalt-Qualität
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# Relative import für config
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import EvaluationConfig, get_config

# Optional imports - graceful fallback
try:
    import fitz  # PyMuPDF

    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    from PIL import Image

    HAS_PIL = True
except ImportError:
    HAS_PIL = False


@dataclass
class FileQuality:
    """Qualitätsbewertung einer einzelnen Datei."""

    file_path: str
    file_name: str
    file_type: str
    file_size_kb: float
    quality_score: float  # 0.0 - 1.0
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PDFQuality(FileQuality):
    """Spezifische Qualitätsbewertung für PDFs."""

    page_count: int = 0
    has_text_layer: bool = False
    text_char_count: int = 0
    avg_chars_per_page: float = 0.0
    needs_ocr: bool = False
    has_images: bool = False
    has_tables: bool = False
    is_scanned: bool = False


@dataclass
class ImageQuality(FileQuality):
    """Spezifische Qualitätsbewertung für Bilder."""

    width: int = 0
    height: int = 0
    resolution: int = 0
    format: str = ""
    is_ocr_candidate: bool = False
    has_text_content: bool = False


@dataclass
class QualityAnalysisResult:
    """Gesamtergebnis der Qualitätsanalyse."""

    total_files: int = 0
    total_size_mb: float = 0.0
    files_by_type: Dict[str, int] = field(default_factory=dict)
    size_by_type: Dict[str, float] = field(default_factory=dict)
    avg_quality_score: float = 0.0
    quality_distribution: Dict[str, int] = field(default_factory=dict)  # high/medium/low
    files_needing_ocr: int = 0
    files_with_issues: int = 0
    diploma_thesis_files: List[FileQuality] = field(default_factory=list)
    all_files: List[FileQuality] = field(default_factory=list)
    pages_analysis: Dict[str, Any] = field(default_factory=dict)


class FormatQualityAnalyzer:
    """Analysiert die Qualität verschiedener Dateiformate."""

    def __init__(self, config: Optional[EvaluationConfig] = None):
        """
        Initialisiert den FormatQualityAnalyzer.

        Args:
            config: EvaluationConfig Instanz
        """
        self.config = config or get_config()
        self.raw_config = self.config.raw_config

        # Load format settings
        format_cfg = self.raw_config.get("FORMAT_ANALYSIS", {})
        self.supported_formats = format_cfg.get("supported_formats", {})
        self.quality_thresholds = format_cfg.get("quality_thresholds", {})

        # Diploma thesis files
        diploma_cfg = self.raw_config.get("DIPLOMA_THESIS", {})
        self.diploma_thesis_files = set(diploma_cfg.get("files", []))

        # Results
        self.result = QualityAnalysisResult()

        # Check available libraries
        if not HAS_PYMUPDF:
            print("  WARNUNG: PyMuPDF nicht installiert - PDF-Analyse eingeschränkt")
        if not HAS_PIL:
            print("  WARNUNG: Pillow nicht installiert - Bild-Analyse eingeschränkt")

    def analyze(self) -> QualityAnalysisResult:
        """
        Führt die vollständige Qualitätsanalyse durch.

        Returns:
            QualityAnalysisResult mit allen Analysen
        """
        print("\n[FormatQualityAnalyzer] Starte Analyse...")

        # Analyze pages
        self._analyze_pages()

        # Analyze media files
        self._analyze_media()

        # Calculate summary statistics
        self._calculate_summary()

        print(f"  Analysiert: {self.result.total_files} Dateien")
        print(f"  Gesamtgröße: {self.result.total_size_mb:.2f} MB")
        print(f"  OCR-Kandidaten: {self.result.files_needing_ocr}")
        print(f"  Diplomarbeiten: {len(self.result.diploma_thesis_files)}")

        return self.result

    def _analyze_pages(self):
        """Analysiert die Wiki-Seiten."""
        content_dir = self.config.page_content_dir
        if not content_dir or not content_dir.exists():
            return

        page_stats = {
            "total": 0,
            "empty": 0,
            "tiny": 0,  # < min_chars
            "small": 0,  # < 1KB
            "medium": 0,  # 1-5KB
            "large": 0,  # > 5KB
            "total_chars": 0,
            "total_words": 0,
            "with_media": 0,
            "issues": [],
        }

        min_chars = self.quality_thresholds.get("page_content", {}).get("min_chars", 50)

        for content_file in content_dir.glob("*.txt"):
            page_stats["total"] += 1

            try:
                content = content_file.read_text(encoding="utf-8")
                char_count = len(content)
                word_count = len(content.split())

                page_stats["total_chars"] += char_count
                page_stats["total_words"] += word_count

                # Size classification
                if char_count == 0:
                    page_stats["empty"] += 1
                    page_stats["issues"].append(f"{content_file.stem}: Leer")
                elif char_count < min_chars:
                    page_stats["tiny"] += 1
                elif char_count < 1000:
                    page_stats["small"] += 1
                elif char_count < 5000:
                    page_stats["medium"] += 1
                else:
                    page_stats["large"] += 1

                # Check for media references
                if "{{" in content and "}}" in content:
                    page_stats["with_media"] += 1

            except Exception as e:
                page_stats["issues"].append(f"{content_file.stem}: {str(e)}")

        self.result.pages_analysis = page_stats

    def _analyze_media(self):
        """Analysiert alle Media-Dateien."""
        media_dir = self.config.media_dir
        if not media_dir or not media_dir.exists():
            return

        # Collect all media files
        for file_path in media_dir.rglob("*"):
            if not file_path.is_file():
                continue

            # Skip metadata files
            if "metadata" in str(file_path).lower():
                continue

            ext = file_path.suffix.lower()
            file_name = file_path.name

            # Analyze by type
            if ext == ".pdf":
                quality = self._analyze_pdf(file_path)
            elif ext in [".jpg", ".jpeg", ".png"]:
                quality = self._analyze_image(file_path)
            elif ext in [".docx", ".xlsx", ".pptx", ".odt"]:
                quality = self._analyze_office(file_path)
            elif ext == ".svg":
                quality = self._analyze_svg(file_path)
            else:
                quality = self._analyze_generic(file_path)

            # Track diploma thesis files separately
            if file_name in self.diploma_thesis_files:
                self.result.diploma_thesis_files.append(quality)
            else:
                self.result.all_files.append(quality)

            # Update stats
            self.result.total_files += 1
            file_size_mb = quality.file_size_kb / 1024
            self.result.total_size_mb += file_size_mb

            file_type = quality.file_type
            self.result.files_by_type[file_type] = self.result.files_by_type.get(file_type, 0) + 1
            self.result.size_by_type[file_type] = (
                self.result.size_by_type.get(file_type, 0) + file_size_mb
            )

            if quality.issues:
                self.result.files_with_issues += 1

    def _analyze_pdf(self, file_path: Path) -> PDFQuality:
        """Analysiert eine PDF-Datei."""
        file_size_kb = file_path.stat().st_size / 1024

        quality = PDFQuality(
            file_path=str(file_path),
            file_name=file_path.name,
            file_type="pdf",
            file_size_kb=file_size_kb,
            quality_score=0.5,  # Default
        )

        if not HAS_PYMUPDF:
            quality.issues.append("PyMuPDF nicht verfügbar - keine Detailanalyse")
            return quality

        try:
            doc = fitz.open(file_path)
            quality.page_count = len(doc)

            total_text = ""
            has_images = False

            for page in doc:
                text = page.get_text()
                # Ensure text is a string (get_text() can return different types)
                if isinstance(text, str):
                    total_text += text
                else:
                    # If it's a list or dict, convert to string representation
                    total_text += str(text)

                # Check for images
                if page.get_images():
                    has_images = True

            doc.close()

            quality.text_char_count = len(total_text)
            quality.has_text_layer = quality.text_char_count > 100
            quality.has_images = has_images

            if quality.page_count > 0:
                quality.avg_chars_per_page = quality.text_char_count / quality.page_count

            # Determine if OCR is needed
            min_text = self.quality_thresholds.get("pdf", {}).get("min_text_chars", 100)
            if quality.text_char_count < min_text and has_images:
                quality.needs_ocr = True
                quality.is_scanned = True
                self.result.files_needing_ocr += 1
                quality.issues.append("Wenig Text - vermutlich gescannt")
                quality.recommendations.append("OCR empfohlen")

            # Calculate quality score
            if quality.has_text_layer and quality.avg_chars_per_page > 500:
                quality.quality_score = 0.9
            elif quality.has_text_layer:
                quality.quality_score = 0.7
            elif quality.needs_ocr:
                quality.quality_score = 0.3
            else:
                quality.quality_score = 0.5

            quality.metadata = {
                "page_count": quality.page_count,
                "avg_chars_per_page": quality.avg_chars_per_page,
                "is_scanned": quality.is_scanned,
            }

        except Exception as e:
            quality.issues.append(f"Analyse-Fehler: {str(e)}")
            quality.quality_score = 0.0

        return quality

    def _analyze_image(self, file_path: Path) -> ImageQuality:
        """Analysiert eine Bilddatei."""
        file_size_kb = file_path.stat().st_size / 1024

        quality = ImageQuality(
            file_path=str(file_path),
            file_name=file_path.name,
            file_type="image",
            file_size_kb=file_size_kb,
            quality_score=0.5,
            format=file_path.suffix.lower(),
        )

        if not HAS_PIL:
            quality.issues.append("Pillow nicht verfügbar - keine Detailanalyse")
            return quality

        try:
            with Image.open(file_path) as img:
                quality.width = img.width
                quality.height = img.height
                quality.resolution = min(quality.width, quality.height)

                # Check OCR candidacy
                min_width = (
                    self.supported_formats.get("images", {})
                    .get("ocr_candidates", {})
                    .get("min_width", 200)
                )
                min_height = (
                    self.supported_formats.get("images", {})
                    .get("ocr_candidates", {})
                    .get("min_height", 100)
                )

                if quality.width >= min_width and quality.height >= min_height:
                    quality.is_ocr_candidate = True

                # Quality scoring
                if quality.resolution >= 800:
                    quality.quality_score = 0.9
                elif quality.resolution >= 400:
                    quality.quality_score = 0.7
                elif quality.resolution >= 200:
                    quality.quality_score = 0.5
                else:
                    quality.quality_score = 0.3
                    quality.issues.append("Niedrige Auflösung")

                quality.metadata = {
                    "width": quality.width,
                    "height": quality.height,
                    "is_ocr_candidate": quality.is_ocr_candidate,
                }

        except Exception as e:
            quality.issues.append(f"Analyse-Fehler: {str(e)}")
            quality.quality_score = 0.0

        return quality

    def _analyze_office(self, file_path: Path) -> FileQuality:
        """Analysiert ein Office-Dokument."""
        file_size_kb = file_path.stat().st_size / 1024
        ext = file_path.suffix.lower()

        file_type_map = {".docx": "word", ".xlsx": "excel", ".pptx": "powerpoint", ".odt": "odt"}

        quality = FileQuality(
            file_path=str(file_path),
            file_name=file_path.name,
            file_type=file_type_map.get(ext, "office"),
            file_size_kb=file_size_kb,
            quality_score=0.7,  # Office files generally good
        )

        # Size-based quality assessment
        if file_size_kb < 10:
            quality.issues.append("Sehr kleine Datei - möglicherweise wenig Inhalt")
            quality.quality_score = 0.5
        elif file_size_kb > 10000:
            quality.issues.append("Große Datei - möglicherweise komplexes Layout")
            quality.recommendations.append("Prüfen ob Chunking-Strategie angepasst werden muss")

        quality.metadata = {
            "format": ext,
            "estimated_complexity": "high" if file_size_kb > 5000 else "normal",
        }

        return quality

    def _analyze_svg(self, file_path: Path) -> FileQuality:
        """Analysiert eine SVG-Datei."""
        file_size_kb = file_path.stat().st_size / 1024

        quality = FileQuality(
            file_path=str(file_path),
            file_name=file_path.name,
            file_type="svg",
            file_size_kb=file_size_kb,
            quality_score=0.8,  # SVGs are generally good
        )

        # SVGs are vector graphics - usually diagrams
        quality.recommendations.append("SVG-Diagramm - Text-Extraktion prüfen")

        return quality

    def _analyze_generic(self, file_path: Path) -> FileQuality:
        """Analysiert eine generische Datei."""
        file_size_kb = file_path.stat().st_size / 1024

        return FileQuality(
            file_path=str(file_path),
            file_name=file_path.name,
            file_type=file_path.suffix.lower().lstrip(".") or "unknown",
            file_size_kb=file_size_kb,
            quality_score=0.5,
        )

    def _calculate_summary(self):
        """Berechnet Zusammenfassungsstatistiken."""
        all_files = self.result.all_files + self.result.diploma_thesis_files

        if all_files:
            total_score = sum(f.quality_score for f in all_files)
            self.result.avg_quality_score = total_score / len(all_files)

        # Quality distribution
        for f in all_files:
            if f.quality_score >= 0.7:
                bucket = "high"
            elif f.quality_score >= 0.4:
                bucket = "medium"
            else:
                bucket = "low"
            self.result.quality_distribution[bucket] = (
                self.result.quality_distribution.get(bucket, 0) + 1
            )

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert Ergebnisse zu Dictionary für JSON-Export."""
        return {
            "summary": {
                "total_files": self.result.total_files,
                "total_size_mb": round(self.result.total_size_mb, 2),
                "avg_quality_score": round(self.result.avg_quality_score, 2),
                "files_needing_ocr": self.result.files_needing_ocr,
                "files_with_issues": self.result.files_with_issues,
            },
            "by_type": self.result.files_by_type,
            "size_by_type_mb": {k: round(v, 2) for k, v in self.result.size_by_type.items()},
            "quality_distribution": self.result.quality_distribution,
            "pages_analysis": self.result.pages_analysis,
            "diploma_thesis": [
                {
                    "file_name": f.file_name,
                    "size_mb": round(f.file_size_kb / 1024, 2),
                    "quality_score": round(f.quality_score, 2),
                    "issues": f.issues,
                    "metadata": f.metadata,
                }
                for f in self.result.diploma_thesis_files
            ],
            "files_with_issues": [
                {
                    "file_name": f.file_name,
                    "file_type": f.file_type,
                    "issues": f.issues,
                    "recommendations": f.recommendations,
                }
                for f in self.result.all_files
                if f.issues
            ],
        }


# =============================================================================
# Test
# =============================================================================

if __name__ == "__main__":
    analyzer = FormatQualityAnalyzer()
    result = analyzer.analyze()

    print("\n" + "=" * 60)
    print("  QUALITY ANALYSIS RESULTS")
    print("=" * 60)
    print(f"\n  Total Files: {result.total_files}")
    print(f"  Total Size: {result.total_size_mb:.2f} MB")
    print(f"  Avg Quality Score: {result.avg_quality_score:.2f}")

    print(f"\n  By Type:")
    for ft, count in sorted(result.files_by_type.items(), key=lambda x: -x[1]):
        size = result.size_by_type.get(ft, 0)
        print(f"    {ft}: {count} files ({size:.2f} MB)")

    print(f"\n  Quality Distribution:")
    for q, count in result.quality_distribution.items():
        print(f"    {q}: {count}")

    print(f"\n  Diploma Thesis PDFs: {len(result.diploma_thesis_files)}")
    for dt in result.diploma_thesis_files:
        print(f"    - {dt.file_name}: {dt.file_size_kb/1024:.2f} MB")
