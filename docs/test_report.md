# Test Report — dev_dito

| | |
|---|---|
| **Projekt** | dev_dito – Wiki-Embedding-Pipeline & Service-Gateway |
| **Branch** | `009-analysis-and-production-polish` |
| **Datum** | 2026-03-19 |
| **Python** | 3.13.7 |
| **pytest** | 8.4.2 |
| **Gesamtergebnis** | **394 bestanden · 0 fehlgeschlagen · 2 übersprungen** |

---

## 1. Testspezifikation

Jeder Testfall beschreibt eine prüfbare Anforderung aus den User Stories oder der Systemarchitektur.
Ein Testfall besteht aus nummerierten Schritten mit dem jeweiligen erwarteten Ergebnis.

---

### Infrastruktur

---

#### TC-INF-01: Docker Compose – Syntaxvalidität

**Bezug:** Docker-Infrastruktur · Constitution Art. III

| # | Schritt | Erwartetes Ergebnis |
|---|---|---|
| 1 | `docker-compose.yml` im Repo-Root öffnen und als YAML parsen | Datei existiert, gültiges YAML ohne Parse-Fehler |
| 2 | `services`-Schlüssel und Projektname prüfen | `name: "stack-g-devdito"` und `services`-Sektion vorhanden |
| 3 | Alle referenzierten Dockerfiles auf Existenz prüfen | Alle Dockerfile-Pfade existieren auf Disk |
| 4 | Netzwerkkonfiguration prüfen | `leonidas-network` definiert und als `external: true` markiert |

---

#### TC-INF-02: Keine hartcodierten Secrets

**Bezug:** Constitution Art. VI (Secret Containment)

| # | Schritt | Erwartetes Ergebnis |
|---|---|---|
| 1 | `docker-compose.yml` nach Secret-Mustern (API-Keys, Passwörter, Tokens) durchsuchen | Keine Treffer |
| 2 | Alle Dockerfiles nach denselben Secret-Mustern durchsuchen | Keine Treffer |

---

#### TC-INF-03: Pflicht-Services vorhanden

**Bezug:** Docker-Infrastruktur

| # | Schritt | Erwartetes Ergebnis |
|---|---|---|
| 1 | Services-Liste aus `docker-compose.yml` lesen | Services-Dict vorhanden |
| 2 | Prüfen ob `orchestrator` in der Liste enthalten ist | Service vorhanden |
| 3 | Prüfen ob `qdrant` in der Liste enthalten ist | Service vorhanden |
| 4 | Jeden Service auf `container_name`-Feld prüfen | Alle Services haben `container_name` |

---

### Konfiguration

---

#### TC-CFG-01: YAML-Konfiguration mit Placeholder-Auflösung

**Bezug:** Constitution Art. II-B (Centralized YAML Configuration)

| # | Schritt | Erwartetes Ergebnis |
|---|---|---|
| 1 | YAML-Datei mit gültigem APP-Abschnitt laden | Dict mit `APP.name` und `APP.version` zurückgegeben |
| 2 | Config-Dict mit `${root_dir}`-Placeholder erstellen | Placeholder vor Auflösung sichtbar |
| 3 | `resolve_placeholders()` aufrufen | `${root_dir}` durch tatsächlichen Pfad ersetzt |
| 4 | Drei verschachtelte Placeholder auflösen (root → config → secrets) | Alle drei Ebenen korrekt aufgelöst |
| 5 | Nicht auflösbaren Placeholder übergeben | Placeholder bleibt unverändert erhalten |

---

#### TC-CFG-02: Konfigurationshash (NFR-005)

**Bezug:** NFR-005 – Reproduzierbarkeit von Experimenten

| # | Schritt | Erwartetes Ergebnis |
|---|---|---|
| 1 | Config-Dict erstellen und `compute_config_hash()` aufrufen | SHA-256-Hash zurückgegeben |
| 2 | Gleichen Dict erneut hashen | Identischer Hash (deterministisch) |
| 3 | `_meta`-Feld (z. B. Zeitstempel) hinzufügen und erneut hashen | Hash identisch — Meta-Daten ausgeschlossen |
| 4 | Config-Wert ändern und erneut hashen | Anderer Hash |

---

### Orchestrator

---

#### TC-ORC-01: Pipeline-Stufenstruktur (FR-013)

**Bezug:** FR-013 – Unified Stage Dictionary

| # | Schritt | Erwartetes Ergebnis |
|---|---|---|
| 1 | `PIPELINE_STAGES`-Konstante aus `server.py` importieren | Dict mit genau 5 Einträgen |
| 2 | Keys der Stages prüfen | `[fetch, evaluate, preprocess, embed, deploy]` in dieser Reihenfolge |
| 3 | Jede Stage auf Pflichtfelder prüfen | Alle haben `name`, `container`, `pipeline_dir` |
| 4 | `embed`-Stage auf `needs_openai_key` prüfen | `True`; alle anderen Stages: `False` |

---

#### TC-ORC-02: Gleichzeitige Jobs abweisen (FR-004)

**Bezug:** FR-004 – Concurrent Job Rejection (HTTP 409)

| # | Schritt | Erwartetes Ergebnis |
|---|---|---|
| 1 | `pipeline_runs.json` mit einem laufenden Job (`status='running'`) simulieren | Testdaten bereit |
| 2 | `get_active_job()` aufrufen | Gibt den laufenden Job zurück |
| 3 | Alle Jobs auf `status='success'` setzen | Keine laufenden Jobs mehr |
| 4 | `get_active_job()` erneut aufrufen | Gibt `None` zurück |

---

### US1 – CLI UX

---

#### TC-US1-01: Hilfe-Banner der CLI

**Bezug:** US1 – CLI UX · pipeline/shared/cli_utils.py

| # | Schritt | Erwartetes Ergebnis |
|---|---|---|
| 1 | `run_preprocessing.py --help` ausführen | Programm startet ohne Absturz |
| 2 | Exit-Code prüfen | `SystemExit(0)` |
| 3 | Ausgabe auf vollständigen Hilfe-Inhalt prüfen | Abschnitte What / Usage / Parameters / Options / Examples vorhanden |
| 4 | `print_help_banner()` mit nur `what`-Parameter aufrufen | Nur What-Abschnitt ausgegeben, andere weggelassen |

---

#### TC-US1-02: SIGINT-Signalbehandlung (Ctrl+C)

**Bezug:** US1 – CLI UX · cli_utils.create_sigint_handler

| # | Schritt | Erwartetes Ergebnis |
|---|---|---|
| 1 | SIGINT-Handler mit optionalem Callback registrieren | Handler registriert |
| 2 | SIGINT-Signal auslösen | Callback einmal aufgerufen |
| 3 | Exit-Code prüfen | `SystemExit(130)` |
| 4 | Stderr auf Abbruch-Banner prüfen | `"ABGEBROCHEN"` in Ausgabe |

---

### US2 – Deep Evaluation Bugfixes

---

#### TC-US2-01: Datei-Deduplizierung bei rglob

**Bezug:** US2 – Bug: Duplikate bei gemischter Groß-/Kleinschreibung

| # | Schritt | Erwartetes Ergebnis |
|---|---|---|
| 1 | Verzeichnis mit `dokument.pdf` und `DOKUMENT.PDF` anlegen | Verzeichnis bereit |
| 2 | `analyze_documents()` aufrufen | Funktion läuft durch |
| 3 | Ergebnisliste auf Duplikate prüfen | Jede Datei nur einmal in der Liste |

---

#### TC-US2-02: Temperature-Passthrough zum LLM

**Bezug:** US2 – Bug: Temperature aus env.yaml erreicht LLM nicht

| # | Schritt | Erwartetes Ergebnis |
|---|---|---|
| 1 | `env.yaml` laden und `LLM.generation.temperature` auslesen | Wert = 0.0 |
| 2 | `LLMClient` mit dieser Config initialisieren | Client erstellt |
| 3 | `gen_params` des Clients prüfen | `temperature == 0.0` |

---

### US3 – Schema Alignment

---

#### TC-US3-01: JSON-Schema-Validierung Pipeline Runs

**Bezug:** US3 – Constitution Art. II (JSON Interface Standard)

| # | Schritt | Erwartetes Ergebnis |
|---|---|---|
| 1 | `data/logs/pipeline_runs.schema.json` laden | Valides JSON-Schema, `type == 'array'` |
| 2 | Pflichtfelder-Liste prüfen | `job_id`, `stage`, `status`, `started_at` vorhanden |
| 3 | Stage-Enum prüfen | Alle 5 Stages enthalten: `fetch`, `evaluate`, `preprocess`, `embed`, `deploy` |
| 4 | Sample-Daten gegen Schema validieren | Validierung erfolgreich |
| 5 | Daten ohne `job_id` validieren | `ValidationError` ausgelöst |
| 6 | Ungültigen Stage-Wert `"invalid_stage"` validieren | `ValidationError` ausgelöst |

