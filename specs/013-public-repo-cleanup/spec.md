# Spec 013 — Public Repository Cleanup & Portfolio Release

**Status:** Draft (design approved in brainstorming, pending spec review)
**Author:** Jan Ritt (IxI-Enki)
**Created:** 2026-07-20
**Goal:** Make `dev_dito` safe and presentable to publish as a public portfolio repository — showing the full engineering process (RAG pipeline, SDD, agentic orchestration, evaluation) while exposing no secrets and no personal data.

---

## 1. Context & Motivation

`dev_dito` is a 5-stage RAG pipeline + evaluation framework built for a diploma thesis (Stack-G).
It will be linked from the author's portfolio. Two forces are in tension:

- **Show the work** — the pipeline code, the 12 numbered feature specs, the Claude/Cursor/Spec-Kit orchestration, and the evaluation framework are the portfolio value and should be fully visible.
- **Expose nothing sensitive** — real API tokens / SSL cert must never leak, and the fetched DokuWiki content (HTL Leonding) contains real personal data.

### Baseline audit findings (2026-07-20)

| Area | Finding | Status |
| :--- | :--- | :--- |
| Secret files (`*.token`, `ssl.cert`) | In `config/secrets/`, correctly gitignored, **never committed** — verified manually **and** by `gitleaks` (153 commits, 0 leaks, 2026-07-20) | 🟢 Safe |
| Hardcoded keys in code | None — all secrets read from token files (Constitution Art. VI) | 🟢 Safe |
| Currently tracked surface | Clean — only placeholder emails (`VORNAME.NACHNAME@…`) | 🟢 Safe |
| Fetched wiki data (`data/`) | Fully gitignored, **not** in repo. Contains **74 distinct real email addresses** (teachers, external contacts, student lists) + namespaces like `exams`, `archive_org_positiver-covid-test` | 🔴 PII if published |
| Absolute local paths | `D:/_Repositories/.../dev_dito` in ~15 tracked files (active configs + historical specs/docs) | 🟡 Unprofessional |
| Internal LAN IP | `192.168.8.3` (LMStudio endpoint) in 2 tracked `env.yaml` | 🟡 Minor leak |
| `.cursor/` | Listed in `.gitignore` yet 9 files tracked — contradictory intent | 🟡 Inconsistent |
| AI-tooling dirs | `.claude/ .cursor/ .specify/ .github/ .prompts/ specs/` — portfolio assets, keep | 🟢 Keep |

**Conclusion:** the secret posture is already sound. The real work is (a) keeping the process artifacts visible, (b) admitting only vetted, anonymized data samples, and (c) cosmetic cleanup of active configs.

---

## 2. Decisions (from brainstorming)

