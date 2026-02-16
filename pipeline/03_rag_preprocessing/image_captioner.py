"""Image Captioner -- Vision-LLM Bild-Captioning (US6)

Generates text descriptions for images using Qwen2.5-VL via LMStudio's
OpenAI-compatible API. All config values come from env.yaml (Article II-B).
"""

from __future__ import annotations

import base64
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
    """

    def __init__(
        self,
        api_base: str,
        model: str,
        timeout: int = 60,
    ) -> None:
        self.api_base = api_base
        self.model = model
        self.timeout = timeout
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
            logger.warning("Image captioning failed for %s: %s", image_path.name, e)
            return ""

    def is_available(self) -> bool:
        """Check if LMStudio endpoint is reachable."""
        try:
            client = self._get_client()
            client.models.list()
            return True
        except Exception:
            return False

    def _encode_image(self, image_path: Path) -> str:
        """Encode image as base64 data URI for OpenAI vision API."""
        data = image_path.read_bytes()
        b64 = base64.b64encode(data).decode("utf-8")
        mime = mimetypes.guess_type(str(image_path))[0] or "image/png"
        return f"data:{mime};base64,{b64}"
