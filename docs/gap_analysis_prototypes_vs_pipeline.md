# Gap Analysis: Prototypes vs dev_dito Pipeline

**Date**: 2026-02-14
**Scope**: 7 prototype directories under `research/techstack/` vs `dev_dito/pipeline/` + `dev_dito/evaluation/`
**Purpose**: Identify all features in prototypes missing or incomplete in dev_dito production pipeline

---

## File Inventory

### Prototype 1: `dokuwiki/fetcher_json_rpc_api/script/` (13 files)
| File | Key Feature |
|------|-------------|
| `api_client.py` | WikiAPIClient with retry logic, permanent/transient error classification |
| `config.py` | YAML-based configuration |
| `fetch_full_wiki_extended.py` | Full wiki fetch: pages + ACL + links + history + backlinks + media |
| `resume_fetch.py` | Resume interrupted fetches by retrying failed items |
| `media_cache.py` | MediaCache: hash-based dedup from archived fetches |
| `create_wiki_inventory.py` | WikiInventoryCreator: pages + namespaces + media + ACL analysis |
| `document_analyzer.py` | DocumentAnalyzer: PDF pages, PPTX slides, DOCX paragraphs, XLSX sheets |
| `analyze_fetched_data.py` | Post-fetch statistics: sizes, namespaces, coverage |
| `extract_links_from_html.py` | LinkExtractor: HTML-based link extraction |
| `fetch_full_wiki.py` | Basic wiki fetch (superseded by extended) |
| `fetch_recent_changes.py` | Recent changes API wrapper |
| `download_media_only.py` | Media-only download |
| `test_all_api_methods.py` | API method explorer/tester |

### Prototype 2: `dokuwiki/fetcher_shared/dokuwiki/` (2 files)
| File | Key Feature |
|------|-------------|
| `__init__.py` | Package init |
| `cli_help.py` | Colorized CLI help with ANSI styling |

### Prototype 3: `dokuwiki/fetched_data_evaluation/script/` (19 files)
| File | Key Feature |
|------|-------------|
| `analyzers/content_classifier.py` | LLM-based content classification |
| `analyzers/document_deep_analyzer.py` | Deep document structure analysis |
| `analyzers/format_quality_analyzer.py` | Format quality assessment |
| `analyzers/media_deep_analyzer.py` | Media file deep analysis |
| `analyzers/query_generator.py` | Query generation for eval |
| `analyzers/rag_readiness_checker.py` | RAG readiness scoring |
| `analyzers/temporal_analyzer.py` | Temporal analysis (freshness) |
| `analyzers/wiki_deep_analyzer.py` | Wiki structure deep analysis |
| `core/file_handler.py` | File I/O utilities |
| `core/llm_client.py` | LLM client for Ollama |
| `generators/strategy_generator.py` | Per-page preprocessing strategy generation |
| `config.py` | Configuration |
| `report_generator.py` | Report generation |
| `run_evaluation.py` | Main evaluation runner |
| `run_deep_evaluation.py` | Deep evaluation runner |
| `run_strategy_generation.py` | Strategy generation runner |
| `check_models.py` | Model availability checker |
| `cleanup_strategies.py` | Strategy cleanup utility |

### Prototype 4: `ragas/professional_evaluation/` (19 files)
| File | Key Feature |
|------|-------------|
| `evaluator.py` | ProfessionalRAGEvaluator: full 9-step eval pipeline orchestrator |
| `config.py` | EvaluationConfig with RAGFlow, LLM, metrics, statistics settings |
| `metrics/ragas_metrics.py` | RAGASMetricsCalculator: Faithfulness, Relevancy, Context P/R, Correctness, Hallucination |
| `metrics/retrieval_metrics.py` | RetrievalMetricsCalculator: MRR, NDCG@K, P@K, R@K, MAP, Hit Rate, F1@K |
| `metrics/statistical_analysis.py` | StatisticalAnalyzer: Bootstrap CI, t-test, Wilcoxon, Mann-Whitney, Cohen's d, correlations |
| `metrics/category_analysis.py` | CategoryAnalyzer: per-category breakdown, error analysis, improvement suggestions |
| `visualization/charts.py` | RAGVisualization: Radar, Box, Heatmap, Bar, Line, Scatter (matplotlib + optional plotly) |
| `reports/generator.py` | ReportGenerator: Markdown + JSON export |
| `reports/notebook_generator.py` | NotebookGenerator: Jupyter notebook generation |
| `qdrant_eval/retriever.py` | QdrantRetriever: loads JSONL embeddings, cosine similarity search |
| `qdrant_eval/evaluator.py` | QdrantEvaluator: Qdrant-based eval using same metrics pipeline |
| `script/run_evaluation.py` | RAGFlow evaluation runner |
| `script/run_qdrant_evaluation.py` | Qdrant evaluation runner |

