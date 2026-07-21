# Portfolio-Cleanup — Design

> **Stand:** 2026-07-21
> **Autor:** Jan Ritt (IxI-Enki), mit Claude Code
> **Ziel:** Die `dev_dito`-Codebase in einen portfolio-gerechten Zustand bringen —
> **ohne** sie durch das Aufräumen weiter zu fragmentieren.

---

## 1. Problem & Leitprinzip

Das Repo hat vor dem Public-Release verstreute lose Enden: Entwicklungs-Dumps
(`.prompts/`, `.cursor/plans/`), fünf widersprüchliche/veraltete Architektur-Docs,
gemischtsprachige Kommentare, und eine per-Stufe-Qualitäts-Story, die nirgends
sauber dokumentiert ist und „immer untergeht".

**Anti-Fragmentierungs-Prinzip:** *Eine* geschriebene Spec legt für *jedes* lose
Ende *einmal* das Ziel fest; die Ausführung passiert in klar begrenzten Phasen auf
*einem* Branch. Es wird nichts gelöscht, was nicht reproduzierbar wieder auffindbar
ist. Der Cleanup ist **Aufräumen + ehrliches Narrativ**, kein Feature-Projekt.

## 2. Getroffene Richtungsentscheidungen

| Thema | Entscheidung |
|---|---|
| **Repo-Fokus** | **Pipeline im Zentrum.** `dokuwiki_plugin` + `backend_services` bleiben, werden aber zur klar abgegrenzten, dokumentierten Integrations-/Deployment-Schicht (eigene READMEs, nicht im Rampenlicht). |
| **Sprachpolitik** | **Code EN, Output darf DE.** Kommentare + Docstrings → Englisch. Benutzersichtbare CLI-/Report-Ausgaben und LLM-Prompts dürfen deutsch bleiben, wo inhaltlich gewollt. Meta-/Entwicklungskommentare werden entfernt. |
| **Cruft-Entsorgung** | **Nach `_archive/` verschieben** (nicht löschen). `_archive/` ist **gitignored** (nur-lokales Sicherheitsnetz). Zusätzlich Tag `archive/pre-portfolio` friert den Ist-Stand ein. Öffentliche `master` bleibt sauber; nichts geht verloren. |
| **Linter/CI** | Verschärfung **ganz am Ende** (optional). CI existiert und funktioniert bereits. |
| **Per-Stufe-Evaluation** | **Dokumentieren + verifizieren.** Die per-Stufe-Gates existieren im Code; sie werden dokumentiert und ins Zentrum gerückt. Während der Umsetzung werden die Impls gelesen und ehrlich verifiziert — **es wird nichts neu gebaut.** |

## 3. Verifizierter Ist-Zustand (Grundlage, Stand 2026-07-21)

