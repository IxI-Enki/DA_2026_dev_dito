# Feature Specification: Evaluation Infrastructure

**Feature Branch**: `007-evaluation-infrastructure`
**Created**: 2026-02-12
**Status**: Draft
**Thesis-Zuordnung**: FF1, FF3, J1, J2, J4, J6
**Constitution**: v1.3.0 (Article X: Evaluation-First, Article XI: Thesis Milestone Alignment)
**Target Milestone**: 2026-03-15

## Kontext

Die Diplomarbeit erfordert quantitative Nachweise fuer drei zentrale Forschungsfragen:
- **FF1**: Semantische Suche vs. Keyword-Suche (MRR, Precision@5)
- **FF3**: Bestes Embedding-Modell fuer deutschsprachige Wiki-Inhalte (NDCG@10)
- **J4**: Einfluss der Chunk-Groesse auf Retrieval-Qualitaet

Aktuell existieren einzelne Prototypen in `research/techstack/` (RAGAS-Evaluierungen, Qdrant-Embeddings-Creator, RAGFlow-Preprocessing), aber KEIN zusammenhaengendes Evaluations-Framework, das:
1. Eine Keyword-Search-Baseline gegen DokuWikis `core.searchPages` erzeugt (FF1-Blocker)
2. Verschiedene Embedding-Modelle austauschbar macht (FF3-Blocker: Ollama, OpenAI, MTEB-Modelle)
3. Chunk-Groessen parametrisch variiert und vergleicht (J4-Blocker)
4. Reproduzierbare Ergebnistabellen fuer die Thesis generiert

**Betroffene Schichten**: Pipeline (Python), Backend Services (Docker/Qdrant)
**Betroffene Docker-Services**: module_embedder (config swap), qdrant (test collections)
**Abgrenzung**: MCP-Server (Stack-H) wird NICHT veraendert. Bestehende Pipeline-Skripte werden wiederverwendet, nicht umgeschrieben.

---

## User Scenarios & Testing

### User Story 1 - Keyword Search Baseline (Priority: P1)

Als Thesis-Autor (Jan) will ich die 50 verifizierten Ground-Truth-Fragen aus `leowiki_qa_50_verified.json` gegen DokuWikis native `core.searchPages` API ausfuehren und MRR sowie Precision@5 berechnen, um die FF1-Vergleichstabelle zu fuellen.

**Why this priority**: Ohne Keyword-Baseline kann FF1 ("Inwiefern verbessert semantische Suche die Auffindbarkeit?") nicht beantwortet werden. Dies ist der zentrale Vergleichspunkt der gesamten Arbeit.

**Independent Test**: Skript laeuft standalone gegen die LeoWiki JSON-RPC API, benoetigt nur die Ground-Truth-Datei und Wiki-Zugang. Liefert eine JSON-Datei mit MRR und P@5 pro Query.

**Acceptance Scenarios**:

1. **Given** die Datei `evaluation/ground_truth/leowiki_qa_50_verified.json` existiert mit mindestens 30 Q&A-Paaren, **When** `python eval_keyword_baseline.py` ausgefuehrt wird, **Then** wird eine Ergebnis-Datei `evaluation/results/keyword_baseline_{timestamp}.json` erzeugt mit MRR und Precision@5 pro Query sowie Durchschnittswerten.
2. **Given** die DokuWiki JSON-RPC API ist nicht erreichbar, **When** das Skript ausgefuehrt wird, **Then** wird ein klarer Fehler mit Verbindungsdetails geloggt und Exit Code 1 zurueckgegeben.
3. **Given** eine Ground-Truth-Frage hat keine relevanten Ergebnisse in der Keyword-Suche, **When** die Metrik berechnet wird, **Then** wird MRR=0 und P@5=0 fuer diese Query korrekt erfasst (kein Skip, kein Crash).

---

### User Story 2 - Model-Agnostic Embedding Evaluation (Priority: P1)

