# Tasks: RAG Preprocessing Pipeline (Feature 005)

## Status Overview

| Phase | Status | Progress |
|-------|--------|----------|
| Phase 1: Core Preprocessing | completed | 20/20 |
| Phase 2: Preprocessing Evaluation | pending | 0/8 |
| Phase 3: Embedder Integration | pending | 0/6 |
| Phase 4: Docker Integration | pending | 0/8 |
| Phase 5: Dashboard Integration | pending | 0/4 |
| **Total** | | **20/46** |

---

## Phase 1: RAG Preprocessing Core

### 1.1 Project Setup
- [x] **T-001**: Create `pipeline/03_rag_preprocessing/` directory
- [x] **T-002**: Create `__init__.py` with module docstring
- [x] **T-003**: Create `requirements.txt` with dependencies:
  - pyyaml>=6.0
  - beautifulsoup4>=4.12.0
  - lxml>=4.9.0
  - pypdf2>=3.0.0
  - python-docx>=1.0.0
  - openpyxl>=3.1.0
  - pytesseract>=0.3.10
- [x] **T-004**: Create `env.yaml` configuration file

### 1.2 Configuration
- [x] **T-005**: Create `config.py` with ConfigLoader class
- [x] **T-006**: Define input/output paths in config
- [x] **T-007**: Add content_type processing parameters

### 1.3 Page Processor
- [x] **T-008**: Create `page_processor.py` skeleton
- [x] **T-009**: Implement heading conversion (====== → #)
- [x] **T-010**: Implement text formatting (bold, italic, underline)
- [x] **T-011**: Implement link conversion ([[page|text]] → [text](page))
- [x] **T-012**: Implement image/media reference conversion
- [x] **T-013**: Implement code block conversion
- [x] **T-014**: Implement table conversion (^ ... ^ → | ... |)
- [x] **T-015**: Implement list conversion
- [ ] **T-016**: Add edge case handling for complex wiki syntax

### 1.4 Metadata Enricher
- [x] **T-017**: Create `metadata_enricher.py` skeleton
- [x] **T-018**: Implement YAML frontmatter generation
- [x] **T-019**: Load metadata from `page_metadata/*.json`
- [x] **T-020**: Integrate evaluation results (content_type, quality_score)

### 1.5 Strategy Loader
- [ ] **T-021**: Create `strategy_loader.py`
- [ ] **T-022**: Load `evaluation_*.json` from Stage 2
- [ ] **T-023**: Map page_id to content_type classification

### 1.6 Media Processor
- [ ] **T-024**: Create `media_processor.py` skeleton
- [ ] **T-025**: Implement PDF text extraction (PyPDF2)
- [ ] **T-026**: Implement DOCX text extraction (python-docx)
- [ ] **T-027**: Implement XLSX data extraction (openpyxl)
- [ ] **T-028**: Implement PPTX extraction (python-pptx)
- [ ] **T-029**: Add OCR fallback for images (pytesseract)
- [ ] **T-030**: Generate .txt files with frontmatter

### 1.7 Exporter
- [ ] **T-031**: Create `exporter.py`
- [ ] **T-032**: Create output directory structure (pages/, media/)
- [ ] **T-033**: Generate `manifest.json` with all processed files
- [ ] **T-034**: Add statistics (file counts, processing time)

### 1.8 Main Entrypoint
- [x] **T-035**: Create `main.py` with CLI interface
- [x] **T-036**: Add --input-dir argument (fetched data)
- [x] **T-037**: Add --evaluation-file argument (Stage 2 output)
- [x] **T-038**: Add --output-dir argument
- [ ] **T-039**: Add progress tracking integration

---

## Phase 2: Preprocessing Evaluation

### 2.1 Evaluator Core
- [ ] **T-040**: Create `pipeline/03b_preprocessing_eval/` directory
- [ ] **T-041**: Create `evaluator.py` skeleton
- [ ] **T-042**: Implement information preservation metric
- [ ] **T-043**: Implement link integrity check
- [ ] **T-044**: Implement structure preservation check

### 2.2 Quality Thresholds
- [ ] **T-045**: Define quality thresholds in config
- [ ] **T-046**: Generate quality report
- [ ] **T-047**: Flag files below threshold

---

## Phase 3: Embedder Integration Fix

### 3.1 Config Updates
- [ ] **T-048**: Update `pipeline/04_embeddings_creator/env.yaml` input paths
- [ ] **T-049**: Change input_dir to `data/preprocessed`

### 3.2 Document Loader Updates
- [ ] **T-050**: Update `document_loader.py` to find `preprocess_at_*` dirs
- [ ] **T-051**: Update YAML frontmatter parsing
- [ ] **T-052**: Test with preprocessed data

### 3.3 Rename Directory
- [ ] **T-053**: Rename `03_embeddings_creator` → `04_embeddings_creator`

---

## Phase 4: Docker Integration

### 4.1 Module Preprocessor
- [ ] **T-054**: Create `backend_services/module_preprocessor/` directory
- [ ] **T-055**: Create `Dockerfile` for preprocessor
- [ ] **T-056**: Create `entrypoint.py` with progress tracking
- [ ] **T-057**: Create `requirements.txt`

### 4.2 Docker Compose
- [ ] **T-058**: Add `module_preprocessor` service to docker-compose.yml
- [ ] **T-059**: Configure volumes (config, data, pipeline)
- [ ] **T-060**: Add to `stack-g-devdito` profile

### 4.3 Orchestrator Updates
- [ ] **T-061**: Add "preprocess" stage to orchestrator/server.py

---

## Phase 5: Dashboard Integration

### 5.1 UI Updates
- [ ] **T-062**: Add "RAG Preprocessing" stage card to dashboard
- [ ] **T-063**: Update pipeline.js for new stage
- [ ] **T-064**: Add preprocessing quality display

### 5.2 PHP Updates
- [ ] **T-065**: Update PipelineOrchestrator.php with preprocess stage

---

## Definition of Done

- [ ] All 209 pages converted to Markdown
- [ ] All .md files have valid YAML frontmatter
- [ ] Embedder successfully reads preprocessed data
- [ ] Full pipeline produces embeddings
- [ ] Docker integration working
- [ ] Dashboard shows all stages

---

## Notes

### Wiki Syntax Edge Cases to Handle:
- Nested tables
- Multi-line code blocks with special characters
- Internal links with anchors (page#section)
- Namespace aliases
- Plugin syntax (wrap, note, etc.)

### Media Extraction Priorities:
1. PDF (most common: 224 docs)
2. Images (93 files, OCR if needed)
3. Office documents (DOCX, XLSX, PPTX)
4. Archives (skip or list contents)

### Reference Implementation:
See `sources_dev_dito.yaml` Section 5 (ragflow_preprocessing) for the research implementation.
