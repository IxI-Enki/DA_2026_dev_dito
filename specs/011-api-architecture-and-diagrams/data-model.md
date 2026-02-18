# Data Model: API Architecture & Thesis Diagrams

**Branch**: `011-api-architecture-and-diagrams` | **Spec**: [spec.md](./spec.md)

This feature is content- and artifact-oriented; there is no database. The "data model" describes the main entities (artifacts), their locations, and relationships.

---

## Entities

### 1. Research note (ch02, ch06_jan)

| Field / concept   | Description                                                                                                |
| ----------------- | ---------------------------------------------------------------------------------------------------------- |
| **Location**      | `dev_prompts_instructions_notes/content/research_notes/ch02/` (T6), `ch06_jan/` (J4/J6, existing).         |
| **Format**        | Markdown.                                                                                                  |
| **Content**       | Protocol summaries, comparison dimensions, citations. Source for API comparison text (FR-017).             |
| **Relationships** | Feeds into API comparison draft; may reference diagram IDs.                                                |

---

### 2. API comparison text

| Field / concept   | Description                                                                                                              |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------ |
| **Location**      | `dev_prompts_instructions_notes/content/research_notes/ch02/` then `content/writing_drafts/`.                             |
| **Format**        | Markdown or LaTeX-ready draft.                                                                                           |
| **Content**       | Structured comparison of REST, OData, GraphQL, MCP over at least 8 dimensions (FR-001). ~1.5–2 thesis pages.             |
| **Relationships** | Built from research notes. References feature-matrix diagram `ch02_mcp_vs_rest_graphql`. Cites primary sources (FR-016). |

---

### 3. Diagram (HTML source + PNG export)

| Field / concept   | Description                                                                                                                                                             |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **ID**            | e.g. `ch02_mcp_vs_rest_graphql`, `ch04_deployment`, `ch04_component_diagram`, `ch02_mcp_nxm_problem`, `ch02_mcp_architecture`, pipeline flowchart (S1).                 |
| **HTML source**   | Self-contained HTML under `assets/diagrams/sources/html_projects/<id>/index.html`. Uses theme-loader and `var(--th-*)`. |
| **PNG export**    | 300 DPI, thesis theme, under `assets/diagrams/exports/png_output/<id>.png`.                                 |
| **Relationships** | Theme: `00_thesis_default`. Pipeline: HTML → Puppeteer/CLI → PNG.                                                                                                       |

**Validation**: All diagrams MUST use thesis theme `00_thesis_default` (FR-012) and 300 DPI (FR-014).

---

### 4. Evaluation visualization (J4, J6)

| Field / concept   | Description                                                                                                                                                                                                                         |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Input**         | JSON from `dev_dito/evaluation/results/`: `chunk_comparison_*.json`, `hybrid_vs_dense_*.json`.                                                                                                                                      |
| **Output**        | PNG in `dev_dito/evaluation/figures/`. 300 DPI, thesis theme.                                                                                                                                                                       |
| **Types**         | J4: bar chart (MRR/NDCG by chunk_size [and difficulty if available]), ContentAwareChunker flowchart, box plot (chunk-size distribution). J6: bar chart (Dense vs Hybrid per metric), scatter (Dense vs Hybrid per query, y=x line). |
| **Relationships** | Notebook or script in `dev_dito/evaluation/notebooks/` or `scripts/`; reads result JSON; writes figures. Missing JSON → warning, skip figure (FR-013).                                                                              |

**State**: No state machine. Artifacts are generated once (or on re-run); no transitions.

---

### 5. Pipeline flowchart (FR-015)

| Field / concept | Description                                                                                                                           |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| **Content**     | 5 stages: 01_wiki_fetcher, 02_deep_evaluation, 03_rag_preprocessing, 04_embeddings_creator, 05_deploy; inputs, outputs, data formats. |
| **Form**        | Diagram (HTML→PNG) in same pipeline as other architecture diagrams.                                                                   |
| **Location**    | Same as Diagram: `assets/diagrams/sources/html_projects/`, export to `assets/diagrams/exports/png_output/`. |

---

## Cross-repository mapping

| Entity type            | Repository                     | Path (spec)                                    |
| ---------------------- | ------------------------------ | ---------------------------------------------- |
| Research notes         | dev_prompts_instructions_notes | content/research_notes/ch02/, ch06_jan/ (existing) |
| API comparison text    | dev_prompts_instructions_notes | content/research_notes/ch02/ then content/writing_drafts/ |
| Diagram HTML/PNG       | dev_prompts_instructions_notes | assets/diagrams/sources/html_projects/, exports/png_output/ |
| Evaluation figures     | dev_dito                       | evaluation/figures/                            |
| Evaluation notebooks   | dev_dito                       | evaluation/notebooks/                          |
| Evaluation result JSON | dev_dito (read-only)           | evaluation/results/                            |

---

## Validation rules (from spec)

- Diagrams: theme `00_thesis_default`; 300 DPI; A4 legible (FR-012, FR-014).
- Visualizations: load from `evaluation/results/`; graceful handling of missing files (FR-013).
- API comparison: ≥8 dimensions; primary source citations (FR-001, FR-016).
- Research notes must exist before comparison text (FR-017).
