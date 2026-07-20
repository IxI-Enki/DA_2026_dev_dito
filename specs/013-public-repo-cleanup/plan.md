# Public Repository Cleanup — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `dev_dito` safe and presentable to publish publicly — process artifacts stay visible, no secret or personal datum is exposed, active configs run out-of-the-box.

**Architecture:** Pure repo-hygiene work on branch `013-public-repo-cleanup`. Most tasks are edits + a verification command (the "test" is a scan/parse/`git grep`). Two tasks are real code changes (loader fallback) done TDD-style. One task adds a small reusable redaction utility with a unit test.

**Tech Stack:** Python 3.13, PyYAML, pytest, gitleaks 8.30.1, pre-commit, PowerShell/bash. Git Bash is available for the shell commands below.

## Global Constraints

- Branch: `013-public-repo-cleanup`. Never commit to `master`.
- Neutral path placeholder (name scrub): `/path/to/legacy-stack`.
- `root_dir` sentinel in yaml: `AUTO` (loader resolves it at runtime).
- Redacted-email replacement token: `redacted@example.org`.
- Do **not** touch the harmless `D:/_Repositories/.../dev_dito` path in `specs/` or `docs/` historical files (only the `leonie`/`internal_leonidas`/`SYP_2025_26`/`POSE_2025_26` token is scrubbed there).
- Samples live under `data/<stage>/samples/`, whitelisted in `.gitignore`; `data/<stage>/*` otherwise stays ignored.
- Every task ends by committing on the branch. Commit style: Conventional Commits, scope `013`.

---

### Task 1: Remove the dead `config/sources.yaml` manifest

**Files:**
- Delete: `config/sources.yaml`

**Interfaces:**
- Consumes: nothing. Produces: nothing (verified no code imports it).

- [ ] **Step 1: Confirm nothing live reads it**

Run: `git grep -lE 'sources\.yaml' -- ':!config/sources.yaml' ':!specs/013*'`
Expected: only `.prompts/Next_Prompt_Feat_006.improved.md` and `docs/.archive/dev_dito_repository_setup.md` (docs/prompt references, no code).

- [ ] **Step 2: Remove the file**

Run: `git rm config/sources.yaml`

- [ ] **Step 3: Verify the token leak is gone from this file's content**

Run: `git grep -iE 'internal_leonidas|leonie' -- config/`
Expected: no matches.

- [ ] **Step 4: Commit**

```bash
git commit -m "chore(013): remove dead config/sources.yaml manifest

Unused ~150-line absolute-path manifest into a private repo; read by
no code and exposed internal naming. History retains it."
```

---

### Task 2: Scrub the `leonie` / `internal_leonidas` / course-structure token everywhere

**Files (modify):**
- `.prompts/Prompt.md`
- `.prompts/Next_Prompt_Feat_006.improved.md`
- `backend_services/.env.template`
- `docs/architecture.md`
- `docs/.archive/dev_dito_repository_setup.md`

**Interfaces:**
- Consumes: nothing. Produces: a tree free of the personal-name/internal token.

- [ ] **Step 1: Snapshot current occurrences (baseline)**

Run: `git grep -niE 'internal_leonidas|/leonie/|\\leonie\\|SYP_2025_26|POSE_2025_26|year_2025_26' -- ':!specs/013*'`
Expected: a list across the 5 files above. Note the count.

- [ ] **Step 2: Replace absolute path prefixes (both slash styles) and bare tokens**

Run (Git Bash, from repo root):

```bash
FILES=".prompts/Prompt.md .prompts/Next_Prompt_Feat_006.improved.md backend_services/.env.template docs/architecture.md docs/.archive/dev_dito_repository_setup.md"
for f in $FILES; do
  sed -i \
    -e 's#D:/_Repositories/year_2025_26/SYP_2025_26/leonie/internal_leonidas#/path/to/legacy-stack#g' \
    -e 's#D:\\_Repositories\\year_2025_26\\SYP_2025_26\\leonie\\internal_leonidas#/path/to/legacy-stack#g' \
    -e 's#D:/_Repositories/year_2025_26/POSE_2025_26#/path/to/legacy-stack#g' \
    -e 's#year_2025_26/SYP_2025_26/leonie/internal_leonidas#legacy-stack#g' \
    -e 's#internal_leonidas#legacy-wiki-repo#g' \
    -e 's#/leonie/#/legacy/#g' \
    "$f"
done
```

