"""
Tests for Pipeline Data Schemas
=================================
Constitution Article II: JSON Interface Standard
Constitution Article III: Critical-Path Unit Testing

Tests:
- pipeline_runs.schema.json is valid JSON Schema
- Sample pipeline run data validates against schema
- Invalid data is correctly rejected
- JSONL output format expectations
"""

import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest

from tests.conftest import DATA_DIR

# =============================================================================
# Test: Schema File Validity
# =============================================================================


class TestPipelineRunsSchema:
    """Validate the pipeline_runs.schema.json file itself."""

    @pytest.fixture
    def schema_path(self) -> Path:
        return DATA_DIR / "logs" / "pipeline_runs.schema.json"

    @pytest.fixture
    def schema(self, schema_path: Path) -> dict:
        assert schema_path.exists(), f"Schema file not found: {schema_path}"
        with open(schema_path, encoding="utf-8") as f:
            return json.load(f)

    def test_schema_file_exists(self, schema_path: Path) -> None:
        assert schema_path.exists()

    def test_schema_is_valid_json(self, schema: dict) -> None:
        assert isinstance(schema, dict)
        assert "$schema" in schema or "type" in schema

    def test_schema_defines_array_type(self, schema: dict) -> None:
        assert schema.get("type") == "array", "Root schema type must be 'array'"

    def test_schema_has_required_fields(self, schema: dict) -> None:
        items = schema.get("items", {})
        required = items.get("required", [])
        expected_required = ["job_id", "stage", "status", "started_at"]
        for field in expected_required:
            assert field in required, f"Schema missing required field: {field}"

    def test_schema_stage_enum(self, schema: dict) -> None:
        items = schema.get("items", {})
        stage_prop = items.get("properties", {}).get("stage", {})
        assert "enum" in stage_prop, "stage must have enum constraint"
        expected_stages = ["fetch", "evaluate", "preprocess", "embed", "deploy"]
        assert set(stage_prop["enum"]) == set(expected_stages)

    def test_schema_status_enum(self, schema: dict) -> None:
        items = schema.get("items", {})
        status_prop = items.get("properties", {}).get("status", {})
        assert "enum" in status_prop, "status must have enum constraint"
        expected_statuses = ["running", "success", "error", "interrupted"]
        assert set(status_prop["enum"]) == set(expected_statuses)


# =============================================================================
# Test: Schema Validation with Sample Data
# =============================================================================


class TestSchemaValidation:
    """Validate sample data against the pipeline_runs schema."""

    @pytest.fixture
    def schema(self) -> dict:
        schema_path = DATA_DIR / "logs" / "pipeline_runs.schema.json"
        with open(schema_path, encoding="utf-8") as f:
            return json.load(f)

    def test_valid_data_passes(
        self, schema: dict, sample_pipeline_runs: list[dict[str, Any]]
    ) -> None:
        """Valid sample data should pass schema validation."""
        jsonschema.validate(instance=sample_pipeline_runs, schema=schema)

    def test_empty_array_passes(self, schema: dict) -> None:
        """Empty array is valid (no pipeline runs yet)."""
        jsonschema.validate(instance=[], schema=schema)

    def test_missing_required_field_fails(self, schema: dict) -> None:
        """Entry missing required 'job_id' should fail validation."""
        invalid_data = [
            {
                # "job_id" intentionally missing
                "stage": "fetch",
                "status": "success",
                "started_at": "2026-02-01T12:00:00Z",
            }
        ]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid_data, schema=schema)

    def test_invalid_stage_fails(self, schema: dict) -> None:
        """Invalid stage value should fail validation."""
        invalid_data = [
            {
                "job_id": "fetch_20260201_120000",
                "stage": "invalid_stage",
                "status": "success",
                "started_at": "2026-02-01T12:00:00Z",
            }
        ]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid_data, schema=schema)

    def test_invalid_status_fails(self, schema: dict) -> None:
        """Invalid status value should fail validation."""
        invalid_data = [
            {
                "job_id": "fetch_20260201_120000",
                "stage": "fetch",
                "status": "unknown_status",
                "started_at": "2026-02-01T12:00:00Z",
            }
        ]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid_data, schema=schema)


# =============================================================================
# Test: Existing pipeline_runs.json Validity
# =============================================================================


class TestExistingPipelineRuns:
    """If pipeline_runs.json exists, validate it against the schema."""

    def test_existing_runs_file_is_valid(self) -> None:
        runs_path = DATA_DIR / "logs" / "pipeline_runs.json"
        schema_path = DATA_DIR / "logs" / "pipeline_runs.schema.json"

        if not runs_path.exists():
            pytest.skip("No pipeline_runs.json found (expected in fresh setup)")

        with open(runs_path, encoding="utf-8") as f:
            runs_data = json.load(f)

        with open(schema_path, encoding="utf-8") as f:
            schema = json.load(f)

        jsonschema.validate(instance=runs_data, schema=schema)
