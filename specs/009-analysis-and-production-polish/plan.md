# Implementation Plan: Analysis & Production Polish

**Branch**: `009-analysis-and-production-polish` | **Date**: 2026-02-15 | **Spec**: [spec.md](./spec.md)
**Input**: Side-by-Side Comparison Analysis (2026-02-14/15) + Spec 009
**Thesis-Zuordnung**: FF1, FF3, J4, J6
**Builds On**: 007-evaluation-infrastructure (complete), 008-pipeline-consolidation (partial -- Preprocessing uebernommen)
**Supersedes**: 008-pipeline-consolidation US5 (Preprocessing)

## Summary

Behebt die kritische Schema-Inkompatibilitaet zwischen Stage 3 (Preprocessing) und Stage 4
(Embeddings Creator), integriert `preprocessing_strategies.yaml` aus Stage 2 als Routing-Quelle,
fuehrt quantitative Freshness-Scores ein, implementiert Vision-LLM Bild-Captioning, verbessert
PDF-Textqualitaet, schafft eine 7-Metrik-Evaluationssuite, und poliert CLI UX + Deep Eval Bugs.

Drei Saeulen:

1. **Schema-Alignment + Data Flow** (US3, US4, US5): Pipeline-Output wird exakt kompatibel mit `document_loader.py`
2. **Content-Qualitaet** (US6, US7, US8): Vision-LLM Captioning, PDF-Cleaning, Evaluations-Metriken
3. **Polish** (US1, US2, US9): CLI UX, Deep Eval Bugfixes, Architektur-Konsolidierung

## Technical Context

**Language/Version**: Python 3.11+ (matching existing pipeline)
**New Dependencies**:
- `sentence-transformers` -- Semantic Similarity Metrik (US8, `paraphrase-multilingual-mpnet-base-v2`)
- `textstat` -- Readability Scoring (US8, Flesch Reading Ease)
- `openai` -- Vision-LLM API Client (US6, OpenAI-compatible endpoint to LMStudio)
**Existing Dependencies** (reused): `pypdf`/`PyPDF2`, `pyyaml`, `pytesseract`, `Pillow`, `pymupdf`
**Testing**: pytest, TDD -- Tests VOR oder GLEICHZEITIG mit Implementation
**Target Platform**: Windows 11 (host-native, venv), LMStudio auf 192.168.8.3:1234 (Qwen2.5-VL)
**LLM Backend**: LMStudio auf 192.168.8.3:1234/v1 (OpenAI-kompatible API, Vision)

## Constitution Check

| Article                              | Status  | Notes                                           |
| ------------------------------------ | ------- | ----------------------------------------------- |
| Article I (Layered Architecture)     | PASS    | Preprocessing bleibt Python-only, kein PHP      |
| Article II (JSON Interface)          | PASS    | Evaluation-Reports JSON, Frontmatter YAML       |
| Article II-B (YAML Config)           | PASS    | Alle Config via env.yaml, Secrets in .token     |
| Article III (Critical-Path Testing)  | PASS    | TDD fuer alle neuen Module (NFR-002)            |
| Article VI (Secret Containment)      | PASS    | LMStudio URL in Config, kein API-Key noetig     |
| Article VII (Integration Simplicity) | PASS    | Reuses bestehende Processors, Enrichers, Config |
| Article VIII (Direct Framework)      | PASS    | `openai` Library direkt fuer Vision-LLM         |
| Article X (Execution Mandate)        | PRIMARY | Liefert funktionsfaehige Preprocessing-Pipeline |
| Article XI (Thesis Alignment)        | PASS    | FF1, FF3, J4, J6 direkt bedient                 |
| Article XII (Resource Governance)    | PASS    | Keine neuen Docker-Services                     |

## Current State Analysis (Gap Summary)

Detaillierte Analyse des IST-Zustands gegenueber den Anforderungen:

