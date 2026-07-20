---
description: Evaluiert Retrieval-Strategien (J6: Hybrid vs Dense). Dense, BM25, Hybrid. Metriken: Precision@5, NDCG@10, Recall@k. RAGAS ContextRelevancy, ContextUtilization.
globs: ["**/qdrant/**", "**/test_corpus/**"]
alwaysApply: false
---

# Retrieval Quality Metrics

**Zweck:** Evaluiert Retrieval-Strategien – Dense vs BM25 vs Hybrid – fuer LeoWiki-Inhalte (Forschungsfrage J6).

## Tests

- **Dense Retrieval** – Nur Vektor-Suche (Embedding + ANN)
- **BM25 Retrieval** – Nur Keyword-Suche
- **Hybrid Search** – Kombination (z.B. gewichtete Fusion oder RRF)

## Metriken

- **Precision@5** – Hauptmetrik fuer J6
- **NDCG@10**
- **Recall@k** – Optional

## RAGAS Metriken

- **ContextRelevancy** – Relevanz des gelieferten Kontexts zur Frage
- **ContextUtilization** – Wird der Kontext genutzt?

## Skript

```bash
python evaluation/ragas_agents/scripts/evaluate_retrieval.py --ground-truth <ground_truth_dataset.json> --qdrant-url <url> [--strategies dense,bm25,hybrid] [--output evaluation_results_retrieval.json]
```

## Eingaben

- `ground_truth_dataset.json`
- Qdrant-Instanz (URL, API-Key) oder lokale Collection
- Config: Alpha fuer Hybrid (Gewicht Dense vs BM25), k

## Ausgaben

- **evaluation_results_retrieval.json** – Pro Strategie: Precision@5, NDCG@10; Ergebnistabelle fuer Kap. 6.6
- Optional: Pro-Frage-Vergleich (welche Strategie gewinnt pro Frage)

## Hinweise

- J6: Bringt Hybrid Search messbaren Vorteil gegenueber reiner Dense Retrieval? Ergebnistabelle + Diskussion; keine Signifikanzaussage noetig
- Chunk-Groesse (J4): Gleicher Skript mit verschiedenen Chunk-Sizes oder separater Lauf
