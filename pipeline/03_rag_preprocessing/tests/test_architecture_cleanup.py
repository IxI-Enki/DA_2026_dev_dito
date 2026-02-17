"""Tests for US9 -- Architecture Cleanup (T031).

Verifies:
- Single entry point (run_preprocessing.py) works
- main.py does NOT exist
- All media formats (PDF, DOCX, XLSX, PPTX, PNG, JPG) are discovered
- DOCUMENT_EXTENSIONS, IMAGE_EXTENSIONS, TEXT_EXTENSIONS constants exist
- process_docx, process_xlsx, process_pptx methods exist
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure module root is importable
_here = Path(__file__).resolve().parent.parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))


class TestSingleEntryPoint:
    """Verify single entry point architecture."""

    def test_main_py_does_not_exist(self):
        """main.py must be deleted after consolidation."""
        main_path = _here / "main.py"
        assert not main_path.exists(), (
            f"main.py still exists at {main_path} -- "
            "it should be deleted after migrating all logic to run_preprocessing.py"
        )

    def test_run_preprocessing_exists(self):
        """run_preprocessing.py must be the single entry point."""
        rp = _here / "run_preprocessing.py"
        assert rp.exists(), "run_preprocessing.py must exist as the single entry point"

    def test_run_preprocessing_has_main(self):
        """run_preprocessing.py must have a main() function."""
        from run_preprocessing import main
        assert callable(main)

    def test_run_preprocessing_has_run(self):
        """run_preprocessing.py must have a run() function."""
        from run_preprocessing import run
        assert callable(run)

    def test_run_preprocessing_help(self):
        """--help should not crash."""
        from run_preprocessing import main
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["run_preprocessing.py", "--help"]):
                main()
        assert exc_info.value.code == 0


class TestMediaFormatDiscovery:
    """Verify all media formats are supported by MediaProcessor."""

    def test_document_extensions_constant(self):
        """DOCUMENT_EXTENSIONS must include PDF, DOCX, XLSX, PPTX."""
        from media_processor import DOCUMENT_EXTENSIONS
        assert ".pdf" in DOCUMENT_EXTENSIONS
        assert ".docx" in DOCUMENT_EXTENSIONS
        assert ".xlsx" in DOCUMENT_EXTENSIONS
        assert ".pptx" in DOCUMENT_EXTENSIONS

    def test_image_extensions_constant(self):
        """IMAGE_EXTENSIONS must include PNG, JPG, JPEG at minimum."""
        from media_processor import IMAGE_EXTENSIONS
        assert ".png" in IMAGE_EXTENSIONS
        assert ".jpg" in IMAGE_EXTENSIONS
        assert ".jpeg" in IMAGE_EXTENSIONS

    def test_process_docx_method_exists(self):
        """MediaProcessor must have process_docx method."""
        from media_processor import MediaProcessor
        mp = MediaProcessor()
        assert hasattr(mp, "process_docx")
        assert callable(mp.process_docx)

    def test_process_xlsx_method_exists(self):
        """MediaProcessor must have process_xlsx method."""
        from media_processor import MediaProcessor
        mp = MediaProcessor()
        assert hasattr(mp, "process_xlsx")
        assert callable(mp.process_xlsx)

    def test_process_pptx_method_exists(self):
        """MediaProcessor must have process_pptx method."""
        from media_processor import MediaProcessor
        mp = MediaProcessor()
        assert hasattr(mp, "process_pptx")
        assert callable(mp.process_pptx)

    def test_process_media_directory_handles_all_formats(self):
        """process_media_directory must handle all document + image formats."""
        from media_processor import MediaProcessor, DOCUMENT_EXTENSIONS, IMAGE_EXTENSIONS
        mp = MediaProcessor()

        # Verify the method exists and returns a list
        result = mp.process_media_directory(Path("/nonexistent"))
        assert isinstance(result, list)

        # Check that extension sets cover all required formats
        all_supported = DOCUMENT_EXTENSIONS | IMAGE_EXTENSIONS
        assert ".pdf" in all_supported
        assert ".docx" in all_supported
        assert ".xlsx" in all_supported
        assert ".pptx" in all_supported
        assert ".png" in all_supported
        assert ".jpg" in all_supported

    def test_process_docx_nonexistent_file(self):
        """process_docx on missing file returns empty string."""
        from media_processor import MediaProcessor
        mp = MediaProcessor()
        result = mp.process_docx(Path("/nonexistent/test.docx"))
        assert result == ""

    def test_process_xlsx_nonexistent_file(self):
        """process_xlsx on missing file returns empty string."""
        from media_processor import MediaProcessor
        mp = MediaProcessor()
        result = mp.process_xlsx(Path("/nonexistent/test.xlsx"))
        assert result == ""

    def test_process_pptx_nonexistent_file(self):
        """process_pptx on missing file returns empty string."""
        from media_processor import MediaProcessor
        mp = MediaProcessor()
        result = mp.process_pptx(Path("/nonexistent/test.pptx"))
        assert result == ""


class TestManifestAndSummary:
    """Verify manifest generation and summary output are in run_preprocessing."""

    def test_run_module_has_print_summary(self):
        """run_preprocessing must have a summary output function."""
        import run_preprocessing as rp
        assert hasattr(rp, "_print_summary") or hasattr(rp, "run")
