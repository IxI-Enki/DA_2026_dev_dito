# Tasks: API Architecture Comparison & Thesis Diagrams

**Input**: Design documents from `specs/011-api-architecture-and-diagrams/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md
**Checklists**: Existing checklists in `specs/011-api-architecture-and-diagrams/checklists/` (e.g. requirements.md)

**Organization**: Tasks are grouped by user story so each story can be implemented and tested independently. This branch uses two repositories: **dev_dito** (evaluation figures, notebooks) and **dev_prompts_instructions_notes** (research notes, diagrams, API comparison text).

**Tests**: Not requested in the spec (content branch; verification by visual inspection and quickstart).

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story (US1–US5) for traceability
- Paths: Repo-relative. dev_prompts_instructions_notes: `content/research_notes/ch02/`, `content/writing_drafts/`, `assets/diagrams/sources/html_projects/`, `assets/diagrams/exports/png_output/`. dev_dito: `evaluation/figures/`, `evaluation/notebooks/`.
- **Thesis-Deliverable-IDs** (constitution /tasks gate): T6 (Ch.2 API comparison), S1/S2/J8 (Ch.4 architecture), J4 (Ch.6 chunk-size), J6 (Ch.6 hybrid vs dense).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Ensure both repositories have required output paths and theme available.

- [ ] T001 Ensure output directories exist in dev_prompts_instructions_notes: `content/research_notes/ch02/`, `content/writing_drafts/`, `assets/diagrams/sources/html_projects/`, `assets/diagrams/exports/png_output/` (create if missing)
- [ ] T002 Ensure dev_dito has `evaluation/figures/` and `evaluation/notebooks/` (create if missing)
- [ ] T003 [P] Verify thesis theme `00_thesis_default` is available in dev_prompts_instructions_notes (e.g. `assets/diagrams/themes/` or theme_manifest) with primary #2E4F8F, secondary #72ADCB, accent #F28D2C per `specs/011-api-architecture-and-diagrams/contracts/thesis_theme.yaml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Prerequisites that MUST be done before user-story content work. FR-017 requires research notes before API comparison text.

- [ ] T004 Document or verify diagram generator in dev_prompts_instructions_notes: ensure diagram generator (e.g. under `assets/diagrams/` or `tools/diagram_generator/`) has `npm install` and generate command for 300 DPI PNG to `assets/diagrams/exports/png_output/` per quickstart and `contracts/diagram_output_contract.md`
- [ ] T005 Create research-notes structure in dev_prompts_instructions_notes at `content/research_notes/ch02/` (e.g. README or index) so T6 research notes have a clear target; FR-017 requires notes before comparison text
- [ ] T005b [P] Verify and cite sources for API comparison (T6): double-check research notes and content in `content/literature/` (do not re-verify whitepapers); use web search where needed so citations reference accurate source URL/page; ensure FR-016 primary sources are cited correctly

**Checkpoint**: Foundation ready; User Story 1 can start (research notes then comparison text then diagram). T005b (citation verification) can run in parallel with T005 or before T006/T007.

---

## Phase 3: User Story 1 – API Protocol Comparison Text & Diagram (Priority: P1) – MVP [T6]

**Goal**: Thesis reader finds in Ch. 2 a structured comparison of MCP vs REST, OData, GraphQL (~1.5–2 pages) and a feature-matrix diagram (`ch02_mcp_vs_rest_graphql`). **Deliverable: T6.**

**Independent Test**: Comparison text is readable in `content/research_notes/ch02/` or `content/writing_drafts/`; feature-matrix diagram exports as 300 DPI PNG with thesis theme; reviewer can confirm at least 8 comparison dimensions and all four protocols.

### Implementation for User Story 1

