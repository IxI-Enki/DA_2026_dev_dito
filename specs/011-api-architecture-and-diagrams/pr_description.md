## Summary

This PR implements the **011 API Architecture & Thesis Diagrams** feature: spec-driven content and diagrams for the diploma thesis. It adds API protocol comparison (MCP vs REST/OData/GraphQL), system/deployment architecture diagrams, evaluation visualizations for J4 (chunk-size) and J6 (hybrid vs dense), data-model documentation, and deploy-pipeline updates for Qdrant/transfer. Remote master has been merged in.

## Spec Reference

- **Spec Directory**: `specs/011-api-architecture-and-diagrams/`
- **GitHub Issue**: Relates to #

<!-- Use "Closes #N" only when the feature is fully complete and human-reviewed -->

## Changes

- Spec kit: `spec.md`, `plan.md`, `tasks.md`, `data-model.md`, `quickstart.md`, contracts and checklists under `specs/011-api-architecture-and-diagrams/`
- Data model documentation updates in `specs/011-api-architecture-and-diagrams/data-model.md`
- Deploy pipeline: updates to `pipeline/05_deploy/config.yaml`, `deploy_config.py`, `deploy_qdrant.py`, `transfer_to_pi.py`, `verify_transfer.py`; new `run_deploy.py`
- Merge of `origin/master` into this branch so it includes latest master changes
- Lint/format: ruff (I001, F401) and black applied to deploy and evaluation scripts
- README.md: pipeline tree and refs updated to 04_embeddings_creator, 05_deploy, run_deploy.py

## Checklist

### Spec Kit Compliance

- [x] `spec.md` exists for this feature branch
- [x] `plan.md` exists (or N/A for bug fixes)
- [x] `tasks.md` exists (or N/A for bug fixes)

### Code Quality (Constitution Articles III, IV)

- [ ] Tests added or updated
- [x] All tests pass (`pytest tests/`)
- [x] Python linting passes (`ruff check .` + `black --check .`)
- [x] PHP follows PSR-12 (if applicable) — N/A

### Security (Constitution Article VI)

- [x] No secrets in diff (API keys, tokens, passwords)
- [x] No hardcoded URLs or paths (use config/env.yaml)
- [x] Secret files referenced via `*_file` pattern, not inline values (SSH_KEY_PATH env, config.yaml)

### Documentation

- [x] Code has docstrings/PHPDoc for public functions
- [x] README updated: complete rewrite — pipeline stages 01-05 and evaluation framework documented

## Test Results

```powershell
pytest tests/ -v --tb=short
```
42 passed, 1 skipped. Black and ruff run and pass after formatting the 5 touched files.

## Screenshots / Evidence

<!-- If applicable, add screenshots or terminal output -->
