---
description: Generiert 20-30 Testfragen aus ausgewaehltem Corpus (J1). Single-Hop/Multi-Hop, spezifisch/abstrakt, deutschsprachig HTL-relevant. RAGAS TestsetGenerator.
globs: ["**/test_corpus_manifest.json"]
alwaysApply: false
---

# Question Generation

**Zweck:** Generiert 20-30 Testfragen aus dem ausgewaehlten Testkorpus gemaess Forschungsfrage J1.

## Strategien

- **Single-Hop Queries** – Spezifisch (faktisch) und abstrakt (erklaerend)
- **Multi-Hop Queries** – Spezifisch und abstrakt, mehrere Quellen
- **Deutschsprachig** – HTL-LeoWiki-relevante Themen (Lehrplaene, Pruefungen, Abteilungen, etc.)

## RAGAS Integration

- **TestsetGenerator** aus Ragas Library nutzen fuer synthetische Frage-Generierung
- Optional: Eigene Prompts fuer deutschsprachige, domaenenspezifische Fragen

## Skript

```bash
python evaluation/ragas_agents/scripts/generate_questions.py --manifest <test_corpus_manifest.json> --corpus-dir <test_corpus_dir> [--num-questions 25] [--output questions.json]
```

## Eingaben

- `test_corpus_manifest.json` (Output von Test Corpus Selection)
- Optional: Verzeichnis mit Corpus-Dateien fuer Kontext
- Config: Anzahl Fragen (20-30), Balance Single-Hop/Multi-Hop

## Ausgaben

- **questions.json** – Liste der generierten Fragen mit question_id, question_text, query_type (single_hop/multi_hop), source_doc_ids
- Optional: RAGAS-Format fuer TestsetGenerator-Output

## Hinweise

- J1: ca. 20-30 Testfragen mit selbst erstellten Relevanzurteilen; dieser Skill liefert die Fragen
- Naechster Schritt: Answer Creation (Skill 6), dann Relevance Judgment (Skill 7)
