# Feature Specification: API Architecture Comparison & Thesis Diagrams

**Feature Branch**: `011-api-architecture-and-diagrams`
**Created**: 2026-02-17
**Status**: Draft
**Input**: Theoretical API/Architecture comparison (REST, OData, GraphQL, MCP), system architecture diagrams, Docker-Stack + npm-Client architecture, and evaluation visualizations for J4 (Chunk-Size) and J6 (Hybrid vs Dense).

## Context & Thesis Alignment

This branch delivers **written content and diagrams** for the diploma thesis. It spans multiple chapters:

| Thesis Reference | What                                                          | Chapter   |
|:-----------------|:--------------------------------------------------------------|:----------|
| **T6** (ABA)     | MCP vs REST/GraphQL/OData theoretical comparison              | Ch. 2     |
| **S1, S2**       | System architecture, component interactions, API contracts    | Ch. 4     |
| **J4**           | Chunk-size impact on retrieval quality (visualizations)       | Ch. 6     |
| **J6**           | Hybrid Search vs Dense Retrieval (visualizations)             | Ch. 6     |
| **J8**           | Docker-Stack + npm-Client deployment architecture             | Ch. 4 / 6 |
| Milestone        | "Theoretische Gegenuberstellung MCP vs REST/OData/GraphQL"    | ABA 15.10 |

---

## User Scenarios & Testing

### User Story 1 - API Protocol Comparison Text & Diagram (Priority: P1)

A thesis reader opens Chapter 2 and finds a clear, concise (~1.5-2 page) comparison of MCP against REST, OData, and GraphQL. The text explains *why* MCP exists as a distinct protocol for AI tool integration and where it differs architecturally. A feature-matrix diagram (`ch02_mcp_vs_rest_graphql`) provides a visual summary.

**Why this priority**: ABA milestone (15.10.2025) and professor requirement. T6 is mandatory theory content and must be completed for the written thesis. Without it, the thesis has a gap in the Theoriekapitel.

**Independent Test**: The comparison text can be read standalone in `docs/content/` or as a LaTeX-ready draft. The feature-matrix diagram renders as a PNG. A reviewer can verify completeness by checking that all four protocols are compared on at least: paradigm, transport, statefulness, schema/typing, tool discovery, streaming, and AI-integration fit.

**Acceptance Scenarios**:

1. **Given** the thesis theory chapter (Ch. 2), **When** a reader looks for the API comparison, **Then** they find a structured comparison of REST, OData, GraphQL, and MCP covering at least 7 comparison dimensions with a visual feature matrix.
2. **Given** the feature matrix diagram, **When** exported as PNG at 300 DPI, **Then** it uses thesis theme `00_thesis_default` colors and is legible at A4 print size.

---

### User Story 2 - System Architecture & Docker-Stack Diagram (Priority: P1)

A thesis reader opens Chapter 4 and finds the system architecture diagram showing Docker-Stack (left: Qdrant, RAGFlow/MCP-Server, Preprocessing) and npm-Client (right), both connecting to the central Qdrant vector database. The deployment diagram (`ch04_deployment`) and component diagram (`ch04_component_diagram`) are present.

**Why this priority**: S1 and S2 are shared chapter content (Kap. 4). J8 requires Docker + npm deployment documentation. The architecture diagram is the central figure for understanding the system.

**Independent Test**: The architecture diagram renders as a self-contained HTML page and converts to PNG. Labels show all Docker services, ports, volumes, and the npm client connection to Qdrant.

**Acceptance Scenarios**:

1. **Given** the system architecture content, **When** a reader views Chapter 4, **Then** they see a component diagram with Docker-Stack services (left), npm-Client (right), central Qdrant, and labeled interfaces/ports.
2. **Given** the Docker deployment diagram, **When** exported, **Then** it shows containers, networks, volumes, and external connections with thesis-theme styling.

---

### User Story 3 - Chunk-Size Evaluation Visualizations (Priority: P2)

A thesis reader opens Chapter 6 (J4) and finds three visualizations showing chunk-size impact on retrieval quality:
- Bar chart: MRR/NDCG by chunk-size x difficulty
- Flowchart: ContentAwareChunker decision logic
- Box plot: Real chunk-size distribution across the corpus

