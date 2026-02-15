# Feature Specification: Analysis & Production Polish

**Feature Branch**: `009-analysis-and-production-polish`
**Created**: 2026-02-15
**Status**: Draft
**Thesis-Zuordnung**: FF1, FF3, J4, J6
**Constitution**: v1.4.0 (Article X: Execution Mandate, Article XI: Thesis Alignment)
**Comparison Analysis**: `___NEXT_UP___/COMPARISON--prototypes_vs_pipeline--executions_outputs_results_side_by_side.md` (Section X)
**Depends On**: 007-evaluation-infrastructure (Phases 1-7 complete), 008-pipeline-consolidation (Draft, teilweise uebernommen)
**Supersedes**: 008-pipeline-consolidation US5 (Preprocessing) -- die uebrigen US (RAGAS, Statistik, Visualisierung) bleiben in 008

---

## Kontext

Eine systematische Side-by-Side-Vergleichsanalyse (2026-02-14/15) hat alle 4 Pipeline-Stages
gegen ihre Prototype-Referenzimplementierungen verglichen. Die Analyse identifizierte:

- **Part 1 (Wiki Fetching)**: 10 Diskrepanzen -- Pipeline ist korrekt, 1 Feature-Gap (CLI UX), 1 Bug
- **Part 2 (Deep Evaluation)**: 7 Diskrepanzen -- algorithmisch identisch, 2 Bugs (rglob-Duplikate, YAML-Duplikate), 1 Optimierung (Temperature)
- **Part 3 (Preprocessing)**: 14 Diskrepanzen -- Pipeline ist KEIN Port, Output-Schema **inkompatibel mit Qdrant Embeddings Creator** (KRITISCH)

Die Preprocessing-Pipeline (`pipeline/03_rag_preprocessing/`) produziert Output, den Stage 4
(Embeddings Creator) nicht laden kann. Dies ist ein **Blocker** fuer die gesamte Evaluations-Kette.

**Datenfluss-Kette** (muss lueckenlos funktionieren):
```sketch
Stage 1: Wiki Fetch ──> Stage 2: Deep Eval ──> Stage 3: Preprocessing ──> Stage 4: Embeddings ──> Qdrant ──> MCP-Server
                              │                       │
                    preprocessing_strategies.yaml    *.md (Qdrant-Schema)
```

**Betroffene Schichten**: `pipeline/01_wiki_fetcher/` (CLI UX), `pipeline/02_deep_evaluation/` (Bugs),
`pipeline/03_rag_preprocessing/` (Schema-Alignment + Features), `pipeline/shared/` (neues CLI-Modul)

---

## Gesamtpipeline nach Abschluss

```sketch
[Stage 1: Fetch]         wiki_fetcher -> data/fetched/
        │                 CLI UX: Farbe, Help, Signal-Handler (US1)
        │
[Stage 2: Evaluate]      deep_evaluation -> preprocessing_strategies.yaml
        │                 Bugfixes: rglob-Dedup, YAML-Dedup, temperature=0.0 (US2)
        │
[Stage 3: Preprocess]    rag_preprocessing -> data/preprocessed/
        │                 Schema-Alignment, Strategy-Integration, Freshness,
        │                 Vision-LLM, PDF-Qualitaet, Evaluation (US3-US8)
        │
[Stage 4: Embed]         embeddings_creator -> data/embeddings/  (NICHT in Scope)
        │
[Stage 5: Deploy]        -> Qdrant  (NICHT in Scope)
```

---

## User Stories

### US1 -- CLI UX Portierung (Priority: P3-Medium)

Als Pipeline-Betreiber will ich farbige Konsolenausgabe, einheitliche Help-Funktionen und
Signal-Handler in allen manuell ausfuehrbaren Pipeline-Skripten, damit die Bedienung
professionell und konsistent ist.

**Comparison-Referenz**: Part 1 Diskrepanz #9, Section X.2.1

**Acceptance Criteria**:

