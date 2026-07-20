# Portfolio-Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the `dev_dito` repo to a portfolio-ready state — remove dev cruft, produce one canonical architecture doc that foregrounds the per-stage quality gates, make the pipeline the visible centerpiece, and unify code-comment language — without fragmenting the codebase further.

**Architecture:** One branch (`014-portfolio-cleanup`, already checked out), one commit per task. Removed cruft is physically moved into a **gitignored** `_archive/` (local-only safety net) plus a `archive/pre-portfolio` git tag; the public `master` stays clean, nothing is lost. Work is disposal + honest narrative — **no feature work** (see spec §6).

**Tech Stack:** git, Python 3.11 (pipeline), ruff + black + pytest (existing CI gates), PowerShell/Git-Bash on Windows.

**Spec:** `docs/superpowers/specs/2026-07-21-portfolio-cleanup-design.md`

## Global Constraints

- Branch: **`014-portfolio-cleanup`** (already created). One commit per task.
- `_archive/` is **gitignored** — moving a tracked file there = untrack (staged deletion) + physical file preserved locally. Never `git add` anything under `_archive/`.
- **Keep** under `.cursor/`: `commands/`, `rules/`, `settings.json`, `hooks/`. **Archive** only `.cursor/agents/` + `.cursor/skills/` (tracked) and `.cursor/plans/` (local-only, untracked).
- Language policy (Phase/Task 9): comments + docstrings → **English**; user-facing CLI/report output strings and LLM prompts **stay as-is** (may be German); remove meta/dev comments. Decide per-string.
- Do **not** modify `backend_services/` or `dokuwiki_plugin/` code — only their READMEs.
- No git-history rewrite. No new eval features. No merging of the two eval layers.
- Every task ends green: `git status` clean of unintended changes; where code changed, `ruff check` + `black --check` + relevant `pytest` pass.
- Commit trailer: `Co-Authored-By: Ona <no-reply@ona.com>`.

---

### Task 1: Safety net (tag + gitignore)

**Files:**
- Modify: `.gitignore`
- Git tag: `archive/pre-portfolio`

**Interfaces:**
- Produces: gitignored `_archive/` path + `tstex_modules/` fully ignored; recovery tag on pre-cleanup HEAD.

- [ ] **Step 1: Tag the current pre-cleanup state**

Run:
```bash
git tag archive/pre-portfolio
git tag --list 'archive/*'
```
Expected: prints `archive/pre-portfolio`.

- [ ] **Step 2: Add `_archive/` and full `tstex_modules/` to `.gitignore`**

Append to `.gitignore` (the existing file already ignores `tstex_modules/_api.ts` at line 209; this generalises it):
```gitignore

# =============================================================================
# Portfolio-cleanup (014): local-only archive + stray generated modules
# =============================================================================
_archive/
tstex_modules/
```

- [ ] **Step 3: Verify the ignore rules work**

Run:
```bash
mkdir -p _archive && echo test > _archive/probe.txt
git check-ignore _archive/probe.txt tstex_modules/_api.ts
rm _archive/probe.txt
```
Expected: both paths are printed (meaning both are ignored).

- [ ] **Step 4: Commit**

```bash
git add .gitignore
git commit -m "chore(014): gitignore _archive/ + tstex_modules/; add pre-portfolio tag

Co-Authored-By: Ona <no-reply@ona.com>"
```

---

### Task 2: Archive `.prompts/` and remove `tstex_modules/`

**Files:**
- Move (untrack): `.prompts/` → `_archive/prompts/` (2 tracked + 1 untracked file)
- Delete (local, untracked): `tstex_modules/`

**Interfaces:**
- Consumes: gitignored `_archive/` from Task 1.
- Produces: repo root free of `.prompts/` and `tstex_modules/`.

- [ ] **Step 1: Move `.prompts/` into the local archive**

Run:
```bash
mkdir -p _archive/prompts
mv .prompts/* _archive/prompts/
rmdir .prompts
```

