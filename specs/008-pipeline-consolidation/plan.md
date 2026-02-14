# Implementation Plan: Pipeline Consolidation

**Branch**: `008-pipeline-consolidation` | **Date**: 2026-02-14 | **Spec**: [spec.md](./spec.md)
**Input**: Gap Analysis `docs/gap_analysis_prototypes_vs_pipeline.md` + Spec 008
**Thesis-Zuordnung**: FF1, FF3, J1, J2, J3, J4, J6
**Builds On**: 007-evaluation-infrastructure (56 tests, 5 eval scripts, provider abstraction)

## Summary

Schliesst 24 fehlende und 7 teilweise portierte Features aus 7 Prototypen. Drei Saeulen:

1. **Evaluation-Erweiterung**: RAGAS.io-Integration, StatisticalAnalyzer, Visualisierungen, Report-Generator, Unified Orchestrator
2. **Preprocessing-Vervollstaendigung**: Strategy-Routing, MetadataEnricher (freshness/access_level), MediaProcessor (OCR), Exporter
3. **Deployment**: Qdrant direct-upload + Watchdog-Modus

Bestehende 56 Tests und 5 Evaluations-Skripte bleiben UNANGETASTET.

## Technical Context

**Language/Version**: Python 3.11+ (matching existing pipeline)
**New Dependencies**:
- `ragas`, `datasets`, `langchain-openai` -- RAGAS.io LLM-as-Judge
- `scipy` -- Statistische Tests (t-test, Wilcoxon, Mann-Whitney, Bootstrap)
- `matplotlib`, `seaborn` -- Visualisierungen
- `pytesseract`, `Pillow` -- OCR fuer Media-Dateien
- `tqdm` -- Progress-Bars
**Existing Dependencies** (reused): `qdrant-client`, `openai`, `ollama`, `pyyaml`, `numpy`
**Testing**: pytest, TDD -- Tests VOR oder GLEICHZEITIG mit Implementation
**Target Platform**: Windows 11 (host-native, venv), Qdrant auf Raspberry Pi (192.168.8.3:6333)
**LLM Backend**: Ollama auf 192.168.8.3:11434 (OpenAI-kompatible API)

## Constitution Check

| Article                              | Status  | Notes                                          |
| ------------------------------------ | ------- | ---------------------------------------------- |
| Article I (Layered Architecture)     | PASS    | Evaluation bleibt Python-only, kein PHP        |
| Article II (JSON Interface)          | PASS    | Alle Ergebnisse JSON/JSONL, Reports Markdown   |
| Article II-B (YAML Config)           | PASS    | Experiment-Configs via YAML, Secrets in .token |
| Article III (Critical-Path Testing)  | PASS    | TDD fuer alle neuen Module (NFR-002)           |
| Article VI (Secret Containment)      | PASS    | Ollama-URL in Config, kein API-Key noetig      |
| Article VII (Integration Simplicity) | PASS    | Reuses bestehende Providers, Metriken, Config  |
| Article VIII (Direct Framework)      | PASS    | `ragas` Library direkt, `qdrant_client` direkt |
| Article X (Execution Mandate)        | PRIMARY | Liefert Ergebnisse fuer Thesis-Tabellen        |
| Article XI (Thesis Alignment)        | PASS    | FF1, FF3, J1-J4, J6 direkt bedient             |
| Article XII (Resource Governance)    | PASS    | Keine neuen Docker-Services                    |

## Project Structure (New + Modified Files)

