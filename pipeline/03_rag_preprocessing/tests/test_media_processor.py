"""T065: Tests for MediaProcessor (PDF/OCR)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture()
def media_dir(tmp_path: Path) -> Path:
    """Create a temp media directory with sample files."""
    d = tmp_path / "media"
    d.mkdir()
    (d / "sample.txt").write_text("Hello world from text file", encoding="utf-8")
    # Create a fake PDF (just bytes - actual extraction is mocked)
    (d / "sample.pdf").write_bytes(b"%PDF-1.4 fake pdf content")
    # Create a fake image
    (d / "sample.png").write_bytes(b"\x89PNG fake image content")
    return d


class TestMediaProcessorPDF:
    """Tests for process_pdf method."""

    def test_process_pdf_returns_string(self, tmp_path: Path) -> None:
        from media_processor import MediaProcessor

        mp = MediaProcessor()
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF")
        with patch("media_processor.MediaProcessor._extract_pdf_text", return_value="Extracted text"):
            result = mp.process_pdf(pdf)
        assert isinstance(result, str)

    def test_process_pdf_fallback_to_ocr(self, tmp_path: Path) -> None:
        from media_processor import MediaProcessor

        mp = MediaProcessor()
        pdf = tmp_path / "scanned.pdf"
        pdf.write_bytes(b"%PDF")
        # Simulate empty text extraction -> should attempt OCR fallback
        with patch("media_processor.MediaProcessor._extract_pdf_text", return_value=""), \
             patch("media_processor.MediaProcessor._ocr_pdf", return_value="OCR result"):
            result = mp.process_pdf(pdf)
        assert result == "OCR result"

    def test_process_pdf_missing_file(self, tmp_path: Path) -> None:
        from media_processor import MediaProcessor

        mp = MediaProcessor()
        result = mp.process_pdf(tmp_path / "nonexistent.pdf")
        assert result == ""


class TestMediaProcessorImage:
    """Tests for process_image method."""

    def test_process_image_returns_string(self, tmp_path: Path) -> None:
        from media_processor import MediaProcessor

        mp = MediaProcessor()
        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG")
        with patch("media_processor.MediaProcessor._ocr_image", return_value="OCR text"):
            result = mp.process_image(img)
        assert isinstance(result, str)

    def test_process_image_missing_file(self, tmp_path: Path) -> None:
        from media_processor import MediaProcessor

        mp = MediaProcessor()
        result = mp.process_image(tmp_path / "nonexistent.png")
        assert result == ""


class TestMediaProcessorDirectory:
    """Tests for process_media_directory method."""

    def test_directory_returns_list(self, media_dir: Path) -> None:
        from media_processor import MediaProcessor

        mp = MediaProcessor()
        with patch.object(mp, "process_pdf", return_value="pdf text"), \
             patch.object(mp, "process_image", return_value="image text"):
            results = mp.process_media_directory(media_dir)
        assert isinstance(results, list)

    def test_directory_entries_have_required_keys(self, media_dir: Path) -> None:
        from media_processor import MediaProcessor

        mp = MediaProcessor()
        with patch.object(mp, "process_pdf", return_value="pdf text"), \
             patch.object(mp, "process_image", return_value="image text"):
            results = mp.process_media_directory(media_dir)
        for entry in results:
            assert "filename" in entry
            assert "text" in entry
            assert "type" in entry
