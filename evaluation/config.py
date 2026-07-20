"""YAML experiment config loader for evaluation infrastructure.

Loads and validates experiment configuration files that define
embedding provider, model, chunk size, retrieval mode, and metrics.
Per Article II-B, all config is in YAML files.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

logger = logging.getLogger(__name__)

EVAL_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True, slots=True)
class ExperimentConfig:
    """Validated experiment configuration.

    Attributes:
        name: Human-readable experiment name.
        experiment_type: One of the supported experiment types.
        thesis_id: Thesis deliverable reference (e.g. 'J2/FF3').
        provider: Embedding provider name ('ollama' or 'openai').
        model: Model identifier for the provider.
        dimensions: Expected embedding vector dimensions.
        chunk_size: Number of tokens per chunk.
        chunk_overlap: Token overlap between chunks.
        retrieval_mode: Dense-only or hybrid (dense + BM25).
        top_k: Number of results to retrieve per query.
        collection_prefix: Prefix for temporary Qdrant collections.
        ground_truth_file: Path to ground truth JSON relative to evaluation/.
        metrics: List of metrics to compute.
        config_hash: SHA-256 hash of the raw YAML for reproducibility (NFR-005).
    """

    name: str
    experiment_type: Literal[
        "model_comparison", "chunk_size", "hybrid_vs_dense", "keyword_baseline"
    ]
    thesis_id: str
    provider: Literal["ollama", "openai", "sentence-transformers"]
    model: str
    dimensions: int
    chunk_size: int = 512
    chunk_overlap: int = 50
    retrieval_mode: Literal["dense", "hybrid"] = "dense"
    top_k: int = 10
    collection_prefix: str = "eval_"
    ground_truth_file: str = "ground_truth/leowiki_qa_50_verified.json"
    metrics: tuple[str, ...] = ("mrr", "precision_at_5", "ndcg_at_10")
    torch_dtype: str = "float32"
    config_hash: str = ""
    # RAGAS (LLM-as-Judge) - optional
    llm_base_url: str = "http://localhost:11434/v1"
    llm_model: str = "llama3.2"
    ragas_temperature: float = 0.0
    # Report and visualization
    output_format: str = "markdown"
    dpi: int = 300


def load_experiment_config(config_path: str | Path) -> ExperimentConfig:
    """Load and validate an experiment YAML config file.

    Args:
        config_path: Path to the YAML config file.

    Returns:
        Validated ExperimentConfig instance.

    Raises:
        FileNotFoundError: If config file does not exist.
        ValueError: If required fields are missing or invalid.
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")

    raw_bytes = path.read_bytes()
    config_hash = hashlib.sha256(raw_bytes).hexdigest()
    raw: dict[str, Any] = yaml.safe_load(raw_bytes.decode("utf-8"))

    experiment = raw.get("experiment", {})
    embedding = raw.get("embedding", {})
    chunking = raw.get("chunking", {})
    retrieval = raw.get("retrieval", {})
    ground_truth = raw.get("ground_truth", {})
    metrics_list = raw.get("metrics", ["mrr", "precision_at_5", "ndcg_at_10"])
    ragas = raw.get("ragas", {})
    report = raw.get("report", {})

    return ExperimentConfig(
        name=experiment.get("name", path.stem),
        experiment_type=experiment.get("type", "model_comparison"),
        thesis_id=experiment.get("thesis_id", ""),
        provider=embedding.get("provider", "ollama"),
        model=embedding.get("model", ""),
        dimensions=embedding.get("dimensions", 1024),
        torch_dtype=embedding.get("torch_dtype", "float32"),
        chunk_size=chunking.get("chunk_size", 512),
        chunk_overlap=chunking.get("chunk_overlap", 50),
        retrieval_mode=retrieval.get("mode", "dense"),
        top_k=retrieval.get("top_k", 10),
        collection_prefix=retrieval.get("collection_prefix", "eval_"),
        ground_truth_file=ground_truth.get("file", "ground_truth/leowiki_qa_50_verified.json"),
        metrics=tuple(metrics_list),
        config_hash=f"sha256:{config_hash}",
        llm_base_url=ragas.get("llm_base_url", "http://localhost:11434/v1"),
        llm_model=ragas.get("model", "llama3.2"),
        ragas_temperature=float(ragas.get("temperature", 0.0)),
        output_format=report.get("output_format", "markdown"),
        dpi=int(report.get("dpi", 300)),
    )


def load_ground_truth(gt_path: str | Path | None = None) -> dict:
    """Load ground truth Q&A pairs from JSON.

    Args:
        gt_path: Path to ground truth file. Defaults to the standard location.

    Returns:
        Parsed JSON dict with 'metadata' and 'qa_pairs' keys.

    Raises:
        FileNotFoundError: If ground truth file does not exist.
    """
    import json

    if gt_path is None:
        gt_path = EVAL_ROOT / "ground_truth" / "leowiki_qa_50_verified.json"
    else:
        gt_path = Path(gt_path)

    if not gt_path.exists():
        raise FileNotFoundError(f"Ground truth not found: {gt_path}")

    with open(gt_path, encoding="utf-8") as f:
        return json.load(f)