- [ ] **Step 2: Remove the stray `tstex_modules/` (untracked, already ignored)**

Run:
```bash
rm -rf tstex_modules
```

- [ ] **Step 3: Verify git sees only the two tracked deletions and nothing new added**

Run:
```bash
git status --porcelain
```
Expected: two `D .prompts/Next_Prompt_Feat_006.improved.md` / `D .prompts/Prompt.md` deletion lines only. **No** `_archive/` entries (it is ignored). No `tstex_modules` line (was untracked).

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore(014): archive .prompts dev dumps; drop stray tstex_modules

Moved to local gitignored _archive/prompts/. tstex_modules was an
untracked generated stray; now fully ignored.

Co-Authored-By: Ona <no-reply@ona.com>"
```

- [ ] **Step 5: Confirm recoverability**

Run:
```bash
ls _archive/prompts/
```
Expected: the 3 original prompt files are present locally.

---

### Task 3: Archive `.cursor/` dev-cruft (keep Spec-Kit essentials)

**Files:**
- Move (untrack): `.cursor/agents/`, `.cursor/skills/` → `_archive/cursor/`
- Move (local-only, untracked): `.cursor/plans/` → `_archive/cursor/plans/`
- **Keep untouched:** `.cursor/commands/`, `.cursor/rules/`, `.cursor/settings.json`, `.cursor/hooks/`

**Interfaces:**
- Consumes: gitignored `_archive/` from Task 1.
- Produces: `.cursor/` reduced to intentional Spec-Kit artifacts only. Closes the open ".cursor decision" from feature 013.

- [ ] **Step 1: Move the tracked RAG-eval cruft + untracked plans**

Run:
```bash
mkdir -p _archive/cursor
mv .cursor/agents _archive/cursor/agents
mv .cursor/skills _archive/cursor/skills
mv .cursor/plans  _archive/cursor/plans
```

- [ ] **Step 2: Verify the keep-list is still tracked and intact**

Run:
```bash
git ls-files .cursor/ | sed 's#/[^/]*$##' | sort -u
```
Expected: only `.cursor`, `.cursor/commands`, `.cursor/rules` remain (agents/ and skills/ gone). `settings.json` (under `.cursor`) still listed.

- [ ] **Step 3: Verify no `_archive/` content got staged**

Run:
```bash
git status --porcelain | grep -c '_archive' || echo 0
```
Expected: `0`.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore(014): archive .cursor RAG-eval agents/skills + local plans

Keep only intentional Spec-Kit artifacts (commands/, rules/,
settings.json, hooks/). Resolves the open .cursor decision (013).

Co-Authored-By: Ona <no-reply@ona.com>"
```

---

### Task 4: Verify the per-stage evaluation gates (read-only findings)

**Files:**
- Read: `pipeline/02_deep_evaluation/evaluator.py`, `pipeline/02_deep_evaluation/report_generator.py`
- Read: `pipeline/03_rag_preprocessing/evaluation/metrics.py`, `pipeline/03_rag_preprocessing/evaluation/report.py`
- Read: `pipeline/05_deploy/verify_transfer.py`
- Create: `_archive/verification-notes.md` (local scratch, gitignored — findings feed Task 5)

**Interfaces:**
- Produces: an honest one-paragraph-per-stage verdict (working gate? partial? placeholder?) that Task 5's `architecture.md` cites truthfully. This is the "document + verify" decision — **read only, build nothing.**

- [ ] **Step 1: Read each per-stage eval implementation**

Read the five files above. For each of the five pipeline stages (fetch, deep-eval, preprocess-eval, embeddings, deploy-verify), determine: what does its quality gate actually check, does it run end-to-end, and is anything a stub?

- [ ] **Step 2: Record findings**

