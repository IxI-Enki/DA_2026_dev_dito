---
description: Evaluiert Preprocessing-Qualitaet. Nutzt techstack/ragflow/preprocessing_evaluation. Metriken: information_preservation, content_quality, error_detection.
globs: ["**/preprocessing_evaluation/results/**/*.json"]
alwaysApply: false
---

# Preprocessing Evaluation

**Zweck:** Evaluiert die Qualitaet der RAG-Preprocessing-Pipeline (DokuWiki zu Markdown/Plaintext) ueber das bestehende Framework.

## Integration

- **Framework:** `techstack/ragflow/preprocessing_evaluation/` (script/, config/, results/)
- **Metriken:** information_preservation (content_completeness, semantic_similarity, entity_preservation, link_integrity), content_quality (noise_detection, readability, structure_preservation), error_detection

## Skript

```bash
python evaluation/ragas_agents/scripts/run_preprocessing_eval.py --original-dir <fetched_dir> --preprocessed-dir <preprocessed_dir> [--config <path_to_preprocessing_evaluation/config>]
```

Alternativ: Direkt das bestehende Framework aufrufen, wenn Pfade im techstack-Repo liegen:

```bash
python <techstack>/ragflow/preprocessing_evaluation/script/run_evaluation.py ...
```

## Eingaben

- Original-Daten (fetched_at_*)
- Preprocessed-Daten (preprocessed_at_* oder for_qdrant/upload_at_*)
- Optional: Eigenes Config-Verzeichnis fuer Schwellwerte

## Ausgaben

- Evaluation-Report (JSON) in `preprocessing_evaluation/results/`
- Zusammenfassung: Pass/Fail pro Metrik, Information Preservation / Content Quality Scores
- Optional: EVALUATION_SUMMARY.md

## Hinweise

- Ergebnisse interpretieren: 100% link_integrity, hohe content_completeness = Pipeline vertrauenswuerdig fuer Testkorpus
- Bei Fehlern: Auf EVALUATION_SUMMARY.md und Fixes im Preprocessing-Code verweisen
