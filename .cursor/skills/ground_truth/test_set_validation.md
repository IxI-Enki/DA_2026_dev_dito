---
description: Validiert Qualitaet des Ground-Truth Datasets. Checks: Frage-Antwort-Konsistenz, Diversity, Balance Single-Hop/Multi-Hop, Beantwortbarkeit mit Corpus.
globs: ["**/ground_truth_dataset.json"]
alwaysApply: false
---

# Test Set Validation

**Zweck:** Validiert die Qualitaet des zusammengestellten Ground-Truth Datasets vor der RAG-Evaluation.

## Checks

- **Frage-Antwort-Konsistenz** – Jede Frage hat eine Reference Answer; Antwort passt zur Frage
- **Diversity** – Verschiedene Query-Types (single_hop, multi_hop, spezifisch, abstrakt)
- **Balance** – Ausgewogenes Verhaeltnis Single-Hop vs Multi-Hop (z.B. 60/40 oder 70/30)
- **Beantwortbarkeit** – Alle Fragen sind mit dem ausgewaehlten Corpus beantwortbar (keine Fragen zu fehlenden Themen)

## Skript

```bash
python evaluation/ragas_agents/scripts/validate_test_set.py --dataset <ground_truth_dataset.json> [--corpus-dir <test_corpus_dir>] [--output validation_report.json]
```

## Eingaben

- `ground_truth_dataset.json` – Kombination aus questions, answers, relevance_judgments im RAGAS-kompatiblen Format
- Optional: Corpus-Verzeichnis fuer Beantwortbarkeits-Check (Abgleich mit source_doc_ids)

## Ausgaben

- **validation_report.json** – passed: bool, checks: { consistency, diversity, balance, answerability }, issues: [...]
- Optional: Liste von Fragen mit Problemen (fehlende Antwort, kein relevantes Dokument, etc.)

## Hinweise

- Vor Embedding/Retrieval-Evaluation ausfuehren; bei Failed-Validierung zuerst Ground-Truth korrigieren
- RAGAS erwartet: user_input, reference, retrieved_contexts, response (response wird spaeter von RAG befuellt)
