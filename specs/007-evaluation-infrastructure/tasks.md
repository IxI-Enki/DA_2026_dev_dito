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

## Phase 1: Setup & Shared Infrastructure — DONE

**Commit**: `ea63e9f` feat(eval): add evaluation infrastructure foundation (Phase 1-2)

- [x] T001 Create `evaluation/` directory structure per plan.md (all subdirectories, `__init__.py` files, `.gitkeep` in `results/`)
- [x] T002 Create `evaluation/requirements.txt` with: `qdrant-client`, `openai`, `ollama`, `requests`, `pyyaml`, `numpy`
- [x] T003 [P] Copy ground truth file from `research/techstack/ragas/ground_truth/leowiki_qa_50_verified.json` to `evaluation/ground_truth/` and create `README.md` documenting corpus (feeds J1 thesis section)

---

## Phase 2: Foundation (Blocking Prerequisites) — DONE

**Commit**: `ea63e9f` (same as Phase 1)
**Tests**: 36/36 passing (29 metrics + 7 providers)

### Metrics Module (Pure functions, no external deps)

- [x] T004 [P] Implement MRR in `evaluation/metrics/mrr.py` — `reciprocal_rank()` + `mean_reciprocal_rank()` taking `list[tuple[list[str], set[str]]]`
- [x] T005 [P] Implement Precision@k in `evaluation/metrics/precision_at_k.py` — `precision_at_k()` + `mean_precision_at_k()`
- [x] T006 [P] Implement NDCG@k in `evaluation/metrics/ndcg.py` — `ndcg_at_k()` using `(2^rel - 1) / log2(i + 2)` DCG formula + `mean_ndcg_at_k()`
- [x] T007 [P] Create `evaluation/metrics/__init__.py` re-exporting all metric functions
- [x] T008 Write unit tests `evaluation/tests/test_metrics.py` — 29 tests covering MRR, P@k, NDCG against hand-calculated examples

### EmbeddingProvider Abstraction

- [x] T009 [P] Implement `evaluation/providers/base.py` — ABC with `embed()`, `model_name`, `dimensions`, `cost_per_token`
- [x] T010 Implement `evaluation/providers/ollama_provider.py` — uses `ollama.Client(host).embed()` (Article VIII direct SDK)
- [x] T011 [P] Create `evaluation/providers/__init__.py` re-exporting `EmbeddingProvider`, `OllamaProvider`
- [x] T012 Write unit tests `evaluation/tests/test_providers.py` — 7 tests with mocked SDK calls for ABC, OllamaProvider, OpenAIProvider
  - **Note**: Required `pip install ollama openai` — SDKs were not pre-installed

### Config Loader

- [x] T013 Implement `evaluation/config.py` — `ExperimentConfig` frozen dataclass with slots, SHA-256 config hash (NFR-005), `load_experiment_config()` from YAML, `load_ground_truth()` from JSON

**Checkpoint**: All verified — 36/36 tests pass

---

## Phase 3: User Story 1 — Keyword Search Baseline (Priority: P1) — DONE

**Commit**: `55ef107` feat(eval): add keyword search baseline script (Phase 3, FF1)
**Tests**: 9/9 passing (6 mapping + 3 runner)

**Goal**: FF1 baseline — run 50 ground-truth queries against DokuWiki `core.searchPages`, compute MRR + P@5
**Independent Test**: `python -m evaluation.scripts.eval_keyword_baseline` produces `evaluation/results/keyword_baseline_{timestamp}.json`
**Thesis Table**: FF1 — Keyword vs Semantic Search

### Implementation

- [x] T014 Create `evaluation/experiments/keyword_baseline.yaml` — config with `type: keyword_baseline`, metrics: [mrr, precision_at_5]
  - Done in Phase 1 commit
- [x] T015 Implement `evaluation/scripts/eval_keyword_baseline.py`:
  - `WikiSearchClient` — lightweight DokuWiki JSON-RPC client reading from central `config/env.yaml` (NOT importing from `pipeline/01_wiki_fetcher/config.py` which has module-level side effects)
  - `source_file_to_page_id()` — ALL underscores become colons (verified against fetched metadata: `archive_exams_semesterpruefungen.txt` → `archive:exams:semesterpruefungen`)
  - Computes MRR + P@5 per query, writes result JSON
  - **Deviation from plan**: Does NOT import `pipeline/01_wiki_fetcher/api_client.py` — created standalone WikiSearchClient to avoid module-level config import side effects
