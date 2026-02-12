# Tasks: Evaluation Infrastructure

**Input**: Design documents from `specs/007-evaluation-infrastructure/`
**Prerequisites**: plan.md (required), spec.md (required)
**Branch**: `007-evaluation-infrastructure`
**Thesis-Zuordnung**: FF1, FF3, J1, J2, J4, J6

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US5)
- Exact file paths included in descriptions

---

## Phase 1: Setup & Shared Infrastructure

**Purpose**: Project structure, dependencies, and core modules that ALL user stories depend on

- [ ] T001 Create `evaluation/` directory structure per plan.md (all subdirectories, `__init__.py` files, `.gitkeep` in `results/`)
- [ ] T002 Create `evaluation/requirements.txt` with: `qdrant-client`, `openai`, `ollama`, `requests`, `pyyaml`, `numpy`
- [ ] T003 [P] Copy ground truth file from `research/techstack/ragas/ground_truth/leowiki_qa_50_verified.json` to `evaluation/ground_truth/` and create `README.md` documenting corpus (feeds J1 thesis section)

---

## Phase 2: Foundation (Blocking Prerequisites)

**Purpose**: Metrics, providers, and config loader — MUST be complete before ANY user story scripts

**CRITICAL**: No evaluation script can run until this phase is complete

### Metrics Module (Pure functions, no external deps)

- [ ] T004 [P] Implement MRR in `evaluation/metrics/mrr.py` — `mean_reciprocal_rank(ranked_results: list[str], relevant: set[str]) -> float`
- [ ] T005 [P] Implement Precision@k in `evaluation/metrics/precision_at_k.py` — `precision_at_k(ranked_results: list[str], relevant: set[str], k: int = 5) -> float`
- [ ] T006 [P] Implement NDCG@k in `evaluation/metrics/ndcg.py` — `ndcg_at_k(ranked_results: list[str], relevance_map: dict[str, int], k: int = 10) -> float`
- [ ] T007 [P] Create `evaluation/metrics/__init__.py` re-exporting all metric functions
- [ ] T008 Write unit tests `evaluation/tests/test_metrics.py` — verify MRR, P@k, NDCG against hand-calculated IR textbook examples (depends on T004-T006)

### EmbeddingProvider Abstraction

- [ ] T009 [P] Implement `evaluation/providers/base.py` — ABC with `embed()`, `model_name`, `dimensions`, `cost_per_token`
- [ ] T010 Implement `evaluation/providers/ollama_provider.py` — uses `ollama.embed()`, any model from `ollama list` (depends on T009)
- [ ] T011 [P] Create `evaluation/providers/__init__.py` re-exporting providers
- [ ] T012 Write unit tests `evaluation/tests/test_providers.py` — interface compliance, mock embed calls (depends on T009-T010)

### Config Loader

- [ ] T013 Implement `evaluation/config.py` — YAML experiment config loader, validates schema (provider, model, chunk_size, retrieval mode, metrics list)

**Checkpoint**: Metrics verified by unit tests, OllamaProvider works, configs load from YAML

---

## Phase 3: User Story 1 — Keyword Search Baseline (Priority: P1)

**Goal**: FF1 baseline — run 50 ground-truth queries against DokuWiki `core.searchPages`, compute MRR + P@5
**Independent Test**: `python evaluation/scripts/eval_keyword_baseline.py` produces `evaluation/results/keyword_baseline_{timestamp}.json`
**Thesis Table**: FF1 — Keyword vs Semantic Search

### Implementation

- [ ] T014 Create `evaluation/experiments/keyword_baseline.yaml` — config with `type: keyword_baseline`, metrics: [mrr, precision_at_5]
- [ ] T015 Implement `evaluation/scripts/eval_keyword_baseline.py` — loads ground truth, calls `core.searchPages` via existing `pipeline/01_wiki_fetcher/api_client.py`, computes MRR + P@5 per query, writes result JSON (depends on T004, T005, T013, T014)
- [ ] T016 Add `--help` flag with argparse (NFR-004) and connection-error handling (AC scenario 2) to `eval_keyword_baseline.py`

