---
description: Waehlt optimale 50-100 Dokumente fuer RAGAS Testkorpus (J1). Kriterien: Diversity, Repraesentativitaet, Qualitaet, Balance (Pages vs Media, kurz vs lang).
globs: ["**/pipeline_results_*.json", "**/preprocessed/**"]
alwaysApply: false
---

# Test Corpus Selection

**Zweck:** Waehlt die optimalen 50-100 Dokumente fuer den RAGAS Testkorpus gemaess Forschungsfrage J1.

## Kriterien

- **Diversity** – Verschiedene Namespaces (departm, teacher, org, exams, etc.)
- **Repraesentativitaet** – Typische DokuWiki-Strukturen (Seiten mit Links, Tabellen, Media)
- **Qualitaet** – Hohe Scores aus Document Quality Assessment
- **Balance** – Mix aus Pages und Media; kurze und laengere Dokumente

## Skript

```bash
python evaluation/ragas_agents/scripts/select_test_corpus.py --pipeline-results <pipeline_results_*.json> --quality-scores <assess_document_quality_output> [--min-docs 50] [--max-docs 100]
```

## Eingaben

- `pipeline_results_*.json` (Seiten-/Media-Statistik, Namespaces)
- Optional: Output von Document Quality Assessment (Quality-Scores)
- Config: `evaluation/ragas_agents/config/ragas_config.yaml` (min/max Dokumente)

## Ausgaben

- **test_corpus_manifest.json** – Liste der ausgewaehlten Dokumente mit Pfaden, Namespace, Typ (page/media)
- Optional: Kopien oder Symlinks in `evaluation/ragas_agents/output/test_corpus/`

## Hinweise

- J1 verlangt ca. 50-100 Wiki-Seiten und ca. 20-30 Testfragen; dieser Skill liefert den Corpus
- Manifest wird von Ground Truth Engineer (Question Generation, Answer Creation) genutzt