- [ ] T006 [US1] **T6** Create research notes in dev_prompts_instructions_notes at `content/research_notes/ch02/` covering 8 dimensions (paradigm, transport, statefulness, schema/typing, discovery, streaming, AI-integration fit, batching/N+1) and primary sources (MCP spec, Fielding REST, GraphQL spec, OData v4.01) per FR-001 and FR-016
- [ ] T007 [US1] **T6** Write API comparison draft in dev_prompts_instructions_notes at `content/research_notes/ch02/` (later move to `content/writing_drafts/`) (~1.5–2 pages, all 4 protocols, at least 8 dimensions, cite FR-016 sources, reference diagram `ch02_mcp_vs_rest_graphql`)
- [ ] T008 [P] [US1] **T6** Create feature-matrix diagram HTML `ch02_mcp_vs_rest_graphql` in dev_prompts_instructions_notes at `assets/diagrams/sources/html_projects/ch02_mcp_vs_rest_graphql/index.html` using theme-loader and `var(--th-*)` for thesis theme
- [ ] T009 [US1] **T6** Export `ch02_mcp_vs_rest_graphql` to 300 DPI PNG in dev_prompts_instructions_notes at `assets/diagrams/exports/png_output/` per `contracts/diagram_output_contract.md`

**Checkpoint**: User Story 1 complete; Ch. 2 comparison and feature-matrix diagram are deliverable.

---

## Phase 4: User Story 2 – System Architecture & Docker-Stack Diagram (Priority: P1) [S1, S2, J8]

**Goal**: Thesis reader finds in Ch. 4 the system architecture (Docker-Stack, npm-Client, Qdrant) and Docker deployment diagram with containers, networks, volumes, ports. **Deliverables: S1, S2, J8.**

**Independent Test**: Both diagrams render as HTML and export to 300 DPI PNG with thesis theme; labels show services, ports, and interfaces.

### Implementation for User Story 2

- [ ] T010 [P] [US2] **S1, J8** Create component diagram HTML `ch04_component_diagram` in dev_prompts_instructions_notes at `assets/diagrams/sources/html_projects/ch04_component_diagram/index.html` (Docker-Stack left, npm-Client right, central Qdrant, labeled interfaces/ports)
- [ ] T011 [P] [US2] **S2, J8** Create deployment diagram HTML `ch04_deployment` in dev_prompts_instructions_notes at `assets/diagrams/sources/html_projects/ch04_deployment/index.html` (containers, networks, volumes, ports)
- [ ] T012 [US2] **S1, S2, J8** Export `ch04_component_diagram` and `ch04_deployment` to 300 DPI PNG in dev_prompts_instructions_notes at `assets/diagrams/exports/png_output/` per `contracts/diagram_output_contract.md`

**Checkpoint**: User Story 2 complete; Ch. 4 architecture and deployment diagrams are deliverable.

---

## Phase 5: User Story 3 – Chunk-Size Evaluation Visualizations (Priority: P2) [J4]

**Goal**: Thesis reader finds in Ch. 6 (J4) three visualizations: bar chart (MRR/NDCG by chunk-size and difficulty), ContentAwareChunker flowchart, box plot of chunk-size distribution. **Deliverable: J4.** Note: Research notes for J4/J6 already exist in dev_prompts_instructions_notes at `content/research_notes/ch06_jan/`; use as needed.

**Independent Test**: Each visualization saves as 300 DPI PNG to `evaluation/figures/`; bar chart loads from `evaluation/results/chunk_comparison_*.json`; flowchart reflects `pipeline/04_embeddings_creator/content_aware_chunker.py`; box plot uses chunk-level data if available (else document limitation per research.md).

### Implementation for User Story 3

- [ ] T013 [US3] **J4** Add or create J4 visualization notebook in dev_dito at `evaluation/notebooks/` that loads from `evaluation/results/` and writes to `evaluation/figures/` with thesis theme (contracts/thesis_theme.yaml) and 300 DPI; implement graceful warning if chunk_comparison_*.json missing per FR-013
- [ ] T014 [US3] **J4** Implement grouped bar chart of MRR and NDCG@10 by chunk-size (256, 512, 1024) and by difficulty if present in chunk_comparison_*.json in dev_dito; save to `evaluation/figures/` per `contracts/evaluation_result_contract.md`
- [ ] T015 [US3] **J4** Create ContentAwareChunker flowchart (heading detection, table handling, list merging, size-based splitting) per dev_dito `pipeline/04_embeddings_creator/content_aware_chunker.py` and save as 300 DPI PNG to dev_dito `evaluation/figures/` (FR-006)
- [ ] T016 [US3] **J4** Implement box plot of chunk-size distribution in dev_dito: use preprocessed corpus or chunk-level data if available and save to `evaluation/figures/`; otherwise document limitation in notebook per `specs/011-api-architecture-and-diagrams/research.md` (FR-007)

