# Tasks: Analysis & Production Polish

**Input**: Design documents from `/specs/009-analysis-and-production-polish/`
**Prerequisites**: plan.md (required), spec.md (required)
**Tests**: Included per NFR-002 (TDD mandate -- tests VOR oder GLEICHZEITIG mit Implementation)
**Organization**: Tasks grouped by user story in dependency order (spec-recommended)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US9)
- Exact file paths included in all descriptions

## Path Conventions

- Pipeline modules: `pipeline/01_wiki_fetcher/`, `pipeline/02_deep_evaluation/`, `pipeline/03_rag_preprocessing/`
- Shared modules: `pipeline/shared/`
- Tests: `pipeline/03_rag_preprocessing/tests/`
- Config (02): `pipeline/02_deep_evaluation/env.yaml`
- Config (03): `pipeline/03_rag_preprocessing/env.yaml`
- Thesis-Zuordnung: FF1, FF3, J4, J6

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependencies, directory scaffolding

- [x] T001 Verify branch `009-analysis-and-production-polish` is active and clean
- [x] T002 Install new Python dependencies: `pip install sentence-transformers textstat openai`
- [x] T003 [P] Create `pipeline/shared/__init__.py` (new shared module directory)
- [x] T004 [P] Create `pipeline/03_rag_preprocessing/evaluation/__init__.py` (new evaluation subdirectory)

---

## Phase 2: US3 -- Schema-Alignment (Priority: P0-Blocker) [FF1, FF3, J4, J6] -- MVP

**Goal**: Preprocessing-Output exakt kompatibel mit `document_loader.py` (Stage 4) machen. Ohne dies ist die gesamte Evaluations-Pipeline blockiert.

**Independent Test**: Exporter erzeugt `.md`-Datei -> `DocumentLoader.extract_frontmatter()` parst sie -> alle Pflichtfelder vorhanden und korrekt typisiert.

### Tests for US3

> **Write these tests FIRST, ensure they FAIL before implementation**

- [x] T005 [P] [US3] Write E2E schema test in `pipeline/03_rag_preprocessing/tests/test_schema_e2e.py` -- Exporter output -> DocumentLoader roundtrip. Assert parseability AND explicit presence+type of ALL 14 required frontmatter fields: `title` (str), `namespace` (str), `source` (str), `page_id`/`media_id` (str), `access_level` (str), `content_type` (str), `freshness_score` (float), `freshness_category` (str in {fresh,recent,outdated,archived}), `chunking_method` (str), `last_modified` (str, ISO), `author` (str), `content_hash` (str, 32-char hex), `links_to` (list), `linked_from` (list). NOTE: `Document.__post_init__()` only extracts 7 fields as properties; remaining 7 are only in `frontmatter` dict -- test both access paths
- [x] T006 [P] [US3] Extend tests in `pipeline/03_rag_preprocessing/tests/test_exporter.py` -- test page frontmatter has all Qdrant-Schema fields, test media frontmatter uses media_id not page_id, test media output has `.md` extension not `.txt`, test content_hash is MD5 of body without frontmatter, test pages/ and media/ subdirectories created
- [x] T007 [P] [US3] Extend tests in `pipeline/03_rag_preprocessing/tests/test_metadata_enricher.py` -- test field name is `last_modified` not `modified_at`, test `linked_from` populated from backlink data, test source URL generation

### Implementation for US3

