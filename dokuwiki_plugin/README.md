# Dev Dito - DokuWiki Plugin

A DokuWiki PHP plugin (`devdito`) that provides an admin-facing service
gateway and pipeline manager: it monitors external services (MCP server,
Qdrant) and exposes AJAX/admin endpoints for triggering and checking on the
Wiki Embedding Pipeline (fetch, evaluate, embed, deploy) from inside the
DokuWiki admin UI. It does **not** provide a user-facing search UI — semantic
search is provided separately by the Leonidas extension.

This is the **integration surface**, not a dependency of the pipeline. The
core wiki→embedding pipeline in [`pipeline/`](../pipeline/) runs standalone
and does not import from this plugin; it talks to DokuWiki only through the
JSON-RPC API. See [docs/architecture.md](../docs/architecture.md) §4 for the
full boundary between the pipeline and this optional integration layer.

## Contents

| Path                 | Purpose                                            |
| -------------------- | --------------------------------------------------- |
| `action.php`          | Action plugin: AJAX endpoints and background health checks for the admin dashboard |
| `admin.php`           | Admin plugin: setup dashboard, service status, connection testing, configuration |
| `lib/`                | `ConfigLoader`, `JobStatusManager`, `PipelineOrchestrator`, `ServiceTester` |
| `conf/`               | Plugin configuration defaults and metadata (`default.php`, `metadata.php`) |
| `lang/`               | Localization strings (`en`, `de`)                  |
| `dist/`               | Built/minified admin dashboard assets (CSS/JS)     |
| `plugin.info.txt`     | DokuWiki plugin manifest (name, version, author)   |