Als Thesis-Autor (Jan) will ich verschiedene Embedding-Modelle (Ollama-basiert, OpenAI API, beliebige MTEB-Modelle) gegen denselben Testkorpus evaluieren und NDCG@10 sowie MRR pro Modell vergleichen, um FF3 zu beantworten.

**Why this priority**: FF3 ("Welches Embedding-Modell erzielt die beste Retrieval-Qualitaet?") erfordert einen Vergleich von mindestens 3 Modellen. Ohne Model-Swap-Faehigkeit existiert keine Vergleichstabelle.

**Independent Test**: Konfigurationsdatei wechselt das Modell (Name + Provider), Skript rechunked nicht (verwendet vorhandene Chunks), embeddet mit neuem Modell, deployed in Test-Collection, fuehrt Queries aus und berechnet Metriken.

**Acceptance Scenarios**:

1. **Given** eine Experiment-Config `evaluation/experiments/model_bge_m3.yaml` mit `provider: ollama` und `model: bge-m3`, **When** `python eval_model_comparison.py --config model_bge_m3.yaml` ausgefuehrt wird, **Then** werden Embeddings erzeugt, in eine temporaere Qdrant-Collection deployed, Ground-Truth-Queries ausgefuehrt und NDCG@10 + MRR berechnet.
2. **Given** eine Experiment-Config mit `provider: openai` und `model: text-embedding-3-large`, **When** dasselbe Skript ausgefuehrt wird, **Then** wird die OpenAI API verwendet und identische Metriken erzeugt.
3. **Given** 3+ Modell-Configs existieren, **When** `python eval_model_comparison.py --compare-all` ausgefuehrt wird, **Then** wird eine Vergleichstabelle (Markdown + JSON) mit allen Modellen nebeneinander erzeugt.

---

### User Story 3 - Chunk Size Parametric Evaluation (Priority: P1)

Als Thesis-Autor (Jan) will ich denselben Testkorpus mit verschiedenen Chunk-Groessen (256, 512, 1024 Token) verarbeiten und die Retrieval-Qualitaet pro Konfiguration vergleichen, um J4 zu beantworten.

**Why this priority**: J4 ("Wie beeinflusst die Chunk-Groesse die Retrieval-Qualitaet?") erfordert eine parametrische Evaluation. Ohne diese Tabelle fehlt ein vollstaendiges Kapitel in der Thesis.

**Independent Test**: Konfigurationsdatei setzt `chunk_size: 256|512|1024`, Skript chunked den Korpus neu, embeddet, deployed in Test-Collection, fuehrt Queries aus.

**Acceptance Scenarios**:

1. **Given** eine Experiment-Config `evaluation/experiments/chunk_256.yaml` mit `chunk_size: 256`, **When** `python eval_chunk_size.py --config chunk_256.yaml` ausgefuehrt wird, **Then** wird der Testkorpus mit 256-Token-Chunks verarbeitet, embeddet, und Retrieval-Metriken (NDCG@10, MRR, Precision@5) berechnet.
2. **Given** Ergebnisse fuer 256, 512 und 1024 Token existieren, **When** `python eval_chunk_size.py --compare` ausgefuehrt wird, **Then** wird eine Vergleichstabelle erzeugt.

---

### User Story 4 - Hybrid vs Dense Retrieval Comparison (Priority: P2)

Als Thesis-Autor (Jan) will ich Dense Retrieval (reine Vektorsuche) gegen Hybrid Search (Dense + BM25) auf identischem Testkorpus vergleichen, um J6 zu beantworten.

**Why this priority**: J6 beantwortet, ob Hybrid Search messbaren Vorteil bringt. Abhaengig von funktionierender Embedding-Pipeline (US2) und Test-Corpus (J1).

**Independent Test**: Qdrant-Collection mit vorhandenen Embeddings, Query-Modus umschalten (dense-only vs hybrid), Metriken vergleichen.

**Acceptance Scenarios**:

