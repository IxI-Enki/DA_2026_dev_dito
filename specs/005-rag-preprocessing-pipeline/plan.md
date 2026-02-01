# Implementation Plan: RAG Preprocessing Pipeline

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CURRENT PIPELINE STATE                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Stage 1: Wiki Fetcher ────────────────────────────────────────────────►│
│  [01_wiki_fetcher/]                                                     │
│       │                                                                 │
│       ▼                                                                 │
│  data/fetched/fetched_at_*/                                             │
│       ├── page_content/*.txt      (DokuWiki raw syntax)                 │
│       ├── page_metadata/*.json    (API metadata)                        │
│       ├── page_links/*.json       (Link data)                           │
│       └── media/*                 (Binary files)                        │
│       │                                                                 │
│       ▼                                                                 │
│  Stage 2: Fetch Evaluation ────────────────────────────────────────────►│
│  [02_deep_evaluation/]                                                  │
│       │                                                                 │
│       ▼                                                                 │
│  data/evaluated/                                                        │
│       └── evaluation_*.json       (Quality scores, classifications)     │
│                                                                         │
│  ════════════════════════════════════════════════════════════════════   │
│  ███████████████████ MISSING STAGES █████████████████████████████████   │
│  ════════════════════════════════════════════════════════════════════   │
│                                                                         │
│       ▼                                                                 │
│  Stage 3: RAG Preprocessing ◄──────────────────────────────── NEW! ────►│
│  [03_rag_preprocessing/]                                                │
│       │                                                                 │
│       ▼                                                                 │
│  data/preprocessed/preprocess_at_*/                                     │
│       ├── pages/*.md              (Markdown + YAML frontmatter)         │
│       ├── media/*.txt             (Extracted text + frontmatter)        │
│       └── manifest.json                                                 │
│       │                                                                 │
│       ▼                                                                 │
│  Stage 3b: Preprocessing Eval ◄────────────────────────────── NEW! ────►│
│  [03b_preprocessing_eval/]                                              │
│       │                                                                 │
│       ▼                                                                 │
│  ════════════════════════════════════════════════════════════════════   │
│                                                                         │
│  Stage 4: Embeddings Creator ──────────────────────────────────────────►│
│  [04_embeddings_creator/]  (renamed from 03_)                           │
│       │                                                                 │
│       ▼                                                                 │
│  data/embeddings/embedded_chunks.jsonl                                  │
│       │                                                                 │
│       ▼                                                                 │
│  Stage 5: Qdrant Deploy ───────────────────────────────────────────────►│
│  [module_deployer]                                                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Phase 1: RAG Preprocessing Core (Priority: HIGH)

### 1.1 Project Structure

```
pipeline/03_rag_preprocessing/
├── __init__.py
├── config.py               # Configuration loader
├── main.py                 # CLI entrypoint
├── page_processor.py       # Wiki syntax → Markdown
├── media_processor.py      # PDF/DOCX/XLSX → Text
├── metadata_enricher.py    # Generate YAML frontmatter
├── strategy_loader.py      # Load evaluation strategies
├── exporter.py             # Output directory/manifest
├── env.yaml                # Configuration
└── requirements.txt
```

### 1.2 Page Processor

**Input:** `data/fetched/*/page_content/*.txt` (DokuWiki syntax)

**Conversions:**
```
DokuWiki                    →  Markdown
====== H1 ======            →  # H1
===== H2 =====              →  ## H2
==== H3 ====                →  ### H3
**bold**                    →  **bold**
//italic//                  →  *italic*
[[page|text]]               →  [text](page)
{{media.jpg}}               →  ![](media.jpg)
<code lang>                 →  ```lang
^ Header ^ Header ^         →  | Header | Header |
</code>                     →  ```
```

**Output:** `.md` file with YAML frontmatter

### 1.3 Metadata Enricher

Generates YAML frontmatter from multiple sources:

```yaml
---
# Core identification
title: "Seitenname"
page_id: "namespace:pagename"
namespace: "namespace"
source: "https://leowiki.htl-leonding.ac.at/doku.php?id=..."

# From Stage 2 Evaluation
content_type: "KNOWLEDGE"       # KNOWLEDGE, PORTAL, NEWS, etc.
quality_score: 0.78
embedding_recommendation: "include"

# Access control
access_level: "public"          # public | teacher_only

# Timestamps
created_at: "2025-12-15T10:30:00"
modified_at: "2026-01-20T14:22:00"
fetched_at: "2026-02-01T12:02:11"

# Relationships
links_to: ["page1", "page2"]
linked_from: ["page3"]
media_refs: ["image.png", "doc.pdf"]
---
```

### 1.4 Strategy Loader

Loads evaluation results from Stage 2:

```python
class StrategyLoader:
    def load_evaluation(self, eval_file: Path) -> Dict:
        """Load evaluation_*.json from Stage 2"""
        
    def get_page_classification(self, page_id: str) -> str:
        """Get content_type for a page"""
        
    def get_processing_strategy(self, content_type: str) -> Dict:
        """Get processing parameters for content type"""
```

### 1.5 Media Processor

```python
class MediaProcessor:
    def process_pdf(self, path: Path) -> str:
        """Extract text from PDF using PyPDF2"""
        
    def process_docx(self, path: Path) -> str:
        """Extract text from DOCX using python-docx"""
        
    def process_xlsx(self, path: Path) -> str:
        """Extract data from XLSX using openpyxl"""
        
    def process_image(self, path: Path) -> str:
        """OCR via pytesseract (fallback)"""
```

## Phase 2: Preprocessing Evaluation (Priority: MEDIUM)

### 2.1 Quality Metrics

```python
class PreprocessingEvaluator:
    def evaluate_information_preservation(
        self, 
        original: str,  # Wiki syntax
        processed: str  # Markdown
    ) -> float:
        """Check if all information is preserved (0.0-1.0)"""
        
    def evaluate_link_integrity(
        self,
        original_links: List[str],
        processed_links: List[str]
    ) -> float:
        """Check if all links are preserved"""
        
    def evaluate_structure_preservation(
        self,
        original: str,
        processed: str
    ) -> float:
        """Check heading structure, lists, tables"""
```

## Phase 3: Embedder Integration Fix (Priority: HIGH)

### 3.1 Update Embedder Config

```yaml
# pipeline/04_embeddings_creator/env.yaml (updated)
PATHS:
  input_dir: D:/.../dev_dito/data/preprocessed
  # Look for latest preprocess_at_* directory
```

### 3.2 Update Document Loader

```python
# document_loader.py changes
def find_input_directory(self) -> Path:
    """Find latest preprocessed directory"""
    preprocess_dir = DATA_PATH / "preprocessed"
    # Find preprocess_at_* directories
```

## Phase 4: Docker Integration (Priority: MEDIUM)

### 4.1 Module Preprocessor

```
backend_services/module_preprocessor/
├── Dockerfile
├── entrypoint.py
└── requirements.txt
```

### 4.2 Update docker-compose.yml

Add `module_preprocessor` service between evaluator and embedder.

## Phase 5: Dashboard Integration (Priority: LOW)

Update DokuWiki dashboard to show new preprocessing stage.

---

## Data Flow Example

**Input (Wiki syntax):**
```
====== Raumliste ======

Liste aller Raeume im HTL Gebaeude.

| Raum | Beschreibung |
^ E01 ^ Sekretariat ^
^ E02 ^ Direktion ^

Siehe auch: [[verwaltung:kontakt|Kontakt]]
```

**Output (Markdown with frontmatter):**
```markdown
---
title: "Raumliste"
page_id: "verwaltung:raumliste"
namespace: "verwaltung"
content_type: "TABLE_DATA"
access_level: "public"
quality_score: 0.82
---

# Raumliste

Liste aller Raeume im HTL Gebaeude.

| Raum | Beschreibung |
|------|--------------|
| E01  | Sekretariat  |
| E02  | Direktion    |

Siehe auch: [Kontakt](verwaltung:kontakt)
```

---

## Timeline Estimate

| Phase | Effort | Priority |
|-------|--------|----------|
| Phase 1: Core Preprocessing | 4-6h | HIGH |
| Phase 2: Preprocessing Eval | 2h | MEDIUM |
| Phase 3: Embedder Fix | 1h | HIGH |
| Phase 4: Docker | 2h | MEDIUM |
| Phase 5: Dashboard | 1h | LOW |
| **Total** | **10-12h** | |