- [ ] **Step 3: Verify the token is fully gone**

Run: `git grep -niE 'internal_leonidas|/leonie/|\\leonie\\|SYP_2025_26|POSE_2025_26|year_2025_26' -- ':!specs/013*'`
Expected: no matches.

- [ ] **Step 4: Read-check the two portfolio-visible files still read sensibly**

Read `docs/architecture.md` around the previously-flagged lines (~112, 223–246) and `backend_services/.env.template` (~17). Confirm the placeholder paths read coherently (e.g. docker mounts now show `/path/to/legacy-stack/...`). Adjust wording by hand only if a sentence now reads oddly.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore(013): scrub personal name and internal repo structure

Replace leonie/internal_leonidas/course-structure paths with neutral
placeholders across docs, prompts, and .env.template."
```

---

### Task 3: `root_dir` auto-fallback in the embeddings-creator loader

**Files:**
- Modify: `pipeline/04_embeddings_creator/config.py` (in `load_config`, before `resolve_variables`)
- Modify: `pipeline/04_embeddings_creator/env.yaml:26`
- Test: `pipeline/04_embeddings_creator/tests/test_config_root_dir.py` (create)

**Interfaces:**
- Produces: `load_config()` tolerates `root_dir: AUTO` / missing, resolving it to the module directory (`Path(__file__).resolve().parent`) so `${root_dir}`-derived paths still resolve.

- [ ] **Step 1: Write the failing test**

```python
# pipeline/04_embeddings_creator/tests/test_config_root_dir.py
from pathlib import Path
import config as cfg  # module under test lives in the package dir

def test_root_dir_auto_resolves_to_module_dir(tmp_path):
    env = tmp_path / "env.yaml"
    env.write_text(
        "PATHS:\n"
        "  root_dir: AUTO\n"
        "  config_dir: ${root_dir}\n"
        "  script_dir: ${root_dir}\n"
        "  output_dir: ${root_dir}/../../data/embeddings\n"
        "  log_dir: ${root_dir}/../../data/logs\n"
        "  preprocessed_base: ${root_dir}/../../data/preprocessed\n"
        "  input_dir: ${preprocessed_base}\n",
        encoding="utf-8",
    )
    resolved = cfg.load_config(str(env))
    module_dir = str(Path(cfg.__file__).resolve().parent)
    assert resolved["PATHS"]["root_dir"] == module_dir
    assert "AUTO" not in resolved["PATHS"]["output_dir"]
```

- [ ] **Step 2: Run it — expect failure**

Run: `python -m pytest pipeline/04_embeddings_creator/tests/test_config_root_dir.py -v`
Expected: FAIL (root_dir stays `"AUTO"`).

- [ ] **Step 3: Implement the fallback**

In `pipeline/04_embeddings_creator/config.py`, inside `load_config`, immediately after `config = yaml.safe_load(f)` (and the empty-config check) and **before** `config = resolve_variables(config)`:

```python
    paths = config.get("PATHS") or {}
    if str(paths.get("root_dir", "")).strip() in ("", "AUTO"):
        paths["root_dir"] = str(Path(__file__).resolve().parent)
        config["PATHS"] = paths
```

Ensure `from pathlib import Path` is present (it is).

- [ ] **Step 4: Run the test — expect pass**

Run: `python -m pytest pipeline/04_embeddings_creator/tests/test_config_root_dir.py -v`
Expected: PASS.

- [ ] **Step 5: Point the real env.yaml at the sentinel**

Edit `pipeline/04_embeddings_creator/env.yaml:26`, replace:
`  root_dir: D:/_Repositories/_Diploma_Thesis_Repositories/dev_dito/pipeline/04_embeddings_creator`
with:
`  root_dir: AUTO   # resolved to this module's directory at runtime`

- [ ] **Step 6: Run the module's full test suite**

