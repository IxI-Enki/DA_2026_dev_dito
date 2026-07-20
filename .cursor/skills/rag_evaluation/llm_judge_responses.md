---
description: Evaluiert RAG-generierte Antworten als LLM-Judge (RAGAS). AnswerCorrectness, AnswerRelevancy, Faithfulness, ResponseGroundedness. LLM: GPT-4o-mini oder Claude (konfigurierbar).
globs: ["**/rag_responses.json", "**/ground_truth_dataset.json"]
alwaysApply: false
---

# LLM Judge RAG Responses

**Zweck:** Evaluiert RAG-generierte Antworten mit RAGAS-Metriken (LLM-as-Judge).

## RAGAS Metriken

- **AnswerCorrectness** – Semantische und faktische Korrektheit (vs. Reference Answer)
- **AnswerRelevancy** – Beantwortet die Antwort die Frage?
- **Faithfulness** – Halluziniert das Modell? (Antwort nur aus Context ableitbar?)
- **ResponseGroundedness** – Basiert die Antwort auf dem gelieferten Context?

## LLM

- **Evaluator-Modell:** GPT-4o-mini oder Claude Sonnet (konfigurierbar in ragas_config.yaml)
- **RAG-Modell** (fuer Antwort-Generierung): Kann identisch oder anders sein

## Skript

```bash
python evaluation/ragas_agents/scripts/llm_judge_responses.py --ground-truth <ground_truth_dataset.json> --rag-responses <rag_responses.json> [--metrics correctness,relevancy,faithfulness,groundedness] [--output evaluation_results_llm_judge.json]
```

## Eingaben

- `ground_truth_dataset.json` (user_input, reference, retrieved_contexts)
- `rag_responses.json` – Pro Frage: question_id, response (RAG-Antwort), retrieved_contexts (optional)
- Config: Evaluator-LLM, API-Keys, Metriken-Liste

## Ausgaben

- **evaluation_results_llm_judge.json** – Pro Metrik: Durchschnitt, Pro-Frage-Scores; fuer Report und Kap. 6
- Optional: Einzelurteile (JSON) fuer Nachvollziehbarkeit

## Hinweise

- RAGAS: `evaluate(dataset, metrics=[...])` nutzen; Dataset-Format: user_input, reference, retrieved_contexts, response
- Token-Kosten: Viele LLM-Calls; Caching und Batch-Ausfuehrung empfohlen