---

#### TC-US3-02: Frontmatter-Schema E2E-Roundtrip

**Bezug:** US3 – T005 · Qdrant-Schema-Compliance

| # | Schritt |Erwartetes Ergebnis |
|---|---|---|
| 1 | Sample-Seite mit vollständigen Metadaten durch `Exporter.export()` verarbeiten | Markdown-Datei mit YAML-Frontmatter erstellt |
| 2 | Exportierte Datei mit `DocumentLoader` laden | Datei gelesen ohne Fehler |
| 3 | Alle 14 Pflichtfelder im Frontmatter prüfen | Alle vorhanden und korrekt typisiert |
| 4 | `content_hash` gegen MD5 des Body-Textes prüfen | Hash stimmt überein (32 Hex-Zeichen) |
| 5 | Media-Datei exportieren und auf `media_id`-Feld prüfen | `media_id` vorhanden, kein `page_id` |

---

### US4 – Strategy Integration

---

#### TC-US4-01: Strategy Loader – YAML laden

**Bezug:** US4 – T064/T013 · StrategyLoader

| # | Schritt | Erwartetes Ergebnis |
|---|---|---|
| 1 | `preprocessing_strategies.yaml` in tmp-Verzeichnis erstellen | Datei vorhanden |
| 2 | `StrategyLoader().load(dir)` aufrufen | Strategien geladen ohne Fehler |
| 3 | `get_strategy("departm:electronics")` aufrufen | `ContentType.KNOWLEDGE`, `chunking="recursive_header"` |
| 4 | `get_strategy("start")` aufrufen | `ContentType.PORTAL`, `chunking="parent_context"` |
| 5 | `is_ignored("abotest20210218")` aufrufen | `True` |
| 6 | `get_strategy("nonexistent:page")` aufrufen | Default: KNOWLEDGE, semantic, process |

---

#### TC-US4-02: Content-Type-Routing

**Bezug:** US4 – T076 · PageProcessor.process_with_strategy

| # | Schritt | Erwartetes Ergebnis |
|---|---|---|
| 1 | Seite mit `PageStrategy(content_type=KNOWLEDGE)` verarbeiten | `result["content_type"] == "knowledge"` |
| 2 | Seite mit `NEWS`-Typ verarbeiten | `result["content_type"] == "news"` |
| 3 | Seite mit `ARCHIVED`-Typ verarbeiten | `result["priority"] == "low"` |

---

### US5 – Freshness-Scoring

---

#### TC-US5-01: Freshness-Score-Berechnung

**Bezug:** US5 – T017/T077 · MetadataEnricher

| # | Schritt | Erwartetes Ergebnis |
|---|---|---|
| 1 | Datum von vor 26 Tagen übergeben | `score=1.0`, `category="fresh"` |
| 2 | Datum von vor 300 Tagen übergeben | `score=0.85`, `category="fresh"` |
| 3 | Datum von vor 650 Tagen übergeben | `score=0.70`, `category="recent"` |
| 4 | Datum von vor 800 Tagen übergeben | `score=0.50`, `category="outdated"` |
| 5 | Namespace `"archive:..."` mit beliebigem Datum übergeben | `score=0.20`, `category="archived"` |
| 6 | Ungültiges Datum übergeben | `score=0.5`, `category="unknown"` |

---

### US6 – Vision-LLM Bildunterschriften

---

#### TC-US6-01: Bildunterschriftsgenerierung

**Bezug:** US6 – T026 · ImageCaptioner

| # | Schritt | Erwartetes Ergebnis |
|---|---|---|
| 1 | `ImageCaptioner` mit gemocktem API-Client initialisieren | Objekt erstellt |
| 2 | `caption(png_file)` mit gültigem Bild und gemockter LLM-Antwort aufrufen | Nicht-leerer Beschreibungsstring |
| 3 | `caption()` mit nicht-existentem Pfad aufrufen | `""` zurückgegeben, kein Absturz |
| 4 | `CAPTIONABLE_EXTENSIONS` auf `.png`, `.jpg`, `.jpeg` prüfen | Alle enthalten |
| 5 | `CAPTIONABLE_EXTENSIONS` auf `.pdf` prüfen | Nicht enthalten |

---

### US7 – PDF-Qualität

---

#### TC-US7-01: PDF-Textbereinigung

**Bezug:** US7 – T021 · MediaProcessor._fix_spaced_characters / _merge_short_lines

| # | Schritt | Erwartetes Ergebnis |
|---|---|---|
| 1 | `_fix_spaced_characters("H T B L A  L e o n d i n g")` aufrufen | `"HTBLA Leonding"` |
| 2 | Normalen Text durch `_fix_spaced_characters()` laufen lassen | Text unverändert |
| 3 | Mehrere kurze Zeilen (<40 Zeichen) durch `_merge_short_lines()` laufen lassen | Zeilen zusammengeführt |
| 4 | Markdown-Überschriften (`# ...`) durch `_merge_short_lines()` laufen lassen | Überschriften getrennt erhalten |
| 5 | `clean_pdf_text()` mit Spaced-Chars und kurzen Zeilen aufrufen | Beide Operationen angewendet |

---

### US8 – Preprocessing-Evaluierung

---

#### TC-US8-01: 7-Metrik-Qualitätssuite

**Bezug:** US8 – T037 · DocumentScore / 7 Metriken

| # | Schritt | Erwartetes Ergebnis |
|---|---|---|
| 1 | Gleichen Text als Original und Verarbeitung übergeben | `content_completeness ≈ 1.0` |
| 2 | DokuWiki-Link `[[start|Startseite]]` durch `LinkIntegrityMetric` prüfen | Score >= 0.90 |
| 3 | Sauberes Markdown durch `NoiseDetectionMetric` prüfen | Score <= 0.02 |
| 4 | Wiki-Syntax-Reste durch `NoiseDetectionMetric` prüfen | Score > 0.02 |
| 5 | `DocumentScore` mit allen Werten über Threshold erstellen | `passes_thresholds() = True` |
| 6 | `content_completeness = 0.50` setzen | `passes_thresholds() = False` |

---

#### TC-US8-02: Regressionsprüfung Preprocessing-Qualität

**Bezug:** US8 – T037 · check_regression()

| # | Schritt | Erwartetes Ergebnis |
|---|---|---|
| 1 | 100 Dokumente simulieren, davon 15 mit `content_completeness < 0.85` | Testdaten bereit |
| 2 | `check_regression()` aufrufen | Ergebnis-Dict zurückgegeben |
| 3 | `check_regression()["content_completeness"]["pass"]` prüfen | `False` (< 90% bestehen) |
| 4 | Alle Dokumente über Threshold setzen und erneut prüfen | `True` |

---

### US9 – Architektur-Cleanup

---

#### TC-US9-01: Einzelner Einstiegspunkt

**Bezug:** US9 – T031 · run_preprocessing.py

| # | Schritt | Erwartetes Ergebnis |
|---|---|---|
| 1 | Preprocessing-Modul-Verzeichnis auf `main.py` scannen | Datei existiert **nicht** |
| 2 | `run_preprocessing.py` auf Existenz prüfen | Existiert |
| 3 | `run_preprocessing.main()` auf Aufrufbarkeit prüfen | `callable(main) = True` |
| 4 | `run_preprocessing.run()` auf Aufrufbarkeit prüfen | `callable(run) = True` |

---

### Evaluierungsinfrastruktur

---

#### TC-MET-01: MRR-Berechnung (Forschungsfrage FF3)

**Bezug:** Constitution Art. III – Critical-Path Metrics

| # | Schritt | Erwartetes Ergebnis |
|---|---|---|
| 1 | `reciprocal_rank(["a","b","c"], {"a"})` aufrufen | 1.0 |
| 2 | `reciprocal_rank(["a","b","c"], {"b"})` aufrufen | 0.5 |
| 3 | `reciprocal_rank(["a","b","c"], {"c"})` aufrufen | ≈ 0.333 |
| 4 | `mean_reciprocal_rank()` mit 3 Queries (RR: 1.0, 0.5, 1/3) aufrufen | ≈ 0.6111 |
| 5 | `mean_reciprocal_rank([])` aufrufen | 0.0 |

---

#### TC-MET-02: NDCG@k-Berechnung

**Bezug:** Constitution Art. III – Critical-Path Metrics

| # | Schritt | Erwartetes Ergebnis |
|---|---|---|
| 1 | Ideal-geordnete Relevanzliste übergeben | NDCG = 1.0 |
| 2 | Händisch berechnetes Beispiel aus IR-Lehrbuch übergeben | ≈ 0.972 |
| 3 | Leere Relevanzmenge übergeben | 0.0 |
| 4 | Gleiche relevante Seite an Rang 1, 2 und 3 testen | NDCG(Rang1) > NDCG(Rang2) > NDCG(Rang3) |

---

#### TC-EVA-01: Modellvergleich-Pipeline E2E (gemockt)