1. **Given** `pipeline/shared/cli_utils.py` existiert, **When** ein Pipeline-Skript importiert wird, **Then** stehen `style()`, `set_use_color()`, `enable_windows_ansi()`, `create_sigint_handler()` zur Verfuegung.
2. **Given** ein Skript wird mit `--no-color` aufgerufen, **When** Output erzeugt wird, **Then** enthaelt der Output keine ANSI-Escape-Sequenzen.
3. **Given** ein Skript wird mit `-h` oder `--help` aufgerufen, **When** die Hilfe angezeigt wird, **Then** folgt sie dem 8-Sektionen-Template (What, Usage, Parameters, Options, Examples, Configuration, Output, Exit Codes).
4. **Given** der Benutzer drueckt Ctrl+C waehrend einer Ausfuehrung, **When** der Signal-Handler greift, **Then** wird ein gelber Abort-Banner mit Fortschrittsstatistiken angezeigt und der Prozess beendet sich mit Exit-Code 130.
5. **Given** Windows PowerShell als Terminal, **When** `enable_windows_ansi()` aufgerufen wird, **Then** werden ANSI-Farben korrekt dargestellt.

**Betroffene Skripte**: `fetch_full_wiki_extended.py`, `incremental_fetcher.py`, `resume_fetch.py`,
`run_deep_evaluation.py`, `run_evaluation.py`, `run_strategy_generation.py`, `run_preprocessing.py` (03_rag_preprocessing)

> **Hinweis**: `main.py` (03_rag_preprocessing) wird durch US9 geloescht und in `run_preprocessing.py` konsolidiert.
> CLI UX Integration betrifft daher `run_preprocessing.py` als einzigen Entry Point.

**Referenz-Implementierung** (Prototype, eingefroren):
- `research/techstack/dokuwiki/fetcher_shared/dokuwiki/cli_help.py`
- `research/techstack/dokuwiki/fetcher_json_rpc_api/script/fetch_full_wiki_extended.py` (Zeilen 45-99, 106-124, 292-301, 1986-2027)

---

### US2 -- Deep Evaluation Bugfixes + Optimierung (Priority: P2-High)

Als Pipeline-Betreiber will ich korrekte Datei-Zaehlung und deterministische LLM-Klassifikation
in der Deep Evaluation, damit die Ergebnisse reproduzierbar und fehlerfrei sind.

**Comparison-Referenz**: Part 2 Diskrepanzen D2, D3, D6, D7, Section X.2.2

**Acceptance Criteria**:

1. **Given** Media-Dateien mit gemischter Gross-/Kleinschreibung (z.B. `file.PDF` und `file.pdf` auf Windows), **When** die File-Discovery laeuft, **Then** wird jeder physische Dateipfad nur einmal gezaehlt (Set-basierte Deduplizierung).
2. **Given** `env.yaml` mit `temperature: 0.0`, **When** die LLM-Klassifikation laeuft, **Then** wird `temperature=0.0` an den LLM-Endpoint uebergeben.
3. **Given** mehrzeilige Summary-Ausgaben, **When** sie geloggt werden, **Then** erscheinen sie als zusammenhaengender Block (kein Timestamp-Prefix pro Zeile).
4. **Given** die `StrategyGenerator` erzeugt YAML-Output, **When** Dateilisten geschrieben werden, **Then** erscheint jeder Dateiname pro Sektion maximal einmal.

**Betroffene Dateien**:
- `pipeline/02_deep_evaluation/run_deep_evaluation.py` (rglob-Dedup)
- `pipeline/02_deep_evaluation/env.yaml` (temperature)
- `pipeline/02_deep_evaluation/generators/strategy_generator.py` (YAML-Dedup)

---

### US3 -- Preprocessing Schema-Alignment (Priority: P0-Blocker)

Als Pipeline-Betreiber will ich, dass der Preprocessing-Output exakt dem Schema entspricht, das
der Qdrant Embeddings Creator (`document_loader.py`) erwartet, damit Stage 4 die Daten laden kann.

