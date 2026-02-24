# Implementation Plan: API Architecture Comparison & Thesis Diagrams

**Branch**: `011-api-architecture-and-diagrams` | **Date**: 2026-02-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/011-api-architecture-and-diagrams/spec.md`

**Note**: This plan is produced by the `/speckit.plan` workflow. This branch requires both repositories: `dev_dito` (evaluation figures, notebooks) and `dev_prompts_instructions_notes` (research notes, diagrams, API comparison text).

## Summary

Deliver thesis content and diagrams for the diploma thesis: (1) structured API comparison text (MCP vs REST, OData, GraphQL) with feature-matrix diagram (T6, Ch. 2); (2) system architecture and Docker deployment diagrams (S1, S2, J8, Ch. 4); (3) chunk-size evaluation visualizations (J4) and hybrid vs dense visualizations (J6) in Chapter 6; (4) MCP NxM and architecture diagrams (T6 supporting). All diagrams use thesis theme `00_thesis_default` and 300 DPI PNG. Research notes are created in `dev_prompts_instructions_notes` before the comparison text; evaluation visualizations load from existing JSON in `dev_dito/evaluation/results/` and write figures to `dev_dito/evaluation/figures/`.

## Technical Context

**Language/Version**: Python 3.11+ (evaluation notebooks, visualization scripts), JavaScript/Node (diagram generator in dev_prompts_instructions_notes), Markdown/HTML (content).  
**Primary Dependencies**: Matplotlib, Seaborn (dev_dito); diagram pipeline per `diagram_catalog.prompt.md` and theme-loader (dev_prompts_instructions_notes); Puppeteer for HTML→PNG.  
**Storage**: File-based. No database. Outputs: Markdown/LaTeX drafts, HTML diagram sources, PNG exports, JSON result files (read-only for this branch).  
**Testing**: Notebook cell execution and visual inspection; diagram render/export verification. No new unit tests required (content branch).  
**Target Platform**: Windows 11 (author environment); diagrams must render at 300 DPI and A4 print size.  
**Project Type**: Content/thesis (two repositories: dev_dito for code-generated figures; dev_prompts_instructions_notes for text and HTML diagrams).  
**Performance Goals**: N/A (batch generation of figures and text).  
**Constraints**: 300 DPI PNG, thesis theme `00_thesis_default` (primary #2E4F8F, secondary #72ADCB, accent #F28D2C); graceful handling of missing evaluation JSON.  
**Scale/Scope**: 9 diagrams/visualizations, 1 comparison text (~1.5–2 pages), research notes in ch02_shared and ch06_jan.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Article I (Layered Module Architecture)**: No violation. This branch produces content and diagrams; no PHP/Python/Docker layer calls.
- [x] **Article VII (Integration Simplicity)**: No new abstractions. Uses existing diagram pipeline and evaluation notebooks.
- [x] **Article VIII (Direct Framework Usage)**: Matplotlib/Seaborn and diagram generator used as-is.
- [x] **Betroffene Docker-Services**: None. No new services; no changes to `docker-compose.yml`.
- [x] **Article VI (Secrets)**: No new secrets or config.
- [x] **Article XII (Resource Limits)**: N/A (no new services).
- [x] **Article XIV (Inter-Stack)**: N/A.
- [x] **Thesis-Zuordnung**: Spec lists T6, S1, S2, J4, J6, J8; all deliverables referenced.

**Verdict**: Gate passed.

## Project Structure

### Documentation (this feature)

```text
specs/011-api-architecture-and-diagrams/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (thesis theme, diagram/result schemas)
└── tasks.md             # Phase 2 output (/speckit.tasks - not created by /speckit.plan)
```

### Source and content layout (two repositories)

**dev_dito** (evaluation figures and notebooks only):

```text
evaluation/
├── results/                    # Input: existing JSON (chunk_comparison_*.json, hybrid_vs_dense_*.json)
├── figures/                    # Output: 300 DPI PNG (J4 bar, flowchart, box; J6 bar, scatter)
├── notebooks/                  # J4/J6 visualization notebooks (existing or new)
└── scripts/                    # eval_chunk_size.py, eval_hybrid_vs_dense.py (existing)
```

**dev_prompts_instructions_notes** (content and HTML diagrams):

```text
content/
├── research_notes/
│   ├── ch02/                   # T6 research notes and API comparison draft (before move to writing_drafts)
│   └── ch06_jan/               # J4/J6 research notes (existing)
├── writing_drafts/             # API comparison draft (final) after ch02
└── literature/                 # Literature and notes for citation verification

assets/diagrams/
├── sources/html_projects/      # HTML sources (ch02_*, ch04_*, pipeline flowchart)
├── exports/png_output/         # Exported PNG (thesis theme, 300 DPI)
└── themes/                     # e.g. 00_thesis_default
```

**Structure Decision**: Dual-repo content feature. No new application code in dev_dito beyond notebook cells and optional small visualization helpers. Diagram authoring and export follow `diagram_catalog.prompt.md` and theme system in dev_prompts_instructions_notes.

## Complexity Tracking

No constitution violations requiring justification. Table left empty.
