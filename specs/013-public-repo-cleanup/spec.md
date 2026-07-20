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
7. **`config/sources.yaml`:** **remove entirely** (`git rm`). It is a dead ~150-line manifest of absolute paths into a private repo, read by no code, and it exposes internal naming. Discoverable via history, absent from the published tree.
8. **Name/internal-structure scrub (`leonie` / `internal_leonidas` / `SYP_2025_26`):** this token — a real first name plus internal course/repo structure — appears in ~5 tracked files including portfolio-visible `docs/architecture.md` and `backend_services/.env.template`. **Exception to decision 3:** scrub *this specific token* to a neutral placeholder in **all** tracked files (docs, `.prompts/`, `.env.template`, `docs/.archive/`). The harmless `dev_dito` path stays in historical files as decided.
9. **`root_dir` sanitization:** the pipeline loaders read `root_dir` directly. Add a small loader fallback so a missing/placeholder `root_dir` resolves to `Path(__file__).parent` — the repo then runs out-of-the-box after cloning. Covered by a test.

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

### B — Sanitize active configs & remove dead manifest
- `git rm config/sources.yaml` (decision 7) — dead, exposes internal naming.
- **Loader fallback (decision 9):** in `pipeline/03_rag_preprocessing/config.py` and `pipeline/04_embeddings_creator/config.py`, when `PATHS.root_dir` is absent or equals the placeholder, resolve it to `Path(__file__).parent`. Covered by a unit test each.
- In `pipeline/03_rag_preprocessing/env.yaml`, `pipeline/04_embeddings_creator/env.yaml`, `config/env.development.yaml`, `config/env.minimal.yaml`, `config/PLACEHOLDER_env.yaml`: replace the absolute `root_dir` value with a neutral placeholder the loader now tolerates.
- Replace LAN IP `192.168.8.3` in `pipeline/03_rag_preprocessing/env.yaml:129` with `localhost`.
- **Name scrub (decision 8):** replace the literal `D:/_Repositories/year_2025_26/SYP_2025_26/leonie/internal_leonidas` (and its backslash variant) with a neutral placeholder in **all** tracked files.
- Leave the harmless `dev_dito` absolute path in `specs/`/`docs/` historical files untouched.
- **Verify:** `git grep -iE 'leonie|internal_leonidas|SYP_2025|192\.168\.' -- ':!specs/013*'` returns nothing; both pipeline test suites still pass.

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

- [x] Zero **un-intended** real emails and zero `D:/` paths / `192.168.*` in **active configs**. *(Intentional & decided: author's official contact `janritt.office@gmail.com`, the plugin org address `dev@htl-leonding.ac.at`, and synthetic test fixtures remain; harmless machine paths — `D:/…/dev_dito` and `D:/…/research/…` — stay in historical `docs/`/`specs/` per decision 3; the LAN IP `192.168.8.3` was scrubbed from active configs **and** active code defaults (`evaluation/config.py`, `evaluation/scripts/eval_pipeline.py`, `pipeline/03_rag_preprocessing/run_preprocessing.py`) → `localhost`; remaining `192.168.*` occurrences are only in historical `specs/008`/`009` and a `192.168.x.x` doc placeholder.)*
- [x] Full git history contains zero secret files (`gitleaks git .` exits clean — 165 commits, 0 leaks, re-run 2026-07-20 after final changes).
- [x] `.pre-commit-config.yaml` present and `pre-commit run --all-files` passes (gitleaks + email guard).
- [x] Every published sample artifact passed the redaction script and manual review (PII-free, verified).
- [x] `.claude/ .cursor/ .specify/ .github/ .prompts/ specs/` visible and coherent. *(Ignore/track contradiction fixed; `config/secrets/.gitkeep`+`README.md` published. `.cursor/` vetted: `agents/skills/rules/settings.json` committed as portfolio artifacts; `plans/` (private thesis-repo refs, collaborator names, professor feedback) and `hooks/` (runtime state) excluded via scoped ignore.)*
- [x] README communicates the portfolio story; `PRIVACY.md` explains data handling.
- [ ] Repo can be flipped to public with the author confident no secret or personal datum is exposed. *(Tracked surface is clean and gated; pending the author's final visibility flip + the `.cursor/` decision above.)*

---

## 6. Risks & Mitigations

| Risk | Mitigation |
| :--- | :--- |
| A sample slips through with an un-redacted name | Redaction script **plus** manual review **plus** the §E gate scan — three independent checks. |
| Rewriting active configs breaks path resolution | Keep `${var}` semantics; smoke-test that each edited env.yaml still resolves. |
| Over-cleaning erases authentic process history | Explicit decision to leave `specs/`/`docs/` untouched. |
| Future fetched data re-introduces PII | `data/` stays gitignored by default; only redacted samples are ever whitelisted. |

---

## 7. Known follow-ups (post whole-branch review, non-blocking)

These do not expose any secret or third-party PII (the tracked surface is verified clean) — they are hardening/decision items for the author before/after the visibility flip:

1. ~~`.cursor/` untracked artifacts~~ **RESOLVED:** vetted and `agents/skills/rules/settings.json` committed (gitleaks-clean, no PII/paths); `plans/` + `hooks/` excluded via scoped ignore.
2. **`--check` email guard skips all `.md`** (`scripts/redact_sample.py`) — the pre-commit PII guard currently excludes Markdown, so a real email later pasted into a doc/spec would not be caught by *this* hook (gitleaks still catches structured secrets; it does not catch plain PII emails). Tightening requires migrating two synthetic literals in historical `.md` (`foo@bar.at` in `specs/008`, `a@b.co` in `specs/013`) to `example.*` domains first.
3. **Stage 03 has no sample** — `data/preprocessed/samples/` is intentionally absent (no clean preprocessed source at cleanup time); README wording was corrected to name only the stages that do ship a sample.