**Why this priority**: J4 is Jan's individual chapter content. The data already exists from completed evaluations (`eval_chunk_size.py`). These are the "Hauptdiagramm J4" per the thesis visualization plan.

**Independent Test**: Each visualization saves as a 300 DPI PNG. The bar chart loads data from `evaluation/results/` JSON files. The flowchart accurately reflects the ContentAwareChunker implementation. The box plot shows actual chunk-size distribution from the preprocessed corpus.

**Acceptance Scenarios**:

1. **Given** chunk-size evaluation results exist, **When** the notebook cell runs, **Then** a grouped bar chart of MRR and NDCG@10 by chunk-size (256, 512, 1024) and difficulty (easy, medium, hard) is saved.
2. **Given** the ContentAwareChunker implementation, **When** the flowchart is created, **Then** it shows the decision tree: heading detection, table handling, list merging, and size-based splitting.
3. **Given** the preprocessed corpus chunks, **When** the box plot is generated, **Then** it shows the actual token-count distribution per chunk-size setting.

---

### User Story 4 - Hybrid vs Dense Retrieval Visualizations (Priority: P2)

A thesis reader opens Chapter 6 (J6) and finds two visualizations comparing Dense vs Hybrid retrieval:
- Grouped bar chart: Dense vs Hybrid per metric (MRR, NDCG@10, Precision@5, Hit Rate)
- Scatter plot: Dense-Score vs Hybrid-Score per query (showing where Hybrid helps)

**Why this priority**: J6 is Jan's individual chapter content. The data exists from `eval_hybrid_vs_dense.py`. These are the "Hauptdiagramm J6" per the thesis visualization plan.

**Independent Test**: Each visualization saves as a 300 DPI PNG. The bar chart and scatter plot load from hybrid-vs-dense result JSON. The scatter plot has a diagonal line (y=x) so queries above the line show Hybrid advantage.

**Acceptance Scenarios**:

1. **Given** hybrid-vs-dense evaluation results exist, **When** the notebook cell runs, **Then** a grouped bar chart comparing Dense and Hybrid on at least 4 metrics is saved.
2. **Given** per-query scores for both strategies, **When** the scatter plot is generated, **Then** each query is a point with Dense-MRR on X and Hybrid-MRR on Y, with a y=x reference line and thesis-theme colors.

---

### User Story 5 - MCP Architecture & N x M Problem Diagrams (Priority: P3)

A thesis reader opens Chapter 2 and finds the N x M integration problem diagram (why MCP reduces N*M integrations to N+M) and the MCP architecture diagram (Host/Client/Server roles).

**Why this priority**: Supporting diagrams for T6 comparison. Valuable for context but lower priority than the comparison text itself.

**Independent Test**: Both diagrams render as HTML pages and convert to PNG at 300 DPI with thesis-theme colors.

**Acceptance Scenarios**:

1. **Given** the N x M problem diagram, **When** rendered, **Then** it shows N AI clients x M data sources with direct connections (left) vs N+M via MCP (right).
2. **Given** the MCP architecture diagram, **When** rendered, **Then** it shows Host, Client, Server roles with labeled protocol arrows (stdio, HTTP Streamable).

---

### Edge Cases

- What happens when evaluation result JSON files are missing? Visualizations should print a clear warning and skip gracefully.
- What happens when Docker service names change? Architecture diagrams should be parameterized or documented so they can be updated.
- How does the system handle incomplete hybrid-vs-dense data (e.g., only dense results exist)? The scatter plot should show only available data points with a note.

## Requirements

### Functional Requirements

