"""
Dev Dito - Shared Test Fixtures
================================
Constitution Article III: Critical-Path Unit Testing
Constitution Article IX: Realistic Integration Testing

Provides:
- REPO_ROOT path fixture
- Temporary config directory fixtures
- YAML config factory fixtures
"""
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

import pytest
import yaml


# =============================================================================
# Path Constants
# =============================================================================

REPO_ROOT = Path(__file__).parent.parent.resolve()
CONFIG_DIR = REPO_ROOT / "config"
BACKEND_SERVICES_DIR = REPO_ROOT / "backend_services"
DATA_DIR = REPO_ROOT / "data"
SPECS_DIR = REPO_ROOT / "specs"


# =============================================================================
# Path Fixtures
# =============================================================================


@pytest.fixture
def repo_root() -> Path:
    """Repository root directory."""
    return REPO_ROOT


@pytest.fixture
def config_dir() -> Path:
    """Config directory path."""
    return CONFIG_DIR


@pytest.fixture
def backend_services_dir() -> Path:
    """Backend services directory path."""
    return BACKEND_SERVICES_DIR


@pytest.fixture
def data_dir() -> Path:
    """Data directory path."""
    return DATA_DIR


# =============================================================================
# Temporary Config Fixtures
# =============================================================================


@pytest.fixture
def tmp_config_dir(tmp_path: Path) -> Path:
    """
    Creates a temporary config directory with a minimal env.yaml.
    Useful for testing config loading without touching real config.
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def minimal_env_yaml(tmp_config_dir: Path) -> Path:
    """
    Creates a minimal but valid env.yaml in a temporary directory.
    Returns the path to the created file.
    """
    config_data = {
        "APP": {
            "name": "dev_dito_test",
            "version": "0.0.1-test",
        },
        "PATHS": {
            "root_dir": str(tmp_config_dir.parent),
            "config_dir": "${root_dir}/config",
            "secrets_dir": "${config_dir}/secrets",
            "data_dir": "${root_dir}/data",
        },
        "SOURCE_WIKI": {
            "api": {
                "url": "https://test-wiki.example.com/lib/exe/jsonrpc.php",
                "base_url": "https://test-wiki.example.com",
            },
            "authentication": {
                "type": "bearer",
                "token_file": "${secrets_dir}/json_rpc_api.token",
            },
        },
        "SERVICES": {
            "mcp_server": {
                "url": "http://localhost:3000",
                "timeout": 10,
            },
            "qdrant": {
                "host": "localhost",
                "port": 18334,
                "collection": "test_wiki_embeddings",
            },
        },
        "PIPELINE": {
            "fetcher": {"timeout": 5, "max_retries": 1},
            "embedder": {"chunk_size": 256, "chunk_overlap": 25},
        },
        "PLUGIN": {
            "enabled": True,
            "panel_position": "right",
            "search_results_limit": 3,
        },
    }
    yaml_path = tmp_config_dir / "env.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f, default_flow_style=False)
    return yaml_path


@pytest.fixture
def sample_pipeline_runs() -> list[dict[str, Any]]:
    """Sample pipeline_runs.json data for schema validation tests."""
    return [
        {
            "job_id": "fetch_20260201_120000",
            "stage": "fetch",
            "status": "success",
            "started_at": "2026-02-01T12:00:00Z",
            "finished_at": "2026-02-01T12:05:30Z",
            "updated_at": "2026-02-01T12:05:30Z",
            "duration_seconds": 330,
            "output_dir": "data/fetched/fetched_at_20260201",
            "stats": {"pages": 150, "media": 42},
            "error": None,
            "progress": None,
        },
        {
            "job_id": "embed_20260201_130000",
            "stage": "embed",
            "status": "running",
            "started_at": "2026-02-01T13:00:00Z",
            "finished_at": None,
            "updated_at": "2026-02-01T13:02:15Z",
            "duration_seconds": None,
            "output_dir": None,
            "stats": None,
            "error": None,
            "progress": {"current": 45, "total": 150, "message": "Embedding batch 3/10"},
        },
    ]