| Bereich                          | IST                                | SOLL                                   | Gap                             |
| -------------------------------- | ---------------------------------- | -------------------------------------- | ------------------------------- |
| Strategy-Quelle                  | `page_strategies.json` (JSON)      | `preprocessing_strategies.yaml` (YAML) | Format-Mismatch, Komplett-Umbau |
| Frontmatter-Feld `last_modified` | Feld heisst `modified_at`          | `last_modified`                        | Rename                          |
| Media-Output-Extension           | `.txt`                             | `.md`                                  | Extension-Aenderung             |
| Frontmatter `content_hash`       | fehlt                              | MD5 des Markdown-Body                  | Neu implementieren              |
| Frontmatter `freshness_score`    | fehlt (nur Kategorie als String)   | Float 0.0-1.0                          | Neu: Hybrid-Formel              |
| Frontmatter `freshness_category` | rudimentaer (4 Stufen)             | 6-stufig (Spec-Formel)                 | Erweitern                       |
| Frontmatter `chunking_method`    | fehlt                              | Aus Strategy-Routing                   | Neu: via StrategyLoader         |
| Frontmatter `linked_from`        | fehlt                              | Backlinks aus `page_backlinks/*.json`  | Neu: Backlink-Integration       |
| Vision-LLM Captioning            | fehlt                              | Qwen2.5-VL via LMStudio                | Komplett neu                    |
| PDF Spaced-Chars                 | keine Korrektur                    | Korrektur + Paragraph-Merging          | Neu: Post-Processing            |
| Evaluation Suite                 | fehlt                              | 7-Metrik-Suite                         | Komplett neu                    |
| CLI UX                           | keine Farben, kein Signal-Handler  | Farbig, Help-Template, Ctrl+C          | Komplett neu (`cli_utils.py`)   |
| Deep Eval rglob                  | Duplikate bei case-insensitive FS  | Set-basierte Dedup                     | Bugfix                          |
| Deep Eval YAML-Dedup             | Duplikate in Dateilisten           | Set-basierte Dedup                     | Bugfix                          |
| Deep Eval temperature            | nicht an LLM uebergeben            | `temperature=0.0`                      | Bugfix                          |
| Entry Points                     | `main.py` + `run_preprocessing.py` | Nur `run_preprocessing.py`             | Konsolidierung                  |

## Project Structure (New + Modified Files)

```text
pipeline/shared/                        # NEW directory
├── __init__.py                         # NEW
└── cli_utils.py                        # NEW: US1 -- style(), sigint, help, color

pipeline/01_wiki_fetcher/
└── fetch_full_wiki_extended.py         # MODIFY: US9 -- media_metadata Bugfix

pipeline/02_deep_evaluation/
├── run_deep_evaluation.py              # MODIFY: US2 -- rglob-Dedup
├── env.yaml                            # MODIFY: US2 -- temperature: 0.0
└── generators/
    └── strategy_generator.py           # MODIFY: US2 -- YAML-Dedup

pipeline/03_rag_preprocessing/
├── __init__.py                         # existing
├── config.py                           # existing
├── page_processor.py                   # existing (minor: title extraction)
├── strategy_loader.py                  # MODIFY: US4 -- YAML statt JSON, neue Kategorien
├── metadata_enricher.py                # MODIFY: US3/US5 -- Schema-Alignment, Freshness-Formel
├── media_processor.py                  # MODIFY: US7 -- Spaced-Chars, Paragraph-Merging
├── exporter.py                         # MODIFY: US3 -- Ziel-Schema, .md Extension, content_hash
├── image_captioner.py                  # NEW: US6 -- Vision-LLM Bild-Captioning
├── run_preprocessing.py                # MODIFY: US3/US4/US6/US9 -- Orchestrator-Umbau
├── main.py                             # DELETE: US9 -- Konsolidierung (Logik -> run_preprocessing)
├── evaluation/                         # NEW: US8 -- komplett neues Unterverzeichnis
│   ├── __init__.py                     # NEW
│   ├── metrics.py                      # NEW: 7-Metrik-Implementierungen
│   ├── run_eval_preprocessing.py       # NEW: CLI-Script fuer Evaluation
│   └── report.py                       # NEW: JSON/Markdown Report-Generator
└── tests/
    ├── conftest.py                     # existing
    ├── test_page_processor.py          # existing
    ├── test_metadata_enricher.py       # MODIFY: neue Tests fuer Schema + Freshness
    ├── test_exporter.py                # MODIFY: neue Tests fuer Ziel-Schema
    ├── test_strategy_loader.py         # MODIFY: neue Tests fuer YAML-Loading
    ├── test_media_processor.py         # MODIFY: neue Tests fuer PDF-Cleaning
    ├── test_image_captioner.py         # NEW: US6 tests
    ├── test_eval_metrics.py            # NEW: US8 tests
    └── test_schema_e2e.py              # NEW: US3 End-to-End-Test
```

## Component Design

### 1. Schema-Alignment -- Exporter Umbau (US3)

Das Kernproblem: `document_loader.py` (Stage 4) erwartet spezifische Frontmatter-Felder,
der aktuelle Exporter liefert ein abweichendes Schema.

**Ziel-Frontmatter** (muss `document_loader.py` `Document.__post_init__` matchen):