- **FR-001**: The feature MUST produce a structured text comparing MCP, REST, OData, and GraphQL across at least 7 dimensions (paradigm, transport, statefulness, schema/typing, tool discovery, streaming support, AI-integration fit).
- **FR-002**: The feature MUST produce a feature-matrix diagram (`ch02_mcp_vs_rest_graphql`) as a thesis-quality PNG (300 DPI, thesis theme colors).
- **FR-003**: The feature MUST produce a system architecture diagram showing Docker-Stack services, npm-Client, and central Qdrant with labeled interfaces.
- **FR-004**: The feature MUST produce a Docker deployment diagram (`ch04_deployment`) showing containers, networks, volumes, and ports.
- **FR-005**: The feature MUST produce a grouped bar chart of MRR/NDCG by chunk-size and difficulty from existing evaluation results (J4).
- **FR-006**: The feature MUST produce a flowchart of the ContentAwareChunker decision logic (J4).
- **FR-007**: The feature MUST produce a box plot of real chunk-size distribution from the preprocessed corpus (J4).
- **FR-008**: The feature MUST produce a grouped bar chart comparing Dense vs Hybrid retrieval per metric (J6).
- **FR-009**: The feature MUST produce a scatter plot of Dense-Score vs Hybrid-Score per query with a y=x reference line (J6).
- **FR-010**: The feature MUST produce the N x M integration problem diagram (`ch02_mcp_nxm_problem`).
- **FR-011**: The feature MUST produce the MCP architecture diagram (`ch02_mcp_architecture`) showing Host/Client/Server roles.
- **FR-012**: All diagrams MUST use the thesis theme `00_thesis_default` (primary #2E4F8F, secondary #72ADCB, accent #F28D2C).
- **FR-013**: All visualizations from evaluation data MUST load from existing JSON result files in `evaluation/results/` and fail gracefully if files are missing.
- **FR-014**: All PNG outputs MUST be at 300 DPI and legible at A4 print size.

### Key Entities

- **API Comparison Text**: Structured prose comparing 4 protocols, stored as a draft markdown or LaTeX-ready file.
- **Diagram**: Self-contained HTML page following the `diagram_catalog.prompt.md` pipeline, converted to 300 DPI PNG.
- **Evaluation Visualization**: Matplotlib/Seaborn figure in the Jupyter notebook, saved as 300 DPI PNG to `evaluation/figures/`.
- **Architecture Diagram**: System-level diagram showing Docker services, npm client, Qdrant, and their connections.

## Success Criteria

### Measurable Outcomes

- **SC-001**: The API comparison text covers all 4 protocols (REST, OData, GraphQL, MCP) with at least 7 comparison dimensions and fits within ~1.5-2 thesis pages.
- **SC-002**: All 9 diagrams/visualizations listed in FR-002 through FR-011 are produced as 300 DPI PNGs and render correctly when included in a LaTeX document.
- **SC-003**: A thesis advisor reviewing Chapter 2 can understand the MCP value proposition and its architectural differences from REST/GraphQL/OData without prior MCP knowledge.
- **SC-004**: A thesis advisor reviewing Chapter 4 can identify all system components, their deployment topology, and their interfaces from the architecture diagrams alone.
- **SC-005**: A thesis advisor reviewing Chapter 6 (J4) can read the chunk-size impact from the bar chart and understand the ContentAwareChunker logic from the flowchart.
- **SC-006**: A thesis advisor reviewing Chapter 6 (J6) can determine whether Hybrid Search provides an advantage over Dense Retrieval from the two visualizations.
- **SC-007**: All figures follow the thesis color theme consistently -- no "default matplotlib blue" or mismatched palettes.

## Assumptions

- Chunk-size evaluation results are available in `evaluation/results/` (from `eval_chunk_size.py` runs on branch 009/010).
- Hybrid-vs-Dense evaluation results are available in `evaluation/results/` (from `eval_hybrid_vs_dense.py`).
- The thesis diagram pipeline (`html_projects/ -> png_output/`) from `diagram_catalog.prompt.md` is the standard for architecture diagrams.
- Evaluation visualizations (J4, J6 charts) go into the existing Jupyter notebook or a new one under `evaluation/notebooks/`.
- The API comparison text is a draft that will later be integrated into the LaTeX thesis document.

## Scope Boundaries

**In scope**:
- API comparison text (T6)
- System architecture diagrams (S1, S2, J8)
- Chunk-size visualizations (J4)
- Hybrid vs Dense visualizations (J6)
- MCP theory diagrams (T6 supporting)

**Out of scope**:
- Writing the full LaTeX chapter (that happens during thesis writing, not here)
- OAuth2/Scalekit diagrams (separate branch, J7)
- MCP Server implementation diagrams (Imre's chapter, Ch. 5)
- Running new evaluations -- this branch only visualizes existing results
