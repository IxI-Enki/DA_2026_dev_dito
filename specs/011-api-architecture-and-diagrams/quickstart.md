# Quickstart: API Architecture & Thesis Diagrams

**Branch**: `011-api-architecture-and-diagrams`

This branch uses **two repositories**:

- **dev_dito**: evaluation figures (J4, J6), notebooks, and result JSON paths.
- **dev_prompts_instructions_notes**: research notes, API comparison text, HTML diagram sources, PNG exports.

---

## 1. Repositories and paths

| Purpose                     | Repository                     | Path                                                                          |
| --------------------------- | ------------------------------ | ----------------------------------------------------------------------------- |
| Research notes (ch02, ch06) | dev_prompts_instructions_notes | `content/research_notes/ch02/`, `ch06_jan/` (existing)                         |
| API comparison draft        | dev_prompts_instructions_notes | `content/research_notes/ch02/` then `content/writing_drafts/`                  |
| Diagram HTML sources        | dev_prompts_instructions_notes | `assets/diagrams/sources/html_projects/`                                      |
| Diagram PNG output          | dev_prompts_instructions_notes | `assets/diagrams/exports/png_output/`                                         |
| Literature (citation check) | dev_prompts_instructions_notes | `content/literature/`                                                         |
| Evaluation result JSON      | dev_dito                       | `evaluation/results/` (read-only)                                             |
| Evaluation figures          | dev_dito                       | `evaluation/figures/`                                                         |
| Evaluation notebooks        | dev_dito                       | `evaluation/notebooks/`                                                       |

See [data-model.md](./data-model.md) and spec [Output Locations](spec.md#output-locations).

---

## 2. Diagram pipeline (HTML → PNG)

**Where**: `dev_prompts_instructions_notes`. Diagram catalog and theme: `.prompts/diagram_generator/diagram_catalog.prompt.md`, theme under `assets/diagrams/themes/` (e.g. `00_thesis_default`).

**Steps**:

1. Open dev_prompts_instructions_notes repo.
2. Create or edit HTML in `assets/diagrams/sources/html_projects/<diagram_id>/index.html`. Use `theme-loader.js`, `diagram-base.css`, and `var(--th-*)` for colors.
3. From diagram generator tool directory (e.g. under `assets/diagrams/` or `tools/diagram_generator/`):
   - `npm install` (once)
   - Export: `node src/cli.js generate` (all) or `node src/cli.js generate -d <diagram_id> -t 00_thesis_default`
4. PNGs appear in `assets/diagrams/exports/png_output/`. Ensure 300 DPI and thesis theme (see [contracts/diagram_output_contract.md](contracts/diagram_output_contract.md)).

**Diagram IDs for this branch**: `ch02_mcp_vs_rest_graphql`, `ch02_mcp_nxm_problem`, `ch02_mcp_architecture`, `ch04_component_diagram`, `ch04_deployment`, plus pipeline flowchart (FR-015).

---

## 3. Evaluation visualizations (J4, J6)

**Where**: dev_dito.

**Prerequisites**: Result JSON in `evaluation/results/`:

- J4: `chunk_comparison_*.json`
- J6: `hybrid_vs_dense_*.json`

**Steps**:

1. Open dev_dito repo.
2. Use existing or new notebook under `evaluation/notebooks/` (e.g. extend `embedding_model_comparison.ipynb` or add J4/J6-specific notebook).
3. Set theme: primary `#2E4F8F`, secondary `#72ADCB`, accent `#F28D2C`; DPI 300 (see [contracts/thesis_theme.yaml](contracts/thesis_theme.yaml)).
4. Load JSON from `evaluation/results/` (see [contracts/evaluation_result_contract.md](contracts/evaluation_result_contract.md)). If file missing, log warning and skip figure.
5. Save figures to `evaluation/figures/` (e.g. `savefig(..., dpi=300)`).

**J4**: Bar chart (MRR/NDCG by chunk_size); ContentAwareChunker flowchart (from `pipeline/04_embeddings_creator/content_aware_chunker.py`); box plot only if chunk-level token data available (see research.md).  
**J6**: Bar chart (Dense vs Hybrid per metric); scatter (Dense-MRR vs Hybrid-MRR per query, y=x line).

---

## 4. API comparison text (T6)

**Where**: dev_prompts_instructions_notes.

**Order** (FR-017):

1. Create research notes in `content/research_notes/ch02/`: protocol summaries, 8 comparison dimensions, primary source citations (FR-016). Use `content/literature/` and verify citations (source URL/page); double-check notes (not whitepapers) and web search where needed (see task T005b).
2. Draft comparison text in `content/research_notes/ch02/` from those notes (~1.5–2 pages); later move to `content/writing_drafts/`. Include reference to diagram `ch02_mcp_vs_rest_graphql`.

**Primary sources**: MCP spec (Anthropic), Fielding REST dissertation (2000), GraphQL spec (GraphQL Foundation), OData v4.01 (OASIS). See [research.md](research.md) section 6.

---

## 5. Theme and contracts

- **Theme**: [contracts/thesis_theme.yaml](contracts/thesis_theme.yaml) — use for all diagrams and figures.
- **Diagram output**: [contracts/diagram_output_contract.md](contracts/diagram_output_contract.md).
- **Evaluation JSON**: [contracts/evaluation_result_contract.md](contracts/evaluation_result_contract.md).

---

## 6. Checklist (high level)

- [ ] Research notes ch02 created; ch06_jan already exists and can be used for J4/J6 context.
- [ ] API comparison draft written and linked to feature-matrix diagram.
- [ ] All diagram IDs created as HTML and exported to 300 DPI PNG with thesis theme.
- [ ] J4 bar chart and (if data available) box plot; ContentAwareChunker flowchart.
- [ ] J6 bar chart and scatter plot.
- [ ] Pipeline flowchart (5 stages) produced.
- [ ] All figures/diagrams in correct repo paths per spec.