- [x] T008 [US3] Rewrite `pipeline/03_rag_preprocessing/exporter.py` -- Qdrant-compatible schema with `_build_page_frontmatter()` and `_build_media_frontmatter()`, `.md` extension for media, `content_hash` via MD5, separate `pages/` and `media/` subdirectories, `manifest.json` generation
- [x] T009 [US3] Modify `pipeline/03_rag_preprocessing/metadata_enricher.py` -- rename `modified_at` to `last_modified` in `generate_frontmatter()`, add `linked_from` field populated from `page_backlinks/*.json`, ensure `source` URL uses correct wiki base URL format
- [x] T010 [US3] Modify `pipeline/03_rag_preprocessing/metadata_enricher.py` `MediaMetadataEnricher` -- align frontmatter schema to match pages (same fields with `media_id` instead of `page_id`), add `content_type`, `freshness_score`, `freshness_category`, `chunking_method`, `content_hash`, `last_modified`
- [x] T011a [US3] Update `pipeline/03_rag_preprocessing/run_preprocessing.py` -- load backlinks data from `page_backlinks/*.json` into a lookup dict keyed by page_id at startup
- [x] T011b [US3] Update `pipeline/03_rag_preprocessing/run_preprocessing.py` -- restructure page processing loop to collect all page dicts (with `source`, `last_modified`, `linked_from` from backlinks, `content_type`, `chunking_method`) into a `pages: list[dict]` before export
- [x] T011c [US3] Update `pipeline/03_rag_preprocessing/run_preprocessing.py` -- restructure media processing to collect all media dicts (with full Qdrant-schema metadata) into a `media: list[dict]` before export
- [x] T011d [US3] Update `pipeline/03_rag_preprocessing/run_preprocessing.py` -- call new Exporter API `export(pages, media, output_base)` to write both collections in a single pass
- [x] T012 [US3] Run all tests including `test_schema_e2e.py` and verify `DocumentLoader` from `pipeline/03_embeddings_creator/document_loader.py` can load the generated output without errors

**Checkpoint**: Stage 4 (Embeddings Creator) can now successfully load Stage 3 output. Pipeline data flow is unblocked.

---

## Phase 3: US4 -- Strategy-Integration (Priority: P1-Critical) [FF1, FF3]

**Goal**: Preprocessing-Pipeline konsumiert `preprocessing_strategies.yaml` (YAML) aus Stage 2 statt `page_strategies.json` (JSON). Content-Type-Routing und Chunking-Methoden durchgaengig.

**Independent Test**: Load a sample `preprocessing_strategies.yaml` -> verify page lookup returns correct ContentType + chunking_method per category, verify ignored pages are skipped, verify unknown pages get defaults.

### Tests for US4

> **Write these tests FIRST, ensure they FAIL before implementation**

- [x] T013 [US4] Extend tests in `pipeline/03_rag_preprocessing/tests/test_strategy_loader.py` -- test YAML loading of `preprocessing_strategies.yaml`, test wiki page category mapping via `_WIKI_CATEGORY_MAP` (knowledge_articles->KNOWLEDGE/recursive_header, portals->PORTAL/parent_context, news->NEWS/naive, ignored->IGNORED/none), test document category mapping via `_DOC_CATEGORY_MAP` (theses->KNOWLEDGE/recursive_header, forms->FORM/metadata_only), test `MediaStrategy` loading (informative_images->caption_and_index, decorative->skip), test `is_ignored()`, test fallback to `page_strategies.json`, test default for unknown page_id

### Implementation for US4

- [x] T014 [US4] Rewrite `pipeline/03_rag_preprocessing/strategy_loader.py` -- new `ContentType` enum (KNOWLEDGE/NEWS/PORTAL/FORM/ARCHIVED/IGNORED), new `PageStrategy` with `chunking_method` and `action` fields, new `MediaStrategy` dataclass, `_load_yaml()` with inverted index from category lists to per-ID lookup, `_load_legacy_json()` for backwards compat, `get_media_strategy()`, `is_ignored()`
- [x] T015 [US4] Update `pipeline/03_rag_preprocessing/run_preprocessing.py` -- use `strategy_loader.is_ignored()` to skip pages, pass `chunking_method` and `content_type` from strategy into page/media dicts, route media via `get_media_strategy()` for Vision-LLM preparation
- [x] T016 [US4] Run tests and verify routing with sample `preprocessing_strategies.yaml` matching the structure from `pipeline/02_deep_evaluation/generators/strategy_generator.py`

**Checkpoint**: Pipeline correctly reads YAML strategies and routes content types. Ignored pages are skipped. Default fallbacks work.

---

## Phase 4: US5 -- Freshness-Scoring (Priority: P1-Critical) [FF1, J6]

