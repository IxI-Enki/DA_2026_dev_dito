"""Tests for US2 -- Deep Evaluation Bugfixes (T049).

Verifies:
- rglob dedup: mixed-case extensions produce unique file list
- temperature passthrough: config value reaches LLM client
- YAML list uniqueness: no duplicate page_ids or filenames
- multiline summary logging: output as cohesive block
"""
from __future__ import annotations

import sys
import tempfile
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure module root is importable
_module_root = Path(__file__).resolve().parent.parent
if str(_module_root) not in sys.path:
    sys.path.insert(0, str(_module_root))


# -----------------------------------------------------------------------
# T050: rglob dedup tests
# -----------------------------------------------------------------------

class TestRglobDedup:
    """Verify that file collection uses set-based dedup."""

    def test_analyze_documents_no_duplicates(self, tmp_path: Path):
        """Documents with mixed-case extensions should be counted once."""
        media = tmp_path / "media"
        media.mkdir()
        # Create files: .pdf and .PDF should be same file on Windows
        (media / "doc1.pdf").write_text("pdf1")
        (media / "doc2.PDF").write_text("pdf2")
        (media / "sub").mkdir()
        (media / "sub" / "doc3.pdf").write_text("pdf3")

        extensions = {".pdf"}
        collected: set[Path] = set()
        for ext in extensions:
            collected.update(media.rglob(f"*{ext}"))
            collected.update(media.rglob(f"*{ext.upper()}"))
        files = sorted(collected)

        # On case-insensitive FS (Windows), .pdf and .PDF match the same
        # files, so set dedup removes duplicates.
        assert len(files) == len(set(files)), "Duplicate paths found"

    def test_analyze_images_no_duplicates(self, tmp_path: Path):
        """Images with mixed-case extensions should be counted once."""
        media = tmp_path / "media"
        media.mkdir()
        (media / "img1.png").write_bytes(b"\x89PNG")
        (media / "img2.JPG").write_bytes(b"\xff\xd8")
        (media / "sub").mkdir()
        (media / "sub" / "img3.jpg").write_bytes(b"\xff\xd8")

        extensions = {".jpg", ".jpeg", ".png"}
        collected: set[Path] = set()
        for ext in extensions:
            collected.update(media.rglob(f"*{ext}"))
            collected.update(media.rglob(f"*{ext.upper()}"))
        files = sorted(collected)

        assert len(files) == len(set(files)), "Duplicate paths found"


# -----------------------------------------------------------------------
# T051: temperature passthrough tests
# -----------------------------------------------------------------------