**Bezug:** FF3 · eval_model_comparison.py

| # | Schritt | Erwartetes Ergebnis |
|---|---|---|
| 1 | Corpus aus gemocktem `fetched_at_*`-Verzeichnis laden | Chunks geladen, Page-ID korrekt (Unterstrich → Doppelpunkt) |
| 2 | `run_model_evaluation()` mit gemocktem Qdrant und Embedding-Provider aufrufen | Läuft ohne Netzwerkzugriff durch |
| 3 | MRR im Ergebnis prüfen | MRR = 1.0 (Mock gibt richtiges Dokument zurück) |
| 4 | NFR-005-Felder im Ergebnis prüfen | `timestamp`, `config_hash`, `code_version` vorhanden |
| 5 | Fehlerfall simulieren (Qdrant schlägt fehl) | `delete_collection` wird trotzdem aufgerufen (Cleanup) |

---

#### TC-EVA-02: Keyword-Baseline (Forschungsfrage FF1)

**Bezug:** FF1 · eval_keyword_baseline.py

| # | Schritt | Erwartetes Ergebnis |
|---|---|---|
| 1 | `source_file="exams_matura-tagesschule-if-it.txt"` in Page-ID umwandeln | `exams:matura-tagesschule-if-it` |
| 2 | `source_file="archive_exams_semesterpruefungen.txt"` umwandeln | `archive:exams:semesterpruefungen` |
| 3 | `run_keyword_baseline()` mit Mock-API (gibt erwartete Seite zurück) aufrufen | MRR = 1.0, P@5 = 0.2 |
| 4 | NFR-005-Felder im Ergebnis prüfen | `timestamp`, `config_hash`, `code_version` vorhanden |

---

#### TC-RAG-01: RAGAS-Evaluator

**Bezug:** T029/T030/T031 · RAGASEvaluator

| # | Schritt | Erwartetes Ergebnis |
|---|---|---|
| 1 | `RAGASEvaluator(llm_base_url, model)` mit gemocktem `ChatOpenAI` instanziieren | Objekt erstellt, Attribute gesetzt |
| 2 | `ChatOpenAI`-Aufruf auf `temperature=0.0` prüfen | Temperature korrekt gesetzt |
| 3 | `evaluate([...])` mit gemocktem `_run_ragas_evaluate` aufrufen | Dict mit Metrik-Scores zurückgegeben |
| 4 | `evaluate([])` mit leerer Liste aufrufen | Leerer Dict zurückgegeben |

---

### Embeddings & Deployment

---

#### TC-EMB-01: Content-Aware Chunking

**Bezug:** pipeline/04_embeddings_creator · ContentAwareChunker

| # | Schritt | Erwartetes Ergebnis |
|---|---|---|
| 1 | Dokument mit `content_type="EMPTY"` übergeben | Leere Chunk-Liste zurückgegeben |
| 2 | Dokument mit `content_type="KNOWLEDGE"` und 600 Zeichen bei `max_chunk_size=512` übergeben | Mehrere Chunks |
| 3 | Jeden Chunk auf Pflichtattribute prüfen | `chunk_id`, `text`, `chunk_index`, `total_chunks` vorhanden |
| 4 | `chunk_id` für ersten Chunk prüfen | Format: `"pages_my_page_0"` |
| 5 | Mix aus KNOWLEDGE- und EMPTY-Dokumenten durch `chunk_all()` laufen lassen | EMPTY übersprungen, KNOWLEDGE behalten |

---

#### TC-EMB-02: Embedding-Ausgabeformat (MCP-Schema)

**Bezug:** pipeline/04_embeddings_creator · MCP Payload Schema

| # | Schritt | Erwartetes Ergebnis |
|---|---|---|
| 1 | Embedding-Record aufbauen | Dict mit `id`, `text`, `embedding`, `metadata` |
| 2 | Embedding-Dimension prüfen | 3072 |
| 3 | Metadata auf MCP-Pflichtfelder prüfen | `text`, `source`, `collection`, `access_level`, `chunk_index`, `total_chunks` |

---

#### TC-DEP-01: Direktupload zu Qdrant

**Bezug:** T082 · QdrantDeployer

| # | Schritt | Erwartetes Ergebnis |
|---|---|---|
| 1 | JSONL-Datei mit 5 Vektorpunkten erstellen | Datei vorhanden |
| 2 | `QdrantDeployer.deploy_direct()` mit gemocktem Qdrant-Client aufrufen | Läuft durch |
| 3 | Rückgabewert prüfen | 5 (Anzahl hochgeladener Punkte) |
| 4 | `deploy_direct()` mit leerer JSONL-Datei aufrufen | 0 |

---

#### TC-DEP-02: Dry-Run-Modus

**Bezug:** T085 · QdrantDeployer – Validierung ohne Upload

| # | Schritt | Erwartetes Ergebnis |
|---|---|---|
| 1 | `QdrantDeployer.deploy_direct(dry_run=True)` aufrufen | Läuft durch ohne Netzwerkzugriff |
| 2 | Anzahl valider Punkte im Rückgabewert prüfen | Korrekte Zahl zurückgegeben |
| 3 | Prüfen ob `upsert()` aufgerufen wurde | `upsert()` wurde **nicht** aufgerufen |

---

## 2. Testprotokoll

Testlauf vom **2026-03-19** · Ausführungsumgebung: Windows 11, Python 3.13.7, pytest 8.4.2

| TC-ID | Beschreibung | Ergebnis | Kommentar |
|---|---|:---:|---|
| TC-INF-01 | Docker Compose Syntaxvalidität | bestanden | |
| TC-INF-02 | Keine hartcodierten Secrets | bestanden | |
| TC-INF-03 | Pflicht-Services vorhanden | bestanden | |
| TC-CFG-01 | YAML-Konfiguration mit Placeholder-Auflösung | bestanden | |
| TC-CFG-02 | Konfigurationshash (NFR-005) | bestanden | |
| TC-ORC-01 | Pipeline-Stufenstruktur | bestanden | |
| TC-ORC-02 | Gleichzeitige Jobs abweisen | bestanden | |
| TC-US1-01 | CLI Hilfe-Banner | bestanden | |
| TC-US1-02 | SIGINT-Signalbehandlung | bestanden | |
| TC-US2-01 | Datei-Deduplizierung bei rglob | bestanden | |
| TC-US2-02 | Temperature-Passthrough zum LLM | bestanden | |
| TC-US3-01 | JSON-Schema-Validierung Pipeline Runs | bestanden | Zuvor fehlgeschlagen: `preprocess` fehlte im erwarteten Enum-Set — behoben |
| TC-US3-02 | Frontmatter-Schema E2E-Roundtrip | bestanden | |
| TC-US4-01 | Strategy Loader YAML | bestanden | Zuvor fehlgeschlagen: `TABLE_DATA` fehlte im erwarteten ContentType-Set — behoben |
| TC-US4-02 | Content-Type-Routing | bestanden | |
| TC-US5-01 | Freshness-Score-Berechnung | bestanden | |
| TC-US6-01 | Bildunterschriftsgenerierung | bestanden | |
| TC-US7-01 | PDF-Textbereinigung | bestanden | |
| TC-US8-01 | 7-Metrik-Qualitätssuite | bestanden | |
| TC-US8-02 | Regressionsprüfung Preprocessing | bestanden | |
| TC-US9-01 | Einzelner Einstiegspunkt | bestanden | |
| TC-MET-01 | MRR-Berechnung | bestanden | |
| TC-MET-02 | NDCG@k-Berechnung | bestanden | |
| TC-EVA-01 | Modellvergleich-Pipeline E2E | bestanden | Zuvor fehlgeschlagen: `_expected_sources` ignorierte `.txt`-Extension — behoben |
| TC-EVA-02 | Keyword-Baseline | bestanden | |
| TC-RAG-01 | RAGAS-Evaluator | bestanden | Zuvor blockiert: `evaluation.ragas`-Paket fehlte — implementiert |
| TC-EMB-01 | Content-Aware Chunking | bestanden | |
| TC-EMB-02 | Embedding-Ausgabeformat | bestanden | |
| TC-DEP-01 | Direktupload zu Qdrant | bestanden | |
| TC-DEP-02 | Dry-Run-Modus | bestanden | |

**Ergebnis:** 30 bestanden · 0 fehlgeschlagen · 0 blockiert

---

## 3. Testreport

Fortschritt des Projekts über die Testläufe auf Branch `009-analysis-and-production-polish`:

| Datum | Bestanden | Fehlgeschlagen | Blockiert | Gesamt |
|---|---:|---:|---:|---:|
| 2026-03-18 | 26 | 2 | 2 | 30 |
| 2026-03-19 | 30 | 0 | 0 | 30 |

