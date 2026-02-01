"""
Preprocessing Evaluation (Stage 3b)
===================================
Quality checks for RAG Preprocessing output.

Verifies that Wiki→Markdown conversion preserved:
- Information completeness
- Link integrity  
- Structure preservation
- Frontmatter validity

Input:  data/preprocessed/preprocess_at_*/
Output: data/evaluated/preprocessing_eval_*.json
"""

__version__ = "1.0.0"
__author__ = "Jan Ritt (IxI-Enki)"