**Comparison-Referenz**: Part 3 Diskrepanzen P3, P4, P5, P6, P7, Section X.2.3.1

**Why Blocker**: Ohne Schema-Kompatibilitaet kann Stage 4 die Daten nicht laden. Die gesamte
Evaluations-Pipeline (FF1, FF3) ist blockiert.

**Ziel-Schema** (Pflicht-Frontmatter fuer Pages UND Media):

```yaml
---
title: "Seitentitel oder Dokumentname"
namespace: "exams:da-inf-it"
source: "https://leowiki.htl-leonding.ac.at/doku.php?id=..."
page_id: "exams:da-inf-it:theses"             # Pages
media_id: "org:forms:schulabmeldung.pdf"       # Media (statt page_id)
access_level: "public"                         # oder "teacher_only"
content_type: "KNOWLEDGE"                      # aus Strategy-Routing
freshness_score: 0.7                           # Float 0.0-1.0
freshness_category: "recent"                   # fresh/recent/outdated/archived
chunking_method: "recursive_header"            # aus Strategy-Routing
last_modified: "2025-12-12T13:59:38"           # ISO-Timestamp
author: "r.raschhofer"                         # Letzter Editor
content_hash: "1ee152ee39..."                  # MD5 des Content-Body
links_to:                                      # Ausgehende Links
  - "page:id:1"
linked_from:                                   # Eingehende Backlinks
  - "page:id:2"
---
```

**Acceptance Criteria**:

1. **Given** eine verarbeitete Wiki-Seite, **When** sie exportiert wird, **Then** enthaelt das YAML-Frontmatter ALLE Pflichtfelder des Ziel-Schemas.
2. **Given** eine verarbeitete Media-Datei (PDF, DOCX, Image), **When** sie exportiert wird, **Then** ist die Dateiendung `.md` (nicht `.txt`) und das Frontmatter enthaelt dieselben Pflichtfelder wie Pages (mit `media_id` statt `page_id`).
3. **Given** das Feld hiesz bisher `modified_at`, **When** der Export laeuft, **Then** heisst es `last_modified`.
4. **Given** `page_backlinks/*.json` Dateien aus dem Fetch-Output, **When** der Export laeuft, **Then** wird das Feld `linked_from` mit den Backlink-Quellen befuellt.
5. **Given** der Content-Body einer Seite, **When** `content_hash` berechnet wird, **Then** ist es ein MD5-Hash des Markdown-Body (ohne Frontmatter).
6. **Given** der Embeddings Creator (`document_loader.py`) wird auf das Output-Verzeichnis gerichtet, **When** er `*.md` Dateien laedt, **Then** werden alle Pages und Media erfolgreich geladen und geparst.

**Referenz**: `research/techstack/qdrant/embeddings_creator/script/document_loader.py` (Frontmatter-Parsing, Feld-Extraktion)

---

### US4 -- Strategy-Integration (Priority: P1-Critical)

Als Pipeline-Betreiber will ich, dass die Preprocessing-Pipeline die `preprocessing_strategies.yaml`
aus Stage 2 (Deep Evaluation) korrekt konsumiert, damit Content-Type-Routing und Chunking-Methoden
durchgaengig funktionieren.

**Comparison-Referenz**: Part 3 Diskrepanz P2, Section X.2.3.2

**Acceptance Criteria**:

1. **Given** `preprocessing_strategies.yaml` existiert im Evaluation-Output, **When** die Preprocessing-Pipeline startet, **Then** wird die YAML-Datei geladen und fuer Routing verwendet (nicht `page_strategies.json`).
2. **Given** eine Seite ist in der Strategy als `knowledge_articles` kategorisiert, **When** sie verarbeitet wird, **Then** erhaelt sie `content_type: KNOWLEDGE` und `chunking_method: recursive_header`.
3. **Given** eine Seite ist als `ignored` kategorisiert, **When** sie verarbeitet wird, **Then** wird sie uebersprungen (kein Output).
4. **Given** ein Dokument (PDF) ist als `forms` kategorisiert, **When** es verarbeitet wird, **Then** erhaelt es `content_type: FORM` und `chunking_method: metadata_only`.
5. **Given** eine Seite existiert NICHT in der Strategy-Datei, **When** sie verarbeitet wird, **Then** erhaelt sie einen sinnvollen Default (`content_type: KNOWLEDGE`, `chunking_method: semantic`).

**Betroffene Dateien**: `pipeline/03_rag_preprocessing/strategy_loader.py` (Komplett-Umbau)

---

### US5 -- Freshness-Scoring (Priority: P1-Critical)

Als Pipeline-Betreiber will ich korrekte Aktualitaets-Scores pro Dokument, damit das Ranking
in Qdrant frische Inhalte bevorzugt, ohne alte Inhalte komplett zu verlieren.

**Comparison-Referenz**: Part 3 Diskrepanzen P5, P14, Section X.2.3.3

**Hybrid-Formel** (aggressiv fuer Neu, sanft fuer Alt):

```sketch
Alter <   30 Tage:  Score 1.00, Kategorie "fresh"
Alter <   90 Tage:  Score 0.85, Kategorie "fresh"
Alter <  180 Tage:  Score 0.70, Kategorie "recent"
Alter <  365 Tage:  Score 0.55, Kategorie "recent"
Alter <  730 Tage:  Score 0.35, Kategorie "outdated"
Alter >= 730 Tage:  Score 0.20, Kategorie "archived"
```

**Acceptance Criteria**:

1. **Given** eine Seite mit `last_modified: 2026-01-20` (26 Tage alt), **When** Freshness berechnet wird, **Then** ist `freshness_score: 1.0` und `freshness_category: "fresh"`.
2. **Given** eine Seite mit `last_modified: 2024-05-10` (~650 Tage alt), **When** Freshness berechnet wird, **Then** ist `freshness_score: 0.35` und `freshness_category: "outdated"`.
3. **Given** eine Seite mit `last_modified: 2022-01-01` (~1500 Tage alt), **When** Freshness berechnet wird, **Then** ist `freshness_score: 0.2` und `freshness_category: "archived"`.
4. **Given** verschiedene Seiten mit unterschiedlichen `last_modified` Timestamps, **When** alle verarbeitet werden, **Then** haben sie unterschiedliche Freshness-Scores (nicht alle denselben Wert).

**Betroffene Dateien**: `pipeline/03_rag_preprocessing/metadata_enricher.py`

---

### US6 -- Vision-LLM Bild-Captioning (Priority: P1-Critical)

Als Pipeline-Betreiber will ich, dass informative Bilder durch ein Vision-LLM beschrieben und
als durchsuchbare Dokumente in Qdrant indexiert werden, damit Bild-Wissen im RAG verfuegbar ist.

**Comparison-Referenz**: Part 3 Diskrepanz P11, Section X.2.3.4

**Acceptance Criteria**:

1. **Given** die `preprocessing_strategies.yaml` kategorisiert ein Bild als `informative_images`, **When** die Preprocessing-Pipeline laeuft, **Then** wird das Bild an Qwen2.5-VL (via LMStudio, `http://192.168.8.3:1234/v1`) gesendet und eine Beschreibung generiert.
2. **Given** ein informatives Bild wurde beschrieben, **When** es exportiert wird, **Then** ist das Output eine `.md` Datei mit YAML-Frontmatter (identisches Schema wie Pages/Media) und der generierten Beschreibung als Markdown-Body.
3. **Given** die Strategy kategorisiert ein Bild als `decorative`, **When** die Pipeline laeuft, **Then** wird das Bild uebersprungen (kein Output, kein LLM-Call).
4. **Given** LMStudio ist nicht erreichbar, **When** ein Bild verarbeitet werden soll, **Then** wird der Fehler geloggt und die Pipeline faehrt mit dem naechsten Item fort (kein Gesamtabbruch).
5. **Given** ~170 informative Bilder, **When** alle verarbeitet werden, **Then** entstehen ~170 zusaetzliche `.md` Dateien im Output.