**Anmerkungen:**
- **2026-03-18:** 2 Tests fehlgeschlagen (`TC-US3-01` fehlende Stage, `TC-US4-01` fehlender ContentType), 2 Tests blockiert (`TC-EVA-01` fehlende Funktion, `TC-RAG-01` fehlendes Paket)
- **2026-03-19:** Alle 4 Diskrepanzen behoben — alle 30 Testfälle bestanden

### Automated Test Suite – Gesamtübersicht

Zusätzlich zu den 30 dokumentierten Testfällen werden **394 automatisierte Unit-Tests** durch pytest ausgeführt:

| Suite | Bestanden | Fehlgeschlagen | Übersprungen | Gesamt |
|---|---:|---:|---:|---:|
| `tests/` – Root (Unit + Smoke) | 55 | 0 | 0 | **55** |
| `evaluation/tests/` – Evaluierungsinfrastruktur | 125 | 0 | 2 | **127** |
| `pipeline/02_deep_evaluation/tests/` | 10 | 0 | 0 | **10** |
| `pipeline/03_rag_preprocessing/tests/` | 161 | 0 | 0 | **161** |
| `pipeline/04_embeddings_creator/tests/` | 19 | 0 | 0 | **19** |
| `pipeline/05_deploy/tests/` | 11 | 0 | 0 | **11** |
| `pipeline/shared/tests/` | 13 | 0 | 0 | **13** |
| **Gesamt** | **394** | **0** | **2** | **396** |

Die 2 übersprungenen Tests (`evaluation/tests/test_integration.py`) erfordern einen laufenden Qdrant-Service und werden in der lokalen Entwicklungsumgebung regulär übersprungen.

---

## 4. Rollen

| Rolle | Person | Aufgaben |
|---|---|---|
| **Test Author** | Jan Riedler | Schreibt Testspezifikationen auf Basis der User Stories; implementiert automatisierte Unit-Tests |
| **Tester** | Jan Riedler | Führt Testläufe aus; dokumentiert Ergebnisse im Testprotokoll |
| **Test Manager** | Jan Riedler | Verantwortlich für den gesamten Testprozess; verfolgt Fortschritt im Testreport |

---

## Anhang A: Tests ausführen

Da die Pipeline-Module als eigenständige Skripte konzipiert sind (Constitution Art. VIII), teilen mehrere Module denselben Dateinamen (`config.py`, `pipeline.py`). Diese Suiten werden daher separat ausgeführt:

```bash
# Root-Tests + Evaluierungsinfrastruktur
pytest tests/ evaluation/tests/

# Pipeline-Module einzeln
pytest pipeline/02_deep_evaluation/tests/
pytest pipeline/03_rag_preprocessing/tests/ pipeline/shared/tests/

# 04 und 05 aus ihrem eigenen Verzeichnis
cd pipeline/04_embeddings_creator && python -m pytest tests/
cd pipeline/05_deploy             && python -m pytest tests/
```

---

## Anhang B: Behobene Fehler

Beim ersten vollständigen Testlauf wurden vier Diskrepanzen zwischen Testerwartungen und Quellcode gefunden. In allen Fällen war der **Quellcode korrekt** — die Tests waren veraltet oder unvollständig.

### B.1 Fehlende Pipeline-Stufe `preprocess` (TC-US3-01)

**Datei:** `tests/unit/test_pipeline_schemas.py`

Der Test erwartete `{fetch, evaluate, embed, deploy}` — das Schema definiert jedoch `{fetch, evaluate, preprocess, embed, deploy}`. **Behebung:** `preprocess` in das erwartete Set aufgenommen.

### B.2 Fehlender Content-Type `TABLE_DATA` (TC-US4-01)

**Datei:** `pipeline/03_rag_preprocessing/tests/test_strategy_loader.py`

Der Test listete nur 6 von 7 Enum-Werten auf. `TABLE_DATA` war im Code korrekt definiert. **Behebung:** `TABLE_DATA` in das erwartete Set aufgenommen.

### B.3 Fehlende Funktion `load_corpus_for_ground_truth` (TC-EVA-01)

**Datei:** `evaluation/tests/test_model_comparison.py` / `evaluation/scripts/eval_model_comparison.py`

Tests importierten eine nicht-existente Funktion. Außerdem Bug in `_expected_sources`: nur `.md`-Extensions wurden entfernt — `.txt`-Dateien aus dem Ground-Truth-Datensatz wurden dadurch nicht korrekt in Page-IDs umgewandelt.

**Behebung:** `_find_fetched_dir()` und `load_corpus_for_ground_truth()` implementiert; Extension-Stripping auf alle Endungen ausgeweitet.

```python
# Vorher (nur .md erkannt):
stem = sf.rsplit(".", 1)[0] if sf.endswith(".md") else sf

# Nachher (alle Endungen entfernt):
stem = sf.rsplit(".", 1)[0] if "." in sf else sf
```

### B.4 Fehlendes `evaluation/ragas/`-Paket (TC-RAG-01)

**Datei:** `evaluation/tests/test_ragas.py`

Tests importierten `RAGASEvaluator` aus einem nicht-existenten Unterpaket. **Behebung:** `evaluation/ragas/__init__.py` und `evaluation/ragas/ragas_evaluator.py` implementiert.

---

## Anhang C: Neue und geänderte Dateien

### Neue Quelldateien

| Datei | Beschreibung |
|---|---|
| `evaluation/ragas/__init__.py` | Paket-Init, re-exportiert `RAGASEvaluator` |
| `evaluation/ragas/ragas_evaluator.py` | RAGAS-Wrapper mit Ollama-kompatiblem LLM-Judge |

### Geänderte Quelldateien

| Datei | Änderung |
|---|---|
| `evaluation/scripts/eval_model_comparison.py` | `_find_fetched_dir()` und `load_corpus_for_ground_truth()` hinzugefügt; `_expected_sources` Bugfix |

### Korrigierte Testdateien

| Datei | Korrektur |
|---|---|
| `tests/unit/test_pipeline_schemas.py` | `preprocess` zur erwarteten Stage-Menge hinzugefügt |
| `pipeline/03_rag_preprocessing/tests/test_strategy_loader.py` | `TABLE_DATA` zur erwarteten ContentType-Menge hinzugefügt |

---

## Anhang D: Detaillierte Unit-Test-Spezifikationen

Alle 394 automatisierten Tests sind auf Funktionsebene mit SUT, Bedingung und erwartetem Ergebnis dokumentiert — gruppiert nach Datei und Klasse.

### D.1 `tests/smoke/test_docker_compose.py`

Articles: III, VI

#### TestDockerComposeSyntax

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_compose_file_exists` | Datei-Existenz | Pfad geprüft | Vorhanden |
| `test_compose_is_valid_yaml` | YAML-Parsing | docker-compose.yml geladen | Enthält `services` |
| `test_compose_has_project_name` | Projektname | `name`-Feld | `"stack-g-devdito"` |
| `test_compose_has_networks` | Netzwerk | Networks geprüft | `leonidas-network` extern |

#### TestDockerfileReferences

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_all_build_contexts_exist` | Build-Pfade | Services mit Build-Config | Alle Dockerfiles existieren |

#### TestNoHardcodedSecrets

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_no_secrets_in_compose` | Secret-Scan compose | OpenAI-Keys, Tokens gesucht | Keine Treffer |
| `test_no_secrets_in_dockerfiles` | Secret-Scan Dockerfiles | Alle Dockerfiles | Keine Treffer |

#### TestRequiredServices

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_orchestrator_service_exists` | Orchestrator | Services-Liste | Vorhanden |
| `test_qdrant_service_exists` | Qdrant | Services-Liste | Vorhanden |
| `test_all_services_have_container_names` | Container-Namen | Jede Service-Config | Alle haben `container_name` |

---

### D.2 `tests/unit/test_config_loader.py`

Articles: II-B, III

#### TestResolvePlaceholders

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_simple_placeholder` | `${root_dir}`-Auflösung | Einfache Referenz | `/test/root/config` |
| `test_nested_placeholder` | Mehrstufige Auflösung | 3 Ebenen | `/test/root/config/secrets` |
| `test_no_placeholders` | Pass-through | Ohne Placeholder | Werte unverändert |
| `test_unresolvable_placeholder_preserved` | Fehlende Variable | Undefinierter Placeholder | Bleibt erhalten |
| `test_non_string_values_unchanged` | Typ-Erhaltung | Numerisch/Boolean | Unverändert |
| `test_list_values_resolved` | Listen-Auflösung | Liste mit Placeholdern | Alle aufgelöst |

#### TestLoadYamlConfig

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_load_valid_yaml` | YAML-Parsing | Gültige Datei | Dict mit `APP.name` |
| `test_load_nonexistent_file_raises` | Fehlende Datei | Pfad ungültig | `FileNotFoundError` |
| `test_load_invalid_yaml_raises` | Ungültiges YAML | Plain-String | `ValueError` |

