---
title: Dev Dito
description: 5-stage RAG pipeline and evaluation framework for the diploma thesis (Stack-G).
author:
  name: Jan Ritt
  github: 'https://github.com/IxI-Enki'
version: 2.0.0
created: 2026-02-13
updated: 2026-02-23
tags: [pipeline, rag, evaluation, dokuwiki, qdrant, embeddings, diploma-thesis, stack-g]
---

# Dev Dito

RAG pipeline (5 stages) and evaluation framework for the diploma thesis (Stack-G).  
Fetches a DokuWiki, preprocesses and embeds the content, deploys to Qdrant, and evaluates retrieval quality.

---

## What this demonstrates

- **RAG pipeline** — a 5-stage DokuWiki → embeddings → Qdrant flow.
- **Spec-Driven Development** — 13 numbered feature specs under `specs/`,
  a project constitution under `.specify/`, and CI that turns specs into issues.
- **Agentic orchestration** — reproducible Claude / Cursor / Spec-Kit command
  sets under `.claude/`, `.cursor/`, and `.prompts/`.
- **Evaluation** — a RAGAS + custom-metric framework under `evaluation/`.

Real source data is **not** published; each stage ships a small, redacted
sample under `data/<stage>/samples/`. See [PRIVACY.md](PRIVACY.md).

---

## Pipeline Overview

```sketch
Stage 01  Wiki Fetcher          DokuWiki JSON-RPC  ->  data/fetched/
Stage 02  Deep Evaluation       content analysis   ->  data/evaluated/
Stage 03  RAG Preprocessing     Markdown + meta    ->  data/preprocessed/
Stage 04  Embeddings Creator    vectors (JSONL)    ->  data/embeddings/
Stage 05  Deploy                SCP / Qdrant       ->  Raspberry Pi / Qdrant
```

---

## Setup

### 1. Python environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r evaluation/requirements.txt
pip install -e .
```

### 2. Configuration

Copy the placeholder config and fill in your values:

```powershell
Copy-Item config/PLACEHOLDER_env.yaml config/env.yaml
```

Key sections in `config/env.yaml`:

| Section          | Purpose                                                   |
| :--------------- | :-------------------------------------------------------- |
| `SOURCE_WIKI`    | DokuWiki API URL, token path, SSL cert                    |
| `FETCH`          | Timeout, retries, media options, namespace depth          |
| `SERVICES.qdrant`| Host and port for Qdrant (default `localhost:18334`)      |
| `EMBEDDINGS`     | Provider (Ollama / OpenAI), model, chunk size             |

Secrets go in `config/secrets/` (gitignored):

| File                         | Used by                        |
| :--------------------------- | :----------------------------- |
| `config/secrets/api.token`   | DokuWiki JSON-RPC bearer token |
| `config/secrets/ssl.cert`    | DokuWiki SSL certificate       |
| `config/secrets/openai.token`| OpenAI embeddings (optional)   |

### 3. Services

Start Qdrant (and optionally DokuWiki) via Docker:

```powershell
# Qdrant only
docker compose -p stack-g-devdito up qdrant -d

# Full stack (DokuWiki + Qdrant)
docker compose -p stack-g-devdito --profile wiki up -d

# Isolated Qdrant for tests (port 18336)
docker compose -p stack-g-devdito --profile test up qdrant-test -d
```

---

## Stage 01 — Wiki Fetcher

Fetches the complete DokuWiki (pages, metadata, HTML, links, media) via JSON-RPC.

```powershell
# Via Docker (recommended)
docker compose -p stack-g-devdito --profile pipeline run module_fetcher

# Direct (from repo root)
python pipeline/01_wiki_fetcher/fetch_full_wiki_extended.py

# Without media download (faster)
python pipeline/01_wiki_fetcher/fetch_full_wiki_extended.py --no-media
```

**Output:** `data/fetched/fetched_at_YYYYMMDD_HHMMSS/`

```tree
fetched_at_TIMESTAMP/
├── page_content/           # raw wiki text per page
├── page_metadata/          # page info + ACL
├── page_html/              # rendered HTML
├── page_links/             # extracted links
├── media/                  # downloaded media files
├── namespaces/             # namespace tree
├── raw_json/               # raw API responses
├── fetch_statistics.json
└── wiki_analysis_report.txt
```

Key config options (`FETCH` section in `env.yaml`):

| Option                      | Default | Description                              |
| :-------------------------- | :------ | :--------------------------------------- |
| `timeout`                   | 2       | Request timeout in seconds               |
| `max_retries`               | 3       | Retries on failure                       |
| `max_namespace_depth`       | 3       | Depth for sub-namespace media scan       |
| `media.enabled`             | true    | Download media files                     |
| `media.max_file_size_mb`    | 50      | Skip files larger than this (0 = all)    |
| `filter.exclude_namespaces` | []      | Skip these namespaces                    |

---

## Stage 02 — Deep Evaluation

Analyzes fetched wiki content and generates preprocessing strategy recommendations.

```powershell
# From pipeline/02_deep_evaluation/
python run_deep_evaluation.py

# Show current config
python run_deep_evaluation.py --show-config
```

**Input:** `data/fetched/fetched_at_*/`  
**Output:** `data/evaluated/` — strategy reports per page/namespace

---

## Stage 03 — RAG Preprocessing

Converts fetched DokuWiki content to Markdown with YAML frontmatter, applying deep-evaluation strategies.

```powershell
# Auto-discovers latest fetched data
python pipeline/03_rag_preprocessing/run_preprocessing.py

# Explicit input directory
python pipeline/03_rag_preprocessing/run_preprocessing.py \
  --input-dir data/fetched/fetched_at_20260201 \
  --evaluated-dir data/evaluated