- [x] T016 Add `--help` flag with argparse, `--verbose`, `--top-k`, `--output-dir` flags (NFR-004) and connection-error handling with exit codes 1/2/3

**Checkpoint**: Verified — 9/9 tests pass, `--help` works

---

## Phase 4: User Story 2 — Model-Agnostic Embedding Evaluation (Priority: P1) — DONE

**Commit**: `475d75f` feat(eval): add model comparison script with prototype-aligned relevance (Phase 4, FF3)
**Tests**: 11/11 passing (5 chunker + 3 relevance + 1 corpus + 2 runner)

**Goal**: FF3 — compare 3+ embedding models (Ollama + OpenAI + MTEB) with NDCG@10 + MRR
**Independent Test**: `python -m evaluation.scripts.eval_model_comparison --config experiments/model_bge_m3.yaml` produces result JSON
**Thesis Table**: FF3 — Embedding Model Comparison

### Implementation

- [x] T017 Implement `evaluation/providers/openai_provider.py` — uses `openai.OpenAI().embeddings.create()`, token usage tracking, cost calculation, API key from file (Article VI)
  - Done in Phase 1-2 commit
- [x] T018 [P] Create experiment configs:
  - `evaluation/experiments/model_bge_m3.yaml` (provider: ollama, model: bge-m3, dim: 1024)
  - `evaluation/experiments/model_openai_3large.yaml` (provider: openai, model: text-embedding-3-large, dim: 3072)
  - `evaluation/experiments/model_mxbai_embed_de.yaml` (provider: ollama, model: mxbai-embed-large-v1, dim: 1024)
  - Done in Phase 1-2 commit
- [x] T019 Implement `evaluation/scripts/eval_model_comparison.py`:
  - `simple_chunk()` — standalone paragraph-based chunker (does NOT import `pipeline/03_embeddings_creator/content_aware_chunker.py` which depends on pipeline config system)
  - `load_corpus_for_ground_truth()` — loads `.txt` files from `data/fetched/fetched_at_*/page_content/` for pages referenced in ground truth
  - `calculate_relevance_score()` — multi-signal relevance scoring ported from prototype `research/techstack/ragas/professional_evaluation/metrics/retrieval_metrics.py` (0.4×word_overlap + 0.3×keyword_match + 0.3×fragment_match)
  - Creates temp Qdrant collection, embeds corpus, queries, deduplicates chunks by page_id
  - Result includes: aggregate metrics with **mean + std dev**, **difficulty breakdown** (easy/medium/hard), **content relevance score**, **cost tracking** (OpenAI)
  - **Enhancement over plan**: Added multi-signal relevance, std dev, difficulty breakdown after reviewing prototypes
- [x] T020 Add `--compare-all` flag — iterates all `model_*.yaml` configs, produces Markdown comparison table + `model_comparison_{timestamp}.json`
- [x] T021 Qdrant temp collection cleanup in `try/finally` block (FR-008) — verified cleanup runs even on error

**Checkpoint**: Verified — 11/11 tests pass, `--help` works, cleanup verified

---

## Phase 5: User Story 3 — Chunk Size Parametric Evaluation (Priority: P1) — DONE

**Commit**: `256cf57` feat(eval): add chunk size, hybrid vs dense, and LaTeX export scripts (Phases 5-7)

**Goal**: J4 — compare 256/512/1024 token chunks on same model + queries
**Independent Test**: `python -m evaluation.scripts.eval_chunk_size --config experiments/chunk_512.yaml`
**Thesis Table**: J4 — Chunk Size Impact

### Implementation

- [x] T022 [P] Create chunk experiment configs:
  - `evaluation/experiments/chunk_256.yaml` (chunk_size: 256, chunk_overlap: 50)
  - `evaluation/experiments/chunk_512.yaml` (chunk_size: 512, chunk_overlap: 50)
  - `evaluation/experiments/chunk_1024.yaml` (chunk_size: 1024, chunk_overlap: 50)
  - Done in Phase 1-2 commit