Write `_archive/verification-notes.md` with one short paragraph per stage:
```markdown
# Per-stage eval verification (2026-07-21)
## Stage 1 fetch — <gate? evidence: file:line>
## Stage 2 deep_evaluation — <what evaluator.py + report_generator.py actually produce>
## Stage 3 preprocessing eval — <what evaluation/metrics.py checks; junk/consistency? file:line>
## Stage 4 embeddings — <chunking strategy source; any quality check?>
## Stage 5 deploy verify — <verify_transfer.py: checksum? what exactly>
```

- [ ] **Step 3: Surface honest gaps to the user before writing the canonical doc**

If any stage's "gate" turns out to be a stub or missing, state it plainly to the user (do not paper over it in the architecture doc). No commit — this task produces local notes only.

---

### Task 5: Write the canonical `docs/architecture.md`

**Files:**
- Overwrite: `docs/architecture.md` (currently the stale legacy-repo doc)

**Interfaces:**
- Consumes: verification findings from Task 4 (`_archive/verification-notes.md`); the verified two-layer map from spec §3.3.
- Produces: the single current architecture reference.

- [ ] **Step 1: Write the new architecture doc**

Replace the entire contents of `docs/architecture.md`. Required sections (content grounded in the verified spec §3.3 map and Task 4 findings — no invented behavior):
1. **Overview** — the repo is a wiki→embedding→RAG pipeline; pipeline is the centerpiece; plugin + backend_services are a separable integration/deployment layer (pipeline runs standalone; only a cosmetic `dokuwiki` URL string couples them, `pipeline/03_rag_preprocessing/page_processor.py:270`).
2. **The 5-stage pipeline** — one subsection per stage (`01_wiki_fetcher` … `05_deploy`) naming real files.
3. **Two evaluation layers** (the key section that "goes under" elsewhere):
   - *Layer 1 — per-stage quality gates* (in-pipeline): stage 2 deep eval, stage 3 `evaluation/`, stage 5 `verify_transfer` — with the honest per-stage verdict from Task 4.
   - *Layer 2 — final RAG evaluation* (top-level `evaluation/`): retrieval metrics, ground_truth QA, `ragas/`, statistics, visualization.
   - A short paragraph on the seam between them.
4. **RAGAS decision** — state the current position honestly: RAGAS was dropped for the final eval (`EVALUATION_WITHOUT_RAGAS.md`), and note the present `evaluation/ragas/` dir and what it actually is (per Task 4 if relevant).
5. **Supersedes** — a note that this doc replaces the earlier `architecture.md` (legacy), `README_ARCHITECTURE.md`, `gap_analysis_prototypes_vs_pipeline.md`, and `dev_dito_pipeline_manager.md`, which are archived.
6. **Header** — `> **Stand:** 2026-07-21` and version.

- [ ] **Step 2: Verify internal links resolve**

Run:
```bash
grep -oE '\]\(([^)]+)\)' docs/architecture.md | sed 's/](//;s/)//' | grep -vE '^https?://' | while read p; do [ -e "$p" ] || [ -e "docs/$p" ] || echo "BROKEN: $p"; done
```
Expected: no `BROKEN:` lines.

- [ ] **Step 3: Commit**

```bash
git add docs/architecture.md
git commit -m "docs(014): rewrite architecture.md as the single current reference

Foregrounds the per-stage quality gates (layer 1) vs final RAG eval
(layer 2). Supersedes four stale architecture-era docs.

Co-Authored-By: Ona <no-reply@ona.com>"
```

---

### Task 6: Archive the stale docs + dedupe test_report

**Files:**
- Move (untrack): `docs/README_ARCHITECTURE.md`, `docs/gap_analysis_prototypes_vs_pipeline.md`, `docs/dev_dito_pipeline_manager.md`, `docs/EVALUATION_WITHOUT_RAGAS.md`, `docs/.archive/` → `_archive/docs/`
- Move (untrack): `docs/test_report.pdf` → `_archive/docs/` (keep `docs/test_report.md`)
- Create: `_archive/docs/WHY-ARCHIVED.md` (local note)