**Checkpoint**: User Story 3 complete; J4 bar chart, flowchart, and (if data available) box plot in `evaluation/figures/`.

---

## Phase 6: User Story 4 – Hybrid vs Dense Retrieval Visualizations (Priority: P2) [J6]

**Goal**: Thesis reader finds in Ch. 6 (J6) grouped bar chart (Dense vs Hybrid per metric) and scatter plot (Dense-MRR vs Hybrid-MRR per query with y=x line). **Deliverable: J6.**

**Independent Test**: Both figures save as 300 DPI PNG; data from `evaluation/results/hybrid_vs_dense_*.json`; scatter has y=x reference line; graceful handling if file or per_query missing (FR-013).

### Implementation for User Story 4

- [ ] T017 [US4] **J6** Implement grouped bar chart Dense vs Hybrid (MRR, NDCG@10, Precision@5, Hit Rate) from hybrid_vs_dense_*.json in dev_dito at `evaluation/notebooks/` (or existing notebook); save to dev_dito `evaluation/figures/`; thesis theme, 300 DPI; graceful warning if file missing (FR-008)
- [ ] T018 [US4] **J6** Implement scatter plot Dense-MRR (X) vs Hybrid-MRR (Y) per query with y=x reference line from hybrid_vs_dense_*.json in dev_dito; save to `evaluation/figures/`; thesis theme; show only available data with note if per_query missing per `contracts/evaluation_result_contract.md` (FR-009)

**Checkpoint**: User Story 4 complete; J6 bar chart and scatter in `evaluation/figures/`.

---

## Phase 7: User Story 5 – MCP Architecture & N x M Problem Diagrams (Priority: P3) [T6]

**Goal**: Thesis reader finds in Ch. 2 the N x M integration diagram and the MCP architecture diagram (Host/Client/Server, stdio, HTTP Streamable). **Deliverable: T6 (supporting).**

**Independent Test**: Both diagrams render as HTML and export to 300 DPI PNG with thesis theme.

### Implementation for User Story 5

- [ ] T019 [P] [US5] **T6** Create N x M problem diagram HTML `ch02_mcp_nxm_problem` in dev_prompts_instructions_notes at `assets/diagrams/sources/html_projects/ch02_mcp_nxm_problem/index.html` (N clients x M sources direct vs N+M via MCP) (FR-010)
- [ ] T020 [P] [US5] **T6** Create MCP architecture diagram HTML `ch02_mcp_architecture` in dev_prompts_instructions_notes at `assets/diagrams/sources/html_projects/ch02_mcp_architecture/index.html` (Host, Client, Server; stdio, HTTP Streamable) (FR-011)
- [ ] T021 [US5] **T6** Export `ch02_mcp_nxm_problem` and `ch02_mcp_architecture` to 300 DPI PNG in dev_prompts_instructions_notes at `assets/diagrams/exports/png_output/`

**Checkpoint**: User Story 5 complete; N x M and MCP architecture diagrams deliverable.

---

## Phase 8: Polish & Cross-Cutting Concerns [S1]

**Purpose**: Pipeline flowchart (FR-015), theme/DPI verification, quickstart validation, and checklist alignment.

- [ ] T022 **S1** Create pipeline flowchart diagram (5 stages: 01_wiki_fetcher, 02_deep_evaluation, 03_rag_preprocessing, 04_embeddings_creator, 05_deploy) with inputs, outputs, and data formats in dev_prompts_instructions_notes at `assets/diagrams/sources/html_projects/`; export to 300 DPI PNG at `assets/diagrams/exports/png_output/` (FR-015)
- [ ] T023 [P] Verify all diagrams and evaluation figures use thesis theme `00_thesis_default` and 300 DPI per `specs/011-api-architecture-and-diagrams/contracts/diagram_output_contract.md` and `contracts/thesis_theme.yaml`
- [ ] T024 Run quickstart validation: confirm paths and steps in `specs/011-api-architecture-and-diagrams/quickstart.md` for diagram pipeline and evaluation visualizations; fix or document any path mismatches
- [ ] T025 [P] Update or add implementation checklist in `specs/011-api-architecture-and-diagrams/checklists/` to reflect completed tasks (e.g. link to tasks.md or add done criteria per user story)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies; start immediately.
- **Phase 2 (Foundational)**: Depends on Phase 1; T005 (research-notes structure) blocks US1 comparison text (FR-017).
- **Phase 3 (US1)**: Depends on Phase 2; T005b (citation verification) before or alongside T006/T007; T006 (research notes) before T007 (comparison text); T008 (HTML) can parallel T006/T007; T009 after T008.
- **Phase 4 (US2)**: Depends on Phase 2; T010 and T011 can run in parallel; T012 after both.
- **Phase 5 (US3)**: Depends on Phase 1 (paths); no dependency on US1/US2; T013–T016 in order within story.
- **Phase 6 (US4)**: Depends on Phase 1; independent of US1–US3; T017 and T018 can run in parallel after notebook exists.
- **Phase 7 (US5)**: Depends on Phase 2 (diagram export); T019 and T020 parallel; T021 after both.
- **Phase 8 (Polish)**: Depends on completion of all user stories that produce diagrams/figures.

