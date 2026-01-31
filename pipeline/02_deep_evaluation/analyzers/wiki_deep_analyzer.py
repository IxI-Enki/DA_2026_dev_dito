"""
Wiki Deep Analyzer - Tiefgehende Inhaltsanalyse von Wiki-Seiten

Nutzt LLMs zur semantischen Klassifizierung und analysiert Struktur.
"""

import re
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import sys

# Relative imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.llm_client import LLMClient
from config import get_config, EvaluationConfig

logger = logging.getLogger(__name__)

class WikiDeepAnalyzer:
    """Führt Deep-Dive Analysen auf Wiki-Seiten durch."""

    def __init__(self, config: Optional[EvaluationConfig] = None):
        self.config = config or get_config()
        self.llm_client = LLMClient(config=self.config)
        
        # Classification Prompt Template
        self.classification_prompt = """
        Analysiere den folgenden Inhalt einer Wiki-Seite der HTL Leonding.
        Klassifiziere die Seite in GENAU EINE der folgenden Kategorien:
        
        - KNOWLEDGE: Ein Artikel, der Wissen vermittelt (z.B. Anleitung, Erklärung).
        - PORTAL: Eine Übersichtsseite, die hauptsächlich auf andere Seiten oder Dokumente verlinkt.
        - FORM_COLLECTION: Eine Sammlung von Formularen oder Vorlagen.
        - NEWS: Ankündigungen, Termine oder Status-Updates.
        - TABLE_DATA: Eine Seite, deren Hauptinhalt eine große Datentabelle ist.
        - EMPTY: Kein relevanter Inhalt.

        Gib auch einen "Relevance Score" (0-10) für RAG (Retrieval Augmented Generation) an.
        
        Format der Antwort (JSON):
        {{
            "category": "CATEGORY_NAME",
            "relevance_score": 8,
            "reasoning": "Kurze Begründung..."
        }}
        
        SEITENINHALT (Ausschnitt):
        {text}
        """

    def analyze_page(self, page_id: str, content: str) -> Dict[str, Any]:
        """
        Analysiert eine einzelne Wiki-Seite tiefgehend.
        """
        # 1. Structural Analysis
        structure_stats = self._analyze_structure(content)
        
        # 2. Semantic Classification (LLM)
        # Use first 2000 chars for context
        context_window = self.config.raw_config.get('ANALYSIS', {}).get('text', {}).get('context_window', 2000)
        snippet = content[:context_window]
        
        llm_result = {}
        if len(content.strip()) > 50: # Skip empty pages
            try:
                response = self.llm_client.analyze_text(
                    text=snippet,
                    prompt_template=self.classification_prompt,
                    system_prompt="Du bist ein Daten-Analyst für ein RAG-System. Antworte nur in JSON."
                )
                llm_result = self._parse_llm_json(response)
            except Exception as e:
                logger.error(f"LLM analysis failed for {page_id}: {e}")
                llm_result = {"category": "ERROR", "relevance_score": 0, "reasoning": str(e)}
        else:
             llm_result = {"category": "EMPTY", "relevance_score": 0, "reasoning": "Too short"}

        return {
            "page_id": page_id,
            "structure": structure_stats,
            "semantic": llm_result
        }

    def _analyze_structure(self, content: str) -> Dict[str, Any]:
        """Analysiert strukturelle Merkmale ohne LLM."""
        return {
            "link_density": self._calculate_link_density(content),
            "has_tables": bool(re.search(r'^\|.*\|$', content, re.MULTILINE)),
            "table_rows": len(re.findall(r'^\|.*\|$', content, re.MULTILINE)),
            "has_code": "<code" in content,
            "length": len(content)
        }

    def _calculate_link_density(self, content: str) -> float:
        """Berechnet das Verhältnis von Link-Text zu Gesamttext."""
        if not content:
            return 0.0
        
        # Simple approximation
        links = re.findall(r'\[\[.*?\]\]', content)
        link_chars = sum(len(l) for l in links)
        return link_chars / len(content)

    def _parse_llm_json(self, text: str) -> Dict[str, Any]:
        """Versucht JSON aus der LLM-Antwort zu extrahieren."""
        text = text.strip()
        # Remove markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:-3]
        elif text.startswith("```"):
            text = text[3:-3]
            
        try:
            import json
            return json.loads(text)
        except Exception:
            # Fallback parsing
            return {
                "category": "UNKNOWN", 
                "relevance_score": 5, 
                "reasoning": "JSON parse failed", 
                "raw_response": text[:100]
            }
