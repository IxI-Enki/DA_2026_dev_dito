# Implementation Plan: Evaluation Infrastructure

**Branch**: `007-evaluation-infrastructure` | **Date**: 2026-02-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/007-evaluation-infrastructure/spec.md`
**Thesis-Zuordnung**: FF1, FF3, J1, J2, J4, J6

## Summary

Aufbau eines modularen Evaluations-Frameworks, das vier Thesis-Tabellen generiert:
1. Keyword vs Semantic Search (FF1) — MRR, Precision@5
2. Embedding Model Comparison (FF3) — NDCG@10 ueber 3+ Modelle (Ollama, OpenAI, MTEB)
3. Chunk Size Impact (J4) — 256/512/1024 Token Vergleich
4. Hybrid vs Dense Retrieval (J6) — Precision@5, NDCG@10

Das Framework nutzt bestehende Komponenten (JSON-RPC API Client, Content-Aware Chunker, Qdrant Client) und erweitert sie um austauschbare Embedding-Provider und parametrische Experiment-Configs.

## Technical Context

**Language/Version**: Python 3.11+ (matching existing pipeline)
**Primary Dependencies**: `qdrant-client`, `openai`, `ollama` (Python SDK), `requests`, `pyyaml`, `numpy`
**Storage**: Qdrant (Stack-D or local dev), JSON/JSONL for results
**Testing**: pytest (unit tests for metrics, integration tests against Qdrant)
**Target Platform**: Windows 11 (host-native, venv), optional Docker
**Performance Goals**: Full evaluation run (3 models x 50 queries) < 30 minutes
**Constraints**: OpenAI costs < $5/run, Ollama models require local GPU/CPU
**Scale/Scope**: 50 ground-truth queries, 3-5 embedding models, 3 chunk sizes

## Constitution Check

| Article                              | Status  | Notes                                                          |
| ------------------------------------ | ------- | -------------------------------------------------------------- |
| Article I (Layered Architecture)     | PASS    | Evaluation is Python-only, no PHP interaction                  |
| Article II (JSON Interface)          | PASS    | All output is JSON/JSONL                                       |
| Article II-B (YAML Config)           | PASS    | Experiment configs are YAML                                    |
| Article III (Critical-Path Testing)  | PASS    | Metric calculations require unit tests                         |
| Article VI (Secret Containment)      | PASS    | OpenAI key via `config/secrets/openai.token`                   |
| Article VII (Integration Simplicity) | PASS    | Reuses existing `api_client.py` and `content_aware_chunker.py` |
| Article VIII (Direct Framework)      | PASS    | Direct `qdrant_client`, `openai`, `ollama` usage               |
| Article X (Evaluation-First)         | PRIMARY | This feature IS Article X's mandate                            |
| Article XI (Thesis Alignment)        | PASS    | Maps directly to FF1, FF3, J1, J2, J4, J6                      |
| Article XII (Resource Governance)    | N/A     | No new Docker services (host-native per NFR-001)               |
| Article XIV (Inter-Stack)            | PASS    | Connects to Stack-D Qdrant via HTTP                            |

## Project Structure

### Documentation

```text
specs/007-evaluation-infrastructure/
├── spec.md              # Feature specification (done)
├── plan.md              # This file
└── tasks.md             # Next: /tasks command
```

### Source Code

```text
evaluation/                              # NEW directory at repo root
├── __init__.py
├── config.py                            # YAML config loader (reuses pattern from pipeline)
├── ground_truth/
│   ├── leowiki_qa_50_verified.json      # COPY from research/techstack/ragas/ground_truth/
│   └── README.md                        # Corpus documentation (feeds J1 thesis section)
├── experiments/                         # YAML experiment configs
│   ├── keyword_baseline.yaml
│   ├── model_bge_m3.yaml
│   ├── model_openai_3large.yaml
│   ├── model_mxbai_embed_de.yaml
│   ├── chunk_256.yaml
│   ├── chunk_512.yaml
│   ├── chunk_1024.yaml
│   └── hybrid_vs_dense.yaml
├── providers/                           # Embedding provider abstraction
│   ├── __init__.py
│   ├── base.py                          # ABC: EmbeddingProvider
│   ├── ollama_provider.py               # Ollama Python SDK
│   └── openai_provider.py               # OpenAI Python Client
├── metrics/                             # Retrieval quality metrics
│   ├── __init__.py
│   ├── mrr.py                           # Mean Reciprocal Rank
│   ├── precision_at_k.py                # Precision@k
│   └── ndcg.py                          # NDCG@k
├── scripts/                             # CLI entry points
│   ├── eval_keyword_baseline.py         # US1: DokuWiki core.searchPages baseline
│   ├── eval_model_comparison.py         # US2: Multi-model evaluation
│   ├── eval_chunk_size.py               # US3: Parametric chunk size
│   ├── eval_hybrid_vs_dense.py          # US4: Dense vs Hybrid retrieval
│   └── eval_export_latex.py             # US5: LaTeX table export
├── results/                             # Output (gitignored except summaries)
│   └── .gitkeep
├── tests/
│   ├── test_metrics.py                  # Unit tests: MRR, P@k, NDCG correctness
│   ├── test_providers.py                # Unit tests: provider interface compliance
│   └── test_integration.py              # Integration: end-to-end with local Qdrant
├── requirements.txt
└── README.md
```

**Structure Decision**: Flat `evaluation/` directory at repo root (not inside `pipeline/`). Rationale: Evaluation is cross-cutting — it tests the ENTIRE pipeline output, not a single stage. Per Article VII, no unnecessary abstraction layers.

## Component Design

### 1. EmbeddingProvider (Abstract Interface)

```python
# evaluation/providers/base.py
from abc import ABC, abstractmethod