**Technische Randbedingung**: LMStudio muss mit geladenem Qwen2.5-VL Modell laufen.
Endpoint identisch zu Stage 2 Deep Evaluation. Deutscher Prompt fuer Beschreibungen.

**Betroffene Dateien**: `pipeline/03_rag_preprocessing/media_processor.py` oder neues `image_captioner.py`

---

### US7 -- PDF-Qualitaet (Priority: P2-High)

Als Pipeline-Betreiber will ich sauberen Text aus PDF-Dateien, damit die Chunk-Qualitaet
und somit die Retrieval-Qualitaet maximiert wird.

**Comparison-Referenz**: Part 3 Diskrepanz P9, Section X.2.3.5

**Acceptance Criteria**:

1. **Given** ein PDF mit Layout-bedingten Spaced Characters ("H T B L A  L e o n d i n g"), **When** der Text extrahiert wird, **Then** werden die Spaces korrigiert zu "HTBLA Leonding".
2. **Given** ein PDF mit Layout-bedingten kurzen Zeilen (< 40 Zeichen, z.B. PDF-Spaltenumbrueche), **When** der Text verarbeitet wird, **Then** werden aufeinanderfolgende kurze Zeilen zu Absaetzen zusammengefuehrt (`merge_short_lines()`).
3. **Given** ein PDF-Absatz der ueber eine Satzgrenze geht, **When** Paragraph-Merging laeuft, **Then** wird an der Satzgrenze korrekt getrennt (nicht mitten im Satz zusammengefuehrt).
4. **Given** eine Liste oder Ueberschrift im PDF, **When** Paragraph-Merging laeuft, **Then** werden Listen-Items und Ueberschriften NICHT mit dem vorherigen Absatz zusammengefuehrt.

**Betroffene Dateien**: `pipeline/03_rag_preprocessing/media_processor.py`

---

### US8 -- Preprocessing Evaluation (Priority: P1-Critical)

Als Pipeline-Betreiber will ich die Qualitaet der Preprocessing-Transformation messen koennen,
damit ich quantitative Evidenz fuer die Thesis habe und Regressionen erkenne.

**Comparison-Referenz**: Part 3 Diskrepanz P1, Section X.2.3.6

**7-Metrik-Suite**:

| #   | Metrik                  | Misst                                                                     | Schwellwert              |
| --- | ----------------------- | ------------------------------------------------------------------------- | ------------------------ |
| 1   | Content Completeness    | Zeichenverhaeltnis Original vs Output (adjustiert fuer Markup-Entfernung) | >= 0.85                  |
| 2   | Semantic Similarity     | Embedding-Cosine-Similarity (`paraphrase-multilingual-mpnet-base-v2`)     | >= 0.85                  |
| 3   | Key Entity Preservation | Erhalt von Daten, Raeumen, Emails, URLs (Regex-basiert)                   | >= 0.95                  |
| 4   | Link Integrity          | DokuWiki-Link-Transformation korrekt (Text + Target erhalten)             | >= 0.95                  |
| 5   | Noise Detection         | Wiki-Syntax-Reste, Mojibake, HTML-Artefakte im Output                     | <= 2% Noise              |
| 6   | Readability             | German-adapted Flesch Reading Ease                                        | >= 20 (technische Texte) |
| 7   | Structure Preservation  | Ueberschriften, Listen, Absaetze erhalten                                 | >= 0.90                  |

**Acceptance Criteria**:

1. **Given** Original-Dateien in `data/fetched/` und Output in `data/preprocessed/`, **When** `python run_eval_preprocessing.py` ausgefuehrt wird, **Then** werden alle 7 Metriken pro Dokument berechnet.
2. **Given** eine Evaluation laeuft, **When** sie abgeschlossen ist, **Then** wird ein JSON-Report mit per-Dokument-Ergebnissen und Aggregat-Summary erzeugt.
3. **Given** die Aggregat-Summary, **When** Content Completeness, Entity Preservation und Link Integrity geprueft werden, **Then** sind alle drei >= 95% Pass-Rate.
4. **Given** die Readability-Metrik, **When** sie auf deutschsprachige technische Dokumente angewendet wird, **Then** ist ein Schwellwert von 20 (Flesch) konfiguriert (nicht der englische Default von 60).
5. **Given** ein Regressions-Test, **When** eine Code-Aenderung die Content-Completeness unter 90% drueckt, **Then** schlaegt der Test fehl.

**Schwellwert-Definitionen** (3 Ebenen):

| Ebene                | Beschreibung                                                    | Wert                                                                                                                               | Beispiel                                                              |
| -------------------- | --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| Per-Dokument         | Minimum-Score pro einzelnem Dokument                            | >= 0.85 (Content Completeness), >= 0.85 (Semantic Sim.), >= 0.95 (Entity/Link), <= 2% (Noise), >= 20 (Flesch), >= 0.90 (Structure) | Ein Dokument mit Content Completeness 0.82 gilt als "nicht bestanden" |
| Aggregat Pass-Rate   | Anteil der Dokumente die den Per-Dokument-Schwellwert erreichen | >= 95%                                                                                                                             | 190 von 200 Dokumenten bestehen = 95% Pass-Rate                       |
| Regressions-Schwelle | Aggregat Pass-Rate unter der ein CI-Test fehlschlaegt           | < 90%                                                                                                                              | Wenn Pass-Rate auf 88% faellt, schlaegt pytest fehl                   |

**Betroffene Dateien**: Neues Unterverzeichnis `pipeline/03_rag_preprocessing/evaluation/`

---

### US9 -- Architektur-Cleanup (Priority: P3-Medium)

Als Entwickler will ich einen einzigen Entry Point pro Pipeline-Modul und keine duplizierte
Logik, damit der Code wartbar bleibt.

**Comparison-Referenz**: Part 3 Diskrepanzen P8, P10, Section X.2.3.7

**Acceptance Criteria**:

1. **Given** `pipeline/03_rag_preprocessing/` hat zwei Entry Points (`run_preprocessing.py` + `main.py`), **When** konsolidiert wird, **Then** gibt es genau einen Entry Point (`run_preprocessing.py`).
2. **Given** Media-Extraktionslogik existiert in `media_processor.py` UND `main.py`, **When** konsolidiert wird, **Then** ist alle Media-Logik ausschliesslich in `media_processor.py`.
3. **Given** der Embeddings Creator erwartet auch DOCX, XLSX, PPTX im Output, **When** die Media-Discovery erweitert wird, **Then** werden alle unterstuetzten Formate (PDF, DOCX, XLSX, PPTX, PNG, JPG) entdeckt und verarbeitet.
4. **Given** `pipeline/01_wiki_fetcher/` erstellt einen leeren `media_metadata/` Ordner, **When** der Bugfix angewendet wird, **Then** wird der Ordner nicht mehr erstellt.

**Betroffene Dateien**:
- `pipeline/03_rag_preprocessing/run_preprocessing.py`, `main.py` (Konsolidierung)
- `pipeline/03_rag_preprocessing/media_processor.py` (Media-Discovery)
- `pipeline/01_wiki_fetcher/fetch_full_wiki_extended.py` (media_metadata Bugfix)

---

## Nicht-Funktionale Anforderungen

