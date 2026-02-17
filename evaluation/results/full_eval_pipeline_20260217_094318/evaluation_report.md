# Evaluation Report

**Generated**: 2026-02-17T10:03:48Z  
**Code Version**: `c58cedf`  
**Models**: 2

## Executive Summary

- **Best Model**: Full_Eval_Pipeline (MRR = 0.0000)
- **Models Evaluated**: 2

## Custom Metrics

| Model | rr | p_at_5 | ndcg_at_10 | recall_at_10 | average_precision | hit_in_top_k |
| --- | --- | --- | --- | --- | --- | --- |
| Full_Eval_Pipeline | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| statistics | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

## RAGAS Metrics (LLM-as-Judge)

| Metric | Score |
| --- | --- |
| answer_correctness | 1.0000 |
| answer_relevancy | 0.8000 |
| context_precision | 0.0000 |
| context_recall | 0.3795 |
| faithfulness | 0.0000 |
| ragas_score | 0.5148 |

## Difficulty Breakdown

### Full_Eval_Pipeline

| Difficulty | Count | rr | p_at_5 | ndcg_at_10 | recall_at_10 | average_precision | hit_in_top_k |
| --- | --- | --- | --- | --- | --- | --- | --- |
| easy | 17 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| hard | 21 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| medium | 40 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

### statistics

## Reproducibility (NFR-005)

- **Timestamp**: 2026-02-17T10:03:48Z
- **Code Version**: `c58cedf`
- **Config Hash (Full_Eval_Pipeline)**: `sha256:d0620ef00dc84f3a2f78ccda0d2a30d24ea8185f7962631a9339e7490bc09d7e`
- **Config Hash (statistics)**: `n/a`
