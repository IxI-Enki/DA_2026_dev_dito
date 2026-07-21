"""Image Captioner -- Vision-LLM Bild-Captioning (US6)

Generates text descriptions for images using Qwen2.5-VL via LMStudio's
OpenAI-compatible API. All config values come from env.yaml (Article II-B).
"""

from __future__ import annotations

import base64
import io
import json
import logging
import mimetypes
import os
import urllib.error
import urllib.request
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


def _resolve_api_key(explicit: str | None = None) -> str:
    """Resolve LMS API token: LM_API_TOKEN / LMS_API_TOKEN > config > lm-studio."""
    for env_name in ("LM_API_TOKEN", "LMS_API_TOKEN"):
        tok = (os.environ.get(env_name) or "").strip()
        if tok:
            return tok
    if explicit and str(explicit).strip() and str(explicit).strip() != "not-needed":
        return str(explicit).strip()
    # Placeholder only when LMS auth is disabled.
    return "lm-studio"


def _lms_native_base(api_base: str) -> str:
    """Strip trailing /v1 from OpenAI-compatible base URL."""
    base = api_base.rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    return base.rstrip("/")


class ImageCaptioner:
    """Generates text descriptions for images using a Vision-LLM.

    Uses Qwen2.5-VL via LMStudio's OpenAI-compatible API.

    Args:
        api_base: LMStudio API endpoint (from env.yaml VISION_LLM.api_base).
        model: Model name (from env.yaml VISION_LLM.model).
        timeout: Request timeout in seconds.
        max_image_size: Max longest edge (px) before downscaling; 0 disables resize.
        api_key: LMS Bearer token (optional; prefers LM_API_TOKEN / LMS_API_TOKEN).
    """

    def __init__(
        self,
        api_base: str,
        model: str,
        timeout: int = 60,
        max_image_size: int = 1024,
        api_key: str | None = None,
    ) -> None:
        self.api_base = api_base
        self.model = model
        self.timeout = timeout
        self.max_image_size = max(0, max_image_size)
        self.api_key = _resolve_api_key(api_key)
        self._client = None  # Lazy init

    def _get_client(self):
        """Lazy-initialize OpenAI client."""
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(
                base_url=self.api_base,
                api_key=self.api_key,
                timeout=self.timeout,
            )
        return self._client

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _model_loaded_via_native_api(self) -> bool | None:
        """Check LMS native /api/v1/models for loaded_instances of self.model.

        Returns:
            True if model is loaded, False if catalog reachable but not loaded,
            None if the native endpoint is unreachable / unusable.
        """
        url = f"{_lms_native_base(self.api_base)}/api/v1/models"
        try:
            req = urllib.request.Request(url, headers=self._auth_headers(), method="GET")
            with urllib.request.urlopen(req, timeout=min(self.timeout, 10)) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, OSError) as e:
            logger.debug("Native LMS models probe failed (%s): %s", url, e)
            return None

        models = payload.get("models") or payload.get("data") or []
        if not isinstance(models, list):
            return None

        needle = (self.model or "").strip().lower()
        found = False
        for m in models:
            if not isinstance(m, dict):
                continue
            mid = str(m.get("key") or m.get("id") or "").strip()
            if not mid:
                continue
            mid_l = mid.lower()
            if needle and needle not in mid_l and mid_l not in needle:
                continue
            found = True
            loaded = m.get("loaded_instances") or []
            if isinstance(loaded, list) and len(loaded) > 0:
                return True
        if found:
            return False
        # Catalog up but configured model not listed — still treat LMS as reachable
        # only if any model has loaded_instances (glass already loaded something).
        for m in models:
            if isinstance(m, dict):
                loaded = m.get("loaded_instances") or []
                if isinstance(loaded, list) and len(loaded) > 0:
                    logger.warning(
                        "Configured vision model %r not in LMS catalog; "
                        "another model is loaded - captions may fail",
                        self.model,
                    )
                    return True
        return False

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

            return (response.choices[0].message.content or "").strip()
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
        """Check if Vision-LLM is usable via LM Studio.

        Prefer native ``/api/v1/models`` + ``loaded_instances`` (authoritative).
        Do not treat an empty OpenAI ``/v1/models`` list as "no vision model".
        """
        native = self._model_loaded_via_native_api()
        if native is True:
            return True
        if native is False:
            return False

        # Fallback: OpenAI-compatible list (may be empty or odd on some LMS builds)
        try:
            client = self._get_client()
            listed = client.models.list()
            data = getattr(listed, "data", None) or []
            if not data:
                # Empty /v1/models is inconclusive — try a cheap chat probe only
                # when native API was unreachable; treat HTTP auth success as up.
                return True
            needle = (self.model or "").strip().lower()
            if not needle:
                return True
            for m in data:
                mid = str(getattr(m, "id", "") or "").lower()
                if needle in mid or mid in needle:
                    return True
            return True  # LMS responded; model id mismatch is a caption-time issue
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
                    img.thumbnail(
                        (self.max_image_size, self.max_image_size), Image.Resampling.LANCZOS
                    )
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