```python
# pipeline/03_rag_preprocessing/exporter.py -- REWRITE
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

class Exporter:
    """Exports preprocessed content in Qdrant-compatible schema.

    Every output file is .md with YAML frontmatter matching the
    fields expected by pipeline/04_embeddings_creator/document_loader.py.
    """

    def export(
        self,
        pages: list[dict[str, Any]],
        media: list[dict[str, Any]],
        output_base: Path,
    ) -> Path:
        """Export pages AND media to timestamped directory.

        Directory layout:
            preprocess_at_{timestamp}/
            ├── pages/
            │   └── *.md
            ├── media/
            │   └── *.md          # <-- .md NOT .txt
            └── manifest.json
        """
        ...

    def _build_page_frontmatter(self, page: dict[str, Any]) -> dict[str, Any]:
        """Build Qdrant-compatible frontmatter for a wiki page.

        Required fields (per document_loader.py Document dataclass):
        - title, namespace, source, page_id, access_level, content_type
        - freshness_score (float), freshness_category (str)
        - chunking_method (str), last_modified (ISO timestamp)
        - author, content_hash, links_to, linked_from
        """
        body = page.get("content", "")
        return {
            "title": page.get("title", ""),
            "namespace": page.get("namespace", ""),
            "source": page.get("source", ""),
            "page_id": page.get("page_id", ""),
            "access_level": page.get("access_level", "public"),
            "content_type": page.get("content_type", "KNOWLEDGE"),
            "freshness_score": page.get("freshness_score", 0.5),
            "freshness_category": page.get("freshness_category", "recent"),
            "chunking_method": page.get("chunking_method", "semantic"),
            "last_modified": page.get("last_modified", ""),  # NOT modified_at
            "author": page.get("author", ""),
            "content_hash": hashlib.md5(body.encode("utf-8")).hexdigest(),
            "links_to": page.get("links_to", []),
            "linked_from": page.get("linked_from", []),
        }

    def _build_media_frontmatter(self, media_item: dict[str, Any]) -> dict[str, Any]:
        """Build Qdrant-compatible frontmatter for a media file.

        Uses media_id instead of page_id, otherwise identical schema.
        """
        body = media_item.get("content", "")
        return {
            "title": media_item.get("title", ""),
            "namespace": media_item.get("namespace", ""),
            "source": media_item.get("source", ""),
            "media_id": media_item.get("media_id", ""),
            "access_level": media_item.get("access_level", "public"),
            "content_type": media_item.get("content_type", "DOCUMENT"),
            "freshness_score": media_item.get("freshness_score", 0.5),
            "freshness_category": media_item.get("freshness_category", "recent"),
            "chunking_method": media_item.get("chunking_method", "metadata_only"),
            "last_modified": media_item.get("last_modified", ""),
            "author": media_item.get("author", ""),
            "content_hash": hashlib.md5(body.encode("utf-8")).hexdigest(),
            "links_to": [],
            "linked_from": [],
        }
```

**Key Changes vs Current**:
- `modified_at` -> `last_modified`
- Media files get `.md` extension (not `.txt`)
- `content_hash` = MD5 of Markdown body (without frontmatter)
- `freshness_score` as Float, `freshness_category` as String -- both in frontmatter
- `chunking_method` from Strategy-Routing
- `linked_from` from backlink data
- Separate `pages/` and `media/` subdirectories

**End-to-End Validierung**: Neuer Test `test_schema_e2e.py` erzeugt eine `.md`-Datei mit
dem Exporter, laedt sie mit `document_loader.py`'s `extract_frontmatter()`, und prueft
alle Pflichtfelder.

### 2. Strategy-Integration -- StrategyLoader Umbau (US4)

**Problem**: `strategy_loader.py` liest `page_strategies.json`, aber Stage 2 erzeugt
`preprocessing_strategies.yaml` (via `strategy_generator.py`). Das YAML hat eine voellig
andere Struktur (kategoriebasiert mit `include_ids` Listen).

