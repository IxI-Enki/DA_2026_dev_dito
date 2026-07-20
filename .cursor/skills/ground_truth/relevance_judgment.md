---
description: Bewertet Relevanz von Dokumenten pro Frage fuer NDCG@10. Skala 0-3. Semi-automatisch (LLM-Vorschlag + Human-Review). Output relevance_judgments.json.
globs: ["**/questions.json", "**/test_corpus/**"]
alwaysApply: false
---

# Relevance Judgment

**Zweck:** Bewertet die Relevanz von Dokumenten (bzw. Chunks) fuer jede Testfrage – Grundlage fuer NDCG@10 und Retrieval-Evaluation.

## Skala

- **0** – Irrelevant
- **1** – Gering relevant
- **2** – Relevant
- **3** – Perfekt relevant (beantwortet Frage vollstaendig)

## Prozess

- **Semi-automatisch:** LLM schlaegt Relevanz vor, Human-Review fuer Stichproben oder alle
- Optional: Nur Human-Review bei kleinerem Testset (20-30 Fragen)

## Skript

```bash
python evaluation/ragas_agents/scripts/judge_relevance.py --questions <questions.json> --corpus-dir <test_corpus_dir> [--output relevance_judgments.json]
```

## Eingaben

- `questions.json` (Fragen inkl. source_doc_ids)
- Testkorpus-Verzeichnis
- Optional: Bereits gerankte Retrieval-Ergebnisse (Top-k pro Frage) fuer Fokus auf diese Dokumente

## Ausgaben

- **relevance_judgments.json** – Pro Frage: question_id, document_id/chunk_id, relevance_score (0-3)
- Wird von evaluate_embeddings.py und evaluate_retrieval.py fuer NDCG@10 genutzt

## Hinweise

- J1: Selbst erstellte Relevanzurteile sind ausreichend; dokumentieren und nachvollziehbar halten
- Bei 20-30 Fragen: Human-Review aller Urteile machbar; bei groesserem Set LLM-Vorschlag + Stichprobe