1. **Given** eine Qdrant-Collection mit Embeddings aus dem Testkorpus, **When** `python eval_hybrid_vs_dense.py` ausgefuehrt wird, **Then** werden beide Retrieval-Modi gegen dieselben Ground-Truth-Queries evaluiert und Precision@5 + NDCG@10 verglichen.
2. **Given** kein signifikanter Unterschied zwischen den Modi, **When** die Ergebnisse geschrieben werden, **Then** wird dies ehrlich dokumentiert (kein kuenstliches Aufblaehen negativer Ergebnisse).

---

### User Story 5 - Thesis-Ready Result Export (Priority: P2)

Als Thesis-Autor (Jan) will ich alle Evaluationsergebnisse in einem Format exportieren, das direkt in LaTeX-Tabellen uebernommen werden kann.

**Why this priority**: Die Thesis wird in LaTeX geschrieben. Manuelle Tabellen-Uebertragung ist fehleranfaellig.

**Independent Test**: Vorhandene JSON-Ergebnisse werden in LaTeX-Tabellen-Format konvertiert.

**Acceptance Scenarios**:

1. **Given** Evaluationsergebnisse in `evaluation/results/`, **When** `python eval_export_latex.py` ausgefuehrt wird, **Then** werden `.tex` Dateien mit `\begin{tabular}` erzeugt, die direkt in die Thesis eingebunden werden koennen.

---

### Edge Cases

- Was passiert, wenn ein Ollama-Modell nicht lokal verfuegbar ist? → Klare Fehlermeldung mit Download-Anweisung (`ollama pull <model>`)
- Was passiert, wenn die OpenAI API rate-limited? → Retry mit exponential backoff, Cost-Tracking pro Run
- Was passiert, wenn der Testkorpus weniger als 30 Fragen hat? → Warning, aber kein Abbruch (Metriken werden trotzdem berechnet)
- Was passiert, wenn Qdrant nicht erreichbar ist? → Verbindungstest am Anfang, klarer Fehler vor Embedding-Start
- Was passiert, wenn ein Chunk-Size-Run partial fehlschlaegt? → Bisherige Ergebnisse werden gespeichert, fehlgeschlagene Queries geloggt

---

## Requirements

### Functional Requirements

- **FR-001**: System MUSS Ground-Truth-Datei im JSON-Format laden (`question`, `expected_pages[]`, `relevance_scores[]`)
- **FR-002**: System MUSS DokuWikis `core.searchPages` via JSON-RPC aufrufen und Top-10-Ergebnisse erfassen
- **FR-003**: System MUSS MRR (Mean Reciprocal Rank) korrekt berechnen: 1/rank des ersten relevanten Ergebnisses
- **FR-004**: System MUSS Precision@k berechnen: Anteil relevanter Ergebnisse in Top-k
- **FR-005**: System MUSS NDCG@10 berechnen: Normalized Discounted Cumulative Gain mit 10 Ergebnissen
- **FR-006**: System MUSS Embedding-Provider abstrahieren: `OllamaProvider`, `OpenAIProvider` mit identischer Schnittstelle (`embed(texts: list[str]) -> list[list[float]]`)
- **FR-007**: System MUSS Experiment-Configs als YAML laden (Modell, Provider, Chunk-Size, Collection-Name)
- **FR-008**: System MUSS temporaere Qdrant-Collections fuer Experimente erstellen und nach Abschluss bereinigen
- **FR-009**: System MUSS Ergebnisse als JSON (maschinell) UND Markdown (menschlich) speichern
- **FR-010**: System MUSS LaTeX-Export fuer Ergebnistabellen bereitstellen
- **FR-011**: System MUSS Cost-Tracking fuer OpenAI-API-Aufrufe implementieren (Token-Count, geschaetzte Kosten)
- **FR-012**: System MUSS Qdrant Hybrid Search (dense + BM25) konfigurierbar aktivieren/deaktivieren

### Non-Functional Requirements