```python
# pipeline/03_rag_preprocessing/strategy_loader.py -- REWRITE
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class ContentType(Enum):
    KNOWLEDGE = "KNOWLEDGE"
    NEWS = "NEWS"
    PORTAL = "PORTAL"
    FORM = "FORM"
    ARCHIVED = "ARCHIVED"
    IGNORED = "IGNORED"


@dataclass(frozen=True)
class PageStrategy:
    page_id: str
    content_type: ContentType
    chunking_method: str         # NEW: replaces recommended_chunk_size
    chunk_size: int
    action: str                  # "process" | "skip" | "metadata_only"


@dataclass(frozen=True)
class MediaStrategy:
    """Strategy for a single media file (document or image)."""
    file_name: str
    content_type: str            # "DOCUMENT" | "IMAGE" | ...
    action: str                  # "process" | "caption_and_index" | "skip"
    parser: str                  # "pdf_standard" | "pdf_scientific" | ...
    chunk_size: int


class StrategyLoader:
    """Loads preprocessing_strategies.yaml from Stage 2 Deep Evaluation.

    YAML structure (from strategy_generator.py):
        PIPELINE_STRATEGIES:
          wiki_pages:
            knowledge_articles: { include_ids: [...], chunking: "recursive_header", ... }
            portals:            { include_ids: [...], action: "index_as_context_only", ... }
            ignored:            { include_ids: [...], action: "skip" }
          documents:
            theses:   { files: [...], parser: "pdf_scientific", ... }
            forms:    { files: [...], action: "index_metadata_only", ... }
          media:
            informative_images: { files: [...], action: "caption_and_index" }
            decorative:         { files: [...], action: "skip" }
    """

    # Wiki page category -> ContentType + chunking_method mapping
    # NOTE: "forms" is a DOCUMENT category (see _DOC_CATEGORY_MAP), not a wiki page category
    _WIKI_CATEGORY_MAP: dict[str, tuple[ContentType, str]] = {
        "knowledge_articles": (ContentType.KNOWLEDGE, "recursive_header"),
        "portals":            (ContentType.PORTAL, "parent_context"),
        "news":               (ContentType.NEWS, "naive"),
        "ignored":            (ContentType.IGNORED, "none"),
    }

    # Document category -> ContentType + chunking_method mapping (PDFs, DOCX, etc.)
    _DOC_CATEGORY_MAP: dict[str, tuple[ContentType, str]] = {
        "theses":  (ContentType.KNOWLEDGE, "recursive_header"),
        "forms":   (ContentType.FORM, "metadata_only"),
    }

    def __init__(self) -> None:
        self._page_strategies: dict[str, PageStrategy] = {}
        self._media_strategies: dict[str, MediaStrategy] = {}

    def load(self, evaluated_dir: Path) -> None:
        """Load strategies from preprocessing_strategies.yaml.

        Falls back to page_strategies.json for backwards compatibility.
        """
        yaml_file = evaluated_dir / "preprocessing_strategies.yaml"
        if yaml_file.exists():
            self._load_yaml(yaml_file)
            return

        # Fallback: legacy JSON (from 008)
        json_file = evaluated_dir / "page_strategies.json"
        if json_file.exists():
            self._load_legacy_json(json_file)
            return

        logger.warning("No strategy file found in %s", evaluated_dir)

    def get_strategy(self, page_id: str) -> PageStrategy:
        """Get strategy for a page. Returns sensible default if unknown."""
        if page_id in self._page_strategies:
            return self._page_strategies[page_id]
        return PageStrategy(
            page_id=page_id,
            content_type=ContentType.KNOWLEDGE,
            chunking_method="semantic",
            chunk_size=512,
            action="process",
        )

    def get_media_strategy(self, file_name: str) -> MediaStrategy:
        """Get strategy for a media file."""
        if file_name in self._media_strategies:
            return self._media_strategies[file_name]
        return MediaStrategy(
            file_name=file_name,
            content_type="DOCUMENT",
            action="process",
            parser="pdf_standard",
            chunk_size=1024,
        )

    def is_ignored(self, page_id: str) -> bool:
        """Check if a page should be skipped."""
        strategy = self.get_strategy(page_id)
        return strategy.action == "skip"

    def _load_yaml(self, path: Path) -> None:
        """Parse preprocessing_strategies.yaml."""
        ...

    def _load_legacy_json(self, path: Path) -> None:
        """Parse page_strategies.json (backwards compat)."""
        ...
```

**Key Design Decisions**:
- Inverted lookup: YAML has categories with ID-lists; loader builds per-ID index
- `MediaStrategy` is NEW -- needed for Vision-LLM routing (informative vs decorative)
- `is_ignored()` convenience method for skip-check in orchestrator
- Backwards-compatible with JSON fallback

### 3. Freshness-Scoring -- Hybrid-Formel (US5)

**Problem**: Current `calculate_freshness_score()` returns only a string category with
4 coarse buckets (30d/180d/365d). Spec requires a Float score + 6-stufige Kategorien.

```python
# pipeline/03_rag_preprocessing/metadata_enricher.py -- REPLACE freshness methods

@dataclass(frozen=True)
class FreshnessResult:
    """Freshness calculation result."""
    score: float          # 0.0 - 1.0
    category: str         # fresh / recent / outdated / archived

def calculate_freshness(self, last_modified: str) -> FreshnessResult:
    """Calculate freshness using the spec's hybrid formula.

    Thresholds (from spec):
        < 30 days:   score=1.00, category="fresh"
        < 90 days:   score=0.85, category="fresh"
        < 180 days:  score=0.70, category="recent"
        < 365 days:  score=0.55, category="recent"
        < 730 days:  score=0.35, category="outdated"
        >= 730 days: score=0.20, category="archived"
    """
    ...
```

**Key Change**: Returns a `FreshnessResult` dataclass with BOTH `score` (Float) and
`category` (String). Both go into frontmatter as `freshness_score` and `freshness_category`.

### 4. Vision-LLM Bild-Captioning (US6)

Komplett neues Modul. Verwendet den OpenAI-kompatiblen Endpoint von LMStudio.

```python
# pipeline/03_rag_preprocessing/image_captioner.py -- NEW
from __future__ import annotations

import base64
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Supported image extensions for captioning
CAPTIONABLE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}


class ImageCaptioner:
    """Generates text descriptions for images using a Vision-LLM.

    Uses Qwen2.5-VL via LMStudio's OpenAI-compatible API.
    All config values MUST come from env.yaml (Article II-B).
    """

    def __init__(
        self,
        api_base: str,
        model: str,
        timeout: int = 60,
    ) -> None:
        self.api_base = api_base  # from env.yaml: VISION_LLM.api_base
        self.model = model        # from env.yaml: VISION_LLM.model
        self.timeout = timeout    # from env.yaml: VISION_LLM.timeout
        self._client = None       # Lazy init

    def _get_client(self):
        """Lazy-initialize OpenAI client."""
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                base_url=self.api_base,
                api_key="not-needed",
                timeout=self.timeout,
            )
        return self._client

    def caption(self, image_path: Path) -> str:
        """Generate a German description for an image.

        Args:
            image_path: Path to the image file.

        Returns:
            Description text (empty string on failure).
        """
        ...

    def is_available(self) -> bool:
        """Check if LMStudio endpoint is reachable."""
        ...
```