```text
evaluation/                              # EXISTING -- erweitert
├── __init__.py                          # existing
├── config.py                            # existing -- ExperimentConfig erweitern
├── ground_truth/                        # existing
│   └── leowiki_qa_50_verified.json      # existing
├── experiments/                         # existing
│   └── full_eval.yaml                   # NEW: unified pipeline config
├── providers/                           # existing
│   ├── base.py                          # existing
│   ├── ollama_provider.py               # existing
│   └── openai_provider.py               # existing
├── metrics/                             # existing -- erweitert
│   ├── mrr.py                           # existing (NICHT AENDERN)
│   ├── precision_at_k.py                # existing (NICHT AENDERN)
│   ├── ndcg.py                          # existing (NICHT AENDERN)
│   ├── recall_at_k.py                   # NEW: US8
│   ├── mean_average_precision.py        # NEW: US8
│   └── hit_rate.py                      # NEW: US8
├── ragas/                               # NEW: US1
│   ├── __init__.py
│   └── ragas_evaluator.py               # RAGAS.io Library-Wrapper
├── statistics/                          # NEW: US2
│   ├── __init__.py
│   ├── statistical_analysis.py          # Bootstrap, t-test, Wilcoxon, Cohen's d
│   └── category_analysis.py             # Per-difficulty breakdown, error analysis
├── visualization/                       # NEW: US3
│   ├── __init__.py
│   └── charts.py                        # Radar, Box, Heatmap, Bar (matplotlib/seaborn)
├── reports/                             # NEW: US4
│   ├── __init__.py
│   └── generator.py                     # Markdown + JSON report generation
├── scripts/                             # existing -- erweitert
│   ├── eval_keyword_baseline.py         # existing (NICHT AENDERN)
│   ├── eval_model_comparison.py         # existing (NICHT AENDERN)
│   ├── eval_chunk_size.py               # existing (NICHT AENDERN)
│   ├── eval_hybrid_vs_dense.py          # existing (NICHT AENDERN)
│   ├── eval_export_latex.py             # existing (NICHT AENDERN)
│   ├── eval_ragas.py                    # NEW: US1 -- RAGAS evaluation script
│   ├── eval_compare.py                  # NEW: US2 -- A/B comparison
│   ├── eval_statistics.py               # NEW: US2 -- single-run statistics
│   ├── eval_visualize.py                # NEW: US3 -- chart generation
│   ├── eval_report.py                   # NEW: US4 -- report generation
│   └── eval_pipeline.py                 # NEW: US7 -- unified orchestrator
├── tests/                               # existing -- erweitert
│   ├── test_metrics.py                  # existing (NICHT AENDERN -- 56 tests)
│   ├── test_providers.py                # existing
│   ├── test_new_metrics.py              # NEW: tests for MAP, Recall@K, Hit Rate
│   ├── test_statistics.py               # NEW: tests for StatisticalAnalyzer
│   ├── test_ragas.py                    # NEW: tests for RAGAS wrapper
│   ├── test_visualization.py            # NEW: tests for chart generation
│   └── test_reports.py                  # NEW: tests for report generator
└── results/                             # existing
    └── .gitkeep

pipeline/03_rag_preprocessing/           # EXISTING -- erweitert
├── __init__.py                          # existing
├── page_processor.py                    # MODIFY: add strategy routing, improve parser
├── metadata_enricher.py                 # MODIFY: add freshness_score, access_level
├── strategy_loader.py                   # NEW: US5 -- load Deep Eval strategies
├── media_processor.py                   # NEW: US5 -- PDF text extraction, image OCR
├── exporter.py                          # NEW: US5 -- export to data/preprocessed/
├── run_preprocessing.py                 # NEW: US5 -- main orchestrator script
└── tests/
    ├── test_page_processor.py           # NEW
    ├── test_metadata_enricher.py        # NEW
    ├── test_strategy_loader.py          # NEW
    ├── test_media_processor.py          # NEW
    └── test_exporter.py                 # NEW

pipeline/04_deploy/                      # EXISTING -- erweitert
├── transfer_to_pi.py                    # existing
├── verify_transfer.py                   # existing
├── deploy_qdrant.py                     # NEW: US6 -- direct upload + watchdog
└── tests/
    └── test_deploy_qdrant.py            # NEW
```

## Component Design

### 1. RAGAS.io Evaluator (US1)

Wrapper um die RAGAS.io Library, NICHT Re-Implementation.

