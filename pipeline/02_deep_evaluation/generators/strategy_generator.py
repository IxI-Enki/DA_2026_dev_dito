"""
Strategy Generator - Erstellt Preprocessing-Konfigurationen

Analysiert die Ergebnisse der Deep Evaluation und erstellt
validierte YAML-Konfigurations-Snippets für die RAG-Pipeline.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

import yaml

logger = logging.getLogger(__name__)


class StrategyGenerator:
    """Generiert Preprocessing-Strategien aus Analyse-Ergebnissen."""

    def __init__(self, results_path: Path):
        self.results_path = results_path
        with open(results_path, encoding="utf-8") as f:
            self.data = json.load(f)

    def generate_strategies(self, output_dir: Path):
        """Hauptfunktion zur Generierung der Strategien."""

        strategies = {
            "PIPELINE_STRATEGIES": {
                "wiki_pages": self._derive_wiki_strategies(),
                "documents": self._derive_document_strategies(),
                "media": self._derive_media_strategies(),
            }
        }

        # Output as YAML
        yaml_path = output_dir / "preprocessing_strategies.yaml"
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(strategies, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

        logger.info(f"Strategies saved to {yaml_path}")
        return yaml_path

    def _derive_wiki_strategies(self) -> Dict[str, Any]:
        """Leitet Strategien für Wiki-Seiten ab."""
        pages = self.data.get("wiki_pages", [])

        # Structural override: if page is table-heavy but LLM did not say TABLE_DATA, override
        TABLE_ROW_DENSITY_THRESHOLD = 0.5
        MIN_TABLE_ROWS = 3
        AVG_CHARS_PER_LINE = 80

        categories = {}
        for p in pages:
            cat = p.get("semantic", {}).get("category", "UNKNOWN")
            structure = p.get("structure", {}) or {}
            table_rows = int(structure.get("table_rows", 0))
            length = int(structure.get("length", 0))
            if cat != "TABLE_DATA" and table_rows >= MIN_TABLE_ROWS and length > 0:
                total_lines_approx = max(1, length // AVG_CHARS_PER_LINE)
                if table_rows / total_lines_approx >= TABLE_ROW_DENSITY_THRESHOLD:
                    cat = "TABLE_DATA"
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(p["page_id"])

        return {
            "knowledge_articles": {
                "description": "Standard Knowledge Base Artikel",
                "chunking": "recursive_header",
                "chunk_size": 1024,
                "include_ids": sorted(set(categories.get("KNOWLEDGE", []))),
            },
            "portals": {
                "description": "Verteilerseiten mit vielen Links",
                "chunking": "parent_context",
                "action": "index_as_context_only",
                "include_ids": sorted(set(categories.get("PORTAL", []))),
            },
            "forms": {
                "description": "Formularsammlungen",
                "chunking": "table_row",
                "action": "extract_links_and_metadata",
                "include_ids": sorted(set(categories.get("FORM_COLLECTION", []))),
            },
            "news": {
                "description": "Zeitkritische News",
                "chunking": "naive",
                "freshness_weight": 0.5,
                "include_ids": sorted(set(categories.get("NEWS", []))),
            },
            "table_data": {
                "description": "Seiten mit tabellarischen Daten als Hauptinhalt",
                "chunking": "table_row",
                "chunk_size": 512,
                "include_ids": sorted(set(categories.get("TABLE_DATA", []))),
            },
            "ignored": {
                "description": "Irrelevanter Content",
                "action": "skip",
                "include_ids": sorted(
                    set(categories.get("EMPTY", []) + categories.get("ERROR", []))
                ),
            },
        }

    def _derive_document_strategies(self) -> Dict[str, Any]:
        """Leitet Strategien für Dokumente ab."""
        docs = self.data.get("documents", [])

        # Group by type
        types = {}
        for d in docs:
            t = d.get("semantic", {}).get("type", "UNKNOWN")
            if t not in types:
                types[t] = []
            types[t].append(d["file_name"])

        return {
            "theses": {
                "description": "Wissenschaftliche Arbeiten",
                "parser": "pdf_scientific",
                "chunk_size": 2048,
                "overlap": 200,
                "files": sorted(set(types.get("THESIS", []))),
            },
            "forms": {
                "description": "Ausfuellbare Formulare",
                "parser": "pdf_form_fields",
                "action": "index_metadata_only",
                "files": sorted(set(types.get("FORM", []))),
            },
            "standard_docs": {
                "description": "Allgemeine Dokumente (Berichte, Infos)",
                "parser": "pdf_standard",
                "chunk_size": 1024,
                "files": sorted(set(types.get("REPORT", []) + types.get("INFO_SHEET", []))),
            },
            "presentations": {
                "description": "Folien-Saetze",
                "parser": "pptx_slide",
                "action": "summarize_slides",
                "files": sorted(set(types.get("PRESENTATION", []))),
            },
        }

    def _derive_media_strategies(self) -> Dict[str, Any]:
        """Leitet Strategien für Bilder ab."""
        media = self.data.get("media", [])

        # Filter useful images
        useful = []
        ignored = []

        for m in media:
            score = m.get("vision_analysis", {}).get("utility_score", 0)
            if score >= 6:
                useful.append(m["file_name"])
            else:
                ignored.append(m["file_name"])

        return {
            "informative_images": {
                "description": "Bilder mit hohem Informationsgehalt",
                "action": "caption_and_index",
                "vision_model": "qwen2.5-vl",
                "files": sorted(set(useful)),
            },
            "decorative": {
                "description": "Dekorative Elemente oder Low-Res",
                "action": "skip",
                "files": sorted(set(ignored)),
            },
        }