**Checkpoint**: First thesis table data (FF1 keyword baseline) available as JSON

---

## Phase 4: User Story 2 — Model-Agnostic Embedding Evaluation (Priority: P1)

**Goal**: FF3 — compare 3+ embedding models (Ollama + OpenAI + MTEB) with NDCG@10 + MRR
**Independent Test**: `python evaluation/scripts/eval_model_comparison.py --config model_bge_m3.yaml` produces result JSON
**Thesis Table**: FF3 — Embedding Model Comparison

### Implementation

- [ ] T017 Implement `evaluation/providers/openai_provider.py` — uses `openai.embeddings.create()`, token usage tracking, cost calculation (depends on T009)
- [ ] T018 [P] Create experiment configs (depends on T013):
  - `evaluation/experiments/model_bge_m3.yaml` (provider: ollama, model: bge-m3, dim: 1024)
  - `evaluation/experiments/model_openai_3large.yaml` (provider: openai, model: text-embedding-3-large, dim: 3072)
  - `evaluation/experiments/model_mxbai_embed_de.yaml` (provider: ollama, model: mxbai-embed-large-v1, dim: 1024)
- [ ] T019 Implement `evaluation/scripts/eval_model_comparison.py` — loads config, embeds ground-truth corpus chunks into temp Qdrant collection (`eval_{model}_{chunk_size}`), runs queries, computes NDCG@10 + MRR, writes result JSON with cost tracking (depends on T004, T006, T008, T010, T013, T017)
- [ ] T020 Add `--compare-all` flag to `eval_model_comparison.py` — iterates all `model_*.yaml` configs, produces comparison table (Markdown + JSON) (depends on T019)
- [ ] T021 Add Qdrant temp collection cleanup — create before experiment, delete after (FR-008) (depends on T019)

**Checkpoint**: FF3 model comparison table with 3+ models available

---

## Phase 5: User Story 3 — Chunk Size Parametric Evaluation (Priority: P1)

**Goal**: J4 — compare 256/512/1024 token chunks on same model + queries
**Independent Test**: `python evaluation/scripts/eval_chunk_size.py --config chunk_512.yaml` produces result JSON
**Thesis Table**: J4 — Chunk Size Impact

### Implementation

- [ ] T022 [P] Create chunk experiment configs (depends on T013):
  - `evaluation/experiments/chunk_256.yaml` (chunk_size: 256, chunk_overlap: 50)
  - `evaluation/experiments/chunk_512.yaml` (chunk_size: 512, chunk_overlap: 50)
  - `evaluation/experiments/chunk_1024.yaml` (chunk_size: 1024, chunk_overlap: 50)
- [ ] T023 Implement `evaluation/scripts/eval_chunk_size.py` — loads config, re-chunks corpus using existing `content_aware_chunker.py` from `pipeline/03_embeddings_creator/`, embeds, deploys to temp Qdrant collection, evaluates with NDCG@10 + MRR + P@5 (depends on T004-T006, T010, T013)
- [ ] T024 Add `--compare` flag — iterates all `chunk_*.yaml` configs, produces comparison table (depends on T023)

**Checkpoint**: J4 chunk size comparison table with 3 sizes available

---

## Phase 6: User Story 4 — Hybrid vs Dense Retrieval (Priority: P2)

**Goal**: J6 — compare dense-only vs hybrid (dense + BM25) retrieval on same collection
**Independent Test**: `python evaluation/scripts/eval_hybrid_vs_dense.py` produces comparison JSON
**Thesis Table**: J6 — Hybrid vs Dense Retrieval

### Implementation

- [ ] T025 Create `evaluation/experiments/hybrid_vs_dense.yaml` — config with both modes defined (depends on T013)
- [ ] T026 Implement `evaluation/scripts/eval_hybrid_vs_dense.py` — uses existing Qdrant collection, queries in dense mode and hybrid mode (Qdrant `query_mode` toggle), computes P@5 + NDCG@10 for both, writes comparison result JSON (depends on T004-T006, T010, T013)