Run: `python -m pytest pipeline/04_embeddings_creator/tests -q`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add pipeline/04_embeddings_creator/config.py pipeline/04_embeddings_creator/env.yaml pipeline/04_embeddings_creator/tests/test_config_root_dir.py
git commit -m "refactor(013): auto-resolve root_dir in embeddings-creator config"
```

---

### Task 4: `root_dir` auto-fallback in the rag-preprocessing loader

**Files:**
- Modify: `pipeline/03_rag_preprocessing/config.py` (the `load`/resolve path, ~line 110–121)
- Modify: `pipeline/03_rag_preprocessing/env.yaml:18`
- Test: `pipeline/03_rag_preprocessing/tests/test_config_root_dir.py` (create)

**Interfaces:**
- Produces: preprocessing config tolerates `root_dir: AUTO`, resolving it to the **repo root** (`Path(__file__).resolve().parents[2]`) so `${root_dir}/data/...` resolves.

- [ ] **Step 1: Inspect the exact resolve site**

Read `pipeline/03_rag_preprocessing/config.py:100-125` to confirm where `raw_config` is loaded and where `resolve_variables` is called (seen: `base = Path(__file__).parent` ~110, `resolve_variables(raw_config)` ~116, `root_dir=Path(paths.get("root_dir", "."))` ~121).

- [ ] **Step 2: Write the failing test**

```python
# pipeline/03_rag_preprocessing/tests/test_config_root_dir.py
from pathlib import Path
import config as cfg

def test_root_dir_auto_resolves_to_repo_root(tmp_path, monkeypatch):
    env = tmp_path / "env.yaml"
    env.write_text(
        "PATHS:\n"
        "  root_dir: AUTO\n"
        "  fetched_dir: ${root_dir}/data/fetched\n"
        "  output_dir: ${root_dir}/data/preprocessed\n"
        "  log_dir: ${root_dir}/data/logs\n",
        encoding="utf-8",
    )
    resolved = cfg.load_yaml(env)
    resolved = cfg._apply_root_dir_fallback(resolved)  # helper added in Step 3
    repo_root = str(Path(cfg.__file__).resolve().parents[2])
    assert resolved["PATHS"]["root_dir"] == repo_root
