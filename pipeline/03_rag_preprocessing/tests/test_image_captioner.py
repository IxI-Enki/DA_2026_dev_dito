"""T026: Tests for ImageCaptioner -- Vision-LLM Bild-Captioning (US6)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


class TestImageCaptionerCaption:
    """Test caption() method with mocked OpenAI client."""

    def test_caption_returns_description_string(self, tmp_path: Path) -> None:
        """caption() returns a non-empty description string."""
        from image_captioner import ImageCaptioner

        captioner = ImageCaptioner(
            api_base="http://192.168.8.3:1234/v1",
            model="qwen2.5-vl",
        )

        # Create a minimal valid PNG (1x1 pixel)
        img = tmp_path / "test.png"
        img.write_bytes(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
            b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
            b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Ein Schulgebäude der HTL Leonding."

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch.object(captioner, "_get_client", return_value=mock_client):
            result = captioner.caption(img)

        assert result == "Ein Schulgebäude der HTL Leonding."
        assert isinstance(result, str)

    def test_caption_graceful_failure_returns_empty(self, tmp_path: Path) -> None:
        """caption() returns empty string on API error, does not raise."""
        from image_captioner import ImageCaptioner

        captioner = ImageCaptioner(
            api_base="http://192.168.8.3:1234/v1",
            model="qwen2.5-vl",
        )

        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG fake")

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = ConnectionError("LMStudio down")

        with patch.object(captioner, "_get_client", return_value=mock_client):
            result = captioner.caption(img)

        assert result == ""

    def test_caption_nonexistent_file_returns_empty(self, tmp_path: Path) -> None:
        """caption() returns empty string for missing file."""
        from image_captioner import ImageCaptioner

        captioner = ImageCaptioner(
            api_base="http://192.168.8.3:1234/v1",
            model="qwen2.5-vl",
        )
        result = captioner.caption(tmp_path / "missing.png")
        assert result == ""


class TestImageCaptionerAvailability:
    """Test is_available() pre-check."""

    def test_is_available_returns_false_when_unreachable(self) -> None:
        """is_available() returns False when endpoint is down."""
        from image_captioner import ImageCaptioner

        captioner = ImageCaptioner(
            api_base="http://127.0.0.1:99999/v1",
            model="qwen2.5-vl",
            timeout=1,
        )
        assert captioner.is_available() is False

    def test_is_available_returns_true_when_reachable(self) -> None:
        """is_available() returns True when native LMS API reports model loaded."""
        from image_captioner import ImageCaptioner

        captioner = ImageCaptioner(
            api_base="http://127.0.0.1:1234/v1",
            model="qwen/qwen2.5-vl-7b",
        )

        with patch.object(captioner, "_model_loaded_via_native_api", return_value=True):
            assert captioner.is_available() is True

    def test_is_available_ignores_empty_openai_models_list(self) -> None:
        """Empty OpenAI /v1/models must not disable Vision-LLM when native API is up."""
        from image_captioner import ImageCaptioner

        captioner = ImageCaptioner(
            api_base="http://127.0.0.1:1234/v1",
            model="qwen/qwen2.5-vl-7b",
        )
        mock_client = MagicMock()
        mock_listed = MagicMock()
        mock_listed.data = []
        mock_client.models.list.return_value = mock_listed

        with (
            patch.object(captioner, "_model_loaded_via_native_api", return_value=None),
            patch.object(captioner, "_get_client", return_value=mock_client),
        ):
            assert captioner.is_available() is True

    def test_is_available_false_when_native_says_not_loaded(self) -> None:
        """Native catalog reachable but model not loaded => unavailable."""
        from image_captioner import ImageCaptioner

        captioner = ImageCaptioner(
            api_base="http://127.0.0.1:1234/v1",
            model="qwen/qwen2.5-vl-7b",
        )
        with patch.object(captioner, "_model_loaded_via_native_api", return_value=False):
            assert captioner.is_available() is False


class TestImageCaptionerBase64:
    """Test base64 image encoding."""

    def test_encodes_image_to_base64(self, tmp_path: Path) -> None:
        """_encode_image returns a valid base64 data URI."""
        from image_captioner import ImageCaptioner

        captioner = ImageCaptioner(
            api_base="http://192.168.8.3:1234/v1",
            model="qwen2.5-vl",
        )

        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG test data")

        result = captioner._encode_image(img)
        assert result.startswith("data:image/png;base64,")
        assert len(result) > 30


class TestCaptionableExtensions:
    """Test CAPTIONABLE_EXTENSIONS constant."""

    def test_png_jpg_supported(self) -> None:
        from image_captioner import CAPTIONABLE_EXTENSIONS

        assert ".png" in CAPTIONABLE_EXTENSIONS
        assert ".jpg" in CAPTIONABLE_EXTENSIONS
        assert ".jpeg" in CAPTIONABLE_EXTENSIONS

    def test_pdf_not_captionable(self) -> None:
        from image_captioner import CAPTIONABLE_EXTENSIONS

        assert ".pdf" not in CAPTIONABLE_EXTENSIONS
