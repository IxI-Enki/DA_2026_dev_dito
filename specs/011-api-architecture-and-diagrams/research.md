# Research: API Architecture Comparison & Thesis Diagrams

**Branch**: `011-api-architecture-and-diagrams` | **Spec**: [spec.md](./spec.md)

## 1. Diagram pipeline and theme

**Decision**: Use the existing diagram system from `dev_prompts_instructions_notes`: self-contained HTML in `html_projects/<id>/index.html`, theme from `theme.yaml` / `theme_manifest.yaml`, export via Puppeteer (e.g. `tools/diagram_generator`) to PNG. Use theme `00_thesis_default` (primary #2E4F8F, secondary #72ADCB, accent #F28D2C) for all new diagrams.

**Rationale**: Spec and constitution require no new abstractions; the diagram catalog and theme system are already the thesis standard. Theme tokens are in `assets/diagrams/themes/_tokens.css`; HTML loads `theme-loader.js` and `diagram-base.css` and uses `var(--th-*)` for colors.

**Alternatives considered**: Building a separate diagram stack was rejected (duplication, maintenance). Using only Matplotlib for architecture diagrams was rejected (spec requires HTML-based pipeline for Ch. 2/4 diagrams).

---

## 2. Output path alignment (content vs assets)

**Decision**: Spec defines target paths as `content/diagrams/html_projects/` and `content/diagrams/png_output/`. The existing repo uses `assets/diagrams/sources/html_projects/` and `assets/diagrams/exports/png_output/`. New artifacts for this branch SHOULD follow the spec paths under `content/diagrams/`; if the generator CLI is wired to `assets/`, either (a) add a second output target for `content/diagrams/` or (b) document in quickstart that deliverables are copied/moved to spec paths after export.

**Rationale**: Spec is the single source of truth for deliverable locations; consistency with existing layout is a convenience, not a requirement.

**Alternatives considered**: Putting everything under `assets/` only was rejected because the spec explicitly names `content/diagrams/`.

---

## 3. Evaluation result JSON and visualizations

**Decision**: J4 bar chart and J6 bar/scatter use existing JSON: `evaluation/results/chunk_comparison_*.json` (aggregate MRR/NDCG per chunk_size; no by_difficulty in current schema) and `evaluation/results/hybrid_vs_dense_*.json` (comparison.dense / comparison.hybrid aggregate metrics plus `dense.per_query` and `hybrid.per_query` for scatter). Notebooks run from `dev_dito`; figures are written to `evaluation/figures/`. If a result file is missing, log a clear warning and skip the corresponding figure (no hard failure).

**Rationale**: Spec FR-013 requires loading from existing JSON and failing gracefully. Chunk-comparison JSON does not include per-difficulty breakdown; if FR-005 is interpreted as "by difficulty", either (a) aggregate only (by chunk_size) is acceptable for this branch or (b) a one-time re-run of eval with by_difficulty output would be a separate task.

**Alternatives considered**: Generating new evaluation runs in this branch was rejected (spec: "no new evaluations").

---

## 4. Box plot (FR-007) — chunk-size distribution

**Decision**: The chunk_comparison JSON contains only aggregate metrics (e.g. corpus_chunks, mrr, ndcg_at_10), not per-chunk token counts. For the box plot of "real chunk-size distribution", use one of: (1) Parse preprocessed corpus output (e.g. JSONL from pipeline 03 or 04) and compute token counts per chunk for each target size (256/512/1024); (2) If such JSONL is not available, document as limitation and show a simplified view (e.g. distribution of chunk counts per document per setting) or defer box plot to a branch that has access to chunk-level data.

**Rationale**: Spec assumption states that chunk-comparison JSON does not contain per-chunk lengths; the box plot explicitly requires "actual token-count distribution per chunk-size setting".

**Alternatives considered**: Inventing synthetic distributions was rejected (thesis integrity). Using only corpus_chunks per setting as a single bar was rejected as not matching FR-007 (distribution).

---

## 5. ContentAwareChunker flowchart (FR-006)

**Decision**: Flowchart source of truth is `dev_dito/pipeline/04_embeddings_creator/content_aware_chunker.py`: flow is (1) should_skip(document) by content_type config, (2) prepare_text (optional frontmatter), (3) chunk_document: content-type-specific config (skip / table / list / default), heading detection (HEADER_PATTERN), list merging, size-based splitting. Diagram should show: document in → content type → skip? → table/list/default handling → heading-aware split → size-based split → chunks out.

**Rationale**: FR-006 requires the flowchart to reflect the implementation; content_aware_chunker is the single implementation.

**Alternatives considered**: High-level "chunking pipeline" without implementation detail was rejected (spec asks for "decision tree: heading detection, table handling, list merging, size-based splitting").

---

## 6. API comparison primary sources (FR-016)

**Decision**: Cite the following as primary sources in the comparison text:

- **MCP**: Model Context Protocol specification (Anthropic, 2024/2025) — official MCP docs/spec.
- **REST**: Fielding, R. T. (2000). *Architectural Styles and the Design of Network-based Software Architectures*. Doctoral dissertation, University of California, Irvine.
- **GraphQL**: GraphQL Foundation (2021). GraphQL Specification (current spec).
- **OData**: OASIS (2022). OData Version 4.01. Part 1: Protocol.

**Rationale**: FR-016 mandates citing official specifications for all four protocols.

**Alternatives considered**: Secondary sources only were rejected (spec requires primary).

---

## 7. Research notes before comparison text (FR-017)

**Decision**: Create research notes in `dev_prompts_instructions_notes/content/research_notes/ch02_shared/` before writing the API comparison. Notes cover: protocol summaries, comparison dimensions (paradigm, transport, statefulness, schema, discovery, streaming, AI-integration fit, batching/N+1), and citations. The comparison text in `content/chapters/ch02/` is then drafted from these notes.

**Rationale**: FR-017 requires research notes as source material for the thesis chapter.

**Alternatives considered**: Writing the comparison directly without notes was rejected (violates FR-017).