class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts. Returns list of vectors."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str: ...

    @property
    @abstractmethod
    def dimensions(self) -> int: ...

    @property
    def cost_per_token(self) -> float:
        return 0.0  # Free for local models
```

**OllamaProvider**: Uses `ollama.embed()` — any model from `ollama list`
**OpenAIProvider**: Uses `openai.embeddings.create()` — tracks token usage and cost

### 2. Experiment Config Schema

```yaml
# evaluation/experiments/model_bge_m3.yaml
experiment:
  name: BGE-M3 via Ollama
  type: model_comparison      # model_comparison | chunk_size | hybrid_vs_dense | keyword_baseline
  thesis_id: 'J2/FF3'

embedding:
  provider: ollama            # ollama | openai
  model: 'bge-m3'
  dimensions: 1024            # Model-specific

chunking:
  strategy: content_aware     # Reuses existing content_aware_chunker.py
  chunk_size: 512             # Default, overridden in chunk_size experiments
  chunk_overlap: 50

retrieval:
  mode: dense                 # dense | hybrid
  top_k: 10
  collection_prefix: 'eval_'  # Temporary collections: eval_bge_m3_512

ground_truth:
  file: 'ground_truth/leowiki_qa_50_verified.json'

metrics:
  - mrr
  - precision_at_5
  - ndcg_at_10
```

### 3. Metric Implementations

All metrics are pure functions with no external dependencies:

- **MRR**: `1/rank` of first relevant result, averaged over queries. `mrr([ranks]) -> float`
- **Precision@k**: `|relevant ∩ top_k| / k`. `precision_at_k(retrieved, relevant, k=5) -> float`
- **NDCG@k**: Normalized DCG using graded relevance scores. `ndcg_at_k(retrieved, relevance_map, k=10) -> float`

Unit tests verify against hand-calculated examples from IR textbooks.

### 4. Keyword Baseline (US1)

Reuses `pipeline/01_wiki_fetcher/api_client.py` for JSON-RPC calls:
```python
# Pseudocode
for query in ground_truth.questions:
    results = api_client.call("core.searchPages", query.text)
    ranked_pages = [r["id"] for r in results[:10]]
    mrr = compute_mrr(ranked_pages, query.relevant_pages)
    p5 = precision_at_k(ranked_pages, query.relevant_pages, k=5)
```

### 5. Result Format

```json
{
  "experiment": "model_bge_m3",
  "timestamp": "2026-02-15T14:30:00Z",
  "code_version": "abc1234",
  "config_hash": "sha256:...",
  "aggregate": {
    "mrr": 0.72,
    "precision_at_5": 0.65,
    "ndcg_at_10": 0.68
  },
  "per_query": [
    {"query_id": "q01", "mrr": 0.5, "precision_at_5": 0.6, "ndcg_at_10": 0.55}
  ],
  "cost": {"tokens": 12500, "usd": 0.15}
}
```

### 6. LaTeX Export (US5)

Reads result JSONs and produces:
```latex
\begin{tabular}{lrrr}
\toprule
Model & MRR & P@5 & NDCG@10 \\
\midrule
Keyword Search (Baseline) & 0.35 & 0.28 & -- \\
BGE-M3 (Ollama) & 0.72 & 0.65 & 0.68 \\
text-embedding-3-large (OpenAI) & 0.78 & 0.71 & 0.74 \\
mxbai-embed-de-large-v1 (Ollama) & 0.75 & 0.68 & 0.71 \\
\bottomrule
\end{tabular}
```

## Dependencies (Reused from Existing Code)

| Component             | Source                                                                  | Usage                          |
| --------------------- | ----------------------------------------------------------------------- | ------------------------------ |
| JSON-RPC API Client   | `pipeline/01_wiki_fetcher/api_client.py`                                | Keyword baseline (US1)         |
| Content-Aware Chunker | `research/techstack/qdrant/embeddings_creator/content_aware_chunker.py` | Chunk size experiments (US3)   |
| Ground Truth Data     | `research/techstack/ragas/ground_truth/leowiki_qa_50_verified.json`     | All evaluations                |
| Config Loader Pattern | `config.py` (repo root)                                                 | YAML experiment config loading |
| Qdrant Client         | `qdrant-client` (pip)                                                   | Collection management, search  |

## Implementation Phases

### Phase 1: Foundation (Days 1-2)
- Metrics module (MRR, P@k, NDCG) with unit tests
- EmbeddingProvider ABC + OllamaProvider
- Config loader for experiment YAML
- Ground truth file copy + README

### Phase 2: Keyword Baseline — FF1 (Day 3)
- `eval_keyword_baseline.py` using existing `api_client.py`
- First thesis table produced

### Phase 3: Model Comparison — FF3 (Days 4-5)
- OpenAIProvider implementation
- `eval_model_comparison.py` with `--config` and `--compare-all`
- Run 3 models, produce comparison table

### Phase 4: Chunk Size — J4 (Day 6)
- `eval_chunk_size.py` integrating existing chunker
- Run 256/512/1024, produce comparison table

### Phase 5: Hybrid vs Dense — J6 (Day 7)
- `eval_hybrid_vs_dense.py` (Qdrant config toggle)
- Produce comparison table

### Phase 6: Export + Polish (Day 8)
- `eval_export_latex.py`
- Integration tests
- README documentation

**Total estimated effort**: 8 focused days. Thesis tables start appearing from Day 3.

## Complexity Tracking

No Constitution violations. All components use direct framework calls (Article VIII), reuse existing code (Article VII), and serve thesis deliverables (Article XI).
