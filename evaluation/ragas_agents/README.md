# RAGAS Evaluation Agents

Agent system for RAG evaluation (thesis FF1, FF3, J1, J2, J4, J6). Three agents with 14 skills and programmatic scripts.

## Structure

- **config/ragas_config.yaml** – Metric thresholds, model names, paths
- **scripts/** – 15 Python scripts (Data Curator, Ground Truth Engineer, RAG Evaluator, orchestrator)
- **output/** – test_corpus, ground_truth, evaluation_results, reports (created on first run)

## Cursor Third-Party Skills Support

1. Open Cursor Settings: `Ctrl+,` (Windows) or `Cmd+,` (Mac)
2. Search for: "third party" or "skills" or "claude"
3. Enable "Third-Party Skills Support" if the option exists
4. `.claude/settings.json` in the project root is created; Cursor v2.4+ may load it automatically

## Quick Run

From repo root (dev_dito):

```bash
# Phase 1 (Data Curator) – needs path to fetched_at_* and preprocessed dir
python -m evaluation.ragas_agents.scripts.analyze_scraped_data --input <path_to_fetched_at_*>
python -m evaluation.ragas_agents.scripts.assess_document_quality --input <path_to_preprocessed>
python -m evaluation.ragas_agents.scripts.select_test_corpus --pipeline-results <pipeline_results_*.json>

# Phase 2 (Ground Truth) – after test_corpus_manifest.json exists
python -m evaluation.ragas_agents.scripts.generate_questions --manifest evaluation/ragas_agents/output/test_corpus_manifest.json
python -m evaluation.ragas_agents.scripts.create_answers --questions evaluation/ragas_agents/output/ground_truth/questions.json
python -m evaluation.ragas_agents.scripts.judge_relevance --questions evaluation/ragas_agents/output/ground_truth/questions.json
python -m evaluation.ragas_agents.scripts.validate_test_set --dataset evaluation/ragas_agents/output/ground_truth/ground_truth_dataset.json

# Phase 3 (RAG Evaluator) – embedding/retrieval/LLM judge + report
python -m evaluation.ragas_agents.scripts.evaluate_embeddings --ground-truth evaluation/ragas_agents/output/ground_truth/ground_truth_dataset.json
python -m evaluation.ragas_agents.scripts.evaluate_retrieval --ground-truth evaluation/ragas_agents/output/ground_truth/ground_truth_dataset.json
python -m evaluation.ragas_agents.scripts.llm_judge_responses --ground-truth evaluation/ragas_agents/output/ground_truth/ground_truth_dataset.json
python -m evaluation.ragas_agents.scripts.analyze_statistics --results-dir evaluation/ragas_agents/output/evaluation_results
python -m evaluation.ragas_agents.scripts.generate_report --results-dir evaluation/ragas_agents/output/evaluation_results --output-dir evaluation/ragas_agents/output/reports

# Full pipeline (with optional inputs)
python -m evaluation.ragas_agents.scripts.run_full_evaluation --input-fetched <path> --input-preprocessed <path>
```

## RAGAS Library Integration (ragas.io)

The following scripts use the **ragas** Python library when installed and `OPENAI_API_KEY` is set:

- **llm_judge_responses.py** – Uses `ragas.evaluate()` with `SingleTurnSample`/`EvaluationDataset` and metrics: `answer_correctness`, `answer_relevancy`, `faithfulness`, `context_precision`. Fallback: placeholder (use `--no-ragas` to force).
- **generate_questions.py** – Uses `ragas.testset.TestsetGenerator` with LangChain docs (`DirectoryLoader`), `LangchainLLMWrapper`, `LangchainEmbeddingsWrapper`; generates synthetic questions (single-hop/multi-hop). Fallback: template-based. Requires `--corpus-dir` for RAGAS.
- **augment_test_data.py** – Uses RAGAS `TestsetGenerator.generate_with_langchain_docs()` when `--corpus-dir` is given to add synthetic samples (evolution: reasoning, multi_context). Fallback: duplicate+paraphrase placeholder.

**Install:** `pip install -r evaluation/requirements.txt` (includes `ragas`, `datasets`, `langchain-community`, `langchain-openai`). Set `OPENAI_API_KEY` for LLM-based evaluation and generation.

## Integration with Existing Evaluation

- **Embedding comparison (J2, FF3):** Use `evaluation.scripts.eval_model_comparison --compare-all` for real NDCG@10/MRR.
- **Retrieval (J6):** Use `evaluation.scripts.eval_hybrid_vs_dense` for real Precision@5/NDCG@10.
- **RAGAS LLM Judge:** Real scores when `ragas` is installed and `OPENAI_API_KEY` is set; otherwise placeholder.

## Agents and Skills

See `.cursor/agents/` (data_curator, ground_truth_engineer, rag_evaluator) and `.cursor/skills/` (data_curator, ground_truth, rag_evaluation).