**Key Design Decisions**:
- Lazy client init: no crash on import if LMStudio is down
- `is_available()` pre-check before batch processing
- German prompt: "Beschreibe dieses Bild ausfuehrlich auf Deutsch..."
- Base64-encodes image for API (OpenAI vision format)
- Graceful failure: returns empty string, logs warning, pipeline continues
- Output: `.md` file with same frontmatter schema as pages/media

**Integration into Orchestrator**:
```sketch
for image in informative_images:
    strategy = strategy_loader.get_media_strategy(image.name)
    if strategy.action == "caption_and_index":
        description = captioner.caption(image)
        if description:
            media_items.append({...frontmatter + description...})
    elif strategy.action == "skip":
        continue  # decorative
```

### 5. PDF-Qualitaet -- Spaced-Chars + Paragraph-Merging (US7)

Erweiterung von `media_processor.py` um Post-Processing-Schritt nach Text-Extraktion.

```python
# pipeline/03_rag_preprocessing/media_processor.py -- NEW methods

def clean_pdf_text(self, raw_text: str) -> str:
    """Post-process extracted PDF text for quality.

    Steps:
    1. fix_spaced_characters(): "H T B L A" -> "HTBLA"
    2. merge_short_lines(): join layout-broken lines into paragraphs
    3. Preserve headings and list items (don't merge across structure)
    """
    text = self._fix_spaced_characters(raw_text)
    text = self._merge_short_lines(text)
    return text

def _fix_spaced_characters(self, text: str) -> str:
    """Fix PDF layout artifacts with spaced characters.

    Pattern: single characters separated by spaces, e.g.
    "H T B L A  L e o n d i n g" -> "HTBLA Leonding"

    Uses heuristic: if >60% of "words" on a line are single characters,
    join them and split on double-spaces.
    """
    ...

def _merge_short_lines(self, text: str, threshold: int = 40) -> str:
    """Merge consecutive short lines into paragraphs.

    Short lines from PDF column breaks are joined. Respects:
    - Sentence boundaries (., !, ?)
    - List items (lines starting with -, *, digits)
    - Headings (lines starting with #)
    - Empty lines (paragraph separator)
    """
    ...
```

**Key Design Decisions**:
- Heuristic-based: no external dictionary needed
- Threshold configurable (default 40 chars from spec)
- Structure-preserving: lists and headings are never merged
- Applied as post-processing step inside `process_pdf()`

### 6. Preprocessing Evaluation -- 7-Metrik-Suite (US8)

Komplett neues Unterverzeichnis `evaluation/` innerhalb von `03_rag_preprocessing`.

```python
# pipeline/03_rag_preprocessing/evaluation/metrics.py -- NEW
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DocumentScore:
    """Scores for a single document."""
    doc_id: str
    content_completeness: float     # Metrik 1: char ratio
    semantic_similarity: float      # Metrik 2: embedding cosine
    entity_preservation: float      # Metrik 3: regex entities
    link_integrity: float           # Metrik 4: link transformation
    noise_ratio: float              # Metrik 5: wiki-syntax noise
    readability: float              # Metrik 6: Flesch
    structure_preservation: float   # Metrik 7: headings/lists/paragraphs


class ContentCompletenessMetric:
    """Metrik 1: Character ratio Original vs Output.

    Adjustiert fuer erwartete Markup-Entfernung (DokuWiki-Syntax).
    Schwellwert: >= 0.85
    """
    def score(self, original: str, processed: str) -> float: ...


class SemanticSimilarityMetric:
    """Metrik 2: Embedding Cosine Similarity.

    Model: paraphrase-multilingual-mpnet-base-v2
    Schwellwert: >= 0.85
    """
    def __init__(self, model_name: str = "paraphrase-multilingual-mpnet-base-v2"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)

    def score(self, original: str, processed: str) -> float: ...


class EntityPreservationMetric:
    """Metrik 3: Key Entity Preservation.

    Entities: dates, room numbers, emails, URLs (Regex-based).
    Schwellwert: >= 0.95
    """
    def score(self, original: str, processed: str) -> float: ...


class LinkIntegrityMetric:
    """Metrik 4: DokuWiki Link Transformation.

    Checks: link text + target preserved after conversion.
    Schwellwert: >= 0.95
    """
    def score(self, original: str, processed: str) -> float: ...


class NoiseDetectionMetric:
    """Metrik 5: Wiki Syntax Noise Detection.

    Detects: wiki-syntax-reste, mojibake, HTML-artefakte.
    Schwellwert: <= 2% noise ratio
    """
    def score(self, processed: str) -> float: ...


class ReadabilityMetric:
    """Metrik 6: German-adapted Flesch Reading Ease.

    Schwellwert: >= 20 (technische Texte, NICHT englischer Default 60)
    """
    def score(self, processed: str) -> float: ...


class StructurePreservationMetric:
    """Metrik 7: Headings, Lists, Paragraphs Preservation.

    Schwellwert: >= 0.90
    """
    def score(self, original: str, processed: str) -> float: ...
```