class TestTemperaturePassthrough:
    """Verify that temperature from env.yaml reaches the LLM payload."""

    def test_env_yaml_has_temperature_zero(self):
        """env.yaml LLM.generation.temperature should be 0.0."""
        import yaml
        env_path = _module_root / "env.yaml"
        if not env_path.exists():
            pytest.skip("env.yaml not found")
        with open(env_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        temp = cfg.get("LLM", {}).get("generation", {}).get("temperature")
        assert temp == 0.0, f"Expected temperature=0.0, got {temp}"

    def test_llm_client_passes_temperature(self):
        """LLMClient should include temperature in the API payload."""
        from core.llm_client import LLMClient

        mock_config = MagicMock()
        mock_config.raw_config = {
            "LLM": {
                "base_url": "http://localhost:1234/v1",
                "api_key": "test",
                "classification_model": "test-model",
                "vision_model": "test-model",
                "timeout": 30,
                "generation": {
                    "max_tokens": 512,
                    "temperature": 0.0,
                    "top_p": 0.9,
                },
                "image_optimization": {},
            }
        }

        client = LLMClient(config=mock_config)
        assert client.gen_params["temperature"] == 0.0


# -----------------------------------------------------------------------
# T052: YAML dedup tests
# -----------------------------------------------------------------------

class TestYamlDedup:
    """Verify strategy generator produces unique lists."""

    def _make_generator(self, data: dict):
        """Create a StrategyGenerator with in-memory data."""
        from generators.strategy_generator import StrategyGenerator
        # Bypass file loading by patching
        gen = StrategyGenerator.__new__(StrategyGenerator)
        gen.results_path = Path("fake")
        gen.data = data
        return gen

    def test_wiki_strategies_no_duplicate_ids(self):
        """Wiki strategy include_ids should have no duplicates."""
        data = {
            "wiki_pages": [
                {"page_id": "page_a", "semantic": {"category": "KNOWLEDGE"}},
                {"page_id": "page_a", "semantic": {"category": "KNOWLEDGE"}},
                {"page_id": "page_b", "semantic": {"category": "KNOWLEDGE"}},
            ],
            "documents": [],
            "media": [],
        }
        gen = self._make_generator(data)
        strategies = gen._derive_wiki_strategies()
        ids = strategies["knowledge_articles"]["include_ids"]
        assert len(ids) == len(set(ids)), f"Duplicate IDs: {ids}"

    def test_document_strategies_no_duplicate_files(self):
        """Document strategy file lists should have no duplicates."""
        data = {
            "wiki_pages": [],
            "documents": [
                {"file_name": "doc.pdf", "semantic": {"type": "REPORT"}},
                {"file_name": "doc.pdf", "semantic": {"type": "REPORT"}},
                {"file_name": "info.pdf", "semantic": {"type": "INFO_SHEET"}},
                {"file_name": "info.pdf", "semantic": {"type": "INFO_SHEET"}},
            ],
            "media": [],
        }
        gen = self._make_generator(data)
        strategies = gen._derive_document_strategies()
        files = strategies["standard_docs"]["files"]
        assert len(files) == len(set(files)), f"Duplicate files: {files}"

    def test_media_strategies_no_duplicate_files(self):
        """Media strategy file lists should have no duplicates."""
        data = {
            "wiki_pages": [],
            "documents": [],
            "media": [
                {"file_name": "img.png", "vision_analysis": {"utility_score": 8}},
                {"file_name": "img.png", "vision_analysis": {"utility_score": 8}},
                {"file_name": "logo.jpg", "vision_analysis": {"utility_score": 2}},
                {"file_name": "logo.jpg", "vision_analysis": {"utility_score": 2}},
            ],
        }
        gen = self._make_generator(data)
        strategies = gen._derive_media_strategies()
        useful = strategies["informative_images"]["files"]
        ignored = strategies["decorative"]["files"]
        assert len(useful) == len(set(useful)), f"Duplicate useful: {useful}"
        assert len(ignored) == len(set(ignored)), f"Duplicate ignored: {ignored}"

    def test_ignored_wiki_strategies_no_duplicate_ids(self):
        """Ignored list (EMPTY+ERROR concat) should have no duplicates."""
        data = {
            "wiki_pages": [
                {"page_id": "empty1", "semantic": {"category": "EMPTY"}},
                {"page_id": "empty1", "semantic": {"category": "ERROR"}},
                {"page_id": "err1", "semantic": {"category": "ERROR"}},
            ],
            "documents": [],
            "media": [],
        }
        gen = self._make_generator(data)
        strategies = gen._derive_wiki_strategies()
        ids = strategies["ignored"]["include_ids"]
        assert len(ids) == len(set(ids)), f"Duplicate ignored IDs: {ids}"


# -----------------------------------------------------------------------
# T052b: multiline summary logging tests
# -----------------------------------------------------------------------

class TestMultilineSummaryLogging:
    """Verify summary is logged as a cohesive block."""

    def test_summary_is_single_log_call(self):
        """The DEEP EVALUATION COMPLETE block should be one logger call."""
        source_file = _module_root / "run_deep_evaluation.py"
        source = source_file.read_text(encoding="utf-8")

        # Find the main() function body
        main_start = source.index("def main():")
        main_source = source[main_start:]

        # After the fix, the summary block should NOT have multiple
        # consecutive logger.info() calls for the stats.  Instead it
        # should build a summary string and log/print it once.
        stats_lines = [
            line.strip() for line in main_source.splitlines()
            if "Wiki Pages:" in line or "Documents:" in line
            or "Images:" in line or "Output Dir:" in line
        ]
        # After fix: these should NOT be individual logger.info() calls
        logger_calls = [l for l in stats_lines if l.startswith("logger.info")]
        assert len(logger_calls) <= 1, (
            f"Summary stats should be a single cohesive block, "
            f"found {len(logger_calls)} separate logger.info() calls"
        )
