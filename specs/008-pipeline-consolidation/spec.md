# Feature Specification: Pipeline Consolidation

**Feature Branch**: `008-pipeline-consolidation`
**Created**: 2026-02-14
**Status**: Draft
**Thesis-Zuordnung**: FF1, FF3, J1, J2, J3, J4, J6
**Constitution**: v1.4.0 (Article X: Execution Mandate, Article XI: Thesis Alignment)
**Gap Analysis**: `docs/gap_analysis_prototypes_vs_pipeline.md`
**Depends On**: 007-evaluation-infrastructure (Phases 1-7 complete)

---

## Kontext

Feature 007 lieferte die **Evaluations-Infrastruktur**: reine IR-Metriken (MRR, NDCG@K, P@K mit 56 Tests), Embedding-Provider-Abstraktion und 5 Evaluations-Skripte fuer Thesis-Tabellen. Was FEHLT, sind drei Ebenen:

1. **RAGAS-Integration** (LLM-as-Judge): Die RAGAS.io-Library fuer qualitative Metriken (Context Precision/Recall, Faithfulness, Answer Correctness) -- notwendig fuer wissenschaftliche Diskussion der Ergebnisse.
2. **Statistische Analyse**: Bootstrap-Konfidenzintervalle, Signifikanztests (t-Test, Wilcoxon), Effektgroessen (Cohen's d) -- notwendig fuer begruendete Vergleiche ("Modell A ist besser als B").
3. **Preprocessing-Pipeline**: Die Bruecke zwischen gefetchten Wiki-Daten und Embeddings (DokuWiki-Parsing, Metadaten-Anreicherung, Media-OCR, Strategy-Routing) ist unvollstaendig.

Eine Gap-Analyse (2026-02-14) zeigt: 30 von 61 Prototyp-Features sind portiert (49%), 7 teilweise (11%), 24 fehlen (39%). Die 3 **Critical** und 5 **High** Gaps blockieren alle die Thesis-Qualitaet.

**Betroffene Schichten**: `evaluation/` (RAGAS, Statistik, Visualisierung), `pipeline/03_rag_preprocessing/` (Preprocessing), `pipeline/05_deploy/` (Qdrant-Deployment)
**Abgrenzung**: MCP-Server (Imres Teil) wird NICHT veraendert. Pipeline Stages 1-2 (Fetch, Deep Evaluation) und Stage 3b (Embeddings Creator) sind bereits portiert und werden nicht umgeschrieben.

---

## Gesamtpipeline nach Abschluss

```sketch
[Stage 1: Fetch]        wiki_fetcher -> data/fetched/
        |
[Stage 2: Evaluate]     deep_evaluation -> data/evaluated/
        |
[Stage 3a: Preprocess]  rag_preprocessing -> data/preprocessed/
        |                 (wiki-to-markdown, OCR, metadata, strategy routing)
        |
[Stage 3b: Embed]       embeddings_creator -> data/embeddings/
        |                 (chunk -> embed -> JSONL)
        |
[Stage 4: Deploy]       deploy -> Qdrant
        |                 (direct upload OR MCP watchdog folder)
        |
[Stage 5: Evaluate]     RAGAS + Custom Metrics -> evaluation/results/
                          (MRR, NDCG, P@K + Context P/R, Faithfulness)
                        + Statistical Analysis
                        + Visualizations
                        + Reports
```

---

## User Stories

### US1 -- RAGAS.io LLM-as-Judge Integration (Priority: P1-Critical)

Als Thesis-Autor will ich die 50 Ground-Truth-Fragen durch die RAGAS.io-Library evaluieren lassen, um qualitative Metriken (Context Precision, Context Recall, Faithfulness, Answer Correctness) zu erhalten, die meine quantitativen IR-Metriken ergaenzen.

**Why Critical**: Ohne LLM-basierte Metriken fehlt die qualitative Diskussionsebene. Die Thesis braucht sowohl "wie oft wurde das richtige Dokument gefunden" (MRR/P@K) als auch "wie gut war die Antwort inhaltlich" (RAGAS).

**Gap-Referenz**: #29 (RAGASMetricsCalculator), #35 (ProfessionalRAGEvaluator), #40 (QdrantEvaluator)

**Acceptance Criteria**:

1. **Given** die RAGAS.io-Library ist installiert (`pip install ragas datasets langchain-openai`), **When** `python eval_ragas.py --config experiment.yaml` ausgefuehrt wird, **Then** werden Context Precision, Context Recall, Faithfulness und Answer Correctness fuer alle 50 Ground-Truth-Fragen berechnet.
2. **Given** Ollama laeuft auf `192.168.8.3:11434` mit einem kompatiblen Modell, **When** RAGAS ausgefuehrt wird, **Then** verwendet es die Ollama OpenAI-kompatible API (kein OpenAI-Key noetig).
3. **Given** RAGAS-Ergebnisse und Custom-Metriken liegen vor, **When** ein Report generiert wird, **Then** enthaelt er beide Metrik-Familien nebeneinander in einer Tabelle.
4. **Given** eine einzelne RAGAS-Berechnung fehlschlaegt (LLM-Timeout), **When** die Evaluation laeuft, **Then** wird der Fehler geloggt und die naechste Frage evaluiert (kein Gesamtabbruch).

**Technische Randbedingung**: RAGAS.io Library verwenden, NICHT Custom-Reimplementation. Deutscher System-Prompt. `temperature=0.0` fuer Reproduzierbarkeit.

---

### US2 -- Statistische Analyse (Priority: P1-Critical)

Als Thesis-Autor will ich die Evaluationsergebnisse statistisch analysieren koennen (Konfidenzintervalle, Signifikanztests, Effektgroessen), um begruendete Vergleichsaussagen zu treffen.

**Why Critical**: Ohne statistische Analyse sind Aussagen wie "Modell A ist besser als B" oder "Hybrid Search bringt einen Vorteil" nicht wissenschaftlich begruendet.

**Gap-Referenz**: #30 (StatisticalAnalyzer), #38 (compare_with_baseline)

**Hinweis zur Thesis**: Die Forschungsfragen J4 und J6 sagen explizit "keine statistische Signifikanzaussage noetig" -- aber die Infrastruktur SOLL vorhanden sein fuer die Diskussion. Wir praesentieren die Statistik als zusaetzliche Evidenz, nicht als Hauptargument.

**Acceptance Criteria**:

1. **Given** zwei Evaluations-Ergebnisdateien (z.B. `model_bge_m3.json` und `model_e5.json`), **When** `python eval_compare.py --baseline model_bge_m3.json --candidate model_e5.json` ausgefuehrt wird, **Then** werden Bootstrap-95%-CI, paired t-test (oder Wilcoxon), und Cohen's d berechnet.
2. **Given** eine einzelne Ergebnisdatei, **When** `python eval_statistics.py --results model_bge_m3.json` ausgefuehrt wird, **Then** werden Deskriptivstatistik (Mean, Median, Std, Q1/Q3) und 95%-Bootstrap-CIs pro Metrik ausgegeben.
3. **Given** Ergebnisse nach Schwierigkeitsgrad vorliegen, **When** Statistik berechnet wird, **Then** wird auch eine Breakdown-Tabelle pro Difficulty-Level erzeugt.

---

### US3 -- Visualisierung (Priority: P2-High)

Als Thesis-Autor will ich automatisch generierte Diagramme (Radar, Box-Plot, Heatmap, Bar-Chart) fuer die Thesis-Kapitel erhalten.

**Gap-Referenz**: #32 (RAGVisualization)

**Acceptance Criteria**:

1. **Given** Evaluationsergebnisse fuer 3+ Modelle liegen vor, **When** `python eval_visualize.py --results-dir evaluation/results/` ausgefuehrt wird, **Then** werden PNG-Dateien generiert: Radar-Chart (alle Metriken), Box-Plot (Score-Verteilungen), Bar-Chart (Modellvergleich).
2. **Given** ein `--format svg` Flag, **When** Visualisierung laeuft, **Then** werden SVG-Dateien fuer LaTeX-Einbindung erzeugt.
3. **Given** eine generierte PNG-Datei, **When** die Metadaten geprueft werden, **Then** ist DPI >= 300 und alle Achsenbeschriftungen sind Deutsch. Keine informellen Farben (akademisches Farbschema).
4. **Given** eine generierte SVG-Datei, **When** sie in LaTeX via `\includegraphics` eingebunden wird, **Then** ist sie skalierbar ohne Qualitaetsverlust.

---

### US4 -- Report-Generator (Priority: P2-High)

Als Thesis-Autor will ich strukturierte Evaluationsberichte (Markdown + JSON) generieren, die alle Metriken, Statistiken und Konfigurationen dokumentieren.

**Gap-Referenz**: #33 (ReportGenerator), #31 (CategoryAnalyzer)

**Acceptance Criteria**:

1. **Given** eine abgeschlossene Evaluation, **When** `python eval_report.py --results evaluation/results/experiment_xyz/` ausgefuehrt wird, **Then** wird ein Markdown-Report mit Executive Summary, Metrik-Tabellen, Difficulty-Breakdown und Konfigurationsdetails erzeugt.
2. **Given** RAGAS-Ergebnisse und Custom-Metriken vorliegen, **Then** enthaelt der Report beide Metrik-Familien.
3. Jeder Report enthaelt: Timestamp, Config-Hash, Code-Version (NFR-005).

---

### US5 -- Preprocessing-Pipeline vervollstaendigen (Priority: P1-Critical)

Als Pipeline-Betreiber will ich gefetchte DokuWiki-Daten zuverlaessig zu sauberem Markdown mit Metadaten konvertieren, damit Stage 3b (Embeddings) qualitativ hochwertigen Input erhaelt.

**Gap-Referenz**: #51 (DokuWikiParser), #52 (Strategy-Routing), #53 (MetadataEnricher), #55 (StrategyLoader), #56 (MediaProcessor), #57 (Exporter)

**Acceptance Criteria**:
1. **Given** gefetchte Wiki-Seiten in `data/fetched/fetched_at_*/page_content/`, **When** `python run_preprocessing.py` ausgefuehrt wird, **Then** werden alle Seiten zu Markdown konvertiert mit YAML-Frontmatter (title, namespace, last_modified, access_level, freshness_score) und nach `data/preprocessed/` exportiert.
2. **Given** Deep-Evaluation-Strategien existieren in `data/evaluated/`, **When** Preprocessing laeuft, **Then** werden Seiten gemaess ihrer Content-Strategie (KNOWLEDGE, NEWS, PORTAL) unterschiedlich verarbeitet.
3. **Given** Media-Dateien (PDF, Bilder) existieren in `data/fetched/*/media/`, **When** Preprocessing laeuft, **Then** werden PDFs via Text-Extraktion und Bilder via OCR (Tesseract) zu Text konvertiert und als separate Markdown-Dateien exportiert.
4. **Given** eine Wiki-Seite mit DokuWiki-Syntax (Headlines ====, Links [[]], Tables ^ |), **When** sie verarbeitet wird, **Then** wird sauberes Markdown erzeugt mit < 1% verbleibender Wiki-Syntax-Reste.
5. **Given** eine Wiki-Seite mit Entitaeten (Raum E309, Datum 15.03.2026, Email foo@bar.at), **When** sie verarbeitet wird, **Then** bleiben alle Entitaeten im Output erhalten.
---

### US6 -- Qdrant-Deployment (Priority: P2-High)

Als Pipeline-Betreiber will ich Embeddings wahlweise direkt in Qdrant hochladen (Testing) oder in ein MCP-Server-Watchdog-Verzeichnis exportieren (Produktion).

**Gap-Referenz**: Teilweise in `04_deploy/` vorhanden, aber unvollstaendig.

**Acceptance Criteria**:

1. **Given** JSONL-Embeddings in `data/embeddings/`, **When** `python deploy_qdrant.py --mode direct --host 192.168.8.3 --port 6333` ausgefuehrt wird, **Then** werden die Embeddings in eine Qdrant-Collection hochgeladen (direct upload via `qdrant_client`).
2. **Given** JSONL-Embeddings in `data/embeddings/`, **When** `python deploy_qdrant.py --mode watchdog --output /path/to/mcp/watchdir/` ausgefuehrt wird, **Then** werden die Dateien in das Watchdog-Verzeichnis kopiert fuer automatisches Einlesen.
3. **Given** eine Collection mit demselben Namen existiert bereits, **When** Deploy mit `--recreate` laeuft, **Then** wird die alte Collection geloescht und neu erstellt.
4. **Given** Deploy laeuft ohne `--recreate`, **When** die Collection existiert, **Then** werden nur neue/geaenderte Punkte upserted.

---

### US7 -- Unified Evaluation Orchestrator (Priority: P2-High)

Als Thesis-Autor will ich eine einzelne Evaluation-Pipeline ausfuehren koennen, die Custom-Metriken + RAGAS + Statistik + Visualisierung + Report in einem Lauf kombiniert.

**Gap-Referenz**: #35 (ProfessionalRAGEvaluator)

**Acceptance Criteria**:

1. **Given** eine Experiment-Config `evaluation/experiments/full_eval.yaml`, **When** `python eval_pipeline.py --config full_eval.yaml` ausgefuehrt wird, **Then** werden nacheinander ausgefuehrt: (1) Qdrant-Retrieval, (2) Custom-Metriken, (3) RAGAS-Metriken, (4) Statistik, (5) Visualisierung, (6) Report-Export.
2. **Given** ein `--skip ragas` Flag, **When** die Pipeline laeuft, **Then** werden nur Custom-Metriken + Statistik + Report erzeugt (fuer schnelle Iterationen ohne LLM-Kosten).
3. **Given** alle Schritte laufen, **Then** werden alle Ergebnisse in `evaluation/results/{experiment_name}_{timestamp}/` gespeichert mit config-hash und code-version.

---

### US8 -- Zusaetzliche IR-Metriken (Priority: P3-Medium)

Als Thesis-Autor will ich MAP, Recall@K und Hit Rate als zusaetzliche Metriken verfuegbar haben.

**Gap-Referenz**: #42 (MAP), #43 (Recall@K), #44 (F1@K), #45 (Hit Rate)

**Acceptance Criteria**:

1. **Given** die bestehende Metrik-Architektur (`evaluation/metrics/`), **When** MAP, Recall@K und Hit Rate implementiert werden, **Then** folgen sie demselben Pattern (pure functions, type hints, eigene Testdateien).
2. **Given** alle neuen Metriken, **When** `pytest evaluation/tests/` laeuft, **Then** bestehen alle Tests (bestehende 56 + neue).

---

## Nicht-Funktionale Anforderungen

| ID      | Anforderung         | Beschreibung                                                                                                                                        |
| ------- | ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| NFR-001 | Python 3.11+        | Type Hints, `from __future__ import annotations`                                                                                                    |
| NFR-002 | TDD                 | Tests VOR oder GLEICHZEITIG mit Implementation. Jede neue Funktion hat Tests.                                                                       |
| NFR-003 | Constitution v1.4.0 | Article VIII (Direct SDK), Article VI (Secrets in .token), Article X (Execution Mandate)                                                            |
| NFR-004 | YAML Config         | Experiment-Konfiguration via YAML, Secrets in separaten .token-Dateien                                                                              |
| NFR-005 | Reproduzierbarkeit  | Alle Ergebnisse enthalten: Timestamp, Config-Hash, Code-Version                                                                                     |
| NFR-006 | Fehlertoleranz      | Pipeline-Schritte loggen Fehler und setzen mit naechstem Item fort                                                                                  |
| NFR-007 | Dependencies        | RAGAS: `ragas`, `datasets`, `langchain-openai`. Statistik: `scipy`, `numpy`. Visualisierung: `matplotlib`, `seaborn`. OCR: `pytesseract`, `Pillow`. |

---

## Abhaengigkeiten und Risiken

| Risiko                           | Wahrscheinlichkeit | Impact  | Mitigation                                            |
| -------------------------------- | ------------------ | ------- | ----------------------------------------------------- |
| RAGAS.io API-Aenderungen         | Mittel             | Hoch    | Version pinnen, Prototyp-Code als Fallback            |
| Ollama nicht erreichbar          | Niedrig            | Hoch    | Graceful degradation: Skip RAGAS, nur Custom-Metriken |
| Tesseract OCR-Qualitaet          | Mittel             | Niedrig | OCR nur als Supplement, nicht als primaere Textquelle |
| Qdrant auf Raspberry Pi Speicher | Mittel             | Mittel  | Collection-Size-Check vor Upload, Warnung bei > 500MB |

---

## Scope-Abgrenzung

**IN Scope:**
- RAGAS.io Integration via Ollama OpenAI-kompatible API
- Statistische Analyse (Bootstrap, Signifikanztests, Effektgroessen)
- Visualisierungen fuer Thesis (PNG/SVG)
- Preprocessing: DokuWiki -> Markdown + Frontmatter + OCR
- Qdrant-Deployment (direct + watchdog)
- Unified Evaluation Orchestrator
- Zusaetzliche IR-Metriken (MAP, Recall@K, Hit Rate)

**OUT of Scope:**
- MCP-Server-Aenderungen (Imres Teil)
- Pipeline Stage 1 (Wiki Fetcher) -- bereits vollstaendig portiert
- Pipeline Stage 2 (Deep Evaluation) -- bereits vollstaendig portiert
- RAGFlow-Integration (Article VIII: Direct SDK, wir verwenden Qdrant direkt)
- Docker-Compose-Aenderungen an Backend-Services
- OAuth2/Scalekit-Integration (J7, separates Feature)
