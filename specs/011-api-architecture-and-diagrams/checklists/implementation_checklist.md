# Implementation Checklist: API Architecture & Thesis Diagrams

**Purpose**: Track completion of implementation tasks per user story.  
**Task list**: [tasks.md](../tasks.md) (authoritative).

## Verification

- [x] All diagrams use thesis theme `00_thesis_default` (primary #2E4F8F, secondary #72ADCB, accent #F28D2C) per [contracts/thesis_theme.yaml](../contracts/thesis_theme.yaml)
- [x] Diagram PNG exports at 300 DPI per [contracts/diagram_output_contract.md](../contracts/diagram_output_contract.md)
- [x] Evaluation figures (J4, J6) saved at 300 DPI to dev_dito `evaluation/figures/`

## User story completion (done criteria)

- [x] **US1 (T6)**: API comparison text in ch02; feature-matrix diagram `ch02_mcp_vs_rest_graphql` exported
- [x] **US2 (S1, S2, J8)**: Component + deployment diagrams `ch04_component_diagram`, `ch04_deployment` exported
- [x] **US3 (J4)**: J4 notebook; bar chart, ContentAwareChunker flowchart; box-plot limitation documented
- [x] **US4 (J6)**: J6 bar chart and scatter from `hybrid_vs_dense_*.json` in `evaluation/figures/`
- [x] **US5 (T6)**: NxM diagram `ch02_mcp_nxm_problem`, MCP architecture `ch02_mcp_architecture` exported
- [x] **Polish**: Pipeline flowchart `pipeline_flowchart` exported; quickstart paths validated

## Notes

- Diagram sources: dev_prompts_instructions_notes `assets/diagrams/sources/html_projects/<id>/index.html`
- PNG output: dev_prompts_instructions_notes `assets/diagrams/exports/png_output/`
- Export command: `node src/cli.js generate -d <id> -t 00_thesis_default` from `tools/diagram_generator`
