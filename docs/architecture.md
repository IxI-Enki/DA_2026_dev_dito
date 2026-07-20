# Dev Dito — Architecture

> **Status:** 2026-07-21
> **Version:** 0.1.0
> **Author:** Jan Ritt ([IxI-Enki](https://github.com/IxI-Enki))

This document is the single current architecture reference for the repository.
It describes the wiki→embedding→RAG **pipeline** (the centerpiece), the
**two evaluation layers**, and how the optional DokuWiki plugin and Docker
backend services relate to the pipeline.

> **Supersedes** four earlier, mutually inconsistent architecture-era
> documents, now archived: the legacy-repo `architecture.md`, the
> "9-stack Docker" `README_ARCHITECTURE.md`, `gap_analysis_prototypes_vs_pipeline.md`,
> and the `dev_dito_pipeline_manager.md` plugin plan.

---

## 1. Overview

Dev Dito turns a DokuWiki instance into a semantically searchable knowledge
base. The **pipeline** (`pipeline/`) fetches wiki content, evaluates its
quality, preprocesses it into clean Markdown, creates embeddings, and deploys
them to a Qdrant vector database on a Raspberry Pi.

The pipeline is **self-contained**: it does not import from `backend_services/`
and references DokuWiki only through one cosmetic URL string
(`pipeline/03_rag_preprocessing/page_processor.py:270`). The DokuWiki plugin
and the Docker backend services are a **separable integration / deployment
layer** — useful for running the system inside a wiki, but not required for the
pipeline to run end to end.

```
DokuWiki  ──▶  1. Fetch  ──▶  2. Deep Eval  ──▶  3. Preprocess  ──▶  4. Embed  ──▶  5. Deploy  ──▶  Qdrant (Raspberry Pi)
                                   │                    ▲
                                   └── per-page strategy ┘
```

---

## 2. The pipeline (centerpiece)

Five ordered stages under `pipeline/`, plus `pipeline/shared/` (`cli_utils.py`
for colored CLI banners and SIGINT handling). Each stage has a `run_*.py` CLI
entry point and reads/writes timestamped directories under `data/`.

### Stage 1 — Wiki Fetcher (`01_wiki_fetcher/`)
Fetches pages, metadata, links, backlinks, history, and media from the DokuWiki
JSON-RPC API.
- `api_client.py` — JSON-RPC client (session pooling, retry, error classification)
- `fetch_full_wiki_extended.py` — full-coverage fetch
- `incremental_fetcher.py` + `change_detector.py` — delta fetches
- `media_cache.py`, `resume_fetch.py`, `manifest.py`, `progress_tracker.py`
- **Output:** `data/fetched/fetched_at_<timestamp>/`

This stage produces data with integrity tracking (manifest + change detection);
it is not itself a pass/fail quality gate.

### Stage 2 — Deep Evaluation (`02_deep_evaluation/`)
Evaluates fetched content and decides how it should be processed. This stage
runs **two complementary evaluators by design**:

1. **Strategy path (LLM-based)** — `run_deep_evaluation.py` orchestrates the
   deep analyzers (`analyzers/wiki_deep_analyzer.py`,
   `document_deep_analyzer.py`, `media_deep_analyzer.py`,
   `content_classifier.py`, `rag_readiness_checker.py`, `temporal_analyzer.py`,
   `format_quality_analyzer.py`) and `generators/strategy_generator.py`, which
   emits a **per-page preprocessing strategy** (what to chunk, how). Output is
   consumed downstream by Stage 3.
2. **Verdict path (heuristic, no LLM)** — `evaluator.py` (`ContentEvaluator`)
   scores each page on content / structure / link / freshness and returns an
   **`include` / `exclude` / `review` recommendation**, flagging empty, stub,
   orphan, broken-link, and template-only pages. It is a fast, cost-free gate
   that needs no LLM.

These are two intentional roles: the LLM path answers *"how should this page be
processed?"*, the heuristic path answers *"should this page be embedded at
all?"*.
- **Output:** `data/evaluated/` (strategy + evaluation report)

### Stage 3 — RAG Preprocessing (`03_rag_preprocessing/`)
Converts wiki markup into clean Markdown, guided by the Stage 2 strategy
(`run_preprocessing.py` loads it via `get_latest_evaluation(...)`).
- `page_processor.py` — DokuWiki→Markdown conversion, section extraction
- `metadata_enricher.py` — access level, freshness, namespace metadata
- `media_processor.py` + `image_captioner.py`, `strategy_loader.py`,
  `exporter.py`, `spot_check.py`
- **`evaluation/` — the strongest per-stage gate** (see §3, Layer 1)
- **Output:** clean Markdown ready for embedding

### Stage 4 — Embeddings Creator (`04_embeddings_creator/`)
Chunks and embeds the preprocessed content.
- `content_aware_chunker.py` — strategy-driven, section- + size-aware chunking
- `document_loader.py`, `embedder.py` (OpenAI / Ollama), `pipeline.py`
- **Output:** `embedded_chunks.jsonl` (vectors + metadata)

This stage is a transformation, not a pass/fail gate.

### Stage 5 — Deploy (`05_deploy/`)
Ships the embeddings to the target and verifies them.
- `transfer_to_pi.py` — SSH/SCP transfer to the Raspberry Pi
- `verify_transfer.py` — **per-stage gate:** MD5 checksum of local vs remote
  JSONL, plus optional Qdrant collection check (`--check-qdrant`)
- `deploy_qdrant.py`, `run_deploy.py` (`transfer` / `qdrant` / `verify`)

---

## 3. Two evaluation layers

The system evaluates quality at **two different altitudes**. Keeping them
distinct is the key to understanding the design.

### Layer 1 — Per-stage quality gates (in-pipeline)
"Is the data good enough to proceed to the next stage?"

| Stage | Gate | What it checks |
|-------|------|----------------|
| 2 | `evaluator.py` (`ContentEvaluator`) | Heuristic per-page include/exclude/review; empty/stub/orphan/broken-link flags |
| 3 | `03_rag_preprocessing/evaluation/` | **7-metric suite** comparing original DokuWiki vs processed Markdown |
| 5 | `verify_transfer.py` | Post-transfer MD5 checksum + optional Qdrant check |

The Stage 3 gate (`evaluation/metrics.py`, runner `run_eval_preprocessing.py`)
is the most rigorous: Content Completeness (≥0.85), Semantic Similarity (≥0.85,
sentence-transformers with a SequenceMatcher fallback), Entity Preservation
(dates/rooms/emails/URLs, ≥0.95), Link Integrity (≥0.95), Noise Detection
(wiki-syntax remnants / mojibake / HTML, ≤0.02), Readability (German-adapted
Flesch, ≥20), and Structure Preservation (≥0.90). Per-document
`passes_thresholds()` plus an aggregate `check_regression()` that fails when the
pass-rate drops below `REGRESSION_THRESHOLD = 0.90` — a CI-style regression gate.

### Layer 2 — Final RAG evaluation (top-level `evaluation/`)
"How good is the retrieval system as a whole?" — answers the thesis research
questions. Separate from the pipeline and from Layer 1.
- `metrics/` — MRR, NDCG@10, Precision@5, Recall@K, MAP, Hit Rate, plus
  `statistical.py` and `llm_judge.py`
- `ground_truth/` — manually verified Q&A sets (e.g. `leowiki_qa_50_verified.json`)
- `experiments/` — FF1 (keyword vs semantic baseline), FF3 (model comparison),
  J4 (chunk size), J6 (hybrid vs dense)
- `providers/`, `statistics/`, `visualization/`, `figures/`, `reports/`,
  `notebooks/`, `ragas/`

### The RAGAS decision
The core thesis results rely on **retrieval metrics on a manually verified
ground-truth set**, *not* on the RAGAS library. RAGAS was originally used for
(1) synthetic question generation (which did not produce usable results) and
(2) optional LLM-as-judge metrics. Both were dropped as requirements. An
optional LLM-as-judge path (`metrics/llm_judge.py`) and a RAGAS integration
(`ragas/ragas_evaluator.py`) still exist, but are not needed to reproduce the
core retrieval results.

---

## 4. Integration / deployment layer (separable)

Neither of these is required for the pipeline to run; both let the system live
inside a running DokuWiki + Docker environment.

- **`dokuwiki_plugin/`** — the DokuWiki PHP plugin (service gateway UI). See its
  own README.
- **`backend_services/`** — Dockerized services (fetcher, preprocessor,
  embedder, evaluator, deployer, orchestrator) plus `docker-compose.yml`. See
  its own README.

---

## 5. Configuration & data

- **Central config:** `config/env.yaml` (single source of truth; secrets in
  `config/secrets/`). Placeholders are committed; the real files are gitignored.
- **Data flow:** `data/fetched/` → `data/evaluated/` → preprocessed Markdown →
  `embedded_chunks.jsonl` → Qdrant on the Raspberry Pi. `data/` contents are
  gitignored (structure kept).
