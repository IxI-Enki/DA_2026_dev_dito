# Diagram output contract

All thesis diagrams produced in this branch MUST satisfy the following so they can be included in the LaTeX thesis.

## Format

- **Primary deliverable**: PNG at **300 DPI** (FR-014).
- **Optional**: SVG for scaling (diagram pipeline may support it).

## Theme

- **Theme ID**: `00_thesis_default` (FR-012).
- **Colors**: primary `#2E4F8F`, secondary `#72ADCB`, accent `#F28D2C`. See [thesis_theme.yaml](./thesis_theme.yaml).
- **HTML diagrams**: Use CSS variables from theme (e.g. `var(--th-primary)`); no hardcoded color literals in diagram-specific CSS.
- **Matplotlib/Seaborn**: Use the same hex values in palette/cycle (see existing `embedding_model_comparison.ipynb`).

## Sizing

- **Print**: Legible at **A4** when included in the thesis (FR-014).
- **Export**: Diagram generator (Puppeteer) and Matplotlib `savefig(..., dpi=300)`.

## Diagram IDs (this branch)

| ID                       | Description                                              |
| ------------------------ | -------------------------------------------------------- |
| ch02_mcp_vs_rest_graphql | Feature matrix MCP vs REST/OData/GraphQL                 |
| ch02_mcp_nxm_problem     | N x M integration problem                                |
| ch02_mcp_architecture    | MCP Host/Client/Server roles                             |
| ch04_component_diagram   | System architecture (Docker-Stack, npm-Client, Qdrant)   |
| ch04_deployment          | Docker deployment (containers, networks, volumes, ports) |
| (pipeline flowchart)     | 5 pipeline stages, inputs/outputs (FR-015)               |

## Pipeline

- **Source**: Self-contained HTML in dev_prompts_instructions_notes at `assets/diagrams/sources/html_projects/<id>/index.html`.
- **Export**: Run diagram generator CLI (e.g. `node src/cli.js generate -d <id>`) → PNG in `assets/diagrams/exports/png_output/`.