### Prototype 5: `ragflow/preprocessing_evaluation/script/` (8 files)
| File | Key Feature |
|------|-------------|
| `evaluator.py` | PreprocessingEvaluator: info preservation, content quality, OCR, error detection |
| `config.py` | Config with YAML, timestamped directories |
| `metrics/information_preservation.py` | ContentCompleteness, SemanticSimilarity, EntityPreservation, LinkIntegrity |
| `metrics/content_quality.py` | NoiseDetection (wiki syntax remnants), Readability (Flesch-DE), StructurePreservation |
| `run_evaluation.py` | Main runner |
| `test_single_page.py` | Single page tester |

### Prototype 6: `ragflow/test_suite_rag_preprocessing/script/` (17 files, 7 archived)
| File | Key Feature |
|------|-------------|
| `page_processor.py` | DokuWikiParser + PageProcessor: section extraction, link parsing, wiki-to-clean conversion |
| `metadata_enricher.py` | MetadataEnricher: access_level, freshness_score, teacher namespace detection |
| `ragflow_uploader.py` | RAGFlowClient + RAGFlowUploader: dataset CRUD, document upload, parsing, RAG query |
| `media_processor.py` | Media file processing |
| `strategy_loader.py` | Load per-page strategies from Deep Evaluation |
| `exporter.py` | Export processed content |
| `config.py` | Config |
| `main.py` | Main orchestrator |
| `setup_raptor.py` | RAPTOR setup utility |

### Prototype 7: `qdrant/embeddings_creator/script/` (7 files)
| File | Key Feature |
|------|-------------|
| `content_aware_chunker.py` | ContentAwareChunker: section-based + size-based chunking |
| `document_loader.py` | DocumentLoader: load from text files |
| `embedder.py` | Embedder: OpenAI/Ollama embedding creation |
| `pipeline.py` | EmbeddingPipeline: load -> chunk -> embed -> upload to Qdrant |
| `config.py` | Config |
| `main.py` | Main runner |

### dev_dito Pipeline (44 files)
- `01_wiki_fetcher/` (12 files) -- WikiAPIClient, fetch_full_wiki_extended, resume_fetch, media_cache, etc.
- `02_deep_evaluation/` (18 files) -- content_classifier, document_deep_analyzer, wiki_deep_analyzer, etc.
- `03_embeddings_creator/` (7 files) -- ContentAwareChunker, DocumentLoader, Embedder, Pipeline
- `03_rag_preprocessing/` (5 files) -- PageProcessor, MetadataEnricher
- `04_deploy/` (2 files) -- transfer_to_pi, verify_transfer

### dev_dito Evaluation (39 files)
- `metrics/` (3 files) -- MRR, NDCG@K, P@K (pure functions, 56 tests)
- `providers/` (3 files) -- base ABC, OllamaProvider, OpenAIProvider
- `config.py` -- ExperimentConfig frozen dataclass
- `scripts/` (5 files) -- eval_keyword_baseline, eval_model_comparison, eval_chunk_size, eval_hybrid_vs_dense, eval_export_latex
- `ragas_agents/scripts/` (16 files) -- various RAGAS agent scripts
- `tests/` (5 files) -- test coverage for metrics, providers, integration

---

## Gap Analysis Table

