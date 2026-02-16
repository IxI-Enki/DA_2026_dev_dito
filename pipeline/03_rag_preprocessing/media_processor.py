"""Media Processor (T071-T073)

Processes media files for the RAG pipeline:
- PDF text extraction with OCR fallback
- Image OCR via Tesseract
- Batch processing of media directories
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Supported file extensions
PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".gif"}


class MediaProcessor:
    """Processes media files for RAG pipeline.

    Args:
        tesseract_path: Path to the Tesseract OCR binary.
            Defaults to system PATH lookup.
        ocr_language: Tesseract language string (e.g. ``deu+eng``).
    """

    def __init__(
        self,
        tesseract_path: str = "",
        ocr_language: str = "deu+eng",
    ) -> None:
        self.tesseract_path = tesseract_path
        self.ocr_language = ocr_language

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_pdf(self, pdf_path: Path) -> str:
        """Extract text from PDF. Falls back to OCR for scanned pages.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Extracted text (empty string on failure).
        """
        if not pdf_path.exists():
            logger.warning("PDF not found: %s", pdf_path)
            return ""

        text = self._extract_pdf_text(pdf_path)
        if text.strip():
            return self.clean_pdf_text(text)

        # Fallback: OCR the PDF
        logger.info("PDF text empty, attempting OCR: %s", pdf_path.name)
        ocr_text = self._ocr_pdf(pdf_path)
        return self.clean_pdf_text(ocr_text) if ocr_text.strip() else ""

    def process_image(self, image_path: Path) -> str:
        """OCR an image using Tesseract.

        Args:
            image_path: Path to the image file.

        Returns:
            Extracted text (empty string on failure).
        """
        if not image_path.exists():
            logger.warning("Image not found: %s", image_path)
            return ""
        return self._ocr_image(image_path)

    def process_media_directory(self, media_dir: Path) -> list[dict[str, Any]]:
        """Process all supported media files in a directory.

        Args:
            media_dir: Directory to scan.

        Returns:
            List of ``{filename, text, type}`` dicts.
        """
        results: list[dict[str, Any]] = []
        if not media_dir.exists():
            return results

        for f in sorted(media_dir.rglob("*")):
            if not f.is_file():
                continue
            ext = f.suffix.lower()
            text = ""
            ftype = ""
            if ext in PDF_EXTENSIONS:
                text = self.process_pdf(f)
                ftype = "pdf"
            elif ext in IMAGE_EXTENSIONS:
                text = self.process_image(f)
                ftype = "image"
            else:
                continue  # skip unsupported

            results.append({"filename": f.name, "text": text, "type": ftype})
        return results

    # ------------------------------------------------------------------
    # PDF text quality (US7)
    # ------------------------------------------------------------------

    def clean_pdf_text(self, raw_text: str) -> str:
        """Post-process extracted PDF text for quality.

        Chains: fix spaced characters -> merge short lines.
        """
        text = self._fix_spaced_characters(raw_text)
        text = self._merge_short_lines(text)
        return text

    def _fix_spaced_characters(self, text: str) -> str:
        """Fix PDF layout artifacts with spaced characters.

        Heuristic: if >60% of 'words' on a line are single characters,
        join them and split on double-spaces.

        Example: ``"H T B L A  L e o n d i n g"`` -> ``"HTBLA Leonding"``
        """
        if not text:
            return ""

        lines = text.split("\n")
        fixed: list[str] = []

        for line in lines:
            words = line.split()
            if not words:
                fixed.append(line)
                continue

            single_chars = sum(1 for w in words if len(w) == 1)
            ratio = single_chars / len(words)

            if ratio > 0.6:
                # Split on double-space (word boundary in spaced text),
                # then join single chars within each group
                groups = re.split(r"  +", line.strip())
                rebuilt = []
                for group in groups:
                    parts = group.split()
                    if all(len(p) == 1 for p in parts):
                        rebuilt.append("".join(parts))
                    else:
                        rebuilt.append(group)
                fixed.append(" ".join(rebuilt))
            else:
                fixed.append(line)

        return "\n".join(fixed)

    def _merge_short_lines(self, text: str, threshold: int = 40) -> str:
        """Merge consecutive short lines into paragraphs.

        Respects structure: list items, headings, and empty lines are
        never merged with the previous line.
        """
        if not text:
            return ""

        lines = text.split("\n")
        merged: list[str] = []

        for line in lines:
            stripped = line.strip()

            # Empty lines are paragraph separators -- keep them
            if not stripped:
                merged.append("")
                continue

            # Structure-preserving: don't merge list items, headings
            is_structure = (
                stripped.startswith("#")
                or stripped.startswith("- ")
                or stripped.startswith("* ")
                or re.match(r"^\d+[\.\)]\s", stripped)
            )

            if is_structure:
                merged.append(stripped)
                continue

            # If previous line exists, is non-empty, and was short -> merge
            if (
                merged
                and merged[-1]
                and len(merged[-1]) < threshold
                and not merged[-1].startswith("#")
                and not merged[-1].startswith("- ")
                and not merged[-1].startswith("* ")
                and not re.match(r"^\d+[\.\)]\s", merged[-1])
            ):
                merged[-1] = merged[-1] + " " + stripped
            else:
                merged.append(stripped)

        return "\n".join(merged)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_pdf_text(self, pdf_path: Path) -> str:
        """Extract text using pypdf / PyPDF2."""
        try:
            try:
                from pypdf import PdfReader
            except ImportError:
                from PyPDF2 import PdfReader  # type: ignore[no-redef]

            reader = PdfReader(str(pdf_path))
            parts = []
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    parts.append(t)
            return "\n\n".join(parts)
        except Exception as e:
            logger.warning("PDF text extraction failed for %s: %s", pdf_path.name, e)
            return ""

    def _ocr_pdf(self, pdf_path: Path) -> str:
        """OCR a scanned PDF by rendering pages to images, then OCR-ing."""
        try:
            import fitz  # pymupdf

            doc = fitz.open(str(pdf_path))
            parts = []
            for page_num in range(len(doc)):
                pix = doc[page_num].get_pixmap(dpi=300)
                from PIL import Image
                import io

                img = Image.open(io.BytesIO(pix.tobytes("png")))
                parts.append(self._ocr_image_obj(img))
            doc.close()
            return "\n\n".join(p for p in parts if p)
        except ImportError:
            logger.warning("pymupdf or Pillow not installed - OCR fallback unavailable")
            return ""
        except Exception as e:
            logger.warning("OCR fallback failed for %s: %s", pdf_path.name, e)
            return ""

    def _ocr_image(self, image_path: Path) -> str:
        """OCR a single image file."""
        try:
            from PIL import Image

            img = Image.open(image_path)
            return self._ocr_image_obj(img)
        except ImportError:
            logger.warning("Pillow not installed - image OCR unavailable")
            return ""
        except Exception as e:
            logger.warning("Image OCR failed for %s: %s", image_path.name, e)
            return ""

    def _ocr_image_obj(self, img: Any) -> str:
        """Run Tesseract on a PIL Image object."""
        try:
            import pytesseract

            if self.tesseract_path:
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
            text: str = pytesseract.image_to_string(img, lang=self.ocr_language)
            return text.strip()
        except ImportError:
            logger.warning("pytesseract not installed")
            return ""
        except Exception as e:
            logger.warning("Tesseract OCR failed: %s", e)
            return ""
