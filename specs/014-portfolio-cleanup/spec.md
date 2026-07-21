# Spec 014 — Portfolio Cleanup

**Status:** Approved (design + plan executed on branch `014-portfolio-cleanup`)
**Author:** Jan Ritt (IxI-Enki)
**Created:** 2026-07-21
**Goal:** Bring `dev_dito` to a portfolio-ready state — remove development cruft, produce one canonical architecture document that foregrounds the per-stage quality gates, make the pipeline the visible centerpiece, and unify code-comment language — **without fragmenting the codebase further.**

> The detailed design and the full task-by-task implementation plan live under the Superpowers workflow:
> - Design: [`docs/superpowers/specs/2026-07-21-portfolio-cleanup-design.md`](../../docs/superpowers/specs/2026-07-21-portfolio-cleanup-design.md)
> - Plan: [`docs/superpowers/plans/2026-07-21-portfolio-cleanup.md`](../../docs/superpowers/plans/2026-07-21-portfolio-cleanup.md)
>
> This file exists to satisfy the Spec-Kit convention (`specs/<NNN>-*/spec.md`) required by the constitution and the CI `validate-spec` gate for numbered feature branches.

---

## 1. Context & Motivation

`dev_dito` is a 5-stage RAG pipeline + evaluation framework built for a diploma thesis. Ahead of the public portfolio release (follow-on to Spec 013), the repository still carried scattered loose ends: development prompt dumps (`.prompts/`), RAG-eval agent/skill artifacts and working plans under `.cursor/`, five mutually inconsistent architecture-era documents, mixed German/English code comments, and — critically — a per-stage quality-evaluation story that was real in code but documented nowhere coherently.

**Anti-fragmentation principle:** one written spec decides the destination for every loose end once; execution happens in bounded phases on one branch; nothing is deleted that is not recoverable.

## 2. User Story

**As** the author presenting this repository as a portfolio piece,
**I want** the codebase free of development cruft, with one accurate architecture document and consistent code-comment language,
**so that** a reviewer sees a clean, self-explanatory system whose per-stage quality engineering is obvious rather than buried.

**Acceptance criteria (Given/When/Then):**
- **Given** the public tree, **when** inspected, **then** it contains no tracked dev cruft (`.prompts/`, `.cursor/agents|skills|plans`, `tstex_modules/`, stale architecture docs); removed content is preserved locally in a gitignored `_archive/` plus the `archive/pre-portfolio` tag.
- **Given** `docs/`, **when** read, **then** exactly one current `docs/architecture.md` exists that (a) presents the 5-stage pipeline as the centerpiece, (b) names the quality gate of each stage, (c) separates the per-stage gates (Layer 1) from the final RAG evaluation (Layer 2).
- **Given** the pipeline Python code, **when** linted and read, **then** comments and docstrings are English, while user-facing output strings and LLM prompts are preserved.
- **Given** CI, **when** it runs, **then** `ruff`, `black`, and the test suites pass.

## 3. Affected Layers

- **Pipeline** (`pipeline/`): comment-language pass (Stage 2), removal of debug instrumentation (Stage 4). No behavior change.
- **Docs / Governance**: new `docs/architecture.md`; archived stale docs; constitution reference fix.
- **Not touched (code):** `backend_services/`, `dokuwiki_plugin/` — READMEs only (they are the separable integration/deployment layer).

## 4. Scope Boundaries (out of scope)

No new evaluation features, no merge of the two evaluation layers, no git-history rewrite, no changes to `backend_services`/`dokuwiki_plugin` code.

## 5. Thesis Alignment

Post-thesis / portfolio-hardening. Supports the public-release milestone (continues Spec 013).