**Goal**: Korrekte Aktualitaets-Scores (Float 0.0-1.0) + Kategorien (fresh/recent/outdated/archived) pro Dokument, basierend auf der 6-stufigen Hybrid-Formel aus der Spec.

**Independent Test**: Call `calculate_freshness()` with known dates -> verify score + category match spec table exactly.

### Tests for US5

> **Write these tests FIRST, ensure they FAIL before implementation**

- [x] T017 [US5] Extend tests in `pipeline/03_rag_preprocessing/tests/test_metadata_enricher.py` -- test 26-day-old page returns score=1.0/category="fresh", test 60-day-old returns 0.85/"fresh", test 120-day-old returns 0.70/"recent", test 300-day-old returns 0.55/"recent", test 650-day-old returns 0.35/"outdated", test 1500-day-old returns 0.20/"archived", test invalid date returns default, test `FreshnessResult` dataclass has both score (float) and category (str)

### Implementation for US5

- [x] T018 [US5] Implement `FreshnessResult` dataclass and `calculate_freshness()` method in `pipeline/03_rag_preprocessing/metadata_enricher.py` -- replace old `calculate_freshness_score()` (string-only), implement 6-tier hybrid formula (<30d: 1.0/fresh, <90d: 0.85/fresh, <180d: 0.70/recent, <365d: 0.55/recent, <730d: 0.35/outdated, >=730d: 0.20/archived)
- [x] T019 [US5] Update `pipeline/03_rag_preprocessing/run_preprocessing.py` -- use new `calculate_freshness()` return value, write both `freshness_score` (float) and `freshness_category` (str) into page and media dicts
- [x] T020 [US5] Run tests and validate with spec examples

**Checkpoint**: Every document in output has `freshness_score` (Float) and `freshness_category` (String) in frontmatter.

---

## Phase 5: US7 -- PDF-Qualitaet (Priority: P2-High) [FF1, J4]

**Goal**: Sauberer Text aus PDFs -- Spaced-Character-Korrektur und Paragraph-Merging fuer bessere Chunk-Qualitaet.

**Independent Test**: Pass known spaced text ("H T B L A  L e o n d i n g") -> get "HTBLA Leonding". Pass short-line PDF text -> get merged paragraphs. Headings and lists remain intact.

### Tests for US7

> **Write these tests FIRST, ensure they FAIL before implementation**

