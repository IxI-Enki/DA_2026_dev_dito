---
title: Evaluation Infrastructure
description: Modular evaluation framework for thesis deliverables including retrieval metrics (MRR, P@5, NDCG@10), keyword vs semantic baseline, embedding model comparison, chunk size impact, and hybrid vs dense retrieval.
author:
  name: Jan Ritt
  github: 'https://github.com/IxI-Enki'
version: 1.0.0
created: 2026-02-01
updated: 2026-02-13
tags: [evaluation, metrics, retrieval, embeddings, thesis, rag]
---

# Evaluation Infrastructure

Modular evaluation framework for thesis deliverables: retrieval metrics (MRR, P@5, NDCG@10), keyword vs semantic baseline (FF1), embedding model comparison (FF3), chunk size impact (J4), and hybrid vs dense retrieval (J6).

**Branch**: `007-evaluation-infrastructure`
**Spec**: `specs/007-evaluation-infrastructure/spec.md`

---

## Setup

### 1. Python environment

From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r evaluation/requirements.txt
pip install -e .
```

### 2. Configuration

- **Qdrant** (for model comparison, chunk size, hybrid vs dense): `config/env.yaml` under `SERVICES.qdrant` (default `localhost:18334`). Start Qdrant via Docker Stack-G.
- **Qdrant Test Instance** (for integration tests): Isolated instance on port **18336** with separate volume. Start with:
  ```powershell
  docker compose -p stack-g-devdito --profile test up qdrant-test -d
  ```
- **Keyword baseline (FF1)** uses `config/env.yaml` → `SOURCE_WIKI.api.url` for DokuWiki JSON-RPC. No Qdrant required.
- **Ollama** (local embeddings): run `ollama serve` and pull a model, e.g. `ollama pull bge-m3`. Used by experiment configs under `evaluation/experiments/`.
- **OpenAI** (optional): place API key in `config/secrets/openai.token` for configs with `provider: openai`.

### 3. Ground truth and data

- Ground truth: `evaluation/ground_truth/leowiki_qa_50_verified.json` (see `evaluation/ground_truth/README.md` for format).
- Model comparison, chunk size, and hybrid scripts need **fetched wiki content**: `data/fetched/fetched_at_*/page_content/*.txt` for pages referenced in the ground truth. Run the wiki fetcher pipeline first if missing.

---

## Usage

All scripts support `--help`. Run from repo root so that `config/env.yaml` and paths resolve.

### FF1 — Keyword search baseline

Runs ground-truth questions against DokuWiki `core.searchPages`, outputs MRR and P@5.

```powershell
python -m evaluation.scripts.eval_keyword_baseline
python -m evaluation.scripts.eval_keyword_baseline --top-k 20 --verbose
```

**Output**: `evaluation/results/keyword_baseline_YYYYMMDD_HHMMSS.json`

### FF3 — Embedding model comparison

Single config or compare all `model_*.yaml` configs (Ollama + OpenAI). Needs Qdrant and embedding provider (Ollama and/or OpenAI key).

```powershell
python -m evaluation.scripts.eval_model_comparison --config evaluation/experiments/model_bge_m3.yaml
python -m evaluation.scripts.eval_model_comparison --compare-all --verbose
```

**Output**: `evaluation/results/model_<name>_<timestamp>.json` or `model_comparison_<timestamp>.json`

### J4 — Chunk size parametric evaluation

Compares chunk sizes (256 / 512 / 1024). Uses same pipeline as model comparison; needs Qdrant and corpus.

```powershell
python -m evaluation.scripts.eval_chunk_size --config evaluation/experiments/chunk_512.yaml
python -m evaluation.scripts.eval_chunk_size --compare
```

**Output**: `evaluation/results/chunk_<size>_<timestamp>.json` or `chunk_comparison_<timestamp>.json`

### J6 — Hybrid vs dense retrieval

Compares dense-only vs hybrid retrieval on one collection. Needs Qdrant and Ollama (or configured provider).

```powershell
python -m evaluation.scripts.eval_hybrid_vs_dense
python -m evaluation.scripts.eval_hybrid_vs_dense --verbose
```

**Output**: `evaluation/results/hybrid_vs_dense_<timestamp>.json`

**Note**: True hybrid (vector + BM25) requires Qdrant full-text index on the collection; see tasks.md deviation D5.

### LaTeX export (thesis tables)

Generates `.tex` tables from existing result JSONs. Auto-discovers latest files per pattern.

```powershell
python -m evaluation.scripts.eval_export_latex
python -m evaluation.scripts.eval_export_latex --results-dir evaluation/results --output-dir thesis/tables
```

**Output**: `evaluation/results/*.tex` (or chosen `--output-dir`) — FF1, FF3, J4, J6 tables.

---

## Ground truth format

See **`evaluation/ground_truth/README.md`** for:

- Schema of `leowiki_qa_50_verified.json`
- Fields: `question`, `ground_truth`, `source_file`, `context_keywords`, `difficulty`
- How `source_file` maps to DokuWiki page IDs for relevance checks

---

## Tests

- **Unit tests** (metrics, providers, keyword baseline, model comparison helpers): no external services.

  ```powershell
  pytest evaluation/tests/test_metrics.py evaluation/tests/test_providers.py evaluation/tests/test_keyword_baseline.py evaluation/tests/test_model_comparison.py -v
  ```

- **Integration tests** (Qdrant + optional Ollama): skipped if services are not reachable.

  ```powershell
  # Start the isolated test Qdrant first
  docker compose -p stack-g-devdito --profile test up qdrant-test -d
  
  # Run integration tests
  pytest evaluation/tests/test_integration.py -v
  ```

  With the test Qdrant (port 18336) and optionally Ollama running, the integration test creates a temporary collection, embeds a minimal corpus, runs a query, and asserts metrics are non-zero. Test data is isolated from production.

Run all evaluation tests:

```powershell
pytest evaluation/tests/ -v
```

---

## Result files (NFR-005)

All result JSONs include:

- `timestamp` (ISO UTC)
- `config_hash` (SHA-256 of experiment config)
- `code_version` (git short hash)

Outputs are under `evaluation/results/` (gitignored except `.gitkeep`). Use `--output-dir` / `--results-dir` where supported to override paths.