#### TestLoadSecretFile

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_load_plain_token` | Token-Extraktion | `sk-test-token-12345` | Token ohne Newlines |
| `test_load_key_value_format` | KEY=VALUE | `TOKEN=my-secret-value` | `my-secret-value` |
| `test_missing_file_returns_empty` | Fehlende Datei | Nicht vorhanden | `""` |
| `test_jwt_token_not_split` | JWT-Erhaltung | Token mit Punkten | Vollständig zurückgegeben |

#### TestGetSetting

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_get_existing_path` | Verschachtelter Zugriff | `APP.name` | String-Wert |
| `test_get_missing_path_returns_default` | Default-Fallback | Fehlender Pfad | `'fallback_value'` |
| `test_get_none_default` | None-Default | Fehlend, kein Default | `None` |

#### TestComputeConfigHash

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_same_config_same_hash` | Deterministik | Gleicher Dict 2× | Identisch |
| `test_different_config_different_hash` | Sensitivität | 2 verschiedene Dicts | Verschieden |
| `test_meta_excluded_from_hash` | `_meta`-Ausschluss | Mit/ohne `_meta` | Identisch |

#### TestPlaceholderEnvYaml

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_placeholder_yaml_is_valid` | Parsbarkeit | `PLACEHOLDER_env.yaml` | Gültig |
| `test_placeholder_has_required_sections` | Pflichtabschnitte | Dateiinhalt | APP, PATHS, SERVICES, PIPELINE, PLUGIN |

---

### D.3 `tests/unit/test_orchestrator_stages.py`

#### TestPipelineStagesStructure

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_has_exactly_five_stages` | Stage-Anzahl | `PIPELINE_STAGES` | Genau 5 |
| `test_each_stage_has_required_keys` | Stage-Schema | Jede Stage | `name`, `container`, `pipeline_dir` |
| `test_deploy_has_entrypoint_args` | Deploy-Einstiegspunkt | `deploy`-Stage | Hat `entrypoint_args` |
| `test_deploy_entrypoint_args_correct` | Deploy-Kommando | `entrypoint_args` | `["python", "run_deploy.py", "qdrant"]` |
| `test_embed_has_needs_openai_key` | OpenAI-Key | `embed`-Stage | `True` |
| `test_no_other_stage_needs_openai_key` | Key-Isolation | Alle anderen | `False` |

#### TestGetLastRunSortKey

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_returns_none_when_no_runs` | Leere Datei | Keine Runs | `None` |
| `test_picks_latest_started_at_not_updated_at` | Sort-Kriterium | 2 Runs, verschiedene Zeiten | Run mit späterem `started_at` |

#### TestRunRequest / TestConcurrentJobRejection

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_default_options_is_empty_dict` | Default | Ohne `options` | `{}` |
| `test_options_accepts_string_dict` | Dict-Zuweisung | `{"mode":"incremental"}` | `options["mode"] == "incremental"` |
| `test_active_job_detected_when_status_running` | Aktiv-Erkennung | `status='running'` | Job zurückgegeben |
| `test_no_active_job_when_all_finished` | Leerlauf | Nur success/error | `None` |

---

### D.4 `tests/unit/test_pipeline_schemas.py`

Articles: II, III

#### TestPipelineRunsSchema

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_schema_file_exists` | Datei | Pfad | Existiert |
| `test_schema_is_valid_json` | JSON-Struktur | Geladen | Gültiger Dict |
| `test_schema_defines_array_type` | Root-Typ | Schema | `type == 'array'` |
| `test_schema_has_required_fields` | Pflichtfelder | `items.required` | `job_id`, `stage`, `status`, `started_at` |
| `test_schema_stage_enum` | Stage-Constraints | `stage`-Property | Alle 5 Stages |
| `test_schema_status_enum` | Status-Constraints | `status`-Property | `running`, `success`, `error`, `interrupted` |

#### TestSchemaValidation / TestExistingPipelineRuns

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_valid_data_passes` | Validierung | Sample-Daten | Erfolgreich |
| `test_empty_array_passes` | Leere Daten | `[]` | Erfolgreich |
| `test_missing_required_field_fails` | Pflichtfeld | Ohne `job_id` | `ValidationError` |
| `test_invalid_stage_fails` | Enum | `stage='invalid_stage'` | `ValidationError` |
| `test_invalid_status_fails` | Enum | `status='unknown_status'` | `ValidationError` |
| `test_existing_runs_file_is_valid` | Echte Datei | Falls vorhanden | Valide |

---

### D.5 `evaluation/tests/test_integration.py`

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_qdrant_connection` | Qdrant-Verbindung | Service läuft | Collections-Liste (übersprungen wenn nicht verfügbar) |
| `test_e2e_qdrant_embed_query_metrics` | E2E-Pipeline | Qdrant + Ollama | MRR > 0 (übersprungen wenn nicht verfügbar) |

---

### D.6 `evaluation/tests/test_keyword_baseline.py`

#### TestSourceFileToPageId

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_single_namespace` | `_` → `:` | `exams_matura-tagesschule-if-it.txt` | `exams:matura-tagesschule-if-it` |
| `test_double_namespace` | Mehrfach | `archive_exams_semesterpruefungen.txt` | `archive:exams:semesterpruefungen` |
| `test_triple_namespace` | Drei Ebenen | `it_studentmail2023_android_gmail.txt` | `it:studentmail2023:android:gmail` |
| `test_no_namespace` | Ohne `_` | `start.txt` | `start` |
| `test_hyphens_preserved` | Bindestriche | `exams_da-inf-it.txt` | `exams:da-inf-it` |
| `test_all_ground_truth_sources` | Batch | Mehrere Beispiele | Alle gültig, kein `.txt`-Suffix |

#### TestRunKeywordBaseline

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_perfect_hits` | Pipeline | Mock gibt richtigen Rang | MRR=1.0, P@5=0.2 |
| `test_no_hits` | Kein Treffer | Mock irrelevant | MRR=0.0 |
| `test_result_has_nfr005_fields` | NFR-005 | Evaluation fertig | `timestamp`, `config_hash`, `code_version` |

---

### D.7 `evaluation/tests/test_metrics.py`

Article: III

#### TestReciprocalRank

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_relevant_at_rank_1` | RR | `relevant={"a"}` | 1.0 |
| `test_relevant_at_rank_2` | RR | `relevant={"b"}` | 0.5 |
| `test_relevant_at_rank_3` | RR | `relevant={"c"}` | ≈1/3 |
| `test_no_relevant_results` | RR | `relevant={"x"}` | 0.0 |
| `test_empty_results` | RR | `ranked=[]` | 0.0 |
| `test_empty_relevant_set` | RR | `relevant={}` | 0.0 |
| `test_multiple_relevant_returns_first` | Erster Treffer | `relevant={"b","c"}` | 0.5 |

#### TestMeanReciprocalRank

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_basic_mrr` | MRR | 3 Queries | ≈0.6111 |
| `test_empty_queries` | Leer | `[]` | 0.0 |
| `test_all_miss` | Alle Misses | Keine Treffer | 0.0 |
| `test_perfect_mrr` | Perfekt | Alle Rang 1 | 1.0 |

#### TestPrecisionAtK

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_all_relevant` | P@k | Alle relevant | 1.0 |
| `test_none_relevant` | P@k | Keine Treffer | 0.0 |
| `test_partial_relevant` | P@k | 2/5 relevant | 0.4 |
| `test_k_larger_than_results` | P@k | k=5, 2 Ergebnisse | 0.2 |
| `test_k_zero` | P@k | k=0 | 0.0 |
| `test_empty_results` | P@k | Leer | 0.0 |
| `test_p_at_5` | P@5 | 3 relevant in 7 | 0.6 |

#### TestMeanPrecisionAtK / TestNdcgAtK / TestMeanNdcgAtK

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_basic` (MeanP@k) | Aggregation | 2 Queries | 0.75 |
| `test_perfect_ranking` (NDCG) | Ideal | Optimal geordnet | 1.0 |
| `test_reverse_ranking` (NDCG) | Worst-Case | Umgekehrt | 0 < x < 1 |
| `test_no_relevant_documents` (NDCG) | Leer | Keine Relevanz | 0.0 |
| `test_hand_calculated_example` (NDCG) | Lehrbuch | Spezifische Konfig | ≈0.972 |
| `test_single_relevant_at_various_positions` (NDCG) | Sensitivität | Rang 1/2/3 | Rang1 > Rang2 > Rang3 |

---