### User Story Dependencies

- **US1 (P1)**: After Foundational; no dependency on US2–US5.
- **US2 (P1)**: After Foundational; no dependency on US1, US3–US5.
- **US3 (P2)**: After Setup; independent of US1, US2, US4, US5.
- **US4 (P2)**: After Setup; independent of US1–US3, US5.
- **US5 (P3)**: After Foundational; independent of US1–US4.

### Parallel Opportunities

- Phase 1: T003 [P] can run with T001/T002.
- Phase 3: T008 [P] can run once research direction is set (can overlap with T006/T007).
- Phase 4: T010 [P], T011 [P] in parallel; then T012.
- Phase 5: T014, T015, T016 are sequential (notebook first, then charts).
- Phase 6: T017 and T018 can run in parallel after notebook/cell structure exists.
- Phase 7: T019 [P], T020 [P] in parallel; then T021.
- Phase 8: T023 [P], T025 [P] in parallel; T022, T024 sequential as needed.
- **Cross-story**: After Phase 2, US1, US2, US3, US4, US5 can be staffed in parallel (different repos/files).

---

## Parallel Example: User Story 1

```text
# After T005 (research-notes structure), T005b (verify citations):
T006: Create research notes in dev_prompts_instructions_notes content/research_notes/ch02/
T007: Write API comparison draft in dev_prompts_instructions_notes content/research_notes/ch02/ (later content/writing_drafts/)
T008 [P]: Create ch02_mcp_vs_rest_graphql HTML in assets/diagrams/sources/html_projects/ch02_mcp_vs_rest_graphql/
# Then:
T009: Export ch02_mcp_vs_rest_graphql to assets/diagrams/exports/png_output/
```

---

## Parallel Example: User Story 2

```text
T010 [P]: Create ch04_component_diagram HTML
T011 [P]: Create ch04_deployment HTML
# Then:
T012: Export both to PNG
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003).
2. Complete Phase 2: Foundational (T004–T005).
3. Complete Phase 3: User Story 1 (T006–T009).
4. **STOP and VALIDATE**: Comparison text readable; feature-matrix diagram exports at 300 DPI with thesis theme; 7+ dimensions and 4 protocols covered.
5. Proceed to US2 or deploy Ch. 2 content.

### Incremental Delivery

1. Setup + Foundational → research-notes structure and diagram pipeline ready.
2. US1 → Ch. 2 comparison + feature-matrix (MVP for ABA/theory).
3. US2 → Ch. 4 architecture and deployment.
4. US3 → J4 visualizations; US4 → J6 visualizations (can run in parallel).
5. US5 → MCP N x M and architecture diagrams.
6. Polish → Pipeline flowchart, theme/DPI check, quickstart validation.

### Parallel Team Strategy

- After Phase 2: One person on US1 (research notes + text + diagram), another on US2 (both Ch. 4 diagrams), another on US3/US4 (notebooks in dev_dito). US5 can start once diagram export is familiar.
- Repo split: dev_prompts_instructions_notes (US1, US2, US5, pipeline flowchart) vs dev_dito (US3, US4 only).

---

## Notes

- [P] = different files or artifacts, no write dependencies.
- [USn] maps task to spec user story for traceability.
- Each user story is independently testable (see Independent Test per phase).
- No automated test tasks (spec does not request tests; verification by visual inspection and quickstart).
- Existing checklists: `specs/011-api-architecture-and-diagrams/checklists/requirements.md` (spec quality); T025 can add or link implementation checklist.
