"""
RAG Preprocessing Pipeline
==========================
Transforms DokuWiki content into RAG-optimized Markdown with YAML frontmatter.

Stage 3 in the Dev Dito Pipeline:
- Input: data/fetched/fetched_at_*/
- Output: data/preprocessed/preprocess_at_*/

Components:
- page_processor: Wiki syntax -> Markdown conversion
- media_processor: PDF/DOCX/XLSX -> plaintext extraction
- metadata_enricher: YAML frontmatter generation
- strategy_loader: Load evaluation results from Stage 2
- exporter: Output directory and manifest generation
"""

__version__ = "1.0.0"
__author__ = "Jan Ritt (IxI-Enki)"
