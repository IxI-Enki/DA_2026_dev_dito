"""
LLM Client - Kommunikation mit LM Studio

Handled Text- und Bild-Anfragen an lokale LLMs.
Alle Einstellungen werden aus config/env.yaml geladen - KEINE hardcoded Werte!
"""

import base64
import io
import logging
from pathlib import Path
from typing import Any, Dict, List

import requests

try:
    from PIL import Image

    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    Image = None

# Resolve config from package root (02_deep_evaluation)
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import get_config

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Client für LM Studio API (OpenAI-kompatibel) mit Image-Optimierung.

    Alle Einstellungen werden aus config/env.yaml geladen.
    """

    def __init__(self, config: Any | None = None):
        """
        Initialisiert den LLMClient.

        Args:
            config: EvaluationConfig Instanz (optional, wird bei Bedarf geladen)
        """
        # Lazy import um circular dependencies zu vermeiden
        if config is None:
            config = get_config()

        self.config = config
        self.llm_cfg = self.config.raw_config.get("LLM", {})

        # KEINE hardcoded Defaults - muss aus env.yaml kommen
        base_url = self.llm_cfg.get("base_url")
        if not base_url:
            raise ValueError("LLM base_url missing in env.yaml (LLM.base_url)")
        self.base_url = base_url

        self.api_key = self.llm_cfg.get("api_key", "lm-studio")

        self.classification_model = self.llm_cfg.get("classification_model")
        if not self.classification_model:
            raise ValueError(
                "LLM classification_model missing in env.yaml (LLM.classification_model)"
            )

        self.vision_model = self.llm_cfg.get("vision_model", self.classification_model)

        # Generation parameters - KEINE Defaults, muss aus config kommen
        gen_cfg = self.llm_cfg.get("generation", {})
        if not gen_cfg:
            raise ValueError("LLM generation parameters missing in env.yaml (LLM.generation)")

        self.gen_params = {
            "max_tokens": gen_cfg.get("max_tokens"),
            "temperature": gen_cfg.get("temperature"),
            "top_p": gen_cfg.get("top_p"),
        }

        # Validate gen_params
        if self.gen_params["max_tokens"] is None:
            raise ValueError("LLM generation.max_tokens missing in env.yaml")
        if self.gen_params["temperature"] is None:
            raise ValueError("LLM generation.temperature missing in env.yaml")
        if self.gen_params["top_p"] is None:
            raise ValueError("LLM generation.top_p missing in env.yaml")

        # Timeout - muss aus config kommen
        self.timeout = self.llm_cfg.get("timeout")
        if not self.timeout:
            raise ValueError("LLM timeout missing in env.yaml (LLM.timeout)")

        # Image optimization settings - aus config oder sensible defaults
        image_cfg = self.llm_cfg.get("image_optimization", {})
        self.image_max_size = image_cfg.get("max_size", 1024)
        self.image_quality = image_cfg.get("jpeg_quality", 85)

        # System prompt - aus config
        self.default_system_prompt = self.llm_cfg.get(
            "system_prompt", "Du bist ein hilfreicher Assistent."
        )

    def analyze_text(
        self, text: str, prompt_template: str, system_prompt: str | None = None
    ) -> str:
        """
        Analysiert Text mit dem LLM.

        Args:
            text: Der zu analysierende Text
            prompt_template: Prompt-Template mit {text} Platzhalter
            system_prompt: System-Prompt (None = aus config)

        Returns:
            LLM-Antwort oder Fehlermeldung
        """
        if system_prompt is None:
            system_prompt = self.default_system_prompt

        prompt = prompt_template.format(text=text)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        return self._chat_completion(messages, self.classification_model)

    def _optimize_image(self, image_path: Path, max_size: int | None = None) -> bytes:
        """
        Lädt ein Bild, skaliert es falls nötig und gibt es als JPEG-Bytes zurück.
        Reduziert die Payload-Größe drastisch.

        Args:
            image_path: Pfad zum Bild
            max_size: Maximale Größe (None = aus config)

        Returns:
            Optimierte Bilddaten als JPEG-Bytes
        """
        if not HAS_PIL or Image is None:
            raise ImportError("PIL/Pillow not installed - required for image optimization")

        if max_size is None:
            max_size = self.image_max_size

        if max_size is None:
            max_size = 1024  # Fallback wenn nicht in config

        img = Image.open(image_path)
        try:
            # Convert to RGB if necessary (e.g. RGBA/PNG)
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Resize if too large
            current_max = max(img.size)
            if current_max > max_size:
                ratio = max_size / float(current_max)
                width, height = img.size
                new_size = (int(width * ratio), int(height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # Save to bytes
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=self.image_quality, optimize=True)
            return buffer.getvalue()
        finally:
            img.close()

    def analyze_image(self, image_path: Path, prompt: str) -> str:
        """
        Analysiert ein Bild mit Vision AI.

        Args:
            image_path: Pfad zum Bild
            prompt: Prompt für die Bildanalyse

        Returns:
            LLM-Antwort oder Fehlermeldung
        """
        if not image_path.exists():
            return "Error: Image not found"

        # SVGs separately
        if image_path.suffix.lower() == ".svg":
            return "Error: Vision models do not support SVG bitmaps."

        try:
            # Optimize image (resize & compress)
            optimized_data = self._optimize_image(image_path)
            base64_image = base64.b64encode(optimized_data).decode("utf-8")

            # Use 'image/jpeg' because we converted it
            mime_type = "image/jpeg"
        except Exception as e:
            logger.error(f"Error preparing image {image_path}: {e}")
            return f"Error preparing image: {e}"

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{base64_image}"},
                    },
                ],
            }
        ]

        return self._chat_completion(messages, self.vision_model)

    def _chat_completion(self, messages: List[Dict[str, Any]], model: str) -> str:
        """
        Führt den API Request durch.

        Args:
            messages: Liste von Message-Dicts
            model: Modell-Name

        Returns:
            LLM-Antwort oder Fehlermeldung
        """
        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": self.gen_params["max_tokens"],
            "temperature": self.gen_params["temperature"],
            "top_p": self.gen_params["top_p"],
            "stream": False,
        }

        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)

            if response.status_code != 200:
                error_detail = response.text
                logger.error(f"LLM Error {response.status_code}: {error_detail}")
                return f"Error: LLM Request failed - {response.status_code} {error_detail[:200]}"

            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"].get("content", "")
                return content.strip() if content else "Error: Empty content in LLM response"

            return "Error: Empty response from LLM"

        except requests.exceptions.Timeout:
            logger.error(f"LLM Request timeout after {self.timeout}s")
            return f"Error: LLM Request timeout after {self.timeout}s"
        except requests.exceptions.RequestException as e:
            logger.error(f"LLM Connection failed: {e}")
            return f"Error: LLM Connection failed - {e}"
        except Exception as e:
            logger.error(f"Unexpected error in LLM request: {e}")
            return f"Error: {e}"


# Test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        client = LLMClient()
        print("Testing connection...")
        response = client.analyze_text("Hallo, bist du bereit?", "Antworte kurz: {text}")
        print(f"Response: {response}")
    except ValueError as e:
        print(f"Configuration error: {e}")
    except Exception as e:
        print(f"Error: {e}")