### 3.1 Cruft (bestätigt)
- `.prompts/` — 3 Dev-Dumps, ~97 KB, getrackt.
- `.cursor/plans/` — 20+ `*.plan.md` Dev-Dumps; `.cursor/agents/` + `.cursor/skills/`
  sind RAG-Eval-Themen. **Behalten:** `.cursor/commands/` (Speckit), `rules`, `settings.json`
  (`.gitignore` erklärt `.cursor/` als „intentionally tracked (Spec-Kit)").
- `tstex_modules/` — enthält nur `_api.ts`, das bereits in `.gitignore:209` steht → **nicht getrackt**,
  reiner lokaler Müll. Ganze Dir statt einer Datei ignorieren.

### 3.2 Docs (fünf stale Epochen, kein aktuelles Doc)
| Doc | Stand | Beschreibt | Status |
|---|---|---|---|
| `architecture.md` | 01-24 | Altes Legacy-Repo (Leonidas + devdito DokuWiki-Plugins) | Obsolet |
| `README_ARCHITECTURE.md` | 01-24 | „9-Stack-Docker A–I / Stack-G"-Vision | Anderes Framing |
| `gap_analysis_prototypes_vs_pipeline.md` | 02-14 | Prototyp-vs-Pipeline-Lücken | Veraltet (Lücken inzwischen gebaut) |
| `EVALUATION_WITHOUT_RAGAS.md` | 02-17 | Finale RAG-Eval ohne RAGAS | Teils überholt (es gibt wieder `evaluation/ragas/`) |
| `dev_dito_pipeline_manager.md` | — | Unimplementierter PHP-Plugin-Plan, alte `research/techstack`-Pfade | Aspirational |
| `docs/.archive/` (2 Files) | — | Bereits archiviert | → `_archive/` |
| `test_report.md` + `test_report.pdf` | — | Dublette (md + pdf) | Eine Form behalten |

### 3.3 Zwei Evaluations-Ebenen (real implementiert, nirgends als Landkarte dokumentiert)

**Ebene 1 — Qualitäts-Gates pro Stufe (in der Pipeline):**
- **Stufe 1** `pipeline/01_wiki_fetcher/` — fetch + change_detection + manifest + progress
- **Stufe 2** `pipeline/02_deep_evaluation/` — `analyzers/` + `generators/` (per-Page-Strategie)
  + `evaluator.py` + `report_generator.py` → bewertet gefetchten Content, kategorisiert
- **Stufe 3** `pipeline/03_rag_preprocessing/` — page_processor, metadata_enricher, media_processor,
  image_captioner, strategy_loader, exporter, spot_check **+ eigenes `evaluation/` (metrics.py, report.py)**
  → Preprocessing-Qualität (consistency/junk). *(War laut gap_analysis „missing" — existiert jetzt.)*
- **Stufe 4** `pipeline/04_embeddings_creator/` — content_aware_chunker (strategie-basiert) + embedder + pipeline
- **Stufe 5** `pipeline/05_deploy/` — transfer_to_pi + verify_transfer + deploy_qdrant

**Ebene 2 — finale RAG-Evaluation (separates top-level `evaluation/`):**
- metrics (MRR/NDCG/…), experiments, ground_truth, providers, `ragas/`, statistics,
  visualization, figures, reports → beantwortet die Forschungsfragen (Ground-Truth-QA + LLM-as-Judge).

**Bekannte Nahtstelle:** Zwischen Ebene 1 und Ebene 2 gibt es keinen dokumentierten
Zusammenhang, und die per-Stufe-Gates sind nirgends als *ein* Konzept benannt. Genau das
behebt Phase 2.

### 3.4 Subsystem-Trennbarkeit (bestätigt)
Die Pipeline importiert **null** aus `backend_services` und referenziert `dokuwiki` nur als
kosmetischen URL-String (`pipeline/03_rag_preprocessing/page_processor.py:270`). Beide
Subsysteme sind echt eigenständig; die Pipeline läuft standalone.

### 3.5 CI/Linter (existiert, permissiv)
- `.github/workflows/ci.yml` — 5 parallele Jobs: ruff+black, Spec-Validation, pytest unit+smoke,
  docker-compose, gitleaks. Pre-commit (gitleaks + email-redact) vorhanden.
- `pyproject.toml` ruff — 14 `ignore`-Regeln, schließt `backend_services/dokuwiki_plugin/research`
  ganz aus; gitleaks in CI ist `continue-on-error: true`.
- **Kritik ist „permissiv", nicht „abwesend".**

## 4. Ausführungs-Strategie

- **Ein** Branch `014-portfolio-cleanup`, **ein Commit pro Phase** (nachvollziehbar, reviewbar,
  keine Streuung auf `master`).
- `_archive/` = gitignored, nur lokal. Tag `archive/pre-portfolio` vor Phase 1.
- Alternativen verworfen: PR-pro-Phase (Overhead), direkt auf master (unübersichtlich/riskant),
  History-Rewrite (nicht nötig — kein Secret-Zwang; Cruft nur getrackt seit jüngerer Zeit).

## 5. Phasen

### Phase 0 · Sicherheitsnetz
- Git-Tag `archive/pre-portfolio` auf den heutigen `master`.
- `.gitignore`: `_archive/` und `tstex_modules/` (ganze Dir) ergänzen.
- **Ergebnis:** Ab hier ist jede Änderung reversibel.

### Phase 1 · Struktureller Cruft
- Nach `_archive/` verschieben (untrack, nicht löschen): `.prompts/`, `.cursor/plans/`,
  `.cursor/agents/`, `.cursor/skills/`.
- **Behalten:** `.cursor/commands/`, `.cursor/rules/`, `.cursor/settings.json`, `.cursor/hooks/`.
- `tstex_modules/` lokal entfernen (bereits ignoriert).
- **Ergebnis:** Offene „.cursor-Entscheidung" aus 013 geschlossen; Repo-Wurzel sauber.

### Phase 2 · Docs = das Herzstück
- **Vorab-Task (verifizieren):** per-Stufe-Eval-Impls lesen — `pipeline/02_deep_evaluation/evaluator.py`,
  `pipeline/03_rag_preprocessing/evaluation/metrics.py`+`report.py`, `pipeline/05_deploy/verify_transfer.py` —
  und einen ehrlichen 1-Absatz-Verifikationsbefund pro Stufe festhalten (funktionierendes Gate? halb da?).
- **Ein** kanonisches `docs/architecture.md` (neu geschrieben) mit:
  (a) 5-Stufen-Pipeline als Herzstück,
  (b) explizitem Qualitäts-Gate pro Stufe (was/wo/wie geprüft),
  (c) klarer Trennung Ebene 1 (per-Stufe) ↔ Ebene 2 (finale RAG-Eval),
  (d) ehrlicher RAGAS-Entscheidung als aktueller Stand.
- Die fünf stale Docs → `_archive/docs/` mit je einer „warum ersetzt"-Zeile.
- `docs/.archive/` → `_archive/docs/`. `test_report`-Dublette klären (eine Form behalten).
- **Ergebnis:** Die per-Stufe-Story steht zentral statt verstreut.

### Phase 3 · Subsystem-Grenze
- Top-`README.md`: Pipeline als Headline; `backend_services/` + `dokuwiki_plugin/` als
  klar abgegrenzte Nebenschicht mit je einem Ein-Zeilen-Pointer.
- `backend_services/README.md` + `dokuwiki_plugin/`-README: „Integrations-/Deployment-Schicht —
  Pipeline läuft standalone", Grenze explizit.
- **Ergebnis:** „Pipeline im Zentrum" auch strukturell/narrativ sichtbar.

### Phase 4 · Code-Sprachpass
- DE-Kommentare/Docstrings → EN über die Pipeline (Schwerpunkt `02_deep_evaluation`).
- **Bewahren:** benutzersichtbare DE-Ausgaben (z.B. Report-Überschriften in `report_generator.py`)
  und LLM-Prompts — pro String bewusst entscheiden.
- Meta-/Dev-Kommentare entfernen.
- Danach `simplify` / code-simplifier auf die geänderten Files.
- **Ergebnis:** Konsistente englische Code-Sprache, DE nur wo inhaltlich gewollt.

### Phase 5 · Linter/CI verschärfen (optional, zuletzt)
- ruff `ignore`-Liste + Excludes wo billig reduzieren; gitleaks-Blocking erwägen.
- **Ergebnis:** Strengere Qualitäts-Signale — nur wenn gewünscht.

### Phase 6 · Verifikation
- Lokal `ruff`/`black`/`pytest` grün; Pipeline läuft; CI grün.
- **Ergebnis:** Nachgewiesen sauber, nicht nur behauptet.

## 6. Scope-Grenzen (bewusst ausgeschlossen)
- **Kein** Bau neuer Eval-Features (Ebene 1/2 bleiben inhaltlich unangetastet).
- **Kein** strukturelles Zusammenlegen der zwei Eval-Ebenen (wäre eigener Plan).
- **Kein** Git-History-Rewrite.
- **Kein** Anfassen von `backend_services`/`dokuwiki_plugin`-Code (nur READMEs).

## 7. Erfolgskriterien
1. Repo-Wurzel + `docs/` enthalten keinen Dev-Cruft mehr; alles Entfernte liegt in `_archive/` (lokal) bzw. im Tag.
2. Genau **ein** aktuelles Architektur-Doc, das die per-Stufe-Qualitäts-Gates benennt und Ebene 1/2 trennt.
3. Pipeline als erkennbares Herzstück; Plugin/Backend als dokumentierte Nebenschicht.
4. Pipeline-Code: Kommentare/Docstrings englisch, Output/Prompts wo gewollt deutsch, keine Meta-Kommentare.
5. `ruff`/`black`/`pytest` + CI grün.
6. Öffentliche `master` enthält kein `_archive/`.