**Run-Script**:
```python
# pipeline/03_rag_preprocessing/evaluation/run_eval_preprocessing.py -- NEW
"""
Usage:
    python run_eval_preprocessing.py
    python run_eval_preprocessing.py --fetched-dir data/fetched/fetched_at_*
    python run_eval_preprocessing.py --preprocessed-dir data/preprocessed/preprocess_at_*
"""
```

**Output**: `evaluation_report_{timestamp}.json` mit per-Dokument-Scores + Aggregat-Summary.

### 7. CLI UX -- Shared Module (US1)

Neues Modul in `pipeline/shared/` das von allen Pipeline-Skripten importiert wird.

```python
# pipeline/shared/cli_utils.py -- NEW
from __future__ import annotations

import os
import sys
import signal
from typing import Callable, Optional


def enable_windows_ansi() -> None:
    """Enable ANSI escape sequences on Windows terminals."""
    if sys.platform == "win32":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)


_USE_COLOR = True


def set_use_color(enabled: bool) -> None:
    """Toggle ANSI color output."""
    global _USE_COLOR
    _USE_COLOR = enabled


def style(text: str, code: str) -> str:
    """Apply ANSI style code to text.

    Returns plain text if color is disabled (--no-color).
    Common codes: '1'=bold, '31'=red, '32'=green, '33'=yellow, '36'=cyan.
    """
    if not _USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


def create_sigint_handler(
    on_abort: Optional[Callable[[], None]] = None,
) -> Callable:
    """Create a Ctrl+C handler that shows abort banner.

    The handler:
    1. Prints a yellow abort banner with stats
    2. Calls optional on_abort callback
    3. Exits with code 130
    """
    def handler(signum, frame):
        print(f"\n{style('[ABORT]', '1;33')} Interrupted by user (Ctrl+C)")
        if on_abort:
            on_abort()
        sys.exit(130)
    return handler


def print_help_banner(
    what: str,
    usage: str,
    parameters: str = "",
    options: str = "",
    examples: str = "",
    configuration: str = "",
    output: str = "",
    exit_codes: str = "",
) -> None:
    """Print 8-section help template.

    Sections: What, Usage, Parameters, Options, Examples,
    Configuration, Output, Exit Codes.
    """
    ...
```

**Betroffene Skripte** (Import + Integration):
1. `pipeline/01_wiki_fetcher/fetch_full_wiki_extended.py`
2. `pipeline/01_wiki_fetcher/incremental_fetcher.py`
3. `pipeline/01_wiki_fetcher/resume_fetch.py`
4. `pipeline/02_deep_evaluation/run_deep_evaluation.py`
5. `pipeline/02_deep_evaluation/run_evaluation.py`
6. `pipeline/02_deep_evaluation/run_strategy_generation.py`
7. `pipeline/03_rag_preprocessing/run_preprocessing.py`

Integration pro Skript:
- Import `cli_utils`
- Add `--no-color` argument
- Register `create_sigint_handler()` in `main()`
- Replace raw `print()` summary blocks with `style()` calls

### 8. Deep Evaluation Bugfixes (US2)

Drei isolierte Fixes, keine Architektur-Aenderungen:

**Fix 1: rglob-Dedup** (`run_deep_evaluation.py`, Zeilen 226-230, 289-291):
```python
# VORHER (Duplikate bei case-insensitive Dateisystemen):
img_files = []
for ext in extensions:
    img_files.extend(media_dir.rglob(f"*{ext}"))
    img_files.extend(media_dir.rglob(f"*{ext.upper()}"))

# NACHHER (Set-basierte Deduplizierung):
img_files_set: set[Path] = set()
for ext in extensions:
    img_files_set.update(media_dir.rglob(f"*{ext}"))
    img_files_set.update(media_dir.rglob(f"*{ext.upper()}"))
img_files = sorted(img_files_set)
```

Gleiches Pattern fuer `analyze_documents()` und `analyze_images()`.

**Fix 2: temperature** (`env.yaml`):
Sicherstellen dass `temperature: 0.0` korrekt an den LLM-Endpoint uebergeben wird.
Pruefen ob `llm_client.py` den Wert weiterreicht.

**Fix 3: YAML-Dedup** (`strategy_generator.py`):
```python
# VORHER (kann Duplikate enthalten):
"include_ids": categories.get("KNOWLEDGE", [])

# NACHHER (Set -> sorted list):
"include_ids": sorted(set(categories.get("KNOWLEDGE", [])))
```

