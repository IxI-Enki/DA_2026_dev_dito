# Feature 005: RAG Preprocessing Pipeline

## Overview

| Field | Value |
|-------|-------|
| **Feature ID** | 005 |
| **Branch** | `005-rag-preprocessing-pipeline` |
| **Status** | Draft |
| **Created** | 2026-02-01 |
| **Author** | Jan Ritt (IxI-Enki) |
| **Priority** | CRITICAL |

## Problem Statement

### Current Situation
Die Pipeline ist **unterbrochen** zwischen Stage 2 (Evaluation) und Stage 4 (Embeddings):

```
Stage 1: Wiki Fetcher     ✅ Funktioniert
Stage 2: Fetch Evaluation ✅ Funktioniert
                          ⬇️
              ┌───────────────────────────┐
              │    MISSING LINK!          │
              │    Stage 3 fehlt          │
              └───────────────────────────┘
                          ⬇️
Stage 4: Embeddings       ❌ Erwartet Input aus Stage 3!
Stage 5: Qdrant Deploy    ❌ Keine Embeddings
```

### Root Cause Analysis

Der `embeddings_creator` (Stage 4) erwartet:
1. **Input-Verzeichnis**: `upload_at_*/pages/` und `upload_at_*/media/`
2. **Datei-Format**: `.md` Dateien mit **YAML Frontmatter**:
   ```markdown
   ---
   title: "Seitenname"
   page_id: "namespace:pagename"
   namespace: "namespace"
   content_type: "KNOWLEDGE"
   access_level: "public"
   ---
   
   # Inhalt hier
   ```
3. **Manifest-Datei**: `manifest.json` mit Metadaten

Aber wir liefern aktuell:
- `data/fetched/fetched_at_*/page_content/*.txt` (Raw Wiki-Syntax)
- `data/evaluated/evaluation_*.json` (nur Reports)

### Missing Components (aus sources_dev_dito.yaml)

**Stage 3: RAG Preprocessing** (Section 5)
- `page_processor.py` - Wiki-Syntax → Markdown
- `media_processor.py` - PDF/DOCX/XLSX → Plaintext
- `metadata_enricher.py` - YAML Frontmatter generieren
- `strategy_loader.py` - Strategien aus Stage 2 laden
- `exporter.py` - Output-Verzeichnis erstellen

**Stage 3b: Preprocessing Evaluation** (Section 6)
- `information_preservation.py` - Vollstaendigkeit pruefen
- `content_quality.py` - Qualitaet bewerten

**Stage 6: RAGAS Evaluation** (Section 7) - Optional
- End-to-End RAG-System Bewertung

---

## Functional Requirements

### FR-1: RAG Preprocessing (Stage 3)

#### FR-1.1: Page Processing
| ID | Requirement |
|----|-------------|
| FR-1.1.1 | System SHALL convert DokuWiki syntax to Markdown |
| FR-1.1.2 | System SHALL preserve all internal links |
| FR-1.1.3 | System SHALL convert wiki tables to Markdown tables |
| FR-1.1.4 | System SHALL handle code blocks and syntax highlighting |
| FR-1.1.5 | System SHALL extract and preserve heading structure |

#### FR-1.2: YAML Frontmatter Generation
| ID | Requirement |
|----|-------------|
| FR-1.2.1 | Each output file SHALL have YAML frontmatter |
| FR-1.2.2 | Frontmatter SHALL include: title, page_id, namespace |
| FR-1.2.3 | Frontmatter SHALL include: content_type (from Stage 2) |
| FR-1.2.4 | Frontmatter SHALL include: access_level (public/teacher) |
| FR-1.2.5 | Frontmatter SHALL include: source URL, timestamps |

#### FR-1.3: Media Processing
| ID | Requirement |
|----|-------------|
| FR-1.3.1 | System SHALL extract text from PDF files |
| FR-1.3.2 | System SHALL extract text from DOCX/DOC files |
| FR-1.3.3 | System SHALL extract data from XLSX files |
| FR-1.3.4 | System SHALL use OCR for images if needed |
| FR-1.3.5 | System SHALL generate .txt files with frontmatter |