```

- [ ] **Step 3: Run it — expect failure**

Run: `python -m pytest pipeline/03_rag_preprocessing/tests/test_config_root_dir.py -v`
Expected: FAIL (`_apply_root_dir_fallback` does not exist).

- [ ] **Step 4: Implement the helper and call it before `resolve_variables`**

Add to `pipeline/03_rag_preprocessing/config.py`:

```python
def _apply_root_dir_fallback(config: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve a missing/`AUTO` PATHS.root_dir to the repo root."""
    paths = config.get("PATHS") or {}
    if str(paths.get("root_dir", "")).strip() in ("", "AUTO"):
        paths["root_dir"] = str(Path(__file__).resolve().parents[2])
        config["PATHS"] = paths
    return config
```

Then, where the config is loaded before `resolve_variables(raw_config)` (~line 116), insert:
`            raw_config = _apply_root_dir_fallback(raw_config)`

- [ ] **Step 5: Run the test — expect pass**

Run: `python -m pytest pipeline/03_rag_preprocessing/tests/test_config_root_dir.py -v`
Expected: PASS.

- [ ] **Step 6: Point the real env.yaml at the sentinel**

Edit `pipeline/03_rag_preprocessing/env.yaml:18`, replace:
`  root_dir: D:/_Repositories/_Diploma_Thesis_Repositories/dev_dito`
with:
`  root_dir: AUTO   # resolved to the repository root at runtime`

- [ ] **Step 7: Run the module's full test suite**

Run: `python -m pytest pipeline/03_rag_preprocessing/tests -q`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add pipeline/03_rag_preprocessing/config.py pipeline/03_rag_preprocessing/env.yaml pipeline/03_rag_preprocessing/tests/test_config_root_dir.py
git commit -m "refactor(013): auto-resolve root_dir in rag-preprocessing config"
```

---

### Task 5: Sanitize remaining active-config paths and the LAN IP

**Files (modify):**
- `config/PLACEHOLDER_env.yaml:27`, `config/env.development.yaml:31`, `config/env.minimal.yaml:11` (root_dir → `AUTO`)
- `pipeline/03_rag_preprocessing/env.yaml:129` (LAN IP → localhost)

**Interfaces:**
- Consumes: the loader fallback from Tasks 3–4 (central `config.py` at repo root already defaults `root_dir` to `REPO_ROOT`, so `AUTO` there is cosmetic; keep it consistent).

- [ ] **Step 1: Replace root_dir in the three config templates**

In each of `config/PLACEHOLDER_env.yaml`, `config/env.development.yaml`, `config/env.minimal.yaml`, set the `root_dir:` value to:
`  root_dir: AUTO   # leave as AUTO; resolved to the repo root at runtime`

- [ ] **Step 2: Replace the LAN IP**

Edit `pipeline/03_rag_preprocessing/env.yaml:129`, replace:
`  api_base: http://192.168.8.3:1234/v1`
with:
`  api_base: http://localhost:1234/v1   # LMStudio OpenAI-compatible endpoint`

- [ ] **Step 3: Verify no absolute dev-machine paths or IPs remain in active configs**

Run: `git grep -nE 'D:/_Repositories|192\.168\.' -- config pipeline/*/env.yaml`
Expected: no matches.

- [ ] **Step 4: Sanity-parse the edited YAML**

Run: `python -c "import yaml,glob;[yaml.safe_load(open(p,encoding='utf-8')) for p in glob.glob('config/*.yaml')+['pipeline/03_rag_preprocessing/env.yaml','pipeline/04_embeddings_creator/env.yaml']];print('yaml ok')"`
Expected: `yaml ok`.

- [ ] **Step 5: Commit**

```bash
git add config/*.yaml pipeline/03_rag_preprocessing/env.yaml
git commit -m "chore(013): replace machine paths and LAN IP in active configs"
```

---

### Task 6: Reusable sample-redaction utility

**Files:**
- Create: `scripts/redact_sample.py`
- Test: `tests/test_redact_sample.py`

**Interfaces:**
- Produces: `redact_text(text: str) -> str` (replaces emails with `redacted@example.org`) and a CLI `python scripts/redact_sample.py <src> <dst>` that redacts file → file. Later tasks call the CLI to produce samples.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_redact_sample.py
from scripts.redact_sample import redact_text

def test_redacts_email():
    assert redact_text("mail a.teacher@example.org now") == \
        "mail redacted@example.org now"

def test_keeps_placeholder_untouched_shape():
    out = redact_text("VORNAME.NACHNAME@students.htl-leonding.ac.at")
    assert out == "redacted@example.org"

def test_no_email_unchanged():
    assert redact_text("no address here") == "no address here"
```

- [ ] **Step 2: Run it — expect failure**

Run: `python -m pytest tests/test_redact_sample.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement the utility**

```python
# scripts/redact_sample.py
"""Redact PII (email addresses) from a fetched-content file for public samples."""
from __future__ import annotations
import re
import sys
from pathlib import Path

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def redact_text(text: str) -> str:
    """Replace every email address with a neutral placeholder."""
    return _EMAIL.sub("redacted@example.org", text)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: python scripts/redact_sample.py <src> <dst>", file=sys.stderr)
        return 2
    src, dst = Path(argv[1]), Path(argv[2])
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(redact_text(src.read_text(encoding="utf-8")), encoding="utf-8")
    print(f"redacted {src} -> {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 4: Run the test — expect pass**

Run: `python -m pytest tests/test_redact_sample.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/redact_sample.py tests/test_redact_sample.py
git commit -m "feat(013): add reusable email-redaction utility for samples"
```

---

### Task 7: Produce curated, redacted samples under `data/<stage>/samples/`

**Files:**
- Create: `data/fetched/samples/exams_matura-tagesschule-if-it.txt` (redacted)
- Create: `data/embeddings/samples/embedded_chunks.sample.jsonl` (first 3 chunks, redacted)
- Create: `data/evaluated/samples/ANALYSIS_REPORT.sample.md` (a report copy)
- Create: `data/fetched/samples/README.md` (explains provenance + redaction)

**Interfaces:**
- Consumes: `scripts/redact_sample.py` from Task 6.

- [ ] **Step 1: Redact the page sample**

Run:
```bash
python scripts/redact_sample.py \
  data/fetched/fetched_at_20260216_174539/page_content/exams_matura-tagesschule-if-it.txt \
  data/fetched/samples/exams_matura-tagesschule-if-it.txt
```

- [ ] **Step 2: Build a 3-chunk embeddings excerpt, then redact it**

Run:
```bash
head -n 3 data/embeddings/embedded_at_20260217_194039/embedded_chunks.jsonl > /tmp/chunks3.jsonl
python scripts/redact_sample.py /tmp/chunks3.jsonl data/embeddings/samples/embedded_chunks.sample.jsonl
```

- [ ] **Step 3: Copy + redact one analysis report**

Run:
```bash
python scripts/redact_sample.py \
  data/evaluated/deep_eval_20260216_174929/ANALYSIS_REPORT_20260216_174929.md \
  data/evaluated/samples/ANALYSIS_REPORT.sample.md
```

- [ ] **Step 4: Write a provenance README**

Create `data/fetched/samples/README.md`:

```markdown
# Sample artifacts

Small, **redacted** examples of each pipeline stage's real output, so the
repository shows end-to-end results without publishing the full dataset.

- Source: LeoWiki (DokuWiki, HTL Leonding) — institutional/procedural pages only.
- All email addresses have been replaced with `redacted@example.org`
  via `scripts/redact_sample.py`.
- The full fetched corpus and embeddings are intentionally **not** published.
```

- [ ] **Step 5: Verify samples are PII-free**

Run: `grep -rInE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' data/*/samples/ | grep -v 'redacted@example.org'`
Expected: no matches (only the placeholder, if any).

- [ ] **Step 6: (defer commit to Task 8, which whitelists these paths)**

The files are currently ignored by `data/<stage>/*` rules; Task 8 adds the whitelist and commits them together.

---

### Task 8: Fix `.gitignore` (`.cursor` contradiction + sample whitelists)

**Files:**
- Modify: `.gitignore`

**Interfaces:**
- Consumes: the sample files from Task 7.

- [ ] **Step 1: Remove the `.cursor/` contradiction**

In `.gitignore`, delete the `.cursor/` line (files under `.cursor/` are intentionally tracked as portfolio artifacts). Leave a comment:
`# .cursor/ is intentionally tracked (Spec-Kit command artifacts)`

- [ ] **Step 2: Add sample whitelists in the Data section**

In `.gitignore`, under each `data/<stage>/*` block, add a negation. After the existing `data/fetched/*` / `!data/fetched/.gitkeep` lines, add for each stage:

```gitignore
# Curated, redacted samples (Spec 013) — explicitly published
!data/fetched/samples/
!data/fetched/samples/**
!data/embeddings/samples/
!data/embeddings/samples/**
!data/evaluated/samples/
!data/evaluated/samples/**
```

- [ ] **Step 3: Verify the samples are now un-ignored and nothing else leaked in**

Run: `git add -A -n data/ && git check-ignore -v data/fetched/samples/exams_matura-tagesschule-if-it.txt || echo "not ignored (good)"`
Then: `git status --porcelain data/ | grep -vE 'samples/'`
Expected: the second command prints nothing (only `samples/` files are staged from `data/`).

- [ ] **Step 4: Stage and commit samples + gitignore together**

```bash
git add .gitignore data/fetched/samples data/embeddings/samples data/evaluated/samples
git status --porcelain   # confirm only intended files
git commit -m "chore(013): publish redacted stage samples; fix .cursor ignore"
```

---

### Task 9: Add `pre-commit` config with gitleaks + email guard

**Files:**
- Create: `.pre-commit-config.yaml`

**Interfaces:**
- Consumes: `gitleaks` (installed), `pre-commit` (installed).

- [ ] **Step 1: Write the config**

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.30.1
    hooks:
      - id: gitleaks
  - repo: local
    hooks:
      - id: no-real-emails
        name: block real email addresses
        entry: python scripts/redact_sample.py
        language: system
        pass_filenames: false
        always_run: true
        args: ["--check"]
```

- [ ] **Step 2: Add a `--check` mode to the redaction script**

In `scripts/redact_sample.py`, extend `main` so that `--check` scans tracked, non-sample files for real emails and exits non-zero if any are found (excludes `data/*/samples/`, `*.md` placeholders, and the `redacted@example.org` token). Add a matching test in `tests/test_redact_sample.py`:

```python
def test_check_mode_passes_on_clean_text(tmp_path):
    from scripts.redact_sample import scan_for_emails
    assert scan_for_emails("no pii here") == []
    assert scan_for_emails("a@b.co") == ["a@b.co"]
```

Implement `scan_for_emails(text)` returning the list of matches, and wire `--check` in `main` to walk `git ls-files`, skipping the excluded paths.

- [ ] **Step 3: Run the hook end-to-end**

Run: `pre-commit run --all-files`
Expected: `gitleaks` passes; `no-real-emails` passes (tracked surface is clean).

- [ ] **Step 4: Commit**

```bash
git add .pre-commit-config.yaml scripts/redact_sample.py tests/test_redact_sample.py
git commit -m "chore(013): add pre-commit gitleaks + email guard hooks"
```

---

### Task 10: README portfolio framing + `PRIVACY.md`

**Files:**
- Modify: `README.md` (add one section)
- Create: `PRIVACY.md`

- [ ] **Step 1: Add a "What this demonstrates" section to README**

Insert after the intro (before `## Pipeline Overview`):

```markdown
## What this demonstrates

- **RAG pipeline** — a 5-stage DokuWiki → embeddings → Qdrant flow.
- **Spec-Driven Development** — 12 numbered feature specs under `specs/`,
  a project constitution under `.specify/`, and CI that turns specs into issues.
- **Agentic orchestration** — reproducible Claude / Cursor / Spec-Kit command
  sets under `.claude/`, `.cursor/`, and `.prompts/`.
- **Evaluation** — a RAGAS + custom-metric framework under `evaluation/`.

Real source data is **not** published; each stage ships a small, redacted
sample under `data/<stage>/samples/`. See [PRIVACY.md](PRIVACY.md).
```

- [ ] **Step 2: Write `PRIVACY.md`**

```markdown
# Data & Privacy

This repository was built against a live DokuWiki (HTL Leonding). To publish
it responsibly:

- **Secrets** (API tokens, SSL certificate) live only in `config/secrets/`,
  are gitignored, and were never committed (verified with `gitleaks` across
  the full history).
- **Personal data** in the source wiki (staff/contact email addresses) is
  **not** published. The full fetched corpus and embeddings stay local.
- **Samples** under `data/<stage>/samples/` are institutional/procedural
  pages only, with all email addresses redacted via `scripts/redact_sample.py`.
- A `pre-commit` hook (gitleaks + an email guard) protects future commits.
```

- [ ] **Step 3: Verify links resolve**

Run: `test -f PRIVACY.md && grep -q 'What this demonstrates' README.md && echo ok`
Expected: `ok`.

- [ ] **Step 4: Commit**

```bash
git add README.md PRIVACY.md
git commit -m "docs(013): add portfolio framing and PRIVACY.md"
```

---

### Task 11: Final pre-publication gate

**Files:** none (verification only) + update `specs/013-public-repo-cleanup/spec.md` checklist.

- [ ] **Step 1: gitleaks full-history rescan**

Run: `gitleaks git .`
Expected: `no leaks found`.

- [ ] **Step 2: Tracked-surface PII scan (only placeholders allowed)**

Run: `git ls-files -z | xargs -0 grep -InE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' | grep -vaiE 'redacted@example.org|VORNAME|NACHNAME|YOUR_|IHR_|example|noreply|placeholder|@v1'`
Expected: no matches.

- [ ] **Step 3: No machine paths / IPs / name token in the published surface**

Run: `git grep -nE 'D:/_Repositories|192\.168\.|internal_leonidas|/leonie/|SYP_2025_26' -- ':!specs/013*'`
Expected: only harmless `D:/_Repositories/.../dev_dito` occurrences inside `specs/`/`docs/` historical files (decided out of scope); zero `internal_leonidas`/`leonie`/IP hits.

- [ ] **Step 4: Secrets dir publishes only structure**

Run: `git ls-files config/secrets/`
Expected: exactly `config/secrets/.gitkeep` and `config/secrets/README.md`.

- [ ] **Step 5: Full test suite green**

Run: `python -m pytest -q`
Expected: passes (or pre-existing unrelated skips only).

- [ ] **Step 6: Tick the spec success criteria and commit**

Check the boxes in `specs/013-public-repo-cleanup/spec.md` §5, then:

```bash
git add specs/013-public-repo-cleanup/spec.md
git commit -m "docs(013): record passing pre-publication gate"
```

- [ ] **Step 7: Hand back for the visibility flip**

Report all gate results to the user. Making the repo public (GitHub visibility change, enabling Push Protection) is a user action — do not perform it automatically.

---

## Self-Review

**Spec coverage:** Workstream A → Tasks 1, 8 (remove dead manifest, fix `.cursor`, keep assets). B → Tasks 2–5. C → Tasks 6–8. D → Tasks 9–10. E → Task 11. Decisions 7 (sources.yaml) → Task 1; 8 (name scrub) → Task 2; 9 (root_dir fallback) → Tasks 3–4. All covered.

**Placeholder scan:** No "TBD/TODO"; every code step shows code; every verify step shows a command + expected output. Task 9 Step 2 describes `--check`/`scan_for_emails` with the signature and a test — concrete, not a placeholder.

**Type consistency:** `redact_text(str)->str`, `scan_for_emails(str)->list`, `_apply_root_dir_fallback(dict)->dict`, sentinel `AUTO`, placeholder `/path/to/legacy-stack`, token `redacted@example.org` — used identically across tasks.