```python
# evaluation/ragas/ragas_evaluator.py
from __future__ import annotations
from ragas import evaluate
from ragas.metrics import (
    context_precision, context_recall,
    faithfulness, answer_correctness,
)
from langchain_openai import ChatOpenAI

class RAGASEvaluator:
    """Wraps RAGAS.io library for LLM-as-Judge evaluation."""

    def __init__(self, llm_base_url: str, model: str, temperature: float = 0.0):
        self.llm = ChatOpenAI(
            base_url=llm_base_url,  # Ollama OpenAI-compat endpoint
            model=model,
            temperature=temperature,
            api_key="not-needed",  # Ollama doesn't need key
        )
        self.metrics = [
            context_precision, context_recall,
            faithfulness, answer_correctness,
        ]

    def evaluate(self, dataset) -> dict[str, float]:
        """Run RAGAS evaluation on a HuggingFace Dataset.

        Returns dict of metric_name -> score.
        Handles per-question errors gracefully (logs + continues).
        """
        ...
```

**Key Design Decisions**:
- Uses `langchain-openai` ChatOpenAI pointed at Ollama's `/v1` endpoint
- `temperature=0.0` for reproducibility
- Returns per-question AND aggregate scores
- Error handling: catches per-question LLM failures, logs, continues

### 2. Statistical Analyzer (US2)

Ported from prototype `ragas/professional_evaluation/metrics/statistical_analysis.py`, adapted to work with existing result JSON format.

```python
# evaluation/statistics/statistical_analysis.py
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from scipy import stats

@dataclass(frozen=True)
class BootstrapCI:
    mean: float
    ci_lower: float
    ci_upper: float
    confidence: float

@dataclass(frozen=True)
class ComparisonResult:
    metric: str
    baseline_mean: float
    candidate_mean: float
    difference: float
    p_value: float
    effect_size: float          # Cohen's d
    effect_interpretation: str  # vernachlaessigbar/klein/mittel/gross
    significant: bool           # p < 0.05

class StatisticalAnalyzer:
    """Statistical analysis for evaluation results."""

    def bootstrap_ci(self, scores: list[float], n_iterations: int = 1000,
                     confidence: float = 0.95) -> BootstrapCI: ...
    def paired_test(self, scores_a: list[float], scores_b: list[float]) -> ComparisonResult: ...
    def cohens_d(self, scores_a: list[float], scores_b: list[float]) -> tuple[float, str]: ...
    def descriptive_stats(self, scores: list[float]) -> dict[str, float]: ...
    def compare_configurations(self, baseline_path: Path, candidate_path: Path) -> list[ComparisonResult]: ...
```

**Key Design Decisions**:
- Pure functions wrapped in a class for grouping (no state)
- Uses `scipy.stats.ttest_rel` for paired data, `wilcoxon` as non-parametric alternative
- Automatically selects test based on normality (Shapiro-Wilk)
- Cohen's d with German interpretations matching thesis language

### 3. Visualization (US3)

```python
# evaluation/visualization/charts.py
from __future__ import annotations
import matplotlib.pyplot as plt
import seaborn as sns

class EvaluationVisualizer:
    """Generates thesis-quality charts from evaluation results."""

    def __init__(self, output_dir: Path, fmt: str = "png", dpi: int = 300):
        self.output_dir = output_dir
        self.fmt = fmt
        self.dpi = dpi
        # German labels, professional academic styling
        sns.set_theme(style="whitegrid", font="serif")
        plt.rcParams['axes.labelsize'] = 12

    def radar_chart(self, results: dict[str, dict[str, float]], title: str) -> Path: ...
    def box_plot(self, per_query_scores: dict[str, list[float]], title: str) -> Path: ...
    def bar_comparison(self, results: dict[str, dict[str, float]], title: str) -> Path: ...
    def heatmap(self, correlation_matrix: dict, title: str) -> Path: ...
```

**Key Design Decisions**:
- DPI >= 300 for print-quality thesis figures
- German axis labels by default
- Returns Path to generated file for report integration
- SVG output via `--format svg` for LaTeX `\includegraphics`

### 4. Report Generator (US4)

