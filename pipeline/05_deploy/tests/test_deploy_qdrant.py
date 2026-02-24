"""Tests for QdrantDeployer (T082-T085)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture()
def sample_jsonl(tmp_path: Path) -> Path:
    """Create a sample embeddings JSONL file."""
    f = tmp_path / "embedded_chunks.jsonl"
    lines = []
    for i in range(5):
        lines.append(
            json.dumps(
                {
                    "id": f"point_{i}",
                    "vector": [0.1 * i] * 384,
                    "payload": {
                        "text": f"Sample chunk text {i}",
                        "page_id": f"ns:page_{i}",
                        "chunk_index": i,
                    },
                }
            )
        )
    f.write_text("\n".join(lines), encoding="utf-8")
    return f


@pytest.fixture()
def mock_qdrant_client() -> MagicMock:
    """Create a mock QdrantClient."""
    client = MagicMock()
    # MagicMock(name=...) uses 'name' as the mock's internal id, not attribute.
    # So we create a plain object with a .name attribute instead.
    mock_coll = MagicMock()
    mock_coll.name = "existing_collection"
    client.get_collections.return_value = MagicMock(collections=[mock_coll])
    client.upsert.return_value = None
    client.delete_collection.return_value = True
    client.create_collection.return_value = True
    return client


class TestDirectUpload:
    """T082: Tests for direct Qdrant upload."""

    def test_deploy_direct_returns_count(
        self, sample_jsonl: Path, mock_qdrant_client: MagicMock
    ) -> None:
        from deploy_qdrant import QdrantDeployer

        deployer = QdrantDeployer.__new__(QdrantDeployer)
        deployer.client = mock_qdrant_client
        count = deployer.deploy_direct(sample_jsonl, "test_collection")
        assert count == 5

    def test_deploy_direct_calls_upsert(
        self, sample_jsonl: Path, mock_qdrant_client: MagicMock
    ) -> None:
        from deploy_qdrant import QdrantDeployer

        deployer = QdrantDeployer.__new__(QdrantDeployer)
        deployer.client = mock_qdrant_client
        deployer.deploy_direct(sample_jsonl, "test_collection")
        assert mock_qdrant_client.upsert.called

    def test_deploy_direct_creates_collection_if_missing(
        self, sample_jsonl: Path, mock_qdrant_client: MagicMock
    ) -> None:
        from deploy_qdrant import QdrantDeployer

        mock_qdrant_client.get_collections.return_value = MagicMock(collections=[])
        deployer = QdrantDeployer.__new__(QdrantDeployer)
        deployer.client = mock_qdrant_client
        deployer.deploy_direct(sample_jsonl, "new_collection")
        assert mock_qdrant_client.create_collection.called

    def test_deploy_direct_empty_file(self, tmp_path: Path, mock_qdrant_client: MagicMock) -> None:
        from deploy_qdrant import QdrantDeployer

        empty = tmp_path / "empty.jsonl"
        empty.write_text("", encoding="utf-8")
        deployer = QdrantDeployer.__new__(QdrantDeployer)
        deployer.client = mock_qdrant_client
        count = deployer.deploy_direct(empty, "test_collection")
        assert count == 0


class TestWatchdogMode:
    """T083: Tests for watchdog mode (file copy)."""

    def test_deploy_watchdog_returns_path(self, sample_jsonl: Path, tmp_path: Path) -> None:
        from deploy_qdrant import QdrantDeployer

        deployer = QdrantDeployer.__new__(QdrantDeployer)
        deployer.client = MagicMock()
        out_dir = tmp_path / "watchdog_out"
        result = deployer.deploy_watchdog(sample_jsonl, out_dir)
        assert isinstance(result, Path)
        assert result.exists()

    def test_deploy_watchdog_copies_file(self, sample_jsonl: Path, tmp_path: Path) -> None:
        from deploy_qdrant import QdrantDeployer

        deployer = QdrantDeployer.__new__(QdrantDeployer)
        deployer.client = MagicMock()
        out_dir = tmp_path / "watchdog_out"
        result = deployer.deploy_watchdog(sample_jsonl, out_dir)
        assert result.read_text(encoding="utf-8") == sample_jsonl.read_text(encoding="utf-8")

    def test_deploy_watchdog_creates_output_dir(self, sample_jsonl: Path, tmp_path: Path) -> None:
        from deploy_qdrant import QdrantDeployer

        deployer = QdrantDeployer.__new__(QdrantDeployer)
        deployer.client = MagicMock()
        out_dir = tmp_path / "nested" / "watchdog"
        deployer.deploy_watchdog(sample_jsonl, out_dir)
        assert out_dir.exists()


class TestRecreateCollection:
    """T084: Tests for --recreate collection behavior."""

    def test_recreate_deletes_existing_collection(
        self, sample_jsonl: Path, mock_qdrant_client: MagicMock
    ) -> None:
        from deploy_qdrant import QdrantDeployer

        deployer = QdrantDeployer.__new__(QdrantDeployer)
        deployer.client = mock_qdrant_client
        deployer.deploy_direct(sample_jsonl, "existing_collection", recreate=True)
        mock_qdrant_client.delete_collection.assert_called_with(
            collection_name="existing_collection"
        )
        mock_qdrant_client.create_collection.assert_called()

    def test_recreate_false_keeps_collection(
        self, sample_jsonl: Path, mock_qdrant_client: MagicMock
    ) -> None:
        from deploy_qdrant import QdrantDeployer

        deployer = QdrantDeployer.__new__(QdrantDeployer)
        deployer.client = mock_qdrant_client
        deployer.deploy_direct(sample_jsonl, "existing_collection", recreate=False)
        mock_qdrant_client.delete_collection.assert_not_called()


class TestUpsertOnly:
    """T085: Tests for upsert-only behavior (without --recreate)."""

    def test_upsert_adds_to_existing_collection(
        self, sample_jsonl: Path, mock_qdrant_client: MagicMock
    ) -> None:
        from deploy_qdrant import QdrantDeployer

        deployer = QdrantDeployer.__new__(QdrantDeployer)
        deployer.client = mock_qdrant_client
        count = deployer.deploy_direct(sample_jsonl, "existing_collection", recreate=False)
        assert count == 5
        assert mock_qdrant_client.upsert.called
        mock_qdrant_client.delete_collection.assert_not_called()
        mock_qdrant_client.create_collection.assert_not_called()


class TestDryRun:
    """Tests for --dry-run validation without upload."""

    def test_dry_run_does_not_upload(
        self, sample_jsonl: Path, mock_qdrant_client: MagicMock
    ) -> None:
        from deploy_qdrant import QdrantDeployer

        deployer = QdrantDeployer.__new__(QdrantDeployer)
        deployer.client = mock_qdrant_client
        count = deployer.deploy_direct(sample_jsonl, "test", dry_run=True)
        assert count == 5  # validation count
        mock_qdrant_client.upsert.assert_not_called()
