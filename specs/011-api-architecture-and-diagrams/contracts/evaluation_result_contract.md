# Evaluation result JSON contract

Visualizations (J4, J6) in this branch **read** these files; they do not define the producer. This document describes the **expected shape** so notebook/script authors can load data and fail gracefully if structure is missing.

---

## Chunk comparison (J4 bar chart, optional by difficulty)

**Path**: `dev_dito/evaluation/results/chunk_comparison_*.json`

**Expected shape** (minimal for bar chart):

```json
{
  "thesis_id": "J4",
  "timestamp": "<ISO8601>",
  "chunk_sizes": [
    {
      "chunk_size": 256 | 512 | 1024,
      "corpus_chunks": <number>,
      "mrr": <number>,
      "ndcg_at_10": <number>,
      "precision_at_5": <number>,
      "hit_rate": <number>
    }
  ]
}
```

- **Bar chart**: Use `chunk_sizes[].chunk_size`, `mrr`, `ndcg_at_10`. If `by_difficulty` or per-difficulty breakdown exists, use it; otherwise aggregate only.
- **Missing file**: Log warning, skip bar chart (FR-013).

---

## Hybrid vs Dense (J6 bar chart + scatter)

**Path**: `dev_dito/evaluation/results/hybrid_vs_dense_*.json`

**Expected shape** (minimal):

- **Aggregate** (for bar chart): `comparison.dense`, `comparison.hybrid` each with `mrr.mean`, `ndcg_at_10.mean`, `precision_at_5.mean`, `hit_rate`.
- **Per-query** (for scatter): `dense.per_query` and `hybrid.per_query` arrays; each element has `id`, `rr` (or `mrr`), and optionally `ndcg_at_10`. Match by query `id` to plot Dense-MRR (x) vs Hybrid-MRR (y) with y=x reference.

**Missing file or missing per_query**: Log warning; if only aggregate present, produce bar chart only and skip scatter or show a note (FR-013, edge case spec).

---

## Box plot (J4) — chunk-size distribution

**Current chunk_comparison JSON does NOT contain per-chunk token counts.** Options:

1. **Separate data source**: Preprocessed corpus (e.g. JSONL from pipeline 03/04) with chunk token counts per `chunk_size` setting. Contract: array of `{ chunk_size, token_count }` or one array per chunk_size.
2. **Defer**: Document in notebook that box plot requires chunk-level data; skip or show placeholder until available.

See [research.md](../research.md) section 4.