**Interfaces:**
- Consumes: canonical `docs/architecture.md` from Task 5 (the replacement).
- Produces: `docs/` containing only current, non-contradictory files.

- [ ] **Step 1: Confirm the canonical doc exists before removing the old ones**

Run:
```bash
test -f docs/architecture.md && head -3 docs/architecture.md
```
Expected: shows the new `Stand: 2026-07-21` header (NOT the old `2026-01-24`).

- [ ] **Step 2: Move stale docs into the local archive**

Run:
```bash
mkdir -p _archive/docs
mv docs/README_ARCHITECTURE.md docs/gap_analysis_prototypes_vs_pipeline.md docs/dev_dito_pipeline_manager.md docs/EVALUATION_WITHOUT_RAGAS.md _archive/docs/
mv docs/.archive _archive/docs/dot-archive
mv docs/test_report.pdf _archive/docs/
```

- [ ] **Step 3: Leave a local note on why each was archived**

Write `_archive/docs/WHY-ARCHIVED.md` with one line per file (superseded by `docs/architecture.md` / stale epoch / duplicate of `test_report.md`).

- [ ] **Step 4: Verify remaining docs are the intended keep-set**

Run:
```bash
find docs -maxdepth 1 -type f | sort
```
Expected: `architecture.md`, `dev_dito_icon.png`, `dev_dito_pipeline_manager.md` **gone**, `sources_dev_dito.yaml`, `test_report.md`. (No `README_ARCHITECTURE.md`, no `gap_analysis…`, no `EVALUATION_WITHOUT_RAGAS.md`, no `test_report.pdf`.)

- [ ] **Step 5: Verify no repo file still links to an archived doc**

Run:
```bash
grep -rEl 'README_ARCHITECTURE|gap_analysis_prototypes_vs_pipeline|dev_dito_pipeline_manager|EVALUATION_WITHOUT_RAGAS|test_report\.pdf' --include='*.md' . | grep -v '_archive/'
```
Expected: no output (fix any file that still references them — e.g. top `README.md`).

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "docs(014): archive four stale architecture-era docs + test_report.pdf dupe

docs/ now holds only current, non-contradictory files. Originals kept
locally in gitignored _archive/docs/.

Co-Authored-By: Ona <no-reply@ona.com>"
```

---

### Task 7: Pipeline-centric top README + subsystem boundary READMEs

**Files:**
- Modify: `README.md` (make pipeline the headline; demote plugin + backend to a one-line pointer each)
- Modify/Create: `backend_services/README.md` (exists — add boundary framing)
- Create or Modify: `dokuwiki_plugin/README.md` (add boundary framing)

**Interfaces:**
- Consumes: canonical `docs/architecture.md` (link target).
- Produces: "Pipeline im Zentrum" visible in the entry docs.

- [ ] **Step 1: Read the current top README and backend README**

Read `README.md` and `backend_services/README.md` to match existing tone/structure before editing.

- [ ] **Step 2: Edit top `README.md`**

Ensure the pipeline is the lead narrative and links to `docs/architecture.md`. Add a short "Related subsystems" section with one line each:
- `dokuwiki_plugin/` — the DokuWiki PHP plugin (integration surface); the pipeline runs without it.
- `backend_services/` — the Dockerized deployment layer; the pipeline runs standalone.

- [ ] **Step 3: Add boundary framing to each subsystem README**

At the top of `backend_services/README.md` and `dokuwiki_plugin/README.md`, add a one-paragraph note: this is the integration/deployment layer; the core wiki→embedding pipeline in `pipeline/` is independent and does not import from here (evidence: no `backend_services` imports; only a cosmetic `dokuwiki` URL string).

- [ ] **Step 4: Verify links resolve**

Run:
```bash
grep -oE '\]\(([^)]+)\)' README.md | sed 's/](//;s/)//' | grep -vE '^https?://|^#' | while read p; do [ -e "$p" ] || echo "BROKEN: $p"; done
```
Expected: no `BROKEN:` lines.

- [ ] **Step 5: Commit**

```bash
git add README.md backend_services/README.md dokuwiki_plugin/README.md
git commit -m "docs(014): pipeline-centric README + subsystem boundary notes

