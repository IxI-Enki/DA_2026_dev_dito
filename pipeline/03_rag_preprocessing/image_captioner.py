"""Image Captioner -- Vision-LLM Bild-Captioning (US6)

Generates text descriptions for images using Qwen2.5-VL via LMStudio's
OpenAI-compatible API. All config values come from env.yaml (Article II-B).
"""

from __future__ import annotations

import base64
import io
import logging
import mimetypes
from pathlib import Path

logger = logging.getLogger(__name__)

# Supported image extensions for captioning
CAPTIONABLE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}

# German prompt for image description
_CAPTION_PROMPT = (
    "Beschreibe dieses Bild ausführlich auf Deutsch. "
    "Nenne alle sichtbaren Texte, Beschriftungen, Personen, Objekte und "
    "räumliche Zusammenhänge. Antworte nur mit der Beschreibung, "
    "ohne Einleitung oder Kommentar."
)


class ImageCaptioner:
    """Generates text descriptions for images using a Vision-LLM.

    Uses Qwen2.5-VL via LMStudio's OpenAI-compatible API.

    Args:
        api_base: LMStudio API endpoint (from env.yaml VISION_LLM.api_base).
        model: Model name (from env.yaml VISION_LLM.model).
        timeout: Request timeout in seconds.
        max_image_size: Max longest edge (px) before downscaling; 0 disables resize.
    """

    def __init__(
        self,
        api_base: str,
        model: str,
        timeout: int = 60,
        max_image_size: int = 1024,
    ) -> None:
        self.api_base = api_base
        self.model = model
        self.timeout = timeout
        self.max_image_size = max(0, max_image_size)
        self._client = None  # Lazy init

    def _get_client(self):
        """Lazy-initialize OpenAI client."""
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(
                base_url=self.api_base,
                api_key="not-needed",
                timeout=self.timeout,
            )
        return self._client

    def caption(self, image_path: Path) -> str:
        """Generate a German description for an image.

        Args:
            image_path: Path to the image file.

        Returns:
            Description text (empty string on failure).
        """
        if not image_path.exists():
            logger.warning("Image not found: %s", image_path)
            return ""

        try:
            data_uri = self._encode_image(image_path)
            client = self._get_client()

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": _CAPTION_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {"url": data_uri},
                            },
                        ],
                    }
                ],
                max_tokens=1024,
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            dims = self._get_image_dimensions(image_path)
            logger.warning(
                "Image captioning failed for %s (dims=%s): %s",
                image_path.name,
                dims,
                e,
            )
            return ""

    def is_available(self) -> bool:
        """Check if LMStudio endpoint is reachable."""
        try:
            client = self._get_client()
            client.models.list()
            return True
        except Exception:
            return False

    def _get_image_dimensions(self, image_path: Path) -> str:
        """Return image dimensions as 'WxH' or 'unknown'."""
        try:
            from PIL import Image
            with Image.open(image_path) as img:
                w, h = img.size
                return f"{w}x{h}"
        except Exception:
            return "unknown"

    def _encode_image(self, image_path: Path) -> str:
        """Encode image as base64 data URI for OpenAI vision API.

        If max_image_size > 0 and the image is larger, it is downscaled
        (longest edge) to reduce token usage and avoid LMStudio context overflow.
        If PIL cannot open the file (e.g. minimal/invalid test image), falls back
        to raw bytes without resize.
        """
        mime = mimetypes.guess_type(str(image_path))[0] or "image/png"

        def _raw_encode() -> str:
            data = image_path.read_bytes()
            b64 = base64.b64encode(data).decode("utf-8")
            return f"data:{mime};base64,{b64}"

        try:
            from PIL import Image
        except ImportError:
            return _raw_encode()

        try:
            with Image.open(image_path) as img:
                img.load()
                w, h = img.size
                if self.max_image_size > 0 and max(w, h) > self.max_image_size:
                    img = img.copy()
                    img.thumbnail((self.max_image_size, self.max_image_size), Image.Resampling.LANCZOS)
                    nw, nh = img.size
                    logger.debug(
                        "Downscaled image %s from %s to %dx%d",
                        image_path.name,
                        f"{w}x{h}",
                        nw,
                        nh,
                    )
                buf = io.BytesIO()
                save_fmt = img.format if img.format in ("PNG", "JPEG", "GIF", "WEBP") else "PNG"
                if save_fmt == "JPEG" and img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(buf, format=save_fmt)
                data = buf.getvalue()
            b64 = base64.b64encode(data).decode("utf-8")
            return f"data:{mime};base64,{b64}"
        except Exception:
            return _raw_encode()