- [x] T023 Implement `evaluation/scripts/eval_chunk_size.py`:
  - **Thin wrapper** around `run_model_evaluation()` from Phase 4 — the model comparison pipeline already reads `chunk_size` from config, so only CLI and comparison table formatting needed
  - **Deviation from plan**: Does NOT use `content_aware_chunker.py` from pipeline — uses `simple_chunk()` to avoid pipeline config dependency. Chunking is by character count (paragraph-boundary-respecting), not token count
- [x] T024 Add `--compare` flag — iterates all `chunk_*.yaml` configs, produces `chunk_comparison_{timestamp}.json`

**Checkpoint**: Verified — `--help` works, reuses Phase 4 pipeline (no new tests needed — same code path)

---

## Phase 6: User Story 4 — Hybrid vs Dense Retrieval (Priority: P2) — DONE

**Commit**: `256cf57` (same as Phase 5)

**Goal**: J6 — compare dense-only vs hybrid (dense + BM25) retrieval on same collection
**Independent Test**: `python -m evaluation.scripts.eval_hybrid_vs_dense`
**Thesis Table**: J6 — Hybrid vs Dense Retrieval

### Implementation

- [x] T025 Create `evaluation/experiments/hybrid_vs_dense.yaml` — config with `mode: hybrid`, metrics: [mrr, precision_at_5, ndcg_at_10]
  - Done in Phase 1-2 commit
- [x] T026 Implement `evaluation/scripts/eval_hybrid_vs_dense.py`:
  - Builds one temp Qdrant collection, runs both dense and hybrid queries against it
  - `_evaluate_queries()` shared function for both modes with full metric output
  - Result includes side-by-side comparison with mean + std for all metrics
  - **Note**: True hybrid (vector + BM25) requires Qdrant full-text index on collection — currently both modes use vector search. Hybrid mode needs Qdrant payload index configuration at runtime.
  - Uses `try/finally` for collection cleanup (FR-008)

**Checkpoint**: Verified — `--help` works, code path reuses shared evaluation functions

---

## Phase 7: User Story 5 — LaTeX Export (Priority: P2) — DONE

**Commit**: `256cf57` (same as Phases 5-6)

**Goal**: All result JSONs exportable as LaTeX `\begin{tabular}` tables for thesis
**Independent Test**: `python -m evaluation.scripts.eval_export_latex`

### Implementation

- [x] T027 Implement `evaluation/scripts/eval_export_latex.py`:
  - `generate_ff1_table()` — Keyword vs Semantic comparison (reads keyword_baseline + model_bge results)
  - `generate_ff3_table()` — Embedding model comparison (reads model_comparison summary)
  - `generate_j4_table()` — Chunk size impact (reads chunk_comparison summary)
  - `generate_j6_table()` — Hybrid vs Dense (reads hybrid_vs_dense result)
  - All tables use `\toprule/\midrule/\bottomrule` (booktabs), `\caption`, `\label`
  - Auto-discovers latest result file per pattern
- [x] T028 Add `--output-dir` and `--results-dir` flags for custom locations

**Checkpoint**: Verified — `--help` works, generates 4 `.tex` files when results exist

---

## Phase 8: Polish & Cross-Cutting — PARTIAL

- [ ] T029 Write integration test `evaluation/tests/test_integration.py` — end-to-end with local Qdrant (embed small corpus, query, verify metrics are non-zero)
  - **Blocked**: Requires running Qdrant instance — should be run manually or in CI
- [ ] T030 [P] Create `evaluation/README.md` — setup instructions, usage examples for each script, ground truth format documentation
- [x] T031 [P] Add `.gitignore` for `evaluation/results/` — ignores `*.json` and `*.tex`, keeps `.gitkeep`
  - **Commit**: `256cf57`
- [x] T032 All result JSONs include timestamp, config-hash (`sha256:...`), and code-version (git short hash) — NFR-005
  - Verified in: `eval_keyword_baseline.py`, `eval_model_comparison.py`, `eval_hybrid_vs_dense.py`
  - `eval_chunk_size.py` and `eval_export_latex.py` inherit from model comparison or read from result files

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