#### FR-1.4: Strategy Integration
| ID | Requirement |
|----|-------------|
| FR-1.4.1 | System SHALL load strategies from Stage 2 evaluation |
| FR-1.4.2 | System SHALL apply content_type-specific processing |
| FR-1.4.3 | System SHALL route pages based on classification |

#### FR-1.5: Output Structure
| ID | Requirement |
|----|-------------|
| FR-1.5.1 | Output SHALL be in `data/preprocessed/preprocess_at_YYYYMMDD_HHMMSS/` |
| FR-1.5.2 | Pages SHALL be in `pages/` subdirectory |
| FR-1.5.3 | Media SHALL be in `media/` subdirectory |
| FR-1.5.4 | System SHALL create `manifest.json` with metadata |

### FR-2: Preprocessing Evaluation (Stage 3b)

#### FR-2.1: Quality Metrics
| ID | Requirement |
|----|-------------|
| FR-2.1.1 | System SHALL measure information preservation |
| FR-2.1.2 | System SHALL detect content loss during conversion |
| FR-2.1.3 | System SHALL verify link integrity |
| FR-2.1.4 | System SHALL check heading structure preservation |

#### FR-2.2: Quality Thresholds
| ID | Requirement |
|----|-------------|
| FR-2.2.1 | Information preservation SHALL be > 95% |
| FR-2.2.2 | Link integrity SHALL be 100% |
| FR-2.2.3 | System SHALL flag pages below threshold |

### FR-3: Embedder Integration Fix

#### FR-3.1: Input Compatibility
| ID | Requirement |
|----|-------------|
| FR-3.1.1 | Embedder SHALL read from `data/preprocessed/` |
| FR-3.1.2 | Embedder SHALL parse YAML frontmatter |
| FR-3.1.3 | Embedder SHALL use frontmatter for metadata |

---

## Technical Design

### Architecture

```
data/fetched/fetched_at_*/
    ├── page_content/*.txt      (DokuWiki syntax)
    ├── page_metadata/*.json
    └── media/*

              ⬇️  Stage 3: RAG Preprocessing

data/preprocessed/preprocess_at_*/
    ├── pages/*.md              (Markdown + YAML frontmatter)
    ├── media/*.txt             (Extracted text + frontmatter)
    └── manifest.json

              ⬇️  Stage 4: Embeddings Creator

data/embeddings/
    └── embedded_chunks.jsonl
```

### File Structure

```
pipeline/
├── 03_rag_preprocessing/       # NEW!
│   ├── __init__.py
│   ├── config.py
│   ├── main.py                 # Entrypoint
│   ├── page_processor.py       # Wiki → Markdown
│   ├── media_processor.py      # PDF/DOCX → Text
│   ├── metadata_enricher.py    # YAML Frontmatter
│   ├── strategy_loader.py      # Load from Stage 2
│   ├── exporter.py             # Output generation
│   ├── env.yaml
│   └── requirements.txt
├── 03b_preprocessing_eval/     # NEW!
│   ├── __init__.py
│   ├── evaluator.py
│   ├── metrics/
│   │   ├── information_preservation.py
│   │   └── content_quality.py
│   └── requirements.txt
└── 03_embeddings_creator/      # RENAME to 04_embeddings_creator
    └── (existing files)
```

### Dependencies

**Stage 3 (RAG Preprocessing):**
```
pyyaml>=6.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
pypdf2>=3.0.0
python-docx>=1.0.0
openpyxl>=3.1.0
pytesseract>=0.3.10  # OCR fallback
```

**Stage 3b (Preprocessing Evaluation):**
```
pyyaml>=6.0
difflib  # stdlib
```

---

## Success Criteria

| Criteria | Measurement |
|----------|-------------|
| All 209 pages converted to .md | File count |
| All .md files have valid frontmatter | YAML parse test |
| Embedder runs without input errors | Integration test |
| Full pipeline produces embeddings | end-to-end test |
| Qdrant contains searchable vectors | Query test |

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Complex Wiki syntax edge cases | Medium | Extensive testing with real data |
| Media extraction failures | Low | OCR fallback, skip gracefully |
| Large file processing time | Medium | Progress tracking, batch processing |
