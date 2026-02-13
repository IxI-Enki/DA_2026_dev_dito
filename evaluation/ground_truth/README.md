# Ground Truth Dataset (J1)

**Thesis Reference**: J1 -- Test Corpus for Embedding Evaluation
**Source**: `research/techstack/ragas/ground_truth/leowiki_qa_50_verified.json`

## Description

50 verified Q&A pairs created from real LeoWiki (HTL Leonding DokuWiki) content.
Used as the shared test corpus for all evaluations:
- **FF1**: Keyword vs Semantic Search (MRR, P@5)
- **FF3**: Embedding Model Comparison (NDCG@10)
- **J4**: Chunk Size Impact (256/512/1024 tokens)
- **J6**: Hybrid vs Dense Retrieval

## Format

```json
{
  "metadata": { "version": "2.0", ... },
  "qa_pairs": [
    {
      "id": "matura-01",
      "question": "Aus welchen Säulen bestehen die Reife- und Diplomprüfungen?",
      "ground_truth": "Die Reife- und Diplomprüfungen bestehen aus 3 Säulen...",
      "source_file": "exams_matura-tagesschule-if-it.txt",
      "context_keywords": ["diplomarbeit", "klausur", ...],
      "difficulty": "easy"
    }
  ]
}
```

## Verification Method

Manually verified against source documents by Jan Ritt (2026-01-02).
Each Q&A pair references its `source_file` for traceability.

## Usage in Evaluation

The `source_file` field identifies which wiki page contains the answer.
Evaluation scripts use this to determine if a retrieval result is relevant:
a result is considered relevant if it originates from the same source page.