| # | Prototype | Feature | Status in dev_dito | Priority | Notes |
|---|-----------|---------|-------------------|----------|-------|
| **PROTOTYPE 1: Wiki Fetcher** | | | | |
| 1 | fetcher_json_rpc_api | WikiAPIClient core (call, retry, error classification) | **Present** | - | Ported to `01_wiki_fetcher/api_client.py` |
| 2 | fetcher_json_rpc_api | `get_page_links()` - API-based link extraction | **Present** | - | In pipeline api_client |
| 3 | fetcher_json_rpc_api | `get_page_backlinks()` - incoming links | **Present** | - | In pipeline api_client |
| 4 | fetcher_json_rpc_api | `get_page_history()` - revision history | **Present** | - | In pipeline api_client |
| 5 | fetcher_json_rpc_api | `get_all_media()` + `get_media_info()` + `get_media_usage()` | **Present** | - | In pipeline api_client |
| 6 | fetcher_json_rpc_api | `fetch_full_wiki_extended.py` - full coverage fetch | **Present** | - | Ported to `01_wiki_fetcher/` |
| 7 | fetcher_json_rpc_api | `resume_fetch.py` - resume interrupted fetches | **Present** | - | Ported to `01_wiki_fetcher/` |
| 8 | fetcher_json_rpc_api | `media_cache.py` - hash-based media dedup | **Present** | - | Ported to `01_wiki_fetcher/` |
| 9 | fetcher_json_rpc_api | `document_analyzer.py` - PDF/PPTX/DOCX/XLSX metadata | **Missing** | Medium | Extracts page counts, slide counts, word counts |
| 10 | fetcher_json_rpc_api | `create_wiki_inventory.py` - wiki inventory + ACL analysis | **Missing** | Low | Documentation utility |
| 11 | fetcher_json_rpc_api | `analyze_fetched_data.py` - post-fetch statistics | **Missing** | Low | Verification utility |
| 12 | fetcher_json_rpc_api | `fetch_recent_changes.py` - incremental change detection | **Partial** | Low | `change_detector.py` + `incremental_fetcher.py` likely covers this |
| 13 | fetcher_json_rpc_api | `download_media_only.py` - media-only download | **Missing** | Low | Convenience script |
| **PROTOTYPE 2: Shared Utilities** | | | | |
| 14 | fetcher_shared | `cli_help.py` - ANSI color styling | **Missing** | Low | Pipeline uses logging instead |
| **PROTOTYPE 3: Fetched Data Evaluation** | | | | |
| 15 | fetched_data_evaluation | Content classifier (LLM-based) | **Present** | - | Ported to `02_deep_evaluation/` |
| 16 | fetched_data_evaluation | Document deep analyzer | **Present** | - | Ported to `02_deep_evaluation/` |
| 17 | fetched_data_evaluation | Format quality analyzer | **Present** | - | Ported to `02_deep_evaluation/` |
| 18 | fetched_data_evaluation | Media deep analyzer | **Present** | - | Ported to `02_deep_evaluation/` |
| 19 | fetched_data_evaluation | Query generator | **Present** | - | Ported to `02_deep_evaluation/` |
| 20 | fetched_data_evaluation | RAG readiness checker | **Present** | - | Ported to `02_deep_evaluation/` |
| 21 | fetched_data_evaluation | Temporal analyzer | **Present** | - | Ported to `02_deep_evaluation/` |
| 22 | fetched_data_evaluation | Wiki deep analyzer | **Present** | - | Ported to `02_deep_evaluation/` |
| 23 | fetched_data_evaluation | LLM client (Ollama) | **Present** | - | Ported to `02_deep_evaluation/` |
| 24 | fetched_data_evaluation | File handler | **Present** | - | Ported to `02_deep_evaluation/` |
| 25 | fetched_data_evaluation | Strategy generator | **Present** | - | Ported to `02_deep_evaluation/` |
| 26 | fetched_data_evaluation | Report generator | **Present** | - | Ported to `02_deep_evaluation/` |
| 27 | fetched_data_evaluation | `check_models.py` - model availability checker | **Missing** | Low | Utility script |
| 28 | fetched_data_evaluation | `cleanup_strategies.py` - strategy cleanup | **Missing** | Low | Maintenance utility |
| **PROTOTYPE 4: RAGAS Professional Evaluation** | | | | |
| 29 | ragas/professional_eval | RAGASMetricsCalculator (Faithfulness, Relevancy, Context P/R, Correctness, Hallucination) | **Missing** | **Critical** | Core RAGAS LLM-as-Judge with German prompts, retry logic, score normalization |
| 30 | ragas/professional_eval | StatisticalAnalyzer (Bootstrap CI, t-test, Wilcoxon, Mann-Whitney, Cohen's d, correlation) | **Missing** | **Critical** | Scientific statistical analysis for thesis. Essential for significance testing. |
| 31 | ragas/professional_eval | CategoryAnalyzer (per-difficulty breakdown, error analysis, improvement suggestions) | **Missing** | **High** | dev_dito has manual difficulty breakdown but no structured analyzer |
| 32 | ragas/professional_eval | RAGVisualization (Radar, Box, Heatmap, Bar, Line, Scatter) | **Missing** | **High** | Professional charts for thesis figures |
| 33 | ragas/professional_eval | ReportGenerator (Markdown + JSON export) | **Missing** | **High** | dev_dito has LaTeX export but no Markdown report generator |
| 34 | ragas/professional_eval | NotebookGenerator (Jupyter notebook generation) | **Missing** | Medium | Auto-generates analysis notebooks |
| 35 | ragas/professional_eval | ProfessionalRAGEvaluator (9-step orchestrator) | **Missing** | **Critical** | Master orchestrator combining all evaluation components |
| 36 | ragas/professional_eval | RAGFlowClient (retrieval API) | **Partial** | Medium | dev_dito uses Qdrant directly (Article VIII) |
| 37 | ragas/professional_eval | LLMClient (OpenAI-compatible for answer generation) | **Partial** | Medium | Providers exist for embeddings, not answer generation |
| 38 | ragas/professional_eval | `compare_with_baseline()` - A/B comparison with statistical tests | **Missing** | **High** | Essential for thesis claims about model superiority |
| 39 | ragas/professional_eval | QdrantRetriever - loads JSONL, cosine similarity | **Partial** | Medium | eval scripts use qdrant_client directly |
| 40 | ragas/professional_eval | QdrantEvaluator - Qdrant + RAGAS combined | **Missing** | **High** | Unified Qdrant retrieval + RAGAS evaluation |
| 41 | ragas/professional_eval | Multi-signal relevance scoring | **Present** | - | Ported to eval scripts |
| 42 | ragas/professional_eval | MAP (Mean Average Precision) metric | **Missing** | Medium | Easy to add |
| 43 | ragas/professional_eval | Recall@K metric | **Missing** | Medium | Easy to add |
| 44 | ragas/professional_eval | F1@K metric | **Missing** | Low | Derivable from P@K + R@K |
| 45 | ragas/professional_eval | Hit Rate metric | **Partial** | Low | Computable from MRR |
| **PROTOTYPE 5: Preprocessing Evaluation** | | | | |
| 46 | ragflow/preproc_eval | PreprocessingEvaluator orchestrator | **Missing** | Medium | Validates Stage 3 output quality |
| 47 | ragflow/preproc_eval | InformationPreservationCalculator | **Missing** | Medium | Content completeness, semantic similarity, entity preservation |
| 48 | ragflow/preproc_eval | ContentQualityCalculator (NoiseDetection, Readability Flesch-DE, StructurePreservation) | **Missing** | Medium | Detects residual wiki markup, encoding errors |
| 49 | ragflow/preproc_eval | Semantic similarity via SentenceTransformer | **Missing** | Low | Requires sentence-transformers dependency |
| 50 | ragflow/preproc_eval | Entity preservation (dates, rooms, emails, URLs) | **Missing** | Medium | Verifies entities survive preprocessing |
| **PROTOTYPE 6: RAG Preprocessing Test Suite** | | | | |
| 51 | ragflow/test_suite | DokuWikiParser (sophisticated section extraction) | **Partial** | Medium | dev_dito has simpler implementation |
| 52 | ragflow/test_suite | PageProcessor with content-aware routing via strategies | **Missing** | Medium | Routes pages by content type from Deep Eval |
| 53 | ragflow/test_suite | MetadataEnricher (freshness_score, access_level) | **Partial** | Medium | dev_dito version lacks freshness + access_level |
| 54 | ragflow/test_suite | RAGFlowClient + RAGFlowUploader | **Missing** | Low | dev_dito uses Qdrant directly per Article VIII |
| 55 | ragflow/test_suite | StrategyLoader (load Deep Eval strategies) | **Missing** | Medium | Missing link between Stage 2 and Stage 3 |
| 56 | ragflow/test_suite | MediaProcessor (PDF text, image OCR) | **Missing** | Medium | No media processing in preprocessing stage |
| 57 | ragflow/test_suite | Exporter (upload-ready format) | **Missing** | Medium | No export step in dev_dito |
| **PROTOTYPE 7: Qdrant Embeddings Creator** | | | | |
| 58 | qdrant/embeddings | ContentAwareChunker | **Present** | - | Ported |
| 59 | qdrant/embeddings | DocumentLoader | **Present** | - | Ported |
| 60 | qdrant/embeddings | Embedder | **Present** | - | Ported |
| 61 | qdrant/embeddings | EmbeddingPipeline | **Present** | - | Ported |

---

## Summary by Status

| Status | Count | Percentage |
|--------|-------|------------|
| **Present** | 30 | 49% |
| **Partial** | 7 | 11% |
| **Missing** | 24 | 39% |

## Summary by Priority (Missing + Partial only)

| Priority | Count | Items |
|----------|-------|-------|
| **Critical** | 3 | RAGAS metrics (#29), Statistical analyzer (#30), Evaluation orchestrator (#35) |
| **High** | 5 | Category analyzer (#31), Visualizations (#32), Report generator (#33), Baseline comparison (#38), Qdrant+RAGAS evaluator (#40) |
| **Medium** | 14 | Document analyzer (#9), MAP/Recall@K (#42-43), Preprocessing evaluator (#46-48,50), Strategy routing (#52,55), Media processor (#56), Exporter (#57), MetadataEnricher gaps (#53), DokuWiki parser gaps (#51), Notebook generator (#34) |
| **Low** | 9 | Inventory creator (#10), CLI help (#14), various utilities |

---

## Critical Path for Thesis

### Must-Port (Critical) -- Blocks thesis claims
1. **RAGAS LLM-as-Judge Metrics** (~530 lines) -- Faithfulness, Answer Relevancy, Context Precision/Recall, Answer Correctness
2. **Statistical Analysis** (~514 lines) -- Bootstrap CI, significance tests, effect sizes, correlation analysis
3. **Evaluation Orchestrator** (~600 lines) -- ProfessionalRAGEvaluator 9-step pipeline

### Should-Port (High) -- Strengthens thesis quality
4. **Category/Difficulty Analysis** (~350 lines) -- Breakdown by category, error analysis
5. **Visualization Suite** -- Radar, box, heatmap, line charts for thesis figures
6. **Report Generator** -- Structured Markdown + JSON reports
7. **Baseline Comparison** -- Statistical comparison of two configurations
8. **Qdrant-Integrated RAGAS Evaluator** -- Combines Qdrant retrieval with RAGAS metrics

### Nice-to-Have (Medium) -- Data quality assurance
9. **Preprocessing Quality Metrics** -- Info preservation, content quality
10. **Strategy Routing** -- Content-aware preprocessing paths
11. **Media Processor** -- PDF text extraction, image OCR in preprocessing stage

---

## What dev_dito Already Does Well
- Custom IR metrics (MRR, NDCG, P@K) as pure functions with 56 passing tests
- Provider abstraction (OllamaProvider, OpenAIProvider) for embeddings
- ExperimentConfig frozen dataclass from YAML
- Evaluation scripts for thesis tables (FF1, FF3, J4, J6)
- LaTeX export (booktabs tables)
- Pipeline stages 1-3 (fetch, evaluate, embed) fully ported

## What Prototypes Have That dev_dito Lacks
- LLM-as-Judge evaluation (RAGAS-style qualitative metrics)
- Statistical rigor (confidence intervals, significance tests, effect sizes)
- Visualization pipeline (automated chart generation)
- Preprocessing quality assurance (noise detection, entity preservation)
- Unified evaluation orchestration (single pipeline vs. fragmented scripts)
- A/B comparison framework (compare configurations with statistical tests)
