"""
Tests for backend_services/orchestrator/server.py

Covers:
  - PIPELINE_STAGES unified dict structure (FR-013)
  - Sort key correctness: started_at, not updated_at (FR-006)
  - RunRequest Pydantic model defaults
  - FR-004: /run/{stage} returns 409 when a job is already active
"""

import sys
from pathlib import Path

import pytest

# Make the orchestrator module importable without installing it
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend_services" / "orchestrator"))

import server  # noqa: E402  (module-level import after sys.path manipulation)

# ---------------------------------------------------------------------------
# PIPELINE_STAGES structure
# ---------------------------------------------------------------------------

EXPECTED_STAGES = ["fetch", "evaluate", "preprocess", "embed", "deploy"]
REQUIRED_KEYS = {"name", "container", "pipeline_dir"}


class TestPipelineStagesStructure:
    def test_has_exactly_five_stages(self) -> None:
        assert list(server.PIPELINE_STAGES.keys()) == EXPECTED_STAGES

    def test_each_stage_has_required_keys(self) -> None:
        for stage_id, cfg in server.PIPELINE_STAGES.items():
            missing = REQUIRED_KEYS - cfg.keys()
            assert not missing, f"Stage '{stage_id}' missing keys: {missing}"

    def test_deploy_has_entrypoint_args(self) -> None:
        assert "entrypoint_args" in server.PIPELINE_STAGES["deploy"]

    def test_deploy_entrypoint_args_correct(self) -> None:
        args = server.PIPELINE_STAGES["deploy"]["entrypoint_args"]
        assert args[:3] == ["python", "run_deploy.py", "qdrant"]

    def test_embed_has_needs_openai_key(self) -> None:
        assert server.PIPELINE_STAGES["embed"].get("needs_openai_key") is True

    def test_no_other_stage_needs_openai_key(self) -> None:
        for stage_id, cfg in server.PIPELINE_STAGES.items():
            if stage_id != "embed":
                assert not cfg.get(
                    "needs_openai_key"
                ), f"Stage '{stage_id}' unexpectedly requires OpenAI key"


# ---------------------------------------------------------------------------
# Sort key: get_last_run must use started_at, not updated_at
# ---------------------------------------------------------------------------


class TestGetLastRunSortKey:
    def test_returns_none_when_no_runs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        status_file = tmp_path / "pipeline_runs.json"
        status_file.write_text("[]")
        monkeypatch.setattr(server, "STATUS_FILE", status_file)
        assert server.get_last_run("fetch") is None

    def test_picks_latest_started_at_not_updated_at(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        Two runs for 'fetch':
          - run_a: started_at EARLIER, updated_at LATER  (should NOT win)
          - run_b: started_at LATER,   updated_at EARLIER (SHOULD win)
        get_last_run must return run_b.
        """
        import json

        run_a = {
            "job_id": "fetch_20260101_100000",
            "stage": "fetch",
            "status": "success",
            "started_at": "2026-01-01T10:00:00",
            "updated_at": "2026-01-01T12:00:00",  # later updated_at
        }
        run_b = {
            "job_id": "fetch_20260101_110000",
            "stage": "fetch",
            "status": "success",
            "started_at": "2026-01-01T11:00:00",  # later started_at
            "updated_at": "2026-01-01T11:05:00",
        }
        status_file = tmp_path / "pipeline_runs.json"
        status_file.write_text(json.dumps([run_a, run_b]))
        monkeypatch.setattr(server, "STATUS_FILE", status_file)

        result = server.get_last_run("fetch")
        assert result is not None
        assert (
            result["job_id"] == "fetch_20260101_110000"
        ), "get_last_run must sort by started_at, not updated_at"


# ---------------------------------------------------------------------------
# RunRequest Pydantic model
# ---------------------------------------------------------------------------


class TestRunRequest:
    def test_default_options_is_empty_dict(self) -> None:
        req = server.RunRequest()
        assert req.options == {}

    def test_options_accepts_string_dict(self) -> None:
        req = server.RunRequest(options={"mode": "incremental"})
        assert req.options["mode"] == "incremental"


# ---------------------------------------------------------------------------
# FR-004: concurrent job rejection (409)
# ---------------------------------------------------------------------------


class TestConcurrentJobRejection:
    def test_active_job_detected_when_status_running(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """
        FR-004 guard: get_active_job() must return the running job so that
        /run/{stage} can raise HTTP 409.  Tests the guard predicate directly
        (avoids starlette TestClient version incompatibilities).
        """
        import json

        active_run = {
            "job_id": "fetch_20260101_100000",
            "stage": "fetch",
            "status": "running",
            "started_at": "2026-01-01T10:00:00",
        }
        status_file = tmp_path / "pipeline_runs.json"
        status_file.write_text(json.dumps([active_run]))
        monkeypatch.setattr(server, "STATUS_FILE", status_file)

        active = server.get_active_job()
        assert active is not None, "get_active_job() must detect the running job"
        assert active["job_id"] == "fetch_20260101_100000"
        assert active["status"] == "running"

    def test_no_active_job_when_all_finished(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_active_job() must return None when no jobs are running."""
        import json

        runs = [
            {
                "job_id": "fetch_old",
                "stage": "fetch",
                "status": "success",
                "started_at": "2026-01-01T09:00:00",
            },
            {
                "job_id": "fetch_err",
                "stage": "fetch",
                "status": "error",
                "started_at": "2026-01-01T08:00:00",
            },
        ]
        status_file = tmp_path / "pipeline_runs.json"
        status_file.write_text(json.dumps(runs))
        monkeypatch.setattr(server, "STATUS_FILE", status_file)

        assert server.get_active_job() is None