- [x] T021 [US7] Extend tests in `pipeline/03_rag_preprocessing/tests/test_media_processor.py` -- test `_fix_spaced_characters()` with "H T B L A  L e o n d i n g" -> "HTBLA Leonding", test with mixed spaced/normal lines, test `_merge_short_lines()` joins consecutive short lines (<40 chars), test merge respects sentence boundaries, test merge preserves list items (-, *, digit prefix), test merge preserves headings (# prefix), test merge preserves empty-line paragraph breaks, test `clean_pdf_text()` chains both operations

### Implementation for US7

- [x] T022 [P] [US7] Implement `_fix_spaced_characters()` in `pipeline/03_rag_preprocessing/media_processor.py` -- heuristic: if >60% of words on a line are single characters, join them and split on double-spaces
- [x] T023 [P] [US7] Implement `_merge_short_lines()` in `pipeline/03_rag_preprocessing/media_processor.py` -- join consecutive lines shorter than threshold (default 40), respect sentence boundaries, preserve lists/headings/empty-line separators
- [x] T024 [US7] Implement `clean_pdf_text()` in `pipeline/03_rag_preprocessing/media_processor.py` -- chain `_fix_spaced_characters()` then `_merge_short_lines()`, integrate as post-processing step called from `process_pdf()` after text extraction
- [x] T025 [US7] Run tests and validate with real PDF text samples from `data/preprocessed/`

**Checkpoint**: PDF text extraction produces clean, readable paragraphs without layout artifacts.

---

## Phase 6: US6 -- Vision-LLM Bild-Captioning (Priority: P1-Critical) [FF1, FF3]

**Goal**: Informative Bilder werden durch Qwen2.5-VL beschrieben und als `.md` Dateien im Qdrant-Schema exportiert. Decorative Bilder werden uebersprungen.

**Independent Test**: Mock LMStudio API -> caption returns description text -> output is `.md` with correct frontmatter. Test graceful failure when API unreachable.

### Tests for US6

> **Write these tests FIRST, ensure they FAIL before implementation**

- [x] T026 [US6] Write tests in `pipeline/03_rag_preprocessing/tests/test_image_captioner.py` -- test `caption()` returns description string with mocked OpenAI client, test `is_available()` returns False when endpoint unreachable, test graceful failure (returns empty string on error, logs warning), test base64 image encoding, test decorative images are NOT captioned (strategy routing in orchestrator), test output `.md` file has correct frontmatter schema

### Implementation for US6

- [x] T027 [US6] Create `pipeline/03_rag_preprocessing/image_captioner.py` -- `ImageCaptioner` class with lazy OpenAI client init, `caption(image_path)` method (base64 encode, German prompt, return description), `is_available()` pre-check, `CAPTIONABLE_EXTENSIONS` constant
- [x] T028 [US6] Add VISION_LLM configuration section to `pipeline/03_rag_preprocessing/env.yaml` -- `api_base`, `model`, `timeout` values (loaded by config.py, no hardcoded defaults in ImageCaptioner constructor per Article II-B)
- [x] T029 [US6] Update `pipeline/03_rag_preprocessing/run_preprocessing.py` -- init `ImageCaptioner` from config, check `is_available()` before batch, iterate informative images from `MediaStrategy`, call `captioner.caption()`, build media dict with Qdrant-schema frontmatter, skip decorative images
- [x] T030 [US6] Run tests with mock, then validate with real LMStudio endpoint if available

**Checkpoint**: Informative images produce `.md` files with Vision-LLM descriptions. Decorative images skipped. Pipeline continues when LMStudio is down.

---

## Phase 7: US9 -- Architektur-Cleanup (Priority: P3-Medium) [J4]

**Goal**: Ein einziger Entry Point (`run_preprocessing.py`), keine duplizierte Logik, alle Media-Formate unterstuetzt.

**Independent Test**: `python run_preprocessing.py --help` works. DOCX/XLSX/PPTX files discovered and processed. `main.py` does not exist. No `media_metadata/` directory created by fetcher.

### Tests for US9

- [x] T031 [US9] Write integration test verifying single entry point works and all media formats (PDF, DOCX, XLSX, PPTX, PNG, JPG) are discovered in `pipeline/03_rag_preprocessing/tests/`

### Implementation for US9

- [x] T032 [US9] Migrate unique features from `pipeline/03_rag_preprocessing/main.py` to `pipeline/03_rag_preprocessing/run_preprocessing.py` -- manifest generation (`_generate_manifest()`), detailed summary output (`_print_summary()`), backlinks loading from `page_links/`
- [x] T033 [US9] Extend `pipeline/03_rag_preprocessing/media_processor.py` -- add `DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".pptx"}`, add `process_docx()`, `process_xlsx()`, `process_pptx()` methods (migrate from `main.py` extraction logic), update `process_media_directory()` to handle all formats
- [x] T034 [US9] Delete `pipeline/03_rag_preprocessing/main.py` after verifying all features migrated to `run_preprocessing.py` and `media_processor.py`
- [x] T035 [P] [US9] Fix `pipeline/01_wiki_fetcher/fetch_full_wiki_extended.py` -- remove the code that creates the empty `media_metadata/` directory
- [x] T036 [US9] Run tests and validate: single entry point, all formats processed, no `media_metadata/` created

**Checkpoint**: One entry point per module. All media formats supported. No dead code.

---

## Phase 8: US8 -- Preprocessing Evaluation (Priority: P1-Critical) [FF1, FF3, J4]

**Goal**: 7-Metrik-Suite misst Preprocessing-Qualitaet quantitativ. JSON-Report mit per-Dokument-Scores + Aggregat-Summary. Regressions-Schutz.

**Independent Test**: `python run_eval_preprocessing.py` on actual preprocessed output -> produces JSON report with all 7 metrics, aggregates pass thresholds.

### Tests for US8

> **Write these tests FIRST, ensure they FAIL before implementation**

- [x] T037 [US8] Write tests in `pipeline/03_rag_preprocessing/tests/test_eval_metrics.py` -- test ContentCompletenessMetric with known char ratios (threshold >=0.85), test SemanticSimilarityMetric with identical/different texts, test EntityPreservationMetric preserves dates/emails/URLs (threshold >=0.95), test LinkIntegrityMetric with DokuWiki->Markdown link pairs (threshold >=0.95), test NoiseDetectionMetric detects wiki-syntax/mojibake/HTML (threshold <=2%), test ReadabilityMetric with German threshold 20 (not English 60), test StructurePreservationMetric for headings/lists/paragraphs (threshold >=0.90), test DocumentScore dataclass, test regression: completeness <0.90 -> fail

### Implementation for US8

- [x] T038 [P] [US8] Implement `ContentCompletenessMetric` in `pipeline/03_rag_preprocessing/evaluation/metrics.py` -- char ratio adjusted for markup removal
- [x] T039 [P] [US8] Implement `SemanticSimilarityMetric` in `pipeline/03_rag_preprocessing/evaluation/metrics.py` -- cosine similarity using `paraphrase-multilingual-mpnet-base-v2`, with normalized SequenceMatcher fallback (strips all DokuWiki+Markdown markup, link-aware text extraction)
- [x] T040 [P] [US8] Implement `EntityPreservationMetric` in `pipeline/03_rag_preprocessing/evaluation/metrics.py` -- regex-based extraction of dates, rooms, emails, URLs (strips wiki markup from original before entity extraction)
- [x] T041 [P] [US8] Implement `LinkIntegrityMetric` in `pipeline/03_rag_preprocessing/evaluation/metrics.py` -- DokuWiki link text + target preservation check
- [x] T042 [P] [US8] Implement `NoiseDetectionMetric` in `pipeline/03_rag_preprocessing/evaluation/metrics.py` -- detect wiki-syntax reste, mojibake, HTML artefakte
- [x] T043 [P] [US8] Implement `ReadabilityMetric` in `pipeline/03_rag_preprocessing/evaluation/metrics.py` -- German-adapted Flesch Reading Ease via `textstat`, structured-content detection (>60% lists/tables -> threshold passthrough)
- [x] T044 [P] [US8] Implement `StructurePreservationMetric` in `pipeline/03_rag_preprocessing/evaluation/metrics.py` -- headings/lists weighted 2x, paragraphs weighted 1x (lenient ratio for wiki/markdown whitespace divergence)
- [x] T045 [US8] Implement `DocumentScore` dataclass and evaluation runner logic in `pipeline/03_rag_preprocessing/evaluation/metrics.py` -- orchestrates all 7 metrics per document
- [x] T046 [US8] Implement `pipeline/03_rag_preprocessing/evaluation/report.py` -- JSON report with per-document scores + aggregate summary, Markdown report for human review
- [x] T047 [US8] Implement `pipeline/03_rag_preprocessing/evaluation/run_eval_preprocessing.py` -- CLI script with `--fetched-dir` and `--preprocessed-dir` args, pairs originals with outputs, runs all metrics, generates report
- [x] T048 [US8] Run evaluation on actual preprocessed output from `data/preprocessed/` and verify aggregate thresholds -- **RESULT**: 196 docs evaluated, 152/196 (77.6%) pass all thresholds, regression check PASS (all 7 metrics >= 90% aggregate pass rate)

**Checkpoint**: `python run_eval_preprocessing.py` produces quantitative quality report. Regressions detectable. **VERIFIED 2026-02-16**.

---

## Phase 9: US2 -- Deep Evaluation Bugfixes (Priority: P2-High) [FF3] -- parallel ab Phase 1

**Goal**: Korrekte Datei-Zaehlung (keine rglob-Duplikate), deterministische LLM-Klassifikation (temperature=0.0), keine Duplikate in YAML-Output, saubere mehrzeilige Log-Ausgabe.

**Independent Test**: Run deep eval file discovery on directory with mixed-case extensions -> each file counted exactly once. Verify temperature=0.0 in LLM request. Verify YAML output has unique lists. Verify multi-line summaries logged as cohesive block.

> **NOTE**: This phase touches `pipeline/02_deep_evaluation/` which is independent from `pipeline/03_rag_preprocessing/`. Can be worked on in parallel with Phases 2-8.

### Tests for US2

- [ ] T049 [US2] Write tests verifying rglob dedup (mixed-case extensions produce unique file list), temperature passthrough (config value reaches LLM client), YAML list uniqueness (no duplicate page_ids or filenames), multiline summary logging (output as cohesive block without per-line timestamps)

### Implementation for US2

- [ ] T050 [P] [US2] Fix rglob dedup in `pipeline/02_deep_evaluation/run_deep_evaluation.py` -- replace list-based file collection with `set[Path]` in `analyze_documents()` (lines ~226-230) and `analyze_images()` (lines ~289-291), then `sorted()` for deterministic order
- [ ] T051 [P] [US2] Fix temperature passthrough in `pipeline/02_deep_evaluation/env.yaml` -- verify `temperature: 0.0` is set (default in config.py is 0.3), trace through `pipeline/02_deep_evaluation/core/llm_client.py` to confirm value reaches the LLM endpoint call
- [ ] T052 [P] [US2] Fix YAML dedup in `pipeline/02_deep_evaluation/generators/strategy_generator.py` -- wrap all `include_ids` and `files` lists with `sorted(set(...))` in `_derive_wiki_strategies()`, `_derive_document_strategies()`, `_derive_media_strategies()`
- [ ] T052b [P] [US2] Fix multiline summary logging in `pipeline/02_deep_evaluation/run_deep_evaluation.py` -- ensure multi-line summary blocks are logged as a single cohesive block without per-line timestamp prefixes (AC3)
- [ ] T053 [US2] Run tests and validate fixes

**Checkpoint**: File counts are correct. LLM output is deterministic. YAML lists have no duplicates.

---

## Phase 10: US1 -- CLI UX Portierung (Priority: P3-Medium) [J4] -- parallel ab Phase 1

**Goal**: Farbige Konsolenausgabe, einheitliche Help-Funktionen, Signal-Handler in allen 7 Pipeline-Skripten.

**Independent Test**: Run any pipeline script with `--no-color` -> no ANSI escape sequences in output. Press Ctrl+C -> yellow abort banner with exit code 130. Run with `-h` -> 8-section help template.

> **NOTE**: This phase creates `pipeline/shared/cli_utils.py` and modifies scripts across all 3 pipeline stages. Independent from preprocessing logic changes.

### Tests for US1

- [ ] T054 [US1] Write tests for `pipeline/shared/cli_utils.py` -- test `style()` returns ANSI-wrapped text when color enabled, test `style()` returns plain text when color disabled via `set_use_color(False)`, test `create_sigint_handler()` calls callback and exits with 130, test `print_help_banner()` outputs all 8 sections, test `enable_windows_ansi()` runs without error on Windows

### Implementation for US1

- [ ] T055 [US1] Create `pipeline/shared/cli_utils.py` -- implement `enable_windows_ansi()`, `set_use_color()`, `style()`, `create_sigint_handler()`, `print_help_banner()` (8-section template: What, Usage, Parameters, Options, Examples, Configuration, Output, Exit Codes)
- [ ] T056 [P] [US1] Integrate cli_utils into `pipeline/01_wiki_fetcher/fetch_full_wiki_extended.py` -- add `--no-color` arg, register `sigint_handler`, replace raw `print()` with `style()` calls
- [ ] T057 [P] [US1] Integrate cli_utils into `pipeline/01_wiki_fetcher/incremental_fetcher.py` -- add `--no-color` arg, register `sigint_handler`
- [ ] T058 [P] [US1] Integrate cli_utils into `pipeline/01_wiki_fetcher/resume_fetch.py` -- add `--no-color` arg, register `sigint_handler`
- [ ] T059 [P] [US1] Integrate cli_utils into `pipeline/02_deep_evaluation/run_deep_evaluation.py` -- add `--no-color` arg, register `sigint_handler`, replace summary prints with `style()`
- [ ] T060 [P] [US1] Integrate cli_utils into `pipeline/02_deep_evaluation/run_evaluation.py` -- add `--no-color` arg, register `sigint_handler`
- [ ] T061 [P] [US1] Integrate cli_utils into `pipeline/02_deep_evaluation/run_strategy_generation.py` -- add `--no-color` arg, register `sigint_handler`
- [ ] T062 [P] [US1] Integrate cli_utils into `pipeline/03_rag_preprocessing/run_preprocessing.py` -- add `--no-color` arg, register `sigint_handler`, replace summary prints with `style()`
- [ ] T063 [US1] Validate all 7 scripts: run with `--no-color`, verify no ANSI codes; run with `-h`, verify 8-section help; test Ctrl+C abort banner

**Checkpoint**: All pipeline scripts have consistent, professional CLI UX.

---

## Phase 11: Polish & Integration Testing [FF1, FF3, J4, J6]

**Purpose**: End-to-end validation, NFR compliance, edge case fixes

- [ ] T064 Run end-to-end pipeline: `data/fetched/` -> Stage 3 Preprocessing -> `data/preprocessed/` -> `DocumentLoader` from Stage 4 -> verify all documents load
- [ ] T065 Verify NFR-005 (Reproduzierbarkeit): timestamp, config-hash, code-version present in all output manifests and reports
- [ ] T066 Run full pipeline on current LeoWiki dump and verify data flow chain is lueckenlos
- [ ] T067 Fix edge cases discovered during integration testing
- [ ] T068 Code cleanup: verify `from __future__ import annotations` in all new files, type hints, PEP 8 compliance

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies -- start immediately
- **US3 (Phase 2)**: Depends on Setup -- **BLOCKS all other preprocessing stories** (US4, US5, US6, US7, US8, US9)
- **US4 (Phase 3)**: Depends on US3 (needs correct schema to route into)
- **US5 (Phase 4)**: Depends on US3 (freshness fields must exist in schema)
- **US7 (Phase 5)**: Depends on US3 (PDF output must use correct schema)
- **US6 (Phase 6)**: Depends on US4 (needs MediaStrategy for routing informative vs decorative)
- **US9 (Phase 7)**: Depends on US3-US7 (consolidation after features are complete)
- **US8 (Phase 8)**: Depends on US3+US7 (needs complete preprocessed output to evaluate)
- **US2 (Phase 9)**: **No preprocessing dependencies** -- can start in parallel from Phase 1 (different module: `02_deep_evaluation/`)
- **US1 (Phase 10)**: **No preprocessing dependencies** -- can start in parallel from Phase 1 (different module: `shared/`)
- **Polish (Phase 11)**: Depends on all user stories being complete

### User Story Dependencies

```text
[Phase 1: Setup] ─────────────────────────────────────────────────────────
       │                    │                               │
       ▼                    ▼                               ▼
[Phase 2: US3 BLOCKER]   [Phase 9: US2 parallel]    [Phase 10: US1 parallel]
       │
       ├──────────────┬──────────────┐
       ▼              ▼              ▼
[Phase 3: US4]  [Phase 4: US5]  [Phase 5: US7]
       │              │              │
       ▼              │              │
[Phase 6: US6]        │              │
       │              │              │
       ▼──────────────┴──────────────┘
[Phase 7: US9]
       │
       ▼
[Phase 8: US8]
       │
       ▼
[Phase 11: Polish]
```

### Within Each User Story

- Tests MUST be written and FAIL before implementation (NFR-002)
- Data structures before logic
- Core implementation before orchestrator integration
- Validation step at end of each story

### Parallel Opportunities

- **Cross-story parallel**: US2 (Phase 9) and US1 (Phase 10) can run completely independently from Phases 2-8
- **Within US7**: `_fix_spaced_characters()` (T022) and `_merge_short_lines()` (T023) can be written in parallel
- **Within US8**: All 7 metric implementations (T038-T044) can be written in parallel (different classes, same file)
- **Within US1**: All 7 script integrations (T056-T062) can be done in parallel (different files)
- **Within US2**: All 3 bugfixes (T050-T052) can be done in parallel (different files)
- **Within US3**: All 3 test files (T005-T007) can be written in parallel

---

## Parallel Example: Phase 2 (US3) Tests

```text
# Launch all US3 tests in parallel (different files):
T005: "Write E2E schema test in tests/test_schema_e2e.py"
T006: "Extend tests in tests/test_exporter.py"
T007: "Extend tests in tests/test_metadata_enricher.py"
```

## Parallel Example: Phase 8 (US8) Metrics

```text
# Launch all 7 metric implementations in parallel (same file, different classes):
T038: "Implement ContentCompletenessMetric"
T039: "Implement SemanticSimilarityMetric"
T040: "Implement EntityPreservationMetric"
T041: "Implement LinkIntegrityMetric"
T042: "Implement NoiseDetectionMetric"
T043: "Implement ReadabilityMetric"
T044: "Implement StructurePreservationMetric"
```

## Parallel Example: Cross-Story

```text
# These can run simultaneously with ANY preprocessing phase:
Phase 9 (US2): Deep Eval Bugfixes (pipeline/02_deep_evaluation/)
Phase 10 (US1): CLI UX (pipeline/shared/ + 7 scripts)
```

---

## Implementation Strategy

### MVP First (US3 Only -- Unblock Pipeline)

1. Complete Phase 1: Setup
2. Complete Phase 2: US3 (Schema-Alignment)
3. **STOP and VALIDATE**: Run `DocumentLoader` on output -> all docs load successfully
4. Pipeline is unblocked -- Stage 4 can consume Stage 3 output

### Incremental Delivery

1. Setup + US3 -> **Pipeline unblocked** (MVP)
2. Add US4 -> Strategy routing works -> **Content types assigned correctly**
3. Add US5 -> Freshness in frontmatter -> **Ranking-ready metadata**
4. Add US7 -> Clean PDF text -> **Better chunk quality**
5. Add US6 -> Image descriptions -> **~170 new searchable documents**
6. Add US9 -> One entry point -> **Clean architecture**
7. Add US8 -> Quality metrics -> **Quantitative thesis evidence**
8. Add US2 -> Deterministic deep eval -> **Reproducible results**
9. Add US1 -> Professional CLI -> **Polished UX**
10. Polish -> End-to-end validated -> **Production-ready**

### Parallel Team Strategy

With two developers:

1. Both complete Setup together
2. **Developer A**: US3 -> US4 -> US5 -> US7 -> US6 -> US9 -> US8 (preprocessing chain)
3. **Developer B**: US2 -> US1 (parallel polish, different modules)
4. Both on Phase 11: Integration testing

---

## Summary

| Metric                     | Value                                                  |
| -------------------------- | ------------------------------------------------------ |
| **Total tasks**            | 72                                                     |
| **US3 (P0-Blocker)**       | 11 tasks (T005-T012, T011 decomposed into T011a-T011d) |
| **US4 (P1-Critical)**      | 4 tasks (T013-T016)                                    |
| **US5 (P1-Critical)**      | 4 tasks (T017-T020)                                    |
| **US7 (P2-High)**          | 5 tasks (T021-T025)                                    |
| **US6 (P1-Critical)**      | 5 tasks (T026-T030)                                    |
| **US9 (P3-Medium)**        | 6 tasks (T031-T036)                                    |
| **US8 (P1-Critical)**      | 12 tasks (T037-T048)                                   |
| **US2 (P2-High)**          | 6 tasks (T049-T053, +T052b for AC3 multiline logging)  |
| **US1 (P3-Medium)**        | 10 tasks (T054-T063)                                   |
| Setup                      | 4 tasks (T001-T004)                                    |
| Polish                     | 5 tasks (T064-T068)                                    |
| **Parallel opportunities** | 29 tasks marked [P]                                    |
| **MVP scope**              | Phase 1 + Phase 2 (US3): 15 tasks                      |

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable at its checkpoint
- Tests MUST fail before implementation (NFR-002 TDD mandate)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- US2 and US1 can start from Day 1 in parallel (different pipeline modules)
