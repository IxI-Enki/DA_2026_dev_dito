---
description: Evaluiert Embedding-Modelle (J2, FF3). NDCG@10, MRR, Precision@5. Modelle: deepset/mxbai-embed-de-large-v1, BAAI/bge-m3, multilingual-e5-large-instruct. RAGAS ContextPrecision, ContextRecall.
globs: ["**/embedding_statistics.json", "**/embedded_chunks.jsonl"]
alwaysApply: false
---

# Embedding Evaluation

**Zweck:** Evaluiert Embedding-Modelle fuer deutschsprachige LeoWiki-Inhalte (Forschungsfrage FF3, J2).

## Metriken

- **NDCG@10** – Hauptmetrik fuer FF3 und J2
- **MRR** – Mean Reciprocal Rank
- **Precision@5** – Anteil relevanter Dokumente in Top-5

## RAGAS Metriken

- **ContextPrecision** – Wie praezise ist der gelieferte Kontext?
- **ContextRecall** – Wurden alle relevanten Dokumente gefunden?

## Modelle (J2)

- `deepset/mxbai-embed-de-large-v1`
- `BAAI/bge-m3`
- `multilingual-e5-large-instruct`

## Skript

```bash
python evaluation/ragas_agents/scripts/evaluate_embeddings.py --ground-truth <ground_truth_dataset.json> --embeddings-dir <path_to_embedded_chunks> [--models mxbai,bge-m3,e5] [--output evaluation_results_embeddings.json]
```

## Eingaben

- `ground_truth_dataset.json` (inkl. relevance_judgments fuer NDCG)
- Embedding-Output: `embedding_statistics.json`, `embedded_chunks.jsonl` oder Qdrant-Collection
- Config: Modell-Namen, k fuer NDCG@k (10), Batch-Size

## Ausgaben

- **evaluation_results_embeddings.json** – Pro Modell: NDCG@10, MRR, Precision@5; Ergebnistabelle fuer Kap. 6.1
- Optional: Pro-Frage-Scores fuer Fehleranalyse

## Hinweise

- FF3: Welches Embedding-Modell erzielt beste Retrieval-Qualitaet fuer Deutsch?
- J2: Ergebnistabelle + begruendete Empfehlung; Trade-offs (Qualitaet vs. Modellgroesse vs. Inferenzzeit) diskutieren