| ID      | Anforderung            | Beschreibung                                                                             |
| ------- | ---------------------- | ---------------------------------------------------------------------------------------- |
| NFR-001 | Python 3.11+           | Type Hints, `from __future__ import annotations`, PEP 8                                  |
| NFR-002 | TDD                    | Tests VOR oder GLEICHZEITIG mit Implementation                                           |
| NFR-003 | Constitution v1.4.0    | Article VIII (Direct SDK), Article VI (Secrets in .token), Article X (Execution Mandate) |
| NFR-004 | YAML Config            | Alle Konfiguration in `env.yaml`, Secrets in `.token`-Dateien                            |
| NFR-005 | Reproduzierbarkeit     | Alle Ergebnisse enthalten: Timestamp, Config-Hash, Code-Version                          |
| NFR-006 | Fehlertoleranz         | Pipeline-Schritte loggen Fehler und fahren mit naechstem Item fort                       |
| NFR-007 | Qdrant-Kompatibilitaet | Output-Schema muss exakt dem `document_loader.py` Frontmatter-Parsing entsprechen        |

---

## Abhaengigkeiten und Risiken

| Risiko                                 | Wahrscheinlichkeit | Impact   | Mitigation                                                        |
| -------------------------------------- | ------------------ | -------- | ----------------------------------------------------------------- |
| LMStudio nicht erreichbar (Vision-LLM) | Mittel             | Hoch     | Graceful Skip: Bilder ohne Captioning exportieren, Warning loggen |
| Tesseract OCR-Qualitaet bei Scans      | Mittel             | Niedrig  | OCR als Supplement, Spaced-Char-Korrektur als Post-Processing     |
| Strategy-YAML Format aendert sich      | Niedrig            | Hoch     | Schema-Validierung beim Laden, Fallback auf Defaults              |
| Embeddings Creator Schema aendert sich | Niedrig            | Kritisch | End-to-End-Test: Pipeline-Output -> DocumentLoader -> Chunks      |

---

## Scope-Abgrenzung

**IN Scope:**
- CLI UX Portierung (`pipeline/shared/cli_utils.py` + 7 Skripte)
- Deep Evaluation Bugfixes (rglob-Dedup, YAML-Dedup, temperature)
- Preprocessing Schema-Alignment (Qdrant-Kompatibilitaet)
- Strategy-Integration (`preprocessing_strategies.yaml`)
- Freshness-Scoring (Hybrid-Formel)
- Vision-LLM Bild-Captioning (Qwen2.5-VL)
- PDF-Qualitaet (Spaced-Chars, Paragraph-Merging)
- Preprocessing Evaluation (7-Metrik-Suite)
- Architektur-Cleanup (Entry Points, media_metadata)

**OUT of Scope:**
- MCP-Server (Imres Teil)
- Stage 4: Embeddings Creator (bereits funktionsfaehig)
- Stage 5: Qdrant Deploy (bereits funktionsfaehig)
- RAGAS-Integration (bleibt in 008)
- Statistische Analyse (bleibt in 008)
- Visualisierungen (bleibt in 008)
- RAGFlow-Integration (entfaellt, nur Qdrant)
- Docker-Compose-Aenderungen

---

## Implementierungs-Reihenfolge (empfohlen)

```sketch
Phase 1: US3 (Schema-Alignment)         <- BLOCKER, zuerst
Phase 2: US4 (Strategy-Integration)     <- davon haengt Routing ab
Phase 3: US5 (Freshness-Scoring)        <- schneller Fix
Phase 4: US7 (PDF-Qualitaet)            <- Spaced-Chars + Merging
Phase 5: US6 (Vision-LLM)               <- braucht LMStudio
Phase 6: US9 (Architektur-Cleanup)      <- Konsolidierung
Phase 7: US8 (Preprocessing Evaluation) <- Qualitaet messen
Phase 8: US2 (Deep Eval Bugfixes)       <- Parallel moeglich
Phase 9: US1 (CLI UX)                   <- Parallel moeglich
```

Phasen 8 und 9 koennen parallel zu Phasen 1-7 bearbeitet werden, da sie andere Module betreffen.