Co-Authored-By: Ona <no-reply@ona.com>"
```

---

### Task 8: Code language pass — comments/docstrings → English

**Files:**
- Modify: `pipeline/**/*.py` (focus `pipeline/02_deep_evaluation/`, which is the most German)
- Run: `simplify` skill on the changed files afterward

**Interfaces:**
- Produces: English comments + docstrings across the pipeline; user-facing output strings and LLM prompts preserved.

- [ ] **Step 1: Inventory the German comment/docstring surface**

Run:
```bash
grep -rnE "#.*(ä|ö|ü|ß|und |oder |nicht |wenn |wird |für |müssen|sollen|Datei|Verzeichnis|Beispiel|gemäß|später|tatsächlich)" pipeline --include=*.py | wc -l
grep -rlE "#.*(ä|ö|ü|ß| für | wird | nicht )" pipeline --include=*.py | sort
```
Expected: a line count and the file list to work through (02_deep_evaluation dominates).

- [ ] **Step 2: Translate comments + docstrings to English, module by module**

For each file, translate `#` comments and `"""docstrings"""` to English. **Do NOT touch:**
- string literals printed to the user (CLI messages, `report_generator.py` German section titles like `"### Dateitypen"`, `"## Empfehlungen für RAG-Preprocessing"`) — these are user-facing output and stay.
- LLM prompt strings.
Also **remove** meta/dev comments (references to sprints, prompts, "TODO from feature 00X", dated developer notes).

Work in small commits per stage-dir so review stays reviewable (e.g. one commit for `02_deep_evaluation/`, one for `03_rag_preprocessing/`, etc.).

- [ ] **Step 3: Verify no unintended change to executable strings**

Run:
```bash
python -m pytest pipeline -q 2>&1 | tail -20
```
Expected: same pass/fail baseline as before the task (translation must not change behavior). If a stage has no tests, at minimum `python -c "import ast,sys; [ast.parse(open(f,encoding='utf-8').read()) for f in sys.argv[1:]]" <changed .py files>` parses clean.

- [ ] **Step 4: Run the linters/formatter on changed files**

Run:
```bash
ruff check pipeline
black --check pipeline
```
Expected: no new violations (fix any introduced).

- [ ] **Step 5: Run the `simplify` skill on the changed files**

Invoke the `simplify` skill scoped to the changed pipeline files (quality-only pass — reuse, clarity, consistency; not bug hunting). Apply its fixes.

- [ ] **Step 6: Re-verify tests + lint after simplify, then confirm remaining German is intentional**

Run:
```bash
python -m pytest pipeline -q 2>&1 | tail -5
grep -rnE "#.*( für | wird | nicht | oder | Datei )" pipeline --include=*.py
```
Expected: tests green; the remaining grep hits (if any) are only inside preserved user-facing strings / prompts, not comments — eyeball to confirm.

- [ ] **Step 7: Commit (if not already committed per-stage in Step 2)**

```bash
git add pipeline
git commit -m "refactor(014): English comments/docstrings across pipeline; drop dev meta-comments

User-facing output strings and LLM prompts left intact per language policy.

Co-Authored-By: Ona <no-reply@ona.com>"
```

---

### Task 9: (Optional) Tighten linter/CI

**Files:**
- Modify: `pyproject.toml` (`[tool.ruff.lint] ignore`, `[tool.ruff] exclude`)
- Optionally modify: `.github/workflows/ci.yml` (gitleaks `continue-on-error`)

**Interfaces:**
- Produces: stricter quality signals. **Skip entirely if the user does not want it** (spec: optional, last).