```python
# evaluation/reports/generator.py
from __future__ import annotations

class ReportGenerator:
    """Generates structured Markdown + JSON evaluation reports."""

    def generate(self, results_dir: Path) -> tuple[Path, Path]:
        """Generate Markdown and JSON reports.

        Report includes:
        - Executive Summary (best model, key findings)
        - Custom Metrics table (MRR, NDCG, P@K per model)
        - RAGAS Metrics table (Context P/R, Faithfulness per model)
        - Statistical Comparison (CI, p-values, effect sizes)
        - Difficulty Breakdown (easy/medium/hard)
        - Config details (timestamp, config-hash, code-version per NFR-005)
        """
        ...
```

### 5. Preprocessing Enhancements (US5)

#### 5a. Strategy Loader

```python
# pipeline/03_rag_preprocessing/strategy_loader.py
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class ContentType(Enum):
    KNOWLEDGE = "knowledge"
    NEWS = "news"
    PORTAL = "portal"
    FORM = "form"
    ARCHIVED = "archived"

@dataclass(frozen=True)
class PageStrategy:
    page_id: str
    content_type: ContentType
    rag_readiness: float       # 0.0 - 1.0
    recommended_chunk_size: int
    noise_level: str           # low / medium / high

class StrategyLoader:
    """Loads per-page processing strategies from Deep Evaluation output."""

    def load(self, evaluated_dir: Path) -> dict[str, PageStrategy]: ...
    def get_strategy(self, page_id: str) -> PageStrategy: ...
```

#### 5b. MetadataEnricher Enhancement

Existing `MetadataEnricher` in `pipeline/03_rag_preprocessing/metadata_enricher.py` gets two new capabilities:
- `freshness_score`: Based on last_modified date vs current date (fresh/recent/outdated/archived)
- `access_level`: Based on namespace (teacher_only if in teacher namespace, else public)

#### 5c. Media Processor

```python
# pipeline/03_rag_preprocessing/media_processor.py
from __future__ import annotations

class MediaProcessor:
    """Processes media files for RAG pipeline."""

    def process_pdf(self, pdf_path: Path) -> str:
        """Extract text from PDF. Falls back to OCR for scanned pages."""
        ...

    def process_image(self, image_path: Path) -> str:
        """OCR an image using Tesseract."""
        ...

    def process_media_directory(self, media_dir: Path) -> list[dict]:
        """Process all media files, return list of {filename, text, type}."""
        ...
```

**Dependencies**: `pytesseract` (requires Tesseract binary at `C:/Program Files/Tesseract-OCR/tesseract.exe`), `Pillow`, `PyPDF2` or `pymupdf`.

#### 5d. Exporter

```python
# pipeline/03_rag_preprocessing/exporter.py
from __future__ import annotations

class Exporter:
    """Exports preprocessed content to timestamped directories."""

    def export(self, pages: list[dict], output_base: Path) -> Path:
        """Export pages to data/preprocessed/preprocessed_at_{timestamp}/

        Each page becomes a .md file with YAML frontmatter.
        Returns path to output directory.
        """
        ...
```

### 6. Qdrant Deployment (US6)

```python
# pipeline/04_deploy/deploy_qdrant.py
from __future__ import annotations
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance

class QdrantDeployer:
    """Deploys embeddings to Qdrant (direct upload or watchdog export)."""

    def __init__(self, host: str = "192.168.8.3", port: int = 6333):
        self.client = QdrantClient(host=host, port=port)

    def deploy_direct(self, jsonl_path: Path, collection_name: str,
                      recreate: bool = False) -> int:
        """Upload JSONL embeddings directly to Qdrant.
        Returns number of points uploaded."""
        ...

    def deploy_watchdog(self, jsonl_path: Path, output_dir: Path) -> Path:
        """Copy JSONL to MCP watchdog directory for auto-ingestion."""
        ...
```

### 7. Unified Orchestrator (US7)