### Actual Execution Order (as implemented)

1. **Phase 1+2** together → commit `ea63e9f` (25 files, 36 tests)
2. **Phase 3** → commit `55ef107` (3 files, +9 tests = 45 total)
3. **Phase 4** → commit `475d75f` (2 files, +11 tests = 56 total)
4. **Phases 5+6+7+T031** together → commit `256cf57` (4 files, 56 tests stable)
5. **Phase 8** — T031+T032 done, T029+T030 remaining

---

## Deviations from Plan

### D1: Standalone WikiSearchClient (T015)
**Planned**: Import `pipeline/01_wiki_fetcher/api_client.py`
**Actual**: Created standalone `WikiSearchClient` in `eval_keyword_baseline.py`
**Reason**: `api_client.py` imports from `config.py` which runs module-level code (loads env.yaml, validates config, prints to stdout). Importing it would trigger side effects and require the fetcher's full config to be valid.

### D2: Standalone simple_chunk() (T019, T023)
**Planned**: Use `content_aware_chunker.py` from `pipeline/03_embeddings_creator/`
**Actual**: Created `simple_chunk()` in `eval_model_comparison.py`
**Reason**: `ContentAwareChunker` depends on pipeline's `config.py` (`get_config()`) and `Document` dataclass. These require the pipeline's YAML config system to be initialized. The evaluation chunker is paragraph-based with size limits — simpler and self-contained.

### D3: Multi-signal relevance scoring (T019)
**Planned**: Binary page-ID matching
**Actual**: Multi-signal scoring (word overlap + keyword match + fragment match) ported from prototype `research/techstack/ragas/professional_evaluation/metrics/retrieval_metrics.py`
**Reason**: User instructed to check prototypes before implementing. The prototype's approach is more sophisticated and better aligned with the RAGAS evaluation methodology used in the research phase.

### D4: Metrics include std dev + difficulty breakdown (T019)
**Planned**: Only aggregate means
**Actual**: All aggregate metrics report `{mean, std}` and results include `by_difficulty` breakdown
**Reason**: Aligned with prototype patterns in `professional_evaluation/metrics/statistical_analysis.py` and `category_analysis.py`. Thesis benefits from showing per-difficulty performance.

### D5: Hybrid mode limitation (T026)
**Planned**: Qdrant `query_mode` toggle between dense and hybrid
**Actual**: Both modes currently use vector search. True hybrid requires Qdrant full-text payload index.
**Reason**: Qdrant's hybrid search requires a pre-configured text index on the collection. The evaluation script structure supports both modes — the actual Qdrant query call needs updating when a full-text index is configured.

---

## Test Summary

| Test File | Count | What |
|-----------|------:|------|
| `test_metrics.py` | 29 | MRR, P@k, NDCG@k with hand-calculated examples |
| `test_providers.py` | 7 | ABC compliance, OllamaProvider, OpenAIProvider (mocked) |
| `test_keyword_baseline.py` | 9 | source_file→page_id mapping (6), mocked eval runner (3) |
| `test_model_comparison.py` | 11 | simple_chunk (5), relevance scoring (3), corpus loading (1), mocked pipeline (2) |
| **Total** | **56** | **All passing** |

---

## Commit History

| Commit | Phase | Files | Description |
|--------|-------|------:|-------------|
| `ea63e9f` | 1+2 | 25 | Foundation: metrics, providers, config, experiments, ground truth |
| `55ef107` | 3 | 3 | Keyword search baseline (FF1) |
| `475d75f` | 4 | 2 | Model comparison with multi-signal relevance (FF3) |
| `256cf57` | 5+6+7 | 4 | Chunk size, hybrid vs dense, LaTeX export, .gitignore |

All pushed to `origin/007-evaluation-infrastructure`.

---

## Remaining Work

1. **T029**: Integration test with real Qdrant — requires running services
2. **T030**: `evaluation/README.md` with setup + usage instructions
3. **D5 fix**: Configure Qdrant full-text index for true hybrid search in T026