- **NFR-001**: Evaluation-Skripte MUESSEN ohne Docker lauffaehig sein (host-native Python, venv)
- **NFR-002**: Ergebnisse MUESSEN reproduzierbar sein (Config + Code-Version + Ground-Truth = identisches Ergebnis)
- **NFR-003**: OpenAI-API-Kosten pro Evaluations-Run MUESSEN unter $5 liegen
- **NFR-004**: Alle Evaluation-Skripte MUESSEN mit `python eval_*.py --help` eine Hilfemeldung anzeigen
- **NFR-005**: Ergebnisdateien MUESSEN Timestamp, Config-Hash und Code-Version enthalten

### Key Entities

- **GroundTruth**: Question, expected relevant page IDs, relevance scores (0-3 Skala)
- **EvalResult**: Config reference, per-query metrics, aggregate metrics, timestamp, code version
- **ExperimentConfig**: Provider (ollama/openai), model name, chunk size, collection name, retrieval mode (dense/hybrid)
- **EmbeddingProvider**: Abstract interface — `embed(texts) -> vectors`, `model_name`, `dimensions`

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: FF1-Vergleichstabelle (Keyword vs Semantic) existiert mit MRR und P@5 fuer mindestens 30 Queries
- **SC-002**: FF3-Modelltabelle vergleicht mindestens 3 Embedding-Modelle (1x Ollama, 1x OpenAI, 1x weiteres) mit NDCG@10
- **SC-003**: J4-Chunk-Size-Tabelle vergleicht 256/512/1024 Token mit identischen Queries und identischem Modell
- **SC-004**: J6-Hybrid-vs-Dense-Tabelle zeigt Precision@5 und NDCG@10 fuer beide Modi
- **SC-005**: Alle Ergebnisse sind als LaTeX-Tabellen exportierbar und direkt in die Thesis einbindbar
- **SC-006**: Jeder Evaluations-Run ist vollstaendig reproduzierbar aus (Config + Ground-Truth + Code-Commit)
- **SC-007**: Gesamtkosten aller OpenAI-Evaluations-Runs bleiben unter $25

---

## Vorgeschlagene Verzeichnisstruktur

```tree
evaluation/
├── ground_truth/
│   └── leowiki_qa_50_verified.json    # Existing (from research/techstack/ragas/)
├── experiments/
│   ├── keyword_baseline.yaml
│   ├── model_bge_m3.yaml
│   ├── model_openai_3large.yaml
│   ├── model_mxbai_embed_de.yaml
│   ├── chunk_256.yaml
│   ├── chunk_512.yaml
│   ├── chunk_1024.yaml
│   └── hybrid_vs_dense.yaml
├── providers/
│   ├── __init__.py
│   ├── base.py                        # Abstract EmbeddingProvider
│   ├── ollama_provider.py
│   └── openai_provider.py
├── metrics/
│   ├── __init__.py
│   ├── mrr.py
│   ├── precision_at_k.py
│   └── ndcg.py
├── scripts/
│   ├── eval_keyword_baseline.py       # US1
│   ├── eval_model_comparison.py       # US2
│   ├── eval_chunk_size.py             # US3
│   ├── eval_hybrid_vs_dense.py        # US4
│   └── eval_export_latex.py           # US5
├── results/                           # Gitignored except summaries
│   └── .gitkeep
└── README.md
```

---

## References

- Constitution v1.3.0: Article X (Evaluation-First), Article XI (Thesis Alignment)
- Ground Truth: `research/techstack/ragas/ground_truth/leowiki_qa_50_verified.json`
- Existing Embedding Pipeline: `pipeline/03_embeddings_creator/`
- Existing Chunker: `research/techstack/qdrant/embeddings_creator/content_aware_chunker.py`
- RAGAS Framework: `research/techstack/ragas/`
- DokuWiki JSON-RPC: `pipeline/01_wiki_fetcher/api_client.py`
- Forschungsfragen: `dev_prompts_instructions_notes/content/research_notes/shared/_froschungsfragen_de.md`