**Checkpoint**: J6 hybrid vs dense comparison table available

---

## Phase 7: User Story 5 — LaTeX Export (Priority: P2)

**Goal**: All result JSONs exportable as LaTeX `\begin{tabular}` tables for thesis
**Independent Test**: `python evaluation/scripts/eval_export_latex.py` reads `evaluation/results/*.json`, produces `.tex` files

### Implementation

- [ ] T027 Implement `evaluation/scripts/eval_export_latex.py` — reads all result JSONs from `evaluation/results/`, generates 4 LaTeX tables (FF1, FF3, J4, J6) with `\toprule/\midrule/\bottomrule` formatting (depends on results from T015, T019, T023, T026)
- [ ] T028 Add `--output-dir` flag for custom `.tex` output location

**Checkpoint**: All 4 thesis tables available as `.tex` files

---

## Phase 8: Polish & Cross-Cutting

**Purpose**: Integration tests, documentation, reproducibility

- [ ] T029 Write integration test `evaluation/tests/test_integration.py` — end-to-end with local Qdrant (embed small corpus, query, verify metrics are non-zero)
- [ ] T030 [P] Create `evaluation/README.md` — setup instructions, usage examples for each script, ground truth format documentation
- [ ] T031 [P] Add `.gitignore` entry for `evaluation/results/*.json` (keep only `.gitkeep` and summary files)
- [ ] T032 Ensure all result JSONs include timestamp, config-hash, and code-version (NFR-005) — verify in T015, T019, T023, T026

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) ─────────────► Phase 2 (Foundation) ──┬──► Phase 3 (US1: Keyword) ──┐
                                                       ├──► Phase 4 (US2: Models)  ──┤
                                                       ├──► Phase 5 (US3: Chunks)  ──┼──► Phase 7 (US5: LaTeX)
                                                       └──► Phase 6 (US4: Hybrid)  ──┘         │
                                                                                                ▼
                                                                                        Phase 8 (Polish)
```

### Key Facts

- **Phases 3-6 can run in parallel** after Phase 2 completes (different scripts, different files)
- **Phase 7 (LaTeX)** needs at least one result JSON — can start after any of Phases 3-6
- **Phase 8 (Polish)** is best done last but `README.md` can start anytime

### Within Each Phase

- Configs ([P] marked) can be created in parallel
- Scripts depend on their configs + Phase 2 modules
- `--compare` flags depend on their base scripts

### Parallel Opportunities

```
After Phase 2 completes, launch all 4 in parallel:
  T015 (keyword baseline)  |  T019 (model comparison)  |  T023 (chunk size)  |  T026 (hybrid vs dense)
```

---

## Implementation Strategy

### MVP First (Thesis Tables ASAP)

1. Phase 1 + 2: Setup + Foundation (T001-T013)
2. Phase 3: Keyword Baseline → **FF1 table data available**
3. Phase 4: Model Comparison → **FF3 table data available**
4. Phase 5: Chunk Size → **J4 table data available**
5. **STOP and VALIDATE**: Three thesis tables ready for writing
6. Phase 6-8: Hybrid + LaTeX + Polish

### Estimated Effort

| Phase | Tasks | Est. Days | Cumulative |
|-------|-------|-----------|------------|
| 1: Setup | T001-T003 | 0.5 | 0.5 |
| 2: Foundation | T004-T013 | 1.5 | 2 |
| 3: US1 Keyword | T014-T016 | 1 | 3 |
| 4: US2 Models | T017-T021 | 2 | 5 |
| 5: US3 Chunks | T022-T024 | 1 | 6 |
| 6: US4 Hybrid | T025-T026 | 1 | 7 |
| 7: US5 LaTeX | T027-T028 | 0.5 | 7.5 |
| 8: Polish | T029-T032 | 0.5 | 8 |

**Total: 32 tasks across 8 phases, ~8 focused days**
**Thesis tables from Day 3 onward (FF1 first)**