Gleiches Pattern fuer alle `include_ids` und `files` Listen.

### 9. Architektur-Cleanup (US9)

**9a. Entry Point Konsolidierung**:
- `main.py` wird geloescht
- Alle Logik die nur in `main.py` existiert wird nach `run_preprocessing.py` migriert
  (insbesondere: Manifest-Generierung, detaillierte Summary-Ausgabe, Backlinks-Loading)
- Aktueller Stand: `run_preprocessing.py` hat bereits die bessere Architektur
  (komponenten-basiert), aber `main.py` hat Features die fehlen:
  - DOCX/XLSX/PPTX-Extraktion (in `_extract_media_text()`)
  - Manifest-Generierung (`_generate_manifest()`)
  - Backlinks-Loading (aus `page_links/`)

**9b. Media-Discovery Erweiterung**:
```python
# media_processor.py -- add supported extensions
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".pptx"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff", ".tif"}
TEXT_EXTENSIONS = {".txt"}
```

**9c. media_metadata Bugfix**:
In `fetch_full_wiki_extended.py` den Code finden der den leeren `media_metadata/`
Ordner erstellt und entfernen.

## Dependencies (Reused from Existing Code)

| Component           | Source                                                         | Usage                        |
| ------------------- | -------------------------------------------------------------- | ---------------------------- |
| PageProcessor       | `pipeline/03_rag_preprocessing/page_processor.py`              | DokuWiki-to-MD conversion    |
| MetadataEnricher    | `pipeline/03_rag_preprocessing/metadata_enricher.py`           | Frontmatter generation       |
| MediaProcessor      | `pipeline/03_rag_preprocessing/media_processor.py`             | PDF/Image text extraction    |
| Exporter            | `pipeline/03_rag_preprocessing/exporter.py`                    | Output file generation       |
| StrategyLoader      | `pipeline/03_rag_preprocessing/strategy_loader.py`             | Strategy routing             |
| DocumentLoader      | `pipeline/04_embeddings_creator/document_loader.py`            | Schema validation (E2E test) |
| StrategyGenerator   | `pipeline/02_deep_evaluation/generators/strategy_generator.py` | YAML-Dedup Bugfix            |
| PreprocessingConfig | `pipeline/03_rag_preprocessing/config.py`                      | Config loading               |

## Implementation Phases

### Phase 1: Schema-Alignment (US3) -- Days 1-2 [BLOCKER]

**Rationale**: Ohne korrektes Schema ist die gesamte Pipeline blockiert.

- `test_schema_e2e.py`: End-to-End-Test -- Exporter Output -> DocumentLoader Parse -> Felder pruefen
- `exporter.py`: Rewrite mit Ziel-Schema (alle Pflichtfelder, `.md` Extension, `content_hash`)
- `metadata_enricher.py`: `modified_at` -> `last_modified` Rename, Backlink-Integration (`linked_from`)
- `test_exporter.py`: Erweiterte Tests fuer alle Frontmatter-Felder
- `test_metadata_enricher.py`: Tests fuer Feld-Rename und Backlinks
- **Deliverable**: `document_loader.py` kann den Output von `exporter.py` fehlerfrei laden

### Phase 2: Strategy-Integration (US4) -- Days 3-4

**Rationale**: Routing haengt von korrektem Strategy-Loading ab.

- `test_strategy_loader.py`: Tests fuer YAML-Parsing, Kategorie-Mapping, Fallback
- `strategy_loader.py`: Komplett-Umbau -- YAML-Loading, `MediaStrategy`, `is_ignored()`
- `run_preprocessing.py`: Strategy-Routing-Integration (skip ignored, route captioning)
- **Deliverable**: Pipeline liest `preprocessing_strategies.yaml` und routet korrekt

### Phase 3: Freshness-Scoring (US5) -- Day 5

**Rationale**: Schneller Fix, keine externen Abhaengigkeiten.

- `test_metadata_enricher.py`: Tests mit konkreten Datum-Beispielen aus der Spec
- `metadata_enricher.py`: Neue `calculate_freshness()` Methode mit Hybrid-Formel + `FreshnessResult`
- `run_preprocessing.py`: Freshness-Score und -Category in Page-Dicts schreiben
- **Deliverable**: Jedes Dokument hat `freshness_score` (Float) + `freshness_category`

### Phase 4: PDF-Qualitaet (US7) -- Days 6-7

**Rationale**: Verbessert Chunk-Qualitaet fuer alle existierenden PDFs.

- `test_media_processor.py`: Tests fuer Spaced-Char-Korrektur und Paragraph-Merging
- `media_processor.py`: `clean_pdf_text()`, `_fix_spaced_characters()`, `_merge_short_lines()`
- Integration in `process_pdf()` als Post-Processing-Schritt
- **Deliverable**: "H T B L A" -> "HTBLA", kurze Zeilen korrekt zusammengefuehrt

