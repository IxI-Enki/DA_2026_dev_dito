"""
Media Deep Analyzer - Analyse von Bildern

Nutzt Vision-LLMs um Bildinhalte zu verstehen.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
import sys

# Relative imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.llm_client import LLMClient
from config import get_config, EvaluationConfig

logger = logging.getLogger(__name__)

class MediaDeepAnalyzer:
    """Führt Analysen auf Bilddateien durch."""

    def __init__(self, config: Optional[EvaluationConfig] = None):
        self.config = config or get_config()
        self.llm_client = LLMClient(config=self.config)
        
        self.vision_prompt = """
        Beschreibe dieses Bild kurz für eine Suchmaschine.
        
        1. Was ist zu sehen? (z.B. Gebäudeplan, Screenshot von Software, Foto von Personen, Diagramm, Logo)
        2. Enthält es relevanten Text? (Ja/Nein)
        3. Ist es nützlich für eine Wissensdatenbank? (Score 0-10)
        
        Antworte im JSON-Format:
        {
            "description": "...",
            "contains_text": true,
            "utility_score": 8,
            "category": "DIAGRAM"
        }
        """

    def analyze_image(self, file_path: Path) -> Dict[str, Any]:
        """
        Analysiert ein Bild mit Vision AI.
        """
        # Skip tiny files (icons, spacers)
        if file_path.stat().st_size < 5000:
            return {
                "file_name": file_path.name,
                "status": "skipped_too_small"
            }
            
        # Skip SVGs for vision model (not a bitmap)
        if file_path.suffix.lower() == '.svg':
            return {
                "file_name": file_path.name,
                "status": "skipped_svg_format",
                "vision_analysis": {
                    "description": "SVG Vektorgrafik (wird als Code behandelt)",
                    "utility_score": 5,
                    "category": "VECTOR_GRAPHIC"
                }
            }

        llm_result = {}
        try:
            response = self.llm_client.analyze_image(
                image_path=file_path,
                prompt=self.vision_prompt
            )
            
            if response.startswith("Error:"):
                llm_result = {
                    "description": response,
                    "category": "ERROR",
                    "utility_score": 0
                }
            else:
                llm_result = self._parse_llm_json(response)
        except Exception as e:
            logger.error(f"Vision analysis failed for {file_path.name}: {e}")
            llm_result = {"error": str(e), "category": "ERROR"}

        return {
            "file_name": file_path.name,
            "file_size": file_path.stat().st_size,
            "vision_analysis": llm_result
        }

    def _parse_llm_json(self, text: str) -> Dict[str, Any]:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:-3]
        elif text.startswith("```"):
            text = text[3:-3]
        try:
            import json
            return json.loads(text)
        except Exception:
            return {"description": text, "category": "UNKNOWN"}
