# Plan 014 — Portfolio Cleanup

**Spec:** [`spec.md`](spec.md)
**Branch:** `014-portfolio-cleanup`
**Constitution gates:** no layer-separation violation (Article I); no new secrets without placeholders (Article VI); Docker-affecting services documented in `docs/architecture.md` (Article V).

> The authoritative, task-by-task implementation plan (with exact commands, verification steps, and per-task commits) lives at
> [`docs/superpowers/plans/2026-07-21-portfolio-cleanup.md`](../../docs/superpowers/plans/2026-07-21-portfolio-cleanup.md).
> This file is the Spec-Kit-convention summary required by the CI `validate-spec` gate.

## Phases (executed, one commit per task)

| Phase | Deliverable | Result |
| :---- | :---------- | :----- |
| 0 · Safety net | `archive/pre-portfolio` tag; `_archive/` + `tstex_modules/` gitignored | reversible baseline |
| 1 · Structural cruft | `.prompts/`, `.cursor/agents|skills|plans` → local `_archive/` | root clean; `.cursor` keeps Spec-Kit commands/rules/settings/hooks |
| 2 · Docs | verify per-stage eval gates → new canonical `docs/architecture.md`; archive 5 stale docs | per-stage story foregrounded |
| 3 · Subsystem boundary | pipeline-centric README + `backend_services`/`dokuwiki_plugin` boundary READMEs | pipeline as centerpiece |
| 4 · Code language | German comments/docstrings → English in `02_deep_evaluation`; output/prompts preserved | consistent EN code |
| 5 · Linter/CI (opt.) | drop dead `UP038` ignore; remove hardcoded-path debug instrumentation; CI green | stricter, cleaner |
| 6 · Verification | `ruff`/`black`/`pytest` green; whole-branch review | READY-TO-MERGE |

## Testing / Verification

- `ruff check .` and `black --check .` pass.
- Per-suite `pytest` (unit, smoke, and each `pipeline/<stage>/tests`) passes.
- Public tree carries no tracked cruft; exactly one architecture doc dated 2026-07-21; no hardcoded personal paths in the pipeline.

## What does NOT change

Existing pipeline behavior (comment/docstring text only; the one code change is removal of dead debug instrumentation). `backend_services`/`dokuwiki_plugin` code untouched.