### D.8 `evaluation/tests/test_model_comparison.py`

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_empty_text` | Chunk | `""` | `[]` |
| `test_short_text_single_chunk` | Chunk | Unter Limit | 1 Chunk |
| `test_respects_chunk_size` | Chunk | 600 Zeichen, size=250 | Mehrere ≤300 |
| `test_high_overlap` | Relevanz | Ähnliche Texte | >0.3 |
| `test_no_overlap` | Relevanz | Unverwandt | <0.2 |
| `test_keyword_boost` | Keyword-Gewichtung | Mit/ohne Keywords | Mit > ohne |
| `test_loads_from_fetched_dir` | Corpus-Laden | Mock-Verzeichnis | Chunks mit Page-ID |
| `test_full_pipeline_mocked` | E2E | Alles gemockt | MRR=1.0, NFR-005 |
| `test_cleanup_on_error` | Cleanup | Fehler in Suche | `delete_collection` aufgerufen |

---

### D.9 `evaluation/tests/test_new_metrics.py`

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_all_relevant_in_top_k` | Recall@k | Alle gefunden | 1.0 |
| `test_some_relevant_in_top_k` | Recall@k | 2/3 gefunden | 2/3 |
| `test_none_relevant_in_top_k` | Recall@k | Kein Treffer | 0.0 |
| `test_k_larger_than_results` | Recall@k | k>Ergebnisse | 1.0 |
| `test_basic_mean_recall` | MeanRecall | 3 Queries | 2/3 |
| `test_perfect_ranking` (AP) | AP | Ideal | 1.0 |
| `test_one_relevant_at_rank_2` (AP) | AP | Ein Treffer Rang 2 | 0.5 |
| `test_basic_map` | MAP | 2 Queries | 0.75 |
| `test_hit_when_relevant_in_top_k` | Hit@k | Treffer | 1 |
| `test_miss_when_no_relevant_in_top_k` | Hit@k | Kein Treffer | 0 |
| `test_all_hits` | Hit-Rate | Alle Queries | 1.0 |
| `test_half_hits` | Hit-Rate | Hälfte | 0.5 |

---

### D.10 `evaluation/tests/test_providers.py`

Article: III

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_cannot_instantiate_abc` | ABC | Direkte Instanz | `TypeError` |
| `test_properties` (Ollama) | Attribute | Init | Korrekt gesetzt |
| `test_is_embedding_provider` (Ollama) | Interface | Instanz | `isinstance = True` |
| `test_embed_calls_sdk` (Ollama) | SDK-Aufruf | Gemockt | `embed()` aufgerufen |
| `test_properties` (OpenAI) | Attribute | Init | `cost_per_token` gesetzt |
| `test_is_embedding_provider` (OpenAI) | Interface | Instanz | `isinstance = True` |
| `test_embed_tracks_tokens` (OpenAI) | Token-Tracking | Gemockte Response | `total_tokens` inkrementiert |

---

### D.11 `evaluation/tests/test_ragas.py`

Task IDs: T029–T031

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_init_accepts_llm_base_url_and_model` | Konstruktor | Init | Attribute gesetzt |
| `test_init_default_temperature_zero` | Temperature | Kein Wert | `ChatOpenAI(temperature=0.0)` |
| `test_init_calls_chat_openai_with_base_url` | Base-URL | Konstruktor | `base_url` und `model` übergeben |
| `test_evaluate_returns_dict_of_metric_scores` | Evaluate | Mock | Dict mit Scores |
| `test_evaluate_empty_data_returns_empty_or_sensible` | Leer | `[]` | Dict |
| `test_evaluate_logs_and_continues_on_single_item_failure` | Fehlerfall | Exception | Propagiert |
| `test_evaluate_handles_ragas_import_error_gracefully` | Import-Fehler | RAGAS fehlt | Leerer Dict |

---

### D.12 `evaluation/tests/test_reports.py`

Task IDs: T051–T054

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_generate_returns_markdown_and_json_paths` | Generierung | JSON-Dateien | `(md_path, json_path)` |
| `test_markdown_contains_required_sections` | Inhalt | Markdown | `# Evaluation Report`, `## Executive Summary` |
| `test_json_is_valid_and_has_sections` | Struktur | JSON | `executive_summary`, `custom_metrics` |
| `test_custom_metrics_table_in_markdown` | Metriktabelle | Markdown | `MRR` enthalten |
| `test_ragas_section_in_markdown` | RAGAS | Scores vorhanden | `RAGAS` enthalten |
| `test_json_contains_timestamp` | NFR-005 | JSON | `timestamp` |
| `test_json_contains_config_hash` | NFR-005 | JSON | `config_hashes` |
| `test_json_contains_code_version` | NFR-005 | JSON | `code_version` |
| `test_difficulty_breakdown_in_markdown` | Schwierigkeit | Markdown | `Difficulty` |
| `test_difficulty_breakdown_in_json` | Schwierigkeit | JSON | `difficulty_breakdown`-Dict |

---

### D.13 `evaluation/tests/test_statistics.py`

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_returns_bootstrap_ci_dataclass` | Bootstrap-CI | 20 Samples | `BootstrapCI` mit mean, ci_lower, ci_upper |
| `test_small_sample` | Klein | `[0.5,0.6,0.7]` | mean≈0.6, ci_lower≤ci_upper |
| `test_empty_scores_raises_or_returns_sensible` | Leer | `[]` | Exception |
| `test_returns_comparison_result` | Paired-Test | 2 Listen | `ComparisonResult` |
| `test_identical_lists` | Kein Unterschied | Gleich | diff=0, effect=0 |
| `test_different_length_raises` | Mismatch | Verschiedene Längen | `ValueError` |
| `test_returns_float_and_interpretation` | Cohen's d | 2 Gruppen | `(float, str)` |
| `test_identical_lists_zero_effect` | Kein Effekt | Gleich | d=0.0 |
| `test_returns_dict_with_mean_median_std` | Deskriptiv | 5 Werte | mean, median, std |
| `test_returns_list_of_comparison_results` | Konfig-Vergleich | JSON-Dateien | Liste von Ergebnissen |
| `test_missing_file_raises` | Fehlend | Ungültige Pfade | `FileNotFoundError` |

---

### D.14 `evaluation/tests/test_visualization.py`

Task IDs: T038–T042

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_radar_chart_returns_path` | Radar | Multi-Modell | PNG-Pfad |
| `test_radar_chart_file_not_empty` | Inhalt | PNG | Größe > 0 |
| `test_radar_chart_creates_output_dir` | Verzeichnis | Fehlend | Auto-erstellt |
| `test_box_plot_returns_path` | Box-Plot | Scores | PNG-Pfad |
| `test_box_plot_file_not_empty` | Inhalt | PNG | Größe > 0 |
| `test_bar_comparison_returns_path` | Balken | Multi-Modell | PNG-Pfad |
| `test_heatmap_returns_path` | Heatmap | Matrix | PNG-Pfad |
| `test_svg_radar_chart` | SVG | `fmt="svg"` | SVG-Datei |
| `test_svg_bar_comparison` | SVG | `fmt="svg"` | SVG-Datei |
| `test_svg_box_plot` | SVG | `fmt="svg"` | SVG-Datei |
| `test_svg_heatmap` | SVG | `fmt="svg"` | SVG-Datei |

---

### D.15 `pipeline/02_deep_evaluation/tests/test_deep_eval_bugfixes.py`

Task IDs: T049–T052b

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_analyze_documents_no_duplicates` | Datei-Dedup | `.pdf` + `.PDF` | Nur einmal |
| `test_analyze_images_no_duplicates` | Bild-Dedup | `.jpg` + `.JPG` | Nur einmal |
| `test_env_yaml_has_temperature_zero` | Config | `env.yaml` | 0.0 |
| `test_llm_client_passes_temperature` | LLM | Client-Init | `gen_params["temperature"]==0.0` |
| `test_wiki_strategies_no_duplicate_ids` | YAML-Dedup | Doppelte Page-IDs | Eindeutig |
| `test_document_strategies_no_duplicate_files` | YAML-Dedup | Doppelte Dateien | Eindeutig |
| `test_media_strategies_no_duplicate_files` | YAML-Dedup | Doppelte Media | Eindeutig |
| `test_ignored_wiki_strategies_no_duplicate_ids` | YAML-Dedup | Ignored-Liste | Eindeutig |
| `test_structural_override_table_data` | Heuristik | 60% Tabellenzeilen | Override → `TABLE_DATA` |
| `test_summary_is_single_log_call` | Logging | `main()` | Ein `logger.info()`-Aufruf |

---

### D.16 `pipeline/03_rag_preprocessing/tests/test_architecture_cleanup.py`

Task ID: T031

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_main_py_does_not_exist` | Konsolidierung | Verzeichnis-Scan | `main.py` nicht vorhanden |
| `test_run_preprocessing_exists` | Einstiegspunkt | Verzeichnis | `run_preprocessing.py` vorhanden |
| `test_run_preprocessing_has_main` | Funktion | Import | `callable(main)` |
| `test_run_preprocessing_has_run` | Funktion | Import | `callable(run)` |
| `test_run_preprocessing_help` | `--help` | Aufruf | `SystemExit(0)` |
| `test_document_extensions_constant` | Konstante | `DOCUMENT_EXTENSIONS` | `.pdf`, `.docx`, `.xlsx`, `.pptx` |
| `test_image_extensions_constant` | Konstante | `IMAGE_EXTENSIONS` | `.png`, `.jpg`, `.jpeg` |
| `test_process_docx_method_exists` | Methode | Klasse | `callable(process_docx)` |
| `test_process_xlsx_method_exists` | Methode | Klasse | `callable(process_xlsx)` |
| `test_process_pptx_method_exists` | Methode | Klasse | `callable(process_pptx)` |
| `test_process_media_directory_handles_all_formats` | Abdeckung | Alle Formate | Liste zurückgegeben |
| `test_process_docx_nonexistent_file` | Fehlend | Ungültig | `""` |
| `test_process_xlsx_nonexistent_file` | Fehlend | Ungültig | `""` |
| `test_process_pptx_nonexistent_file` | Fehlend | Ungültig | `""` |

