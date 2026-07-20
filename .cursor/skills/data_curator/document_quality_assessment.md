---
description: Bewertet Qualitaet einzelner Dokumente fuer Testkorpus-Eignung. Metriken: Content completeness, Link integrity, Readability (Flesch), Structure preservation.
globs: ["**/preprocessed/**/*.md"]
alwaysApply: false
---

# Document Quality Assessment

**Zweck:** Bewertet die Qualitaet einzelner Dokumente (preprocessed Markdown) fuer die Eignung im RAGAS Testkorpus.

## Metriken

- **Content completeness** – Anteil erhaltener Inhalte (Token/Zeichen-Vergleich Original vs. preprocessed)
- **Link integrity** – Links erhalten (bereits 100% in Pipeline dokumentiert)
- **Readability** – Flesch Reading Ease (Deutsch: Schwellwert ca. 20 fuer technische Texte)
- **Structure preservation** – Headings, Listen, Absaetze erhalten

## Skript

```bash
python evaluation/ragas_agents/scripts/assess_document_quality.py --input <preprocessed_dir> [--config evaluation/ragas_agents/config/ragas_config.yaml]
```

## Eingaben

- Verzeichnis mit preprocessed Markdown-Dateien (z.B. `preprocessed_at_*` oder `for_qdrant/upload_at_*`)
- Optional: Config mit Schwellwerten fuer Readability, Completeness

## Ausgaben

- Pro-Dokument-Scores (JSON oder CSV)
- Aggregierte Qualitaets-Scores fuer Corpus Selection
- Liste von Dokumenten unter Schwellwert (zur Filterung)

## Hinweise

- Deutsche technische Dokumente: Flesch-Threshold niedriger (20) als fuer Englisch (30)
- Ergebnisse fliessen in Test Corpus Selection ein (Skill 3)
