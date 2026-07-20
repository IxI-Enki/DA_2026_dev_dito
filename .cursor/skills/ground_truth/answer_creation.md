---
description: Erstellt Reference Answers fuer generierte Fragen. Methoden: Extractive (aus Dokumenten), Abstractive (LLM, human-reviewed), Hybrid.
globs: ["**/questions.json", "**/test_corpus/**"]
alwaysApply: false
---

# Answer Creation

**Zweck:** Erstellt Reference Answers (Ground-Truth-Antworten) fuer die generierten Testfragen.

## Methoden

- **Extractive** – Direkt aus Dokumenten extrahierte Saetze/Absaetze
- **Abstractive** – LLM-generierte Antwort, human-reviewed
- **Hybrid** – Kombination: Kernfakten extrahiert, Formulierung angepasst

## Skript

```bash
python evaluation/ragas_agents/scripts/create_answers.py --questions <questions.json> --corpus-dir <test_corpus_dir> [--method hybrid] [--output answers.json]
```

## Eingaben

- `questions.json` (Output von Question Generation)
- Testkorpus-Verzeichnis (preprocessed Markdown) fuer Kontext
- Optional: method (extractive | abstractive | hybrid)

## Ausgaben

- **answers.json** oder Erweiterung von questions.json: pro Frage reference_answer, source_chunks, method_used
- Format kompatibel mit RAGAS Evaluation Dataset (user_input, reference, retrieved_contexts, response)

## Hinweise

- Fuer RAGAS: reference (Ground-Truth-Antwort) wird fuer AnswerCorrectness etc. genutzt
- Pragmatisch: Eigene Beurteilung genuegt (kein Crowd-Sourcing); human-review fuer Abstractive/Hybrid empfohlen