```python
# evaluation/scripts/eval_pipeline.py
from __future__ import annotations

class EvaluationPipeline:
    """Unified evaluation pipeline: Retrieval -> Metrics -> RAGAS -> Stats -> Viz -> Report."""

    def __init__(self, config_path: Path):
        self.config = ExperimentConfig.from_yaml(config_path)

    def run(self, skip_ragas: bool = False) -> Path:
        """Run full pipeline. Returns path to results directory.

        Steps:
        1. Qdrant Retrieval (retrieve top-k for each ground-truth query)
        2. Custom Metrics (MRR, NDCG, P@K, MAP, Recall@K)
        3. RAGAS Metrics (Context P/R, Faithfulness) -- skippable
        4. Statistical Analysis (descriptive + bootstrap CIs)
        5. Visualization (charts)
        6. Report Generation (Markdown + JSON)
        """
        ...
```

## Dependencies (Reused from Existing Code)

| Component           | Source                                                    | Usage                          |
| ------------------- | --------------------------------------------------------- | ------------------------------ |
| ExperimentConfig    | `evaluation/config.py`                                    | Config loading for all scripts |
| MRR, NDCG, P@K      | `evaluation/metrics/`                                     | Custom IR metrics (56 tests)   |
| OllamaProvider      | `evaluation/providers/ollama_provider.py`                 | Embedding generation           |
| OpenAIProvider      | `evaluation/providers/openai_provider.py`                 | Embedding generation           |
| PageProcessor       | `pipeline/03_rag_preprocessing/page_processor.py`         | DokuWiki-to-MD conversion      |
| MetadataEnricher    | `pipeline/03_rag_preprocessing/metadata_enricher.py`      | YAML frontmatter               |
| ContentAwareChunker | `pipeline/03_embeddings_creator/content_aware_chunker.py` | Chunking                       |
| WikiAPIClient       | `pipeline/01_wiki_fetcher/api_client.py`                  | Keyword baseline               |
| Ground Truth        | `evaluation/ground_truth/leowiki_qa_50_verified.json`     | All evaluations                |

## Prototype Sources (Port-from)

| New Module                           | Port From                                                                           | Adaptation                                                    |
| ------------------------------------ | ----------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| `ragas/ragas_evaluator.py`           | `research/techstack/ragas/professional_evaluation/metrics/ragas_metrics.py`         | Rewrite to use RAGAS.io library instead of custom LLM prompts |
| `statistics/statistical_analysis.py` | `research/techstack/ragas/professional_evaluation/metrics/statistical_analysis.py`  | Adapt to work with existing result JSON format                |
| `statistics/category_analysis.py`    | `research/techstack/ragas/professional_evaluation/metrics/category_analysis.py`     | Integrate with existing difficulty field from ground truth    |
| `visualization/charts.py`            | `research/techstack/ragas/professional_evaluation/visualization/charts.py`          | German labels, thesis-quality DPI, SVG support                |
| `reports/generator.py`               | `research/techstack/ragas/professional_evaluation/reports/generator.py`             | Add RAGAS + Custom metrics side-by-side                       |
| `strategy_loader.py`                 | `research/techstack/ragflow/test_suite_rag_preprocessing/script/strategy_loader.py` | Adapt to dev_dito directory structure                         |
| `media_processor.py`                 | `research/techstack/ragflow/test_suite_rag_preprocessing/script/media_processor.py` | Use Tesseract path from env.yaml                              |
| `exporter.py`                        | `research/techstack/ragflow/test_suite_rag_preprocessing/script/exporter.py`        | Export to data/preprocessed/                                  |
| `deploy_qdrant.py`                   | NEW (partially from `04_deploy/transfer_to_pi.py`)                                  | qdrant_client direct upload + watchdog mode                   |
| `metrics/recall_at_k.py`             | `research/techstack/ragas/professional_evaluation/metrics/retrieval_metrics.py`     | Extract Recall@K as pure function                             |
| `metrics/mean_average_precision.py`  | same source                                                                         | Extract MAP as pure function                                  |
| `metrics/hit_rate.py`                | same source                                                                         | Extract Hit Rate as pure function                             |

## Implementation Phases

