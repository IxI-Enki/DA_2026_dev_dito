"""Shared fixtures for 04_embeddings_creator tests (TDD)."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

# Ensure 04_embeddings_creator is importable
_pkg = Path(__file__).resolve().parent.parent
if str(_pkg) not in sys.path:
    sys.path.insert(0, str(_pkg))


@dataclass
class PathsConfig:
    root_dir: str
    config_dir: str
    script_dir: str
    output_dir: str
    log_dir: str
    preprocessing_base: str
    input_dir: str


@dataclass
class ChunkingConfig:
    default: dict[str, Any]
    content_types: dict[str, dict[str, Any]]


@dataclass
class OutputConfig:
    format: str
    encoding: str
    combined: bool
    filename: str
    schema: dict[str, str]
    include_metadata: dict[str, bool]


@dataclass
class MinimalConfig:
    """Minimal config for unit tests (no env.yaml required)."""

    paths: PathsConfig
    chunking: ChunkingConfig
    output: Any = field(default_factory=dict)
    text_prep: dict[str, Any] = field(default_factory=dict)
    statistics: dict[str, Any] = field(default_factory=dict)
    logging: dict[str, Any] = field(default_factory=dict)
    processing: dict[str, Any] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)
    app: dict[str, Any] = field(default_factory=dict)
    openai: Any = field(default_factory=MagicMock)
    _raw: dict[str, Any] = field(default_factory=dict, repr=False)

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        value = self._raw
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value


@pytest.fixture
def minimal_chunker_config() -> MinimalConfig:
    """Config for ContentAwareChunker tests (no env.yaml)."""
    paths = PathsConfig(
        root_dir=str(_pkg),
        config_dir=str(_pkg),
        script_dir=str(_pkg),
        output_dir=str(_pkg / "out"),
        log_dir=str(_pkg / "logs"),
        preprocessing_base=str(_pkg),
        input_dir=str(_pkg),
    )
    chunking = ChunkingConfig(
        default={
            "method": "semantic",
            "max_chunk_size": 512,
            "chunk_overlap": 50,
            "min_chunk_size": 100,
        },
        content_types={
            "EMPTY": {"action": "skip"},
            "KNOWLEDGE": {"method": "recursive_header", "max_chunk_size": 512},
            "NEWS": {"method": "naive", "max_chunk_size": 1024},
        },
    )
    text_prep = {
        "include_frontmatter_in_text": True,
        "frontmatter_fields_in_text": ["title", "namespace", "content_type"],
    }
    return MinimalConfig(
        paths=paths,
        chunking=chunking,
        text_prep=text_prep,
        output=MagicMock(),
        statistics={},
        logging={},
        processing={},
        validation={},
        app={"name": "test"},
        _raw={
            "CHUNKING": {"default": chunking.default, "content_types": chunking.content_types},
            "TEXT_PREP": text_prep,
        },
    )


@pytest.fixture
def minimal_output_schema() -> dict[str, str]:
    """MCP-compatible output schema (id, text, embedding, metadata)."""
    return {
        "id_field": "id",
        "text_field": "text",
        "embedding_field": "embedding",
        "metadata_field": "metadata",
    }


@pytest.fixture
def minimal_include_metadata() -> dict[str, bool]:
    """Metadata fields included in output (MCP payload)."""
    return {
        "source": True,
        "collection": True,
        "title": True,
        "namespace": True,
        "page_id": True,
        "media_id": True,
        "access_level": True,
        "content_type": True,
        "chunk_index": True,
        "total_chunks": True,
        "embedding_model": True,
        "embedding_dimensions": True,
        "created_at": True,
    }