1. **Data strategy:** curated samples. `data/` stays gitignored; add small vetted sample artifacts per stage.
2. **Privacy:** clean samples **plus** an automated redaction pass (emails/names → placeholders). Double safety.
3. **Path cleanup:** active configs only. Rewrite absolute paths + LAN IP in `pipeline/*/env.yaml` and `config/*`. Leave `specs/` and `docs/` as an untouched historical record.
4. **License:** none for now (all rights reserved); may add later.
5. **Sample location:** samples live **inside `data/`** (mirroring the pipeline's own output layout, e.g. `data/fetched/samples/…`, `data/embeddings/samples/…`), whitelisted via targeted `.gitignore` negations — not a separate top-level `samples/` tree.
6. **Tooling:** `gitleaks` as the local pre-publication gate (installed 2026-07-20, v8.30.1); a `.pre-commit-config.yaml` wiring gitleaks + an email/PII regex hook for ongoing prevention. Work happens on branch `013-public-repo-cleanup`.

---

## 3. Scope

### In scope
- Cosmetic cleanup of **active** config files (paths, LAN IP).
- A reusable redaction/scrubbing script for producing anonymized samples.
- Curated, redacted sample artifacts (1–2 per pipeline stage).
- `.gitignore` correction (`.cursor/` contradiction) + targeted sample whitelists.
- README portfolio framing + a `PRIVACY.md` explaining data handling.
- Final pre-publication security/PII gate.

### Out of scope
- Rewriting historical `specs/` and `docs/` content.
- Any change to `config/secrets/` handling (already correct).
- Adding a license (deferred by decision).
- Publishing full fetched datasets or embeddings.

---

## 4. Workstreams

### A — Keep portfolio assets visible
- Confirm `.claude/ .cursor/ .specify/ .github/ .prompts/ specs/ docs/` remain tracked.
- Remove the contradictory `.cursor/` line from `.gitignore` (files are intentionally tracked).
- **Verify:** `git ls-files` still lists all these dirs; `.gitignore` no longer ignores tracked-and-intended paths.

### B — Sanitize active configs
- Files: `pipeline/03_rag_preprocessing/env.yaml`, `pipeline/04_embeddings_creator/env.yaml`, `config/*.yaml` (those containing `D:/`).
- Replace absolute `D:/_Repositories/.../dev_dito` with `${root_dir}` / relative paths consistent with existing `${var}` resolution.
- Replace LAN IP `192.168.8.3` with `localhost` or a `${VISION_LLM_HOST}` placeholder.
- **Do not touch** `specs/` and `docs/` occurrences.
- **Verify:** `git grep 'D:/_Repositories' -- pipeline config` returns nothing; the two env.yaml still parse and resolve paths.

### C — Redaction script + curated samples
- Build a small, documented script (e.g. `scripts/redact_sample.py`) that, given a fetched artifact, replaces:
  - email addresses → `REDACTED_EMAIL` (or `firstname.lastname@example.org` style)
  - obvious personal-name patterns where feasible
  - keeps institutional/structural content intact.
- Select samples (institutional/procedural content, e.g. Matura rules, IT how-tos):
  - Stage 01: 1 fetched page + 1 media metadata record
  - Stage 03: 1 preprocessed Markdown page (with frontmatter)
  - Stage 04: a short `embedded_chunks.jsonl` excerpt
  - Stage 02/eval: 1 `ANALYSIS_REPORT_*.md` + one summary JSON
- Place under a `samples/` subfolder **inside the matching `data/` stage dir** (e.g. `data/fetched/samples/`, `data/preprocessed/samples/`, `data/embeddings/samples/`, `data/evaluated/samples/`), mirroring the real pipeline output layout.
- Add targeted `.gitignore` negations for exactly these sample files (e.g. `!data/*/samples/`, `!data/*/samples/**`) while `data/*` stays ignored.
- **Verify:** every sample passes the PII scan (§E); `git ls-files samples` shows only intended files.

### D — Public-repo polish
- README: add a concise "What this demonstrates" section (RAG pipeline · Spec-Driven Development · agentic orchestration · evaluation) and one line noting data is provided only as anonymized samples.
- Add `PRIVACY.md` (or a README section) describing: source data contained PII; it is excluded; samples are redacted; secrets live outside the repo.
- Add `.pre-commit-config.yaml` wiring a `gitleaks` hook + a lightweight email/PII regex hook, so future commits are guarded automatically.
- **Verify:** README renders; links resolve; claims match reality; `pre-commit run --all-files` passes.

### E — Final pre-publication gate (must pass before making public)
- History secret rescan via `gitleaks git .` → **PASSED 2026-07-20** (153 commits, 0 leaks). Re-run after all changes land.
- Tracked-surface PII scan: `git grep -IE '<email-regex>'` returns only placeholders.
- No `D:/` and no `192.168.` in tracked active configs.
- `config/secrets/` in the tracked set contains only `.gitkeep` + `README.md`.
- **Verify:** all four checks green (gitleaks re-run after final changes), recorded in this spec's checklist before flipping visibility.

---

## 5. Success Criteria

- [ ] `git grep` finds zero real email addresses, zero `D:/` paths, zero `192.168.*` in the tracked, published surface.
- [ ] Full git history contains zero secret files (`gitleaks git .` exits clean).
- [ ] `.pre-commit-config.yaml` present and `pre-commit run --all-files` passes.
- [ ] Every published sample artifact has passed the redaction script and a manual review.
- [ ] `.claude/ .cursor/ .specify/ .github/ .prompts/ specs/` are visible and coherent (no ignore/track contradictions).
- [ ] README communicates the portfolio story; `PRIVACY.md` explains data handling.
- [ ] Repo can be flipped to public with the author confident no secret or personal datum is exposed.

---

## 6. Risks & Mitigations

| Risk | Mitigation |
| :--- | :--- |
| A sample slips through with an un-redacted name | Redaction script **plus** manual review **plus** the §E gate scan — three independent checks. |
| Rewriting active configs breaks path resolution | Keep `${var}` semantics; smoke-test that each edited env.yaml still resolves. |
| Over-cleaning erases authentic process history | Explicit decision to leave `specs/`/`docs/` untouched. |
| Future fetched data re-introduces PII | `data/` stays gitignored by default; only redacted samples are ever whitelisted. |