---

### D.17 `pipeline/03_rag_preprocessing/tests/test_eval_metrics.py`

Task ID: T037

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_identical_text_returns_1` | Completeness | Gleich | ≈1.0 |
| `test_half_content_returns_low` | Completeness | 80/200 Zeichen | <0.85 |
| `test_markup_removed_still_passes` | Completeness | Wiki→MD | ≥0.70 |
| `test_identical_texts_high_score` | Semantic | Gleich | ≥0.95 |
| `test_different_texts_lower_score` | Semantic | Unverwandt | <0.85 |
| `test_all_entities_preserved` | Entity | Datum, Raum, Mail, URL | 1.0 |
| `test_entity_lost_reduces_score` | Entity | E-Mail weg | 0.5≤x<1.0 |
| `test_links_preserved` | Link | `[[]]`→`[]()` | ≥0.90 |
| `test_clean_text_low_noise` | Noise | Sauber | ≤0.02 |
| `test_wiki_syntax_detected` | Noise | Wiki-Reste | >0.02 |
| `test_simple_text_readable` | Readability | Deutsch einfach | ≥20 |
| `test_threshold_is_20_not_60` | Threshold | Deutsch | =20.0 |
| `test_structure_fully_preserved` | Structure | Wiki→MD | ≥0.80 |
| `test_passes_thresholds` | DocScore | Alle über Threshold | `True` |
| `test_fails_thresholds_low_completeness` | DocScore | completeness=0.50 | `False` |
| `test_regression_fails_below_90_percent` | Regression | 15% scheitern | `False` |
| `test_regression_passes_above_90_percent` | Regression | Alle bestehen | `True` |

---

### D.18 `pipeline/03_rag_preprocessing/tests/test_exporter.py`

Task IDs: T066, T006

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_export_returns_path` | Export | Sample-Seiten | Existierender Pfad |
| `test_export_creates_timestamped_dir` | Verzeichnis | Export | Beginnt mit `"preprocessed_at_"` |
| `test_export_creates_pages_subdir` | Struktur | Seiten | `pages/` mit `.md`-Dateien |
| `test_export_creates_media_subdir` | Struktur | Media | `media/` mit `.md`-Dateien |
| `test_media_output_has_md_extension_not_txt` | Endung | Media | `.md`, kein `.txt` |
| `test_exported_file_has_yaml_frontmatter` | Frontmatter | Datei | `---\n`...`---\n` |
| `test_export_empty_pages_returns_dir` | Leer | Keine Seiten | Verzeichnis erstellt |
| `test_page_has_all_required_fields` | Pflichtfelder | Seite | 14 Felder |
| `test_content_hash_is_md5_of_body` | Hash | Seite | MD5(body), 32 Zeichen |
| `test_freshness_score_is_float` | Typ | Frontmatter | Float |
| `test_links_to_is_list` | Typ | Frontmatter | Liste |
| `test_linked_from_is_list` | Typ | Frontmatter | Liste |
| `test_media_uses_media_id` | Media-ID | Media | `media_id`, kein `page_id` |
| `test_media_has_all_required_fields` | Media | Felder | Alle vorhanden |

---

### D.19 `pipeline/03_rag_preprocessing/tests/test_image_captioner.py`

Task ID: T026

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_caption_returns_description_string` | Caption | Gültiges PNG | Deutschen String |
| `test_caption_graceful_failure_returns_empty` | Fehler | API-Fehler | `""` |
| `test_caption_nonexistent_file_returns_empty` | Fehlend | Kein Pfad | `""` |
| `test_is_available_returns_false_when_unreachable` | Verfügbarkeit | Ungültiger Endpunkt | `False` |
| `test_is_available_returns_true_when_reachable` | Verfügbarkeit | Gemockt | `True` |
| `test_encodes_image_to_base64` | Base64 | PNG | `"data:image/png;base64,..."` |
| `test_png_jpg_supported` | Konstante | `CAPTIONABLE_EXTENSIONS` | `.png`, `.jpg`, `.jpeg` |
| `test_pdf_not_captionable` | Konstante | `CAPTIONABLE_EXTENSIONS` | Kein `.pdf` |

---

### D.20 `pipeline/03_rag_preprocessing/tests/test_media_processor.py`

Task IDs: T065, T021

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_process_pdf_returns_string` | PDF | Gemockt | String |
| `test_process_pdf_tries_docling_first` | Docling-Priorität | Docling liefert MD | Docling-Output |
| `test_process_pdf_fallback_to_ocr` | OCR-Fallback | Docling+pypdf leer | OCR-Ergebnis |
| `test_process_pdf_missing_file` | Fehlend | Kein PDF | `""` |
| `test_process_docx_tries_docling_first` | Docling | DOCX | Markdown |
| `test_process_docx_fallback_extracts_tables` | Tabellen | Docling leer | `|`-Syntax |
| `test_process_xlsx_tries_docling_first` | Docling | XLSX | Markdown |
| `test_process_xlsx_fallback_produces_markdown_tables` | Tabellen | Docling leer | `|` und `---` |
| `test_process_image_returns_string` | OCR | Gemockt | String |
| `test_process_image_missing_file` | Fehlend | Kein Bild | `""` |
| `test_directory_returns_list` | Verzeichnis | Media-Dir | Liste |
| `test_directory_entries_have_required_keys` | Struktur | Verarbeitet | `filename`, `text`, `type` |
| `test_htbla_leonding` | Spaced-Chars | `"H T B L A ..."` | `"HTBLA Leonding"` |
| `test_normal_text_unchanged` | No-op | Normal | Unverändert |
| `test_joins_consecutive_short_lines` | Zeilen-Merge | Kurze Zeilen | Zusammengeführt |
| `test_respects_sentence_boundaries` | Satzenden | `.`-Zeilen | Grenzen respektiert |
| `test_preserves_list_items` | Listen | Bullet-Items | Getrennt |
| `test_preserves_headings` | Überschriften | `#`-Zeilen | Getrennt |
| `test_chains_spaced_chars_then_merge` | Pipeline | Beide Fälle | Beide angewendet |
| `test_process_pdf_integrates_clean` | Integration | Raw PDF | Bereinigt |

---

### D.21 `pipeline/03_rag_preprocessing/tests/test_metadata_enricher.py`

Task IDs: T068, T007, T017, T077, T078

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_26_day_old_returns_fresh_1_0` | Freshness | 26 Tage | score=1.0, fresh |
| `test_60_day_old_returns_fresh_1_0` | Freshness | 60 Tage | score=1.0, fresh |
| `test_120_day_old_returns_fresh_0_85` | Freshness | 120 Tage | score=0.85, fresh |
| `test_300_day_old_returns_fresh_0_85` | Freshness | 300 Tage | score=0.85, fresh |
| `test_650_day_old_returns_recent_0_70` | Freshness | 650 Tage | score=0.70, recent |
| `test_800_day_old_returns_outdated_0_50` | Freshness | 800 Tage | score=0.50, outdated |
| `test_1500_day_old_returns_stale_0_30` | Freshness | 1500 Tage | score=0.30, stale |
| `test_archive_namespace_always_archived` | Freshness | archive:... | score=0.20, archived |
| `test_invalid_date_returns_default` | Fehler | Ungültig | score=0.5, unknown |
| `test_teacher_namespace` | Access | teacher:docs | teacher_only |
| `test_lehrer_namespace` | Access | lehrer:material | teacher_only |
| `test_public_namespace` | Access | departm:... | public |
| `test_empty_namespace` | Access | `""` | public |
| `test_field_name_is_last_modified_not_modified_at` | Feldname | Frontmatter | `last_modified` (kein `modified_at`) |
| `test_linked_from_populated_from_backlinks` | Backlinks | Übergeben | `linked_from` befüllt |
| `test_source_url_uses_wiki_base_url` | Source-URL | base+page_id | Korrekt kombiniert |

---

### D.22 `pipeline/03_rag_preprocessing/tests/test_page_processor.py`

Task IDs: T067, T076

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_heading_h1` | H1 | `"====== Title ======"` | `"# Title"` |
| `test_heading_h2` | H2 | `"===== Sub ====="` | `"## Sub"` |
| `test_bold_text` | Fett | `"**bold**"` | `"**bold**"` |
| `test_italic_text` | Kursiv | `"//italic//"` | `"*italic*"` |
| `test_internal_link` | Link | `"[[page|text]]"` | `"[text](page)"` |
| `test_internal_link_namespace_colon_lowercase` | Namespace | `"[[departm:ELD|...]]"` | `"(departm:eld)"` |
| `test_unordered_list` | Liste | `"  * item"` | `"- item"` |
| `test_table_conversion` | Tabelle | `"^ H1 ^ H2 ^"` | `"| H1 | H2 |"` |
| `test_empty_content_fails` | Leer | `""` | `result.success = False` |
| `test_knowledge_page` | Routing | KNOWLEDGE | `content_type="knowledge"` |
| `test_news_page` | Routing | NEWS | `content_type="news"` |
| `test_archived_page_marked_low_priority` | Routing | ARCHIVED | `priority="low"` |

