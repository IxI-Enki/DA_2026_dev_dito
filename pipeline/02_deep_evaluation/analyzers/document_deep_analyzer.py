"""
Document Deep Analyzer - Analyse von PDF/Office Dokumenten

Extrahiert Text und nutzt LLMs zur Klassifizierung des Dokumententyps.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
import sys

# Relative imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.llm_client import LLMClient
from core.file_handler import FileHandler
from config import get_config, EvaluationConfig

logger = logging.getLogger(__name__)

class DocumentDeepAnalyzer:
    """Führt Deep-Dive Analysen auf Dokumenten durch."""

    def __init__(self, config: Optional[EvaluationConfig] = None):
        self.config = config or get_config()
        self.llm_client = LLMClient(config=self.config)
        self.file_handler = FileHandler(config=self.config)
        
        self.classification_prompt = """
        Analysiere den Beginn des folgenden Dokuments.
        Klassifiziere es in GENAU EINE der folgenden Kategorien:
        
        - THESIS: Eine wissenschaftliche Arbeit (Diplomarbeit, Dissertation).
        - FORM: Ein Formular zum Ausfüllen (Antrag, Bestätigung).
        - CURRICULUM: Ein Lehrplan oder Kompetenzraster.
        - PRESENTATION: Eine Präsentation (Folien).
        - INFO_SHEET: Ein Informationsblatt oder Handout.
        - REPORT: Ein Bericht oder Protokoll.
        
        Gib an, ob das Dokument "fillable" (ausfüllbar) wirkt (Unterstriche, Formularfelder).
        
        Format (JSON):
        {{
            "type": "FORM",
            "is_fillable": true,
            "topic": "Kurze Zusammenfassung des Themas",
            "rag_value": 3
        }}
        
        DOKUMENT-BEGINN:
        {text}
        """

    def analyze_document(self, file_path: Path) -> Dict[str, Any]:
        """
        Analysiert ein Dokument (PDF, DOCX, etc.).
        """
        # 1. Text Extraction
        content = self.file_handler.get_file_content(file_path)
        
        if content.startswith("[Error") or not content.strip():
            return {
                "file_name": file_path.name,
                "status": "extraction_failed",
                "error": content
            }
            
        # 2. Semantic Analysis (LLM)
        snippet = content[:1500] # First 1500 chars usually contain header/title
        
        llm_result = {}
        try:
            response = self.llm_client.analyze_text(
                text=snippet,
                prompt_template=self.classification_prompt,
                system_prompt="Du bist ein Dokumenten-Archivar. Antworte in JSON."
            )
            llm_result = self._parse_llm_json(response)
        except Exception as e:
            logger.error(f"LLM analysis failed for {file_path.name}: {e}")
            llm_result = {"type": "ERROR", "error": str(e)}

        return {
            "file_name": file_path.name,
            "file_type": file_path.suffix,
            "char_count": len(content),
            "semantic": llm_result
        }

    def _parse_llm_json(self, text: str) -> Dict[str, Any]:
        # Reuse same parsing logic
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:-3]
        elif text.startswith("```"):
            text = text[3:-3]
        try:
            import json
            return json.loads(text)
        except Exception:
            return {"type": "UNKNOWN", "raw": text[:50]}