### Phase 5: Vision-LLM Bild-Captioning (US6) -- Days 8-9

**Rationale**: Braucht LMStudio, daher erst nach Basis-Fixes.

- `test_image_captioner.py`: Unit-Tests mit Mock-API, Integration-Test mit Real-Endpoint
- `image_captioner.py`: Neues Modul -- `ImageCaptioner` Klasse
- `run_preprocessing.py`: Integration -- informative Bilder captionen, decorative skippen
- Config: LMStudio URL + Model in `env.yaml`
- **Deliverable**: ~170 informative Bilder erzeugen `.md` Dateien mit Beschreibung

### Phase 6: Architektur-Cleanup (US9) -- Day 10

**Rationale**: Konsolidierung nachdem alle Features implementiert sind.

- Migrate `main.py` Features (Manifest, DOCX/XLSX/PPTX, Summary) nach `run_preprocessing.py`
- Delete `main.py`
- Erweitere `media_processor.py` um DOCX/XLSX/PPTX Support
- Bugfix: `fetch_full_wiki_extended.py` leerer `media_metadata/` Ordner
- **Deliverable**: Ein Entry Point, alle Formate unterstuetzt

### Phase 7: Preprocessing Evaluation (US8) -- Days 11-13

**Rationale**: Evaluation braucht fertigen Preprocessing-Output als Input.

- `pip install sentence-transformers textstat`
- `evaluation/metrics.py`: Alle 7 Metrik-Klassen
- `evaluation/report.py`: JSON + Markdown Report-Generator
- `evaluation/run_eval_preprocessing.py`: CLI-Script
- `test_eval_metrics.py`: Tests fuer jede Metrik mit bekannten Inputs
- **Deliverable**: `python run_eval_preprocessing.py` berechnet alle 7 Metriken

### Phase 8: Deep Eval Bugfixes (US2) -- Day 14 [parallel ab Day 1 moeglich]

**Rationale**: Isolierte Fixes in anderem Modul, keine Abhaengigkeiten.

- `run_deep_evaluation.py`: rglob Set-Dedup in `analyze_documents()` und `analyze_images()`
- `env.yaml` + `core/llm_client.py`: temperature=0.0 Weiterleitung pruefen
- `strategy_generator.py`: `sorted(set(...))` fuer alle Listen
- **Deliverable**: Keine Duplikate, deterministischer LLM-Output

### Phase 9: CLI UX (US1) -- Days 15-16 [parallel ab Day 1 moeglich]

**Rationale**: Polish-Feature, keine funktionale Abhaengigkeit.

- `pipeline/shared/cli_utils.py`: Neues Modul
- Integration in 7 Skripte: `--no-color`, `sigint_handler`, `style()`
- Tests fuer `style()` mit/ohne Farbe, `set_use_color()`
- **Deliverable**: Professionelle CLI UX in allen Pipeline-Skripten

### Phase 10: Integration Testing + Polish -- Days 17-18

- End-to-End: `fetched/` -> Preprocessing -> `preprocessed/` -> DocumentLoader -> Chunks
- Verify NFR-005: timestamp, config-hash, code-version in Outputs
- Run full pipeline auf aktuellem LeoWiki-Dump
- Fix edge cases aus Integration
- **Deliverable**: Komplette Pipeline funktioniert lueckenlos

**Total estimated effort**: 18 fokussierte Tage.
Phasen 8+9 koennen parallel zu 1-7 laufen (andere Module).
Schema-Alignment (Phase 1) entsperrt alle nachfolgenden Phasen.

## Risk Mitigations

| Risk                                   | Mitigation                                                     | Phase |
| -------------------------------------- | -------------------------------------------------------------- | ----- |
| LMStudio nicht erreichbar (Vision-LLM) | `is_available()` Pre-Check, Graceful Skip, Warning loggen      | 5     |
| Spaced-Char Heuristik zu aggressiv     | Threshold konfigurierbar, Whitelist fuer bekannte Abkuerzungen | 4     |
| Strategy-YAML Format aendert sich      | Schema-Validierung beim Laden, Fallback auf Defaults           | 2     |
| Embeddings Creator Schema aendert sich | End-to-End-Test in `test_schema_e2e.py` als Regressionsschutz  | 1     |
| sentence-transformers Download-Groesse | Model wird einmal heruntergeladen und gecacht (~420MB)         | 7     |
| main.py hat Features die fehlen        | Systematischer Diff vor Loeschung, Migrate-Checklist           | 6     |

## Complexity Tracking

No Constitution violations. All changes:
- Use direct SDK/library calls (Article VIII: `openai`, `sentence-transformers`)
- Reuse existing code patterns (Article VII: Config, Enricher, Processor)
- Serve thesis deliverables directly (Article XI: FF1, FF3)
- Follow existing directory conventions (`pipeline/03_rag_preprocessing/`)
- Include tests per TDD mandate (NFR-002)
- Secrets via env.yaml, no hardcoded credentials (Article VI)