### Phase 1: Additional IR Metrics (US8) -- Day 1
- `evaluation/metrics/recall_at_k.py` + tests
- `evaluation/metrics/mean_average_precision.py` + tests
- `evaluation/metrics/hit_rate.py` + tests
- Pure functions, same pattern as existing metrics
- **Deliverable**: All tests pass (56 existing + ~20 new)

### Phase 2: Statistical Analysis (US2) -- Days 2-3
- `evaluation/statistics/statistical_analysis.py` + tests
- `evaluation/statistics/category_analysis.py` + tests
- `evaluation/scripts/eval_statistics.py` (single-run descriptive stats)
- `evaluation/scripts/eval_compare.py` (A/B comparison)
- **Deliverable**: Can compare two result JSONs with p-values + CIs

### Phase 3: RAGAS.io Integration (US1) -- Days 4-5
- `pip install ragas datasets langchain-openai`
- `evaluation/ragas/ragas_evaluator.py` + tests
- `evaluation/scripts/eval_ragas.py`
- Test against Ollama on 192.168.8.3:11434
- **Deliverable**: RAGAS scores for 50 ground-truth questions

### Phase 4: Visualization + Reports (US3, US4) -- Days 6-7
- `evaluation/visualization/charts.py` + tests
- `evaluation/reports/generator.py` + tests
- `evaluation/scripts/eval_visualize.py`
- `evaluation/scripts/eval_report.py`
- **Deliverable**: PNG/SVG charts + Markdown report from result JSONs

### Phase 5: Preprocessing Completion (US5) -- Days 8-10
- `pipeline/03_rag_preprocessing/strategy_loader.py` + tests
- `pipeline/03_rag_preprocessing/media_processor.py` + tests
- `pipeline/03_rag_preprocessing/exporter.py` + tests
- Modify `page_processor.py`: strategy-aware routing
- Modify `metadata_enricher.py`: freshness_score + access_level
- `pipeline/03_rag_preprocessing/run_preprocessing.py` orchestrator
- **Deliverable**: `data/fetched/` -> `data/preprocessed/` full conversion

### Phase 6: Qdrant Deployment (US6) -- Day 11
- `pipeline/04_deploy/deploy_qdrant.py` + tests
- Direct upload mode via `qdrant_client`
- Watchdog export mode (file copy)
- **Deliverable**: Embeddings in Qdrant, queryable

### Phase 7: Unified Orchestrator (US7) -- Day 12
- `evaluation/scripts/eval_pipeline.py`
- Chains: Retrieval -> Custom Metrics -> RAGAS -> Stats -> Viz -> Report
- `--skip ragas` flag for fast iterations
- **Deliverable**: Single command runs full evaluation

### Phase 8: Integration Testing + Polish -- Days 13-14
- End-to-end: preprocessed data -> embeddings -> Qdrant -> evaluation -> report
- Verify all NFR-005 fields (timestamp, config-hash, code-version)
- Run full pipeline on actual LeoWiki data
- Fix edge cases discovered during integration
- **Deliverable**: Complete pipeline works end-to-end

**Total estimated effort**: 14 focused days. Statistical analysis available from Day 3, RAGAS from Day 5, full pipeline from Day 12.

## Risk Mitigations

| Risk                                 | Mitigation                                                          | Phase |
| ------------------------------------ | ------------------------------------------------------------------- | ----- |
| RAGAS.io incompatible with Ollama    | Test early in Phase 3. Fallback: use prototype's custom LLM prompts | 3     |
| Tesseract not installed              | `media_processor.py` gracefully skips OCR, logs warning             | 5     |
| Qdrant on Pi unreachable             | Deploy script has `--dry-run` mode, local Qdrant fallback           | 6     |
| Large media files slow preprocessing | Configurable extraction limits from env.yaml (pdf_max_pages, etc.)  | 5     |

## Complexity Tracking

No Constitution violations. All new components:
- Use direct SDK/library calls (Article VIII)
- Reuse existing code patterns (Article VII)
- Serve thesis deliverables directly (Article XI)
- Follow existing directory conventions
- Include tests per TDD mandate (NFR-002)
