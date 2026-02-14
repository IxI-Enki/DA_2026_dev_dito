# Tasks: Pipeline Consolidation

**Input**: Design documents from `/specs/008-pipeline-consolidation/`
**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: TDD-style tests are INCLUDED per NFR-002 ("Tests VOR oder GLEICHZEITIG mit Implementation").

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. User story order matches plan.md phases (US8 first, then US2, US1, US3, US4, US5, US6, US7).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US8)
- Include exact file paths in descriptions

## Path Conventions

- **evaluation/**: All evaluation-related modules (metrics, RAGAS, statistics, visualization, reports)
- **pipeline/03_rag_preprocessing/**: RAG preprocessing pipeline components
- **pipeline/04_deploy/**: Deployment scripts

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependency installation, and basic structure

- [x] T001 Install new dependencies: `pip install ragas datasets langchain-openai scipy matplotlib seaborn pytesseract Pillow tqdm`
- [x] T002 [P] Configure Tesseract binary path in `pipeline/03_rag_preprocessing/config/env.yaml` per Article II-B
- [x] T003 [P] Create `evaluation/ragas/__init__.py` with module docstring
- [x] T004 [P] Create `evaluation/statistics/__init__.py` with module docstring
- [x] T005 [P] Create `evaluation/visualization/__init__.py` with module docstring
- [x] T006 [P] Create `evaluation/reports/__init__.py` with module docstring
- [x] T007 [P] Create `evaluation/experiments/full_eval.yaml` with unified pipeline config skeleton

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Extend existing infrastructure that multiple user stories depend on

**Note**: Existing evaluation infrastructure (56 tests, 5 eval scripts, provider abstraction) remains UNTOUCHED.

- [x] T008 Extend `evaluation/config.py`: Add fields for RAGAS config (llm_base_url, llm_model, temperature) and report config (output_format, dpi)
- [x] T009 Verify existing tests still pass: `pytest evaluation/tests/test_metrics.py` (56 tests)

**Checkpoint**: Foundation ready - existing functionality preserved, config extended

---

## Phase 3: User Story 8 - Additional IR Metrics (Priority: P3-Medium -> Implementation: Phase 1)

**Goal**: Add MAP, Recall@K, and Hit Rate metrics following existing metric patterns

**Independent Test**: `pytest evaluation/tests/test_new_metrics.py` passes with all new metrics

**Why First**: Pure functions with no external dependencies. Quick wins that extend existing test suite.

### Tests for User Story 8

- [x] T010 [P] [US8] Create test file `evaluation/tests/test_new_metrics.py` with test cases for Recall@K
- [x] T011 [P] [US8] Add test cases for MAP to `evaluation/tests/test_new_metrics.py`
- [x] T012 [P] [US8] Add test cases for Hit Rate to `evaluation/tests/test_new_metrics.py`

### Implementation for User Story 8

- [x] T013 [P] [US8] Implement `evaluation/metrics/recall_at_k.py` with pure function `recall_at_k()`
- [x] T014 [P] [US8] Implement `evaluation/metrics/mean_average_precision.py` with pure function `mean_average_precision()`
- [x] T015 [P] [US8] Implement `evaluation/metrics/hit_rate.py` with pure function `hit_rate()`
- [x] T016 [US8] Update `evaluation/metrics/__init__.py` to export new metrics
- [x] T017 [US8] Verify all metrics tests pass: `pytest evaluation/tests/test_new_metrics.py`

**Checkpoint**: 56 existing + ~20 new metric tests pass

---

## Phase 4: User Story 2 - Statistical Analysis (Priority: P1-Critical)

**Goal**: Bootstrap CIs, paired tests (t-test/Wilcoxon), Cohen's d, category breakdown

**Independent Test**: `python evaluation/scripts/eval_compare.py --baseline a.json --candidate b.json` produces comparison with p-values

### Tests for User Story 2

- [x] T018 [P] [US2] Create `evaluation/tests/test_statistics.py` with tests for `bootstrap_ci()`
- [x] T019 [P] [US2] Add tests for `paired_test()` (t-test and Wilcoxon selection) to test_statistics.py
- [x] T020 [P] [US2] Add tests for `cohens_d()` with effect size interpretation to test_statistics.py
- [x] T021 [P] [US2] Add tests for `descriptive_stats()` to test_statistics.py
- [x] T022 [P] [US2] Add tests for `compare_configurations()` to test_statistics.py

### Implementation for User Story 2

- [x] T023 [US2] Implement `evaluation/statistics/statistical_analysis.py` with `StatisticalAnalyzer` class
- [x] T024 [US2] Implement dataclasses `BootstrapCI` and `ComparisonResult` in statistical_analysis.py
- [x] T025 [US2] Implement `evaluation/statistics/category_analysis.py` with per-difficulty breakdown
- [x] T026 [US2] Create `evaluation/scripts/eval_statistics.py` for single-run descriptive stats
- [x] T027 [US2] Create `evaluation/scripts/eval_compare.py` for A/B comparison with p-values and CIs
- [x] T028 [US2] Verify all statistics tests pass: `pytest evaluation/tests/test_statistics.py`

**Checkpoint**: Can compare two result JSONs with p-values + CIs + Cohen's d

---

## Phase 5: User Story 1 - RAGAS.io LLM-as-Judge Integration (Priority: P1-Critical)

**Goal**: RAGAS.io library wrapper for Context P/R, Faithfulness, Answer Correctness via Ollama

**Independent Test**: `python evaluation/scripts/eval_ragas.py --config experiment.yaml` produces RAGAS scores for ground truth

### Tests for User Story 1

- [x] T029 [P] [US1] Create `evaluation/tests/test_ragas.py` with mock tests for RAGASEvaluator initialization
- [x] T030 [P] [US1] Add tests for RAGAS evaluate() with mocked LLM responses to test_ragas.py
- [x] T031 [P] [US1] Add tests for error handling (LLM timeout graceful continuation) to test_ragas.py

### Implementation for User Story 1

- [x] T032 [US1] Implement `evaluation/ragas/ragas_evaluator.py` with `RAGASEvaluator` class
- [x] T033 [US1] Configure RAGASEvaluator to use `langchain-openai` ChatOpenAI pointed at Ollama `/v1` endpoint
- [x] T034 [US1] Implement per-question error handling in RAGASEvaluator (log + continue on failure)
- [x] T035 [US1] Create `evaluation/scripts/eval_ragas.py` CLI script
- [x] T036 [US1] Test against Ollama on 192.168.8.3:11434 with sample ground truth questions (manual when Ollama available)
- [x] T037 [US1] Verify RAGAS tests pass: `pytest evaluation/tests/test_ragas.py`

**Checkpoint**: RAGAS scores (Context P/R, Faithfulness, Answer Correctness) for 50 ground-truth questions

---

## Phase 6: User Story 3 - Visualization (Priority: P2-High)

**Goal**: Thesis-quality charts (Radar, Box-Plot, Bar, Heatmap) with English labels

**Independent Test**: `python evaluation/scripts/eval_visualize.py --results-dir evaluation/results/` generates PNG files

### Tests for User Story 3

- [x] T038 [P] [US3] Create `evaluation/tests/test_visualization.py` with tests for `radar_chart()` output
- [x] T039 [P] [US3] Add tests for `box_plot()` generation to test_visualization.py
- [x] T040 [P] [US3] Add tests for `bar_comparison()` generation to test_visualization.py
- [x] T041 [P] [US3] Add tests for `heatmap()` generation to test_visualization.py
- [x] T042 [P] [US3] Add tests for SVG output format option to test_visualization.py

### Implementation for User Story 3

- [x] T043 [US3] Implement `evaluation/visualization/charts.py` with `EvaluationVisualizer` class
- [x] T044 [US3] Implement `radar_chart()` method with English labels and DPI>=300
- [x] T045 [US3] Implement `box_plot()` method for score distributions
- [x] T046 [US3] Implement `bar_comparison()` method for model comparisons
- [x] T047 [US3] Implement `heatmap()` method for correlation matrices
- [x] T048 [US3] Add `--format svg` support for LaTeX `\includegraphics`
- [x] T049 [US3] Create `evaluation/scripts/eval_visualize.py` CLI script
- [x] T050 [US3] Verify visualization tests pass: `pytest evaluation/tests/test_visualization.py`

**Checkpoint**: PNG/SVG charts with English labels, print-quality DPI

---

## Phase 7: User Story 4 - Report Generator (Priority: P2-High)

**Goal**: Structured Markdown + JSON reports with Custom Metrics, RAGAS, Statistics, Config details

**Independent Test**: `python evaluation/scripts/eval_report.py --results evaluation/results/experiment_xyz/` generates report

### Tests for User Story 4

- [X] T051 [P] [US4] Create `evaluation/tests/test_reports.py` with tests for report structure generation
- [X] T052 [P] [US4] Add tests for RAGAS + Custom metrics side-by-side table to test_reports.py
- [X] T053 [P] [US4] Add tests for NFR-005 fields (timestamp, config-hash, code-version) to test_reports.py
- [X] T054 [P] [US4] Add tests for difficulty breakdown table to test_reports.py

### Implementation for User Story 4

- [X] T055 [US4] Implement `evaluation/reports/generator.py` with `ReportGenerator` class
- [X] T056 [US4] Implement Executive Summary generation in ReportGenerator
- [X] T057 [US4] Implement Custom Metrics table (MRR, NDCG, P@K, MAP, Recall@K) generation
- [X] T058 [US4] Implement RAGAS Metrics table (Context P/R, Faithfulness) generation
- [X] T059 [US4] Implement Statistical Comparison section (CI, p-values, effect sizes)
- [X] T060 [US4] Implement Difficulty Breakdown section
- [X] T061 [US4] Add NFR-005 reproducibility fields: timestamp, config-hash, code-version
- [X] T062 [US4] Create `evaluation/scripts/eval_report.py` CLI script
- [X] T063 [US4] Verify report tests pass: `pytest evaluation/tests/test_reports.py`

**Checkpoint**: Markdown + JSON reports from result JSONs with all required sections

---

## Phase 8: User Story 5 - RAG Preprocessing Pipeline (Priority: P1-Critical)

**Goal**: Complete RAG preprocessing: DokuWiki->Markdown, strategy routing, OCR, metadata enrichment, export

**Independent Test**: `python pipeline/03_rag_preprocessing/run_preprocessing.py` converts `data/fetched/` to `data/preprocessed/`

### Tests for User Story 5

- [ ] T064 [P] [US5] Create `pipeline/03_rag_preprocessing/tests/test_strategy_loader.py` with StrategyLoader tests
- [ ] T065 [P] [US5] Create `pipeline/03_rag_preprocessing/tests/test_media_processor.py` with PDF/OCR tests
- [ ] T066 [P] [US5] Create `pipeline/03_rag_preprocessing/tests/test_exporter.py` with export tests
- [ ] T067 [P] [US5] Create `pipeline/03_rag_preprocessing/tests/test_page_processor.py` with DokuWiki conversion tests
- [ ] T068 [P] [US5] Create `pipeline/03_rag_preprocessing/tests/test_metadata_enricher.py` with freshness/access tests

### Implementation for User Story 5

- [ ] T069 [US5] Implement `pipeline/03_rag_preprocessing/strategy_loader.py` with `StrategyLoader` class
- [ ] T070 [US5] Implement `ContentType` enum and `PageStrategy` dataclass in strategy_loader.py
- [ ] T071 [US5] Implement `pipeline/03_rag_preprocessing/media_processor.py` with `MediaProcessor` class
- [ ] T072 [US5] Implement `process_pdf()` method with text extraction and OCR fallback
- [ ] T073 [US5] Implement `process_image()` method with Tesseract OCR (path from `config/env.yaml`)
- [ ] T074 [US5] Implement `pipeline/03_rag_preprocessing/exporter.py` with `Exporter` class
- [ ] T075 [US5] Implement export to `data/preprocessed/preprocessed_at_{timestamp}/` with YAML frontmatter
- [ ] T076 [US5] Modify `pipeline/03_rag_preprocessing/page_processor.py`: add strategy-aware routing
- [ ] T077 [US5] Modify `pipeline/03_rag_preprocessing/metadata_enricher.py`: add `freshness_score` field
- [ ] T078 [US5] Modify `pipeline/03_rag_preprocessing/metadata_enricher.py`: add `access_level` field
- [ ] T079 [US5] Create `pipeline/03_rag_preprocessing/run_preprocessing.py` main orchestrator script
- [ ] T080 [US5] Verify preprocessing tests pass: `pytest pipeline/03_rag_preprocessing/tests/`
- [ ] T081 [US5] Add regression test for DokuWiki syntax conversion accuracy (assert < 1% Wiki syntax markers remaining in output)

**Checkpoint**: `data/fetched/` -> `data/preprocessed/` full conversion with metadata

---

## Phase 9: User Story 6 - Qdrant Deployment (Priority: P2-High)

**Goal**: Direct upload to Qdrant via `qdrant_client` or watchdog export mode

**Independent Test**: `python pipeline/04_deploy/deploy_qdrant.py --mode direct --dry-run` validates without uploading

### Tests for User Story 6

- [ ] T082 [P] [US6] Create `pipeline/04_deploy/tests/test_deploy_qdrant.py` with direct upload tests (mocked client)
- [ ] T083 [P] [US6] Add tests for watchdog mode (file copy) to test_deploy_qdrant.py
- [ ] T084 [P] [US6] Add tests for `--recreate` collection behavior to test_deploy_qdrant.py
- [ ] T085 [P] [US6] Add tests for upsert-only behavior (without --recreate) to test_deploy_qdrant.py

### Implementation for User Story 6

- [ ] T086 [US6] Implement `pipeline/04_deploy/deploy_qdrant.py` with `QdrantDeployer` class
- [ ] T087 [US6] Implement `deploy_direct()` method for direct Qdrant upload via `qdrant_client`
- [ ] T088 [US6] Implement `deploy_watchdog()` method for MCP watchdog folder copy
- [ ] T089 [US6] Add `--recreate` flag to delete and recreate existing collections
- [ ] T090 [US6] Add `--dry-run` flag for validation without actual upload
- [ ] T091 [US6] Verify deploy tests pass: `pytest pipeline/04_deploy/tests/test_deploy_qdrant.py`

**Checkpoint**: Embeddings uploadable to Qdrant directly or via watchdog folder

---

## Phase 10: User Story 7 - Unified Evaluation Orchestrator (Priority: P2-High)

**Goal**: Single command runs: Retrieval -> Custom Metrics -> RAGAS -> Stats -> Viz -> Report

**Independent Test**: `python evaluation/scripts/eval_pipeline.py --config full_eval.yaml --skip ragas` runs full pipeline without RAGAS

### Implementation for User Story 7

- [ ] T092 [US7] Implement `evaluation/scripts/eval_pipeline.py` with `EvaluationPipeline` class
- [ ] T093 [US7] Implement Step 1: Qdrant Retrieval (top-k for each ground-truth query)
- [ ] T094 [US7] Implement Step 2: Custom Metrics calculation (MRR, NDCG, P@K, MAP, Recall@K)
- [ ] T095 [US7] Implement Step 3: RAGAS Metrics calculation (Context P/R, Faithfulness)
- [ ] T096 [US7] Implement Step 4: Statistical Analysis (descriptive + bootstrap CIs)
- [ ] T097 [US7] Implement Step 5: Visualization (charts)
- [ ] T098 [US7] Implement Step 6: Report Generation (Markdown + JSON)
- [ ] T099 [US7] Add `--skip ragas` flag for fast iterations without LLM costs
- [ ] T100 [US7] Implement results output to `evaluation/results/{experiment_name}_{timestamp}/`
- [ ] T101 [US7] Add NFR-005 fields to output: config-hash, code-version

**Checkpoint**: Single command runs full evaluation pipeline

---

## Phase 11: Integration Testing & Polish

**Purpose**: End-to-end validation, edge case fixes, final polish

- [ ] T102 Run end-to-end test: preprocessed data -> embeddings -> Qdrant -> evaluation -> report
- [ ] T103 Verify all NFR-005 fields present in final outputs (timestamp, config-hash, code-version)
- [ ] T104 Run full pipeline on actual LeoWiki data
- [ ] T105 [P] Fix edge cases discovered during integration testing
- [ ] T106 [P] Verify all existing tests still pass: `pytest evaluation/tests/test_metrics.py` (56 tests)
- [ ] T107 [P] Run full test suite: `pytest evaluation/tests/ pipeline/03_rag_preprocessing/tests/ pipeline/04_deploy/tests/`
- [ ] T108 Update `evaluation/experiments/full_eval.yaml` with production-ready configuration

**Checkpoint**: Complete pipeline works end-to-end with all 8 user stories

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - extends existing config
- **User Stories (Phases 3-10)**: All depend on Foundational phase completion
  - US8 (Phase 3): Pure metrics, no external dependencies - START HERE
  - US2 (Phase 4): Depends on T008 (config extension)
  - US1 (Phase 5): Depends on T008 (RAGAS config fields)
  - US3 (Phase 6): Depends on US2 (uses statistical results)
  - US4 (Phase 7): Depends on US1, US2, US3 (includes all metric types)
  - US5 (Phase 8): Independent of evaluation phases
  - US6 (Phase 9): Independent of evaluation phases
  - US7 (Phase 10): Depends on US1, US2, US3, US4 (orchestrates all)
- **Polish (Phase 11)**: Depends on all user stories being complete

### User Story Dependencies

| Story                   | Depends On         | Can Run In Parallel With     |
| ----------------------- | ------------------ | ---------------------------- |
| US8 (Metrics)           | Foundational       | -                            |
| US2 (Statistics)        | Foundational       | US8, US5, US6                |
| US1 (RAGAS)             | Foundational       | US8, US2, US5, US6           |
| US3 (Visualization)     | US2                | US5, US6                     |
| US4 (Reports)           | US1, US2, US3      | US5, US6                     |
| US5 (RAG Preprocessing) | Foundational       | US8, US2, US1, US3, US4      |
| US6 (Qdrant Deploy)     | Foundational       | US8, US2, US1, US3, US4, US5 |
| US7 (Orchestrator)      | US1, US2, US3, US4 | -                            |

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD per NFR-002)
- Models/dataclasses before services
- Core implementation before CLI scripts
- Story complete before marking checkpoint

### Parallel Opportunities

**Phase 1 (Setup)**:
```
T002, T003, T004, T005, T006, T007 -- all config/init files
```

**Phase 3 (US8 - Metrics)**:
```
T010, T011, T012 -- all test cases
T013, T014, T015 -- all metric implementations
```

**Phase 4 (US2 - Statistics)**:
```
T018, T019, T020, T021, T022 -- all test cases
```

**Phase 5 (US1 - RAGAS)**:
```
T029, T030, T031 -- all test cases
```

**Phase 6 (US3 - Visualization)**:
```
T038, T039, T040, T041, T042 -- all test cases
```

**Phase 7 (US4 - Reports)**:
```
T051, T052, T053, T054 -- all test cases
```

**Phase 8 (US5 - RAG Preprocessing)**:
```
T064, T065, T066, T067, T068 -- all test files
```

**Phase 9 (US6 - Qdrant Deploy)**:
```
T082, T083, T084, T085 -- all test cases
```

---

## Parallel Example: User Story 8 (Additional IR Metrics)

```bash
# Launch all tests together:
Task T010: "Create test_new_metrics.py with Recall@K tests"
Task T011: "Add MAP tests to test_new_metrics.py"
Task T012: "Add Hit Rate tests to test_new_metrics.py"

# Launch all metric implementations together:
Task T013: "Implement evaluation/metrics/recall_at_k.py"
Task T014: "Implement evaluation/metrics/mean_average_precision.py"
Task T015: "Implement evaluation/metrics/hit_rate.py"
```

---

## Implementation Strategy

### MVP First (US8 + US2 + US1)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US8 (Additional IR Metrics) - Quick wins
4. Complete Phase 4: US2 (Statistical Analysis) - Critical for thesis
5. Complete Phase 5: US1 (RAGAS Integration) - Critical for thesis
6. **STOP and VALIDATE**: Statistical comparisons + RAGAS scores available
7. Deploy for thesis writing iteration

**Deliverable at MVP**: Statistical analysis available from Day 3, RAGAS from Day 5

### Incremental Delivery

1. Setup + Foundational -> Foundation ready
2. US8 (Metrics) -> 76 tests pass (56 + ~20 new)
3. US2 (Statistics) -> A/B comparisons with p-values
4. US1 (RAGAS) -> LLM-as-Judge scores for 50 questions
5. US3 + US4 (Viz + Reports) -> Thesis-quality outputs
6. US5 + US6 (RAG Preprocessing + Deploy) -> Full pipeline
7. US7 (Orchestrator) -> Single command runs all

### Parallel Team Strategy

With multiple developers:
1. All complete Setup + Foundational together
2. Once Foundational done:
   - Developer A: US8 + US2 + US1 (Evaluation track)
   - Developer B: US5 + US6 (Pipeline track)
3. Converge for US7 (Orchestrator) + US3 + US4 (outputs)

---

## Summary

| Metric                                | Count |
| ------------------------------------- | ----- |
| **Total Tasks**                       | 108   |
| **Phase 1 (Setup)**                   | 7     |
| **Phase 2 (Foundational)**            | 2     |
| **Phase 3 (US8 - Metrics)**           | 8     |
| **Phase 4 (US2 - Statistics)**        | 11    |
| **Phase 5 (US1 - RAGAS)**             | 9     |
| **Phase 6 (US3 - Visualization)**     | 13    |
| **Phase 7 (US4 - Reports)**           | 13    |
| **Phase 8 (US5 - RAG Preprocessing)** | 18    |
| **Phase 9 (US6 - Qdrant Deploy)**     | 10    |
| **Phase 10 (US7 - Orchestrator)**     | 10    |
| **Phase 11 (Polish)**                 | 7     |

**Parallel Opportunities**: 46 tasks marked [P]

**MVP Scope**: Phases 1-5 (US8, US2, US1) = 37 tasks

**Suggested MVP**: Complete through Phase 5 (RAGAS) to have statistical analysis + LLM-as-Judge available for thesis writing.