```

**Output:** `data/preprocessed/preprocessed_at_YYYYMMDD_HHMMSS/`  
Each page → `{page_id}.md` with frontmatter (`source`, `namespace`, `difficulty`, `chunk_strategy`, …)

---

## Stage 04 — Embeddings Creator

Chunks the preprocessed Markdown and creates vector embeddings (Ollama or OpenAI).

```powershell
# Process all documents
python pipeline/04_embeddings_creator/run_embeddings.py

# Limit to 10 documents (testing)
python pipeline/04_embeddings_creator/run_embeddings.py --limit 10

# Custom experiment config
python pipeline/04_embeddings_creator/run_embeddings.py \
  --config evaluation/experiments/chunk_512.yaml
```

**Output:** `data/embeddings/embedded_at_YYYYMMDD_HHMMSS/embedded_chunks.jsonl`

Each line in the JSONL:

```json
{
  "id": "...",
  "page_id": "...",
  "chunk_index": 0,
  "chunk_text": "...",
  "embedding": [...],
  "metadata": { "chunk_size": 512, "model": "bge-m3", ... }
}
```

---

## Stage 05 — Deploy

Transfers embeddings to a Raspberry Pi via SCP or uploads directly to a Qdrant instance.

```powershell
# Transfer to Raspberry Pi (SCP)
python pipeline/05_deploy/run_deploy.py transfer

# Dry run (show what would be transferred)
python pipeline/05_deploy/run_deploy.py transfer --dry-run

# Upload directly to Qdrant
python pipeline/05_deploy/run_deploy.py qdrant

# Verify a previous transfer (MD5 checksum)
python pipeline/05_deploy/run_deploy.py verify --check-qdrant
```

**Configuration:** `pipeline/05_deploy/config.yaml`

```yaml
ssh:
  host: raspi-docker
  user: imreo
  port: 22
remote:
  embeddings_dir: ~/mcp-diploma-thesis-final/data/incoming/
qdrant:
  host: localhost
  port: 6333
  collection_name: wiki_embeddings
```

---

## Evaluation

Framework for thesis deliverables. All scripts run from the repo root; results go to `evaluation/results/`.

### FF1 — Keyword search baseline

Runs ground-truth questions against DokuWiki `core.searchPages`, outputs MRR and P@5.

```powershell
python -m evaluation.scripts.eval_keyword_baseline
python -m evaluation.scripts.eval_keyword_baseline --top-k 20 --verbose
```

**Output:** `evaluation/results/keyword_baseline_YYYYMMDD_HHMMSS.json`

---

### FF3 — Embedding model comparison

Compares embedding models (Ollama + OpenAI) on the same ground truth. Needs Qdrant + provider.

```powershell
python -m evaluation.scripts.eval_model_comparison \
  --config evaluation/experiments/model_bge_m3.yaml

# Compare all model configs
python -m evaluation.scripts.eval_model_comparison --compare-all --verbose
```

**Output:** `evaluation/results/model_<name>_<timestamp>.json`

---

### J4 — Chunk size impact

Compares chunk sizes 256 / 512 / 1024 on MRR, P@5, NDCG@10.

```powershell
python -m evaluation.scripts.eval_chunk_size \
  --config evaluation/experiments/chunk_512.yaml

# Compare all chunk sizes
python -m evaluation.scripts.eval_chunk_size --compare
```

**Output:** `evaluation/results/chunk_<size>_<timestamp>.json`

---

### J6 — Hybrid vs dense retrieval

Compares dense-only vs hybrid retrieval on one collection.

```powershell
python -m evaluation.scripts.eval_hybrid_vs_dense
python -m evaluation.scripts.eval_hybrid_vs_dense --verbose
```

**Output:** `evaluation/results/hybrid_vs_dense_<timestamp>.json`

> Note: True hybrid (vector + BM25) requires a Qdrant full-text index on the collection (see tasks.md D5).

---

### Visualizations (J4, J6)

Generates figures for the thesis (saved as 300 DPI PNG to `evaluation/figures/`).

```powershell
python -m evaluation.scripts.eval_visualize_j4_j6
```

---

### LaTeX export

Generates `.tex` tables from existing result JSONs. Auto-discovers latest files per pattern.

```powershell
python -m evaluation.scripts.eval_export_latex

# Custom directories
python -m evaluation.scripts.eval_export_latex \
  --results-dir evaluation/results \
  --output-dir thesis/tables
```

**Output:** `evaluation/results/*.tex` — tables for FF1, FF3, J4, J6.

---

## Ground Truth

50 verified Q&A pairs: `evaluation/ground_truth/leowiki_qa_50_verified.json`

Fields per entry: `question`, `ground_truth`, `source_file`, `context_keywords`, `difficulty`

See `evaluation/ground_truth/README.md` for the full schema.

---

## Tests

```powershell
# All root-level tests
pytest tests/ -v --tb=short

# Evaluation unit tests only (no external services)
pytest evaluation/tests/ -v

# Integration tests (requires Qdrant on port 18336)
docker compose -p stack-g-devdito --profile test up qdrant-test -d
pytest evaluation/tests/test_integration.py -v
```

Result JSONs include `timestamp`, `config_hash` (SHA-256), and `code_version` (git short hash).

---

## Experiment Configs

Reusable YAML configs under `evaluation/experiments/`:

| File                  | Description                        |
| :-------------------- | :--------------------------------- |
| `model_bge_m3.yaml`   | BGE-M3 via Ollama                  |
| `model_openai.yaml`   | OpenAI text-embedding-3-small      |
| `chunk_256.yaml`      | Chunk size 256 tokens              |
| `chunk_512.yaml`      | Chunk size 512 tokens              |
| `chunk_1024.yaml`     | Chunk size 1024 tokens             |