---

### D.23 `pipeline/03_rag_preprocessing/tests/test_regression_wiki_syntax.py`

Task ID: T081

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_conversion_removes_almost_all_wiki_syntax` | Syntax-Entfernung | Komplex | <1% Wiki-Muster |
| `test_headings_fully_converted` | Überschriften | Alle Ebenen | Kein `"====="` mehr |
| `test_links_fully_converted` | Links | `[[]]`-Muster | Kein `[[` oder `]]` |
| `test_media_fully_converted` | Media | `{{}}`-Muster | Kein `{{` oder `}}` |

---

### D.24 `pipeline/03_rag_preprocessing/tests/test_run_preprocessing.py`

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_backlinks_use_page_id_from_json` | Backlinks-Key | JSON mit `page_id` | Keys aus JSON |
| `test_backlinks_fallback_stem_when_no_page_id` | Fallback | Kein `page_id` | Stem-Transformation |
| `test_backlinks_empty_dir` | Fehlend | Kein Verzeichnis | `{}` |

---

### D.25 `pipeline/03_rag_preprocessing/tests/test_schema_e2e.py`

Task ID: T005

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_page_roundtrip_all_fields_present` | Roundtrip | Seite exportiert+geladen | 14 Felder |
| `test_media_roundtrip_uses_media_id` | Media | Exportiert+geladen | `media_id`, kein `page_id` |
| `test_content_hash_is_md5_of_body_without_frontmatter` | Hash | Exportiert | MD5(body only) |
| `test_output_has_pages_and_media_subdirs` | Struktur | Export | `pages/` und `media/` |
| `test_manifest_json_created` | Manifest | Export | `manifest.json` mit Zählern |

---

### D.26 `pipeline/03_rag_preprocessing/tests/test_strategy_loader.py`

Task IDs: T064, T013

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_load_yaml_finds_file` | YAML-Laden | Datei vorhanden | Strategien geladen |
| `test_knowledge_articles_mapping` | Mapping | knowledge_articles | KNOWLEDGE + recursive_header |
| `test_portals_mapping` | Mapping | portals | PORTAL + parent_context |
| `test_news_mapping` | Mapping | news | NEWS + naive |
| `test_forms_wiki_page_mapping` | Mapping | forms | FORM |
| `test_ignored_pages_skipped` | Ignored | In Liste | `is_ignored()=True` |
| `test_underscore_to_colon_conversion` | Konvertierung | YAML mit `_` | Abfrage mit `:` |
| `test_unknown_page_gets_default` | Default | Unbekannt | KNOWLEDGE, semantic, process |
| `test_informative_images_action` | Media | Informativ | `caption_and_index` |
| `test_decorative_images_skip` | Media | Dekorativ | `skip` |
| `test_document_strategy` | Media | PDF-Dokument | Hat `parser` |
| `test_thesis_document` | Media | Wissenschaftlich | `pdf_scientific` |
| `test_unknown_media_gets_default` | Media | Unbekannt | `process`, `DOCUMENT` |
| `test_json_fallback` | JSON | `page_strategies.json` | Geladen |
| `test_yaml_preferred_over_json` | Präferenz | Beide vorhanden | YAML gewinnt |
| `test_empty_dir_no_error` | Leer | Kein File | Defaults |
| `test_all_types_exist` | Enum | ContentType | Alle 7 Typen |

---

### D.27 `pipeline/04_embeddings_creator/tests/test_content_aware_chunker.py`

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_chunk_has_required_attributes` | Felder | Chunk erstellt | `chunk_id`, `text`, `chunk_index`, `total_chunks`, `source`, `collection`, `access_level` |
| `test_chunk_id_format` | Format | Erster Chunk | `"pages_my_page_0"` |
| `test_chunk_index_and_total_chunks` | Tracking | Mehrere Chunks | Korrekte Werte |
| `test_skip_empty_content_type` | Skip | EMPTY | `[]` |
| `test_do_not_skip_knowledge` | Verarbeiten | KNOWLEDGE | ≥1 Chunk |
| `test_short_text_single_chunk` | Semantisch | Kurz | 1 Chunk |
| `test_respects_max_chunk_size` | Größe | 600 Zeichen, max 512 | Mehrere Chunks |
| `test_naive_splits_long_text` | Naiv | NEWS, 1500 Zeichen | Mehrere Chunks |
| `test_prepare_text_adds_frontmatter_when_configured` | Frontmatter | `include=True` | Titel+Body |
| `test_returns_content_type_config` | Config | KNOWLEDGE | `method="recursive_header"` |
| `test_chunk_all_returns_flat_list` | Multi-Doc | 2 Dokumente | Flache Liste |
| `test_chunk_all_skips_empty_type` | Filter | Mix KNOWLEDGE+EMPTY | EMPTY übersprungen |

---

### D.28 `pipeline/04_embeddings_creator/tests/test_embedding_output_format.py`

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_record_has_required_top_level_keys` | Struktur | Record gebaut | `id`, `text`, `embedding`, `metadata` |
| `test_record_id_is_string` | Typ | ID | String |
| `test_embedding_dimensions_3072` | Dimension | Konstante | 3072 |
| `test_build_metadata_contains_mcp_payload_fields` | Metadata | MCP-Felder | `text`, `source`, `collection`, `access_level`, `chunk_index`, `total_chunks` |

---

### D.29 `pipeline/05_deploy/tests/test_deploy_qdrant.py`

Task IDs: T082–T085

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_deploy_direct_returns_count` | Upload | 5 Punkte | 5 |
| `test_deploy_direct_calls_upsert` | Methode | Direct | `upsert()` aufgerufen |
| `test_deploy_direct_creates_collection_if_missing` | Erstellung | Fehlt | `create_collection()` |
| `test_deploy_direct_empty_file` | Leer | Leeres JSONL | 0 |
| `test_deploy_watchdog_returns_path` | Watchdog | Copy-Mode | Existierender Pfad |
| `test_deploy_watchdog_copies_file` | Kopieren | Quelldatei | Identischer Inhalt |
| `test_deploy_watchdog_creates_output_dir` | Verzeichnis | Fehlt | Erstellt |
| `test_recreate_deletes_existing_collection` | Recreate | `recreate=True` | `delete_collection` aufgerufen |
| `test_recreate_false_keeps_collection` | Kein Recreate | `recreate=False` | `delete_collection` NICHT aufgerufen |
| `test_upsert_adds_to_existing_collection` | Upsert-Only | `recreate=False` | Punkte hinzugefügt |
| `test_dry_run_does_not_upload` | Dry-Run | `dry_run=True` | `upsert` NICHT aufgerufen |

---

### D.30 `pipeline/shared/tests/test_cli_utils.py`

Task ID: T054

| Test | SUT | Bedingung | Erwartet |
|---|---|---|---|
| `test_returns_ansi_when_color_enabled` | ANSI | Farbe an, "green" | `\033[32m` und `\033[0m` |
| `test_returns_plain_when_color_disabled` | Plain | Farbe aus | Kein Escape-Code |
| `test_multiple_codes` | Mehrere Codes | "bold"+"yellow" | `\033[1m` und `\033[33m` |
| `test_no_codes_returns_plain` | Kein Styling | Kein Code | Klartext |
| `test_unknown_code_ignored` | Unbekannt | Unbekannter Code | Ignoriert |
| `test_handler_exits_130` | SIGINT | Signal | `SystemExit(130)` |
| `test_handler_calls_callback` | Callback | Mit Callback | Einmal aufgerufen |
| `test_handler_prints_abort_banner` | Banner | Ausgeführt | `"ABGEBROCHEN"` in stderr |
| `test_all_sections_present` | Hilfe | Alle Parameter | 8 Abschnitte |
| `test_empty_sections_omitted` | Optional | Nur `what` | Nur `what` angezeigt |
| `test_runs_without_error` | Windows-ANSI | Aufruf | Keine Exception |
| `test_add_no_color_arg` | CLI-Arg | Parser-Setup | `--no-color` akzeptiert |
| `test_apply_disables_color` | Deaktivierung | `--no-color` | `get_use_color()=False` |