- [ ] **Step 1: Confirm with the user that Phase 5 is in scope now**

Only proceed if the user opts in. Otherwise mark this task skipped and go to Task 10.

- [ ] **Step 2: Remove cheap `ignore` entries and re-lint**

Remove ruff `ignore` rules that no longer trigger (e.g. cosmetic `W291`/`W293` if the code is now clean). After each removal:
```bash
ruff check .
```
Expected: passes. Revert any rule whose removal produces noise not worth fixing now.

- [ ] **Step 3: (Optional) Make gitleaks blocking**

In `.github/workflows/ci.yml`, remove `continue-on-error: true` from the `secret-scan` job only after confirming a clean local scan.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml .github/workflows/ci.yml
git commit -m "chore(014): tighten ruff ignores + gitleaks gating

Co-Authored-By: Ona <no-reply@ona.com>"
```

---

### Task 10: Final verification

**Files:** none (verification only)

**Interfaces:**
- Consumes: all prior tasks.
- Produces: evidence the repo is clean and green.

- [ ] **Step 1: Lint + format check**

Run:
```bash
ruff check .
black --check .
```
Expected: both pass.

- [ ] **Step 2: Tests**

Run:
```bash
python -m pytest tests/unit tests/smoke -q 2>&1 | tail -15
python -m pytest pipeline -q 2>&1 | tail -15
```
Expected: same green baseline as pre-cleanup (no regressions from the language pass).

- [ ] **Step 3: Confirm the public tree is cruft-free and `_archive/` is not tracked**

Run:
```bash
git ls-files | grep -E '^\.prompts/|^\.cursor/(agents|skills|plans)/|^tstex_modules/|^_archive/|README_ARCHITECTURE|gap_analysis_prototypes|dev_dito_pipeline_manager|EVALUATION_WITHOUT_RAGAS' || echo "CLEAN"
```
Expected: `CLEAN`.

- [ ] **Step 4: Confirm exactly one architecture doc, dated today**

Run:
```bash
head -3 docs/architecture.md
git ls-files docs/ | grep -iE 'architect'
```
Expected: `Stand: 2026-07-21`; only `docs/architecture.md` matches.

- [ ] **Step 5: Report the per-stage verification verdict to the user**

Summarize the Task 4 findings (which stages have a real quality gate, which are partial) and confirm the architecture doc reflects them honestly. This closes the "document + verify" commitment.

- [ ] **Step 6: Offer next steps**

Cleanup branch is green. Offer: (a) open a PR `014-portfolio-cleanup → master`, or (b) use `superpowers:finishing-a-development-branch`. Do not push/PR without the user's go.

---

## Self-Review

**Spec coverage** (spec §5 phases → tasks):
- Phase 0 → Task 1 ✅ · Phase 1 → Tasks 2–3 ✅ · Phase 2 → Tasks 4–6 ✅ (verify + canonical doc + archive) · Phase 3 → Task 7 ✅ · Phase 4 → Task 8 ✅ · Phase 5 → Task 9 ✅ (optional) · Phase 6 → Task 10 ✅.
- Spec §6 scope-limits (no feature work, no history rewrite, no eval merge, no subsystem code edits) → encoded in Global Constraints + Task 4 read-only + Task 8 file scope. ✅
- Spec §7 success criteria → Task 10 steps 1–5 map to criteria 1–5. ✅

**Placeholder scan:** No "TBD/TODO/implement later". Task 5's doc content is specified by required sections grounded in verified facts rather than pre-written prose (correct — its content depends on Task 4 findings). Task 8 cannot enumerate every translation (hundreds of comments) — it gives the exact method, the do-not-touch list, and grep/test verification, which is the right level for a mechanical language pass.

**Type consistency:** No cross-task code signatures — this is a file-movement/doc/comment plan. Path names are consistent across tasks (`_archive/prompts/`, `_archive/cursor/`, `_archive/docs/`, `docs/architecture.md`). ✅
