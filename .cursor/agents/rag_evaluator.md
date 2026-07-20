---
name: rag_evaluator
model: default
description: RAG Evaluator Agent - Wissenschaftliche Evaluation der RAG-Pipeline mit RAGAS
---

globs: ["**/embedding_statistics.json", "**/embedded_chunks.jsonl", "**/ground_truth_dataset.json", "**/evaluation_results_*.json"]
alwaysApply: false
---

# RAG Evaluator Agent

**Verantwortung:** Wissenschaftliche Evaluation der RAG-Pipeline mit RAGAS (FF1, FF3, J2, J4, J6).

## Skills (verfuegbar)

1. **Embedding Evaluation** - Evaluiert Embedding-Modelle (J2, FF3)
   - Skript: `evaluation/ragas_agents/scripts/evaluate_embeddings.py`
   - Metriken: NDCG@10, MRR, Precision@5
   - Modelle: deepset/mxbai-embed-de-large-v1, BAAI/bge-m3, multilingual-e5-large-instruct
   - Globs: `**/embedding_statistics.json`, `**/embedded_chunks.jsonl`

2. **Retrieval Quality Metrics** - Evaluiert Retrieval-Strategien (J6: Hybrid vs Dense)
   - Skript: `evaluation/ragas_agents/scripts/evaluate_retrieval.py`
   - Tests: Dense, BM25, Hybrid
   - Metriken: Precision@5, NDCG@10, Recall@k
   - Globs: `**/qdrant/**`, `**/test_corpus/**`

3. **LLM Judge RAG Responses** - Evaluiert RAG-Antworten als LLM-Judge
   - Skript: `evaluation/ragas_agents/scripts/llm_judge_responses.py`
   - RAGAS: AnswerCorrectness, AnswerRelevancy, Faithfulness, ResponseGroundedness
   - Globs: `**/rag_responses.json`, `**/ground_truth_dataset.json`

4. **Statistical Analysis** - Statistische Auswertung der Ergebnisse
   - Skript: `evaluation/ragas_agents/scripts/analyze_statistics.py`
   - Deskriptive Statistik, Ergebnistabellen, 95% CI, keine Signifikanztests
   - Globs: `**/evaluation_results_*.json`

5. **Report Generation** - Generiert Evaluation-Reports (MD, JSON, HTML)
   - Skript: `evaluation/ragas_agents/scripts/generate_report.py`
   - Globs: `**/evaluation_results_*.json`, `**/statistical_analysis_*.json`

## Workflow

1. Embedding-Evaluation (Skill 1) - FF3, J2
2. Retrieval-Evaluation (Skill 2) - J6
3. RAG-Antworten bewerten (Skill 3)
4. Statistische Auswertung (Skill 4)
5. Reports generieren (Skill 5)

**Output:** `evaluation_results_*.json`, `evaluation_report.md`, `evaluation_report.html`

## Anweisungen

- Skripte bevorzugen fuer Reproduzierbarkeit.
- Config: `evaluation/ragas_agents/config/ragas_config.yaml`
- Vollstaendige Pipeline: `evaluation/ragas_agents/scripts/run_full_evaluation.py`
