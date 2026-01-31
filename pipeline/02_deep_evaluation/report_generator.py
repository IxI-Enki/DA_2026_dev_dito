"""
Report Generator - Generiert Evaluierungsberichte

Ausgabeformate:
- Markdown Report
- JSON Summary
- HTML (optional)
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from config import EvaluationConfig, get_config


class ReportGenerator:
    """Generiert Evaluierungsberichte in verschiedenen Formaten."""

    def __init__(
        self,
        config: Optional[EvaluationConfig] = None,
        results: Optional[Dict[str, Any]] = None
    ):
        """
        Initialisiert den ReportGenerator.

        Args:
            config: EvaluationConfig Instanz
            results: Dictionary mit Evaluierungsergebnissen
        """
        self.config = config or get_config()
        self.results = results or {}

        # Report settings
        self.author = self.config.reports.author
        self.institution = self.config.reports.institution

    def generate(self, output_dir: Path) -> Path:
        """
        Generiert alle konfigurierten Reports.

        Args:
            output_dir: Ausgabeverzeichnis

        Returns:
            Pfad zum Haupt-Report
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate Markdown report
        if self.config.reports.generate_markdown:
            md_path = self._generate_markdown(output_dir)

        # Generate JSON summary
        if self.config.reports.generate_json:
            self._generate_json_summary(output_dir)

        return md_path if self.config.reports.generate_markdown else output_dir

    def _generate_markdown(self, output_dir: Path) -> Path:
        """Generiert den Markdown-Report."""
        run_name = self.results.get('run_name', 'evaluation')
        # Timestamp im Format YYYYMMDD_HHMMSS (konsistent)
        timestamp = self.results.get('timestamp')
        if not timestamp:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        elif len(timestamp) == 8:  # Nur Datum, füge Zeit hinzu
            timestamp = f"{timestamp}_{datetime.now().strftime('%H%M%S')}"
        
        # Parse timestamp für schöne Anzeige
        try:
            if '_' in timestamp:
                date_part, time_part = timestamp.split('_', 1)
                dt = datetime.strptime(f"{date_part}_{time_part}", '%Y%m%d_%H%M%S')
                date_display = dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                date_display = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        except:
            date_display = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        md_path = output_dir / f"{run_name}_report.md"

        lines = [
            f"# Fetched Data Evaluation Report",
            "",
            f"**Run:** {run_name}",
            f"**Timestamp:** {timestamp}",
            f"**Datum:** {date_display}",
            f"**Autor:** {self.author}",
            f"**Institution:** {self.institution}",
            "",
            "---",
            "",
        ]

        # Executive Summary
        lines.extend(self._section_summary())

        # Content Classification
        lines.extend(self._section_content_classification())

        # Format & Quality
        lines.extend(self._section_format_quality())

        # RAG Readiness
        lines.extend(self._section_rag_readiness())

        # Temporal Analysis
        lines.extend(self._section_temporal())

        # Query Generation (if available)
        if 'query_generation' in self.results and not self.results['query_generation'].get('skipped'):
            lines.extend(self._section_queries())

        # Diploma Thesis Analysis
        lines.extend(self._section_diploma_thesis())

        # Recommendations
        lines.extend(self._section_recommendations())

        # Write file
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        return md_path

    def _section_summary(self) -> list:
        """Generiert die Zusammenfassung."""
        summary = self.results.get('summary', {})

        lines = [
            "## Executive Summary",
            "",
            "| Metrik | Wert |",
            "|--------|------|",
            f"| Gesamtseiten | {summary.get('total_pages', 'N/A')} |",
            f"| Media-Dateien | {summary.get('total_media_files', 'N/A')} |",
            f"| Teacher-Restricted | {summary.get('teacher_restricted_pages', 'N/A')} |",
            f"| Archiviert | {summary.get('archived_pages', 'N/A')} |",
            f"| Avg. RAG Readiness | {summary.get('avg_rag_readiness', 'N/A')} |",
            f"| Avg. Freshness | {summary.get('avg_freshness', 'N/A')} |",
            f"| OCR-Kandidaten | {summary.get('files_needing_ocr', 'N/A')} |",
            f"| Diplomarbeiten | {summary.get('diploma_thesis_pdfs', 'N/A')} |",
            "",
            "---",
            "",
        ]
        return lines

    def _section_content_classification(self) -> list:
        """Generiert die Content-Klassifizierung."""
        cc = self.results.get('content_classification', {})
        summary = cc.get('summary', {})
        by_namespace = cc.get('by_namespace', {})
        by_content_type = cc.get('by_content_type', {})

        lines = [
            "## Content Classification",
            "",
            "### Übersicht",
            "",
            f"- **Total Pages:** {summary.get('total_pages', 'N/A')}",
            f"- **Teacher-Restricted:** {summary.get('teacher_restricted', 'N/A')}",
            f"- **Public:** {summary.get('public', 'N/A')}",
            f"- **Archived:** {summary.get('archived', 'N/A')}",
            "",
            "### Nach Namespace",
            "",
            "| Namespace | Seiten |",
            "|-----------|--------|",
        ]

        for ns, count in sorted(by_namespace.items(), key=lambda x: -x[1]):
            lines.append(f"| {ns} | {count} |")

        lines.extend([
            "",
            "### Nach Content-Typ",
            "",
            "| Typ | Seiten |",
            "|-----|--------|",
        ])

        for ct, count in sorted(by_content_type.items(), key=lambda x: -x[1]):
            lines.append(f"| {ct} | {count} |")

        lines.extend(["", "---", ""])
        return lines

    def _section_format_quality(self) -> list:
        """Generiert die Format-Qualitäts-Sektion."""
        fq = self.results.get('format_quality', {})
        summary = fq.get('summary', {})
        by_type = fq.get('by_type', {})
        quality_dist = fq.get('quality_distribution', {})

        lines = [
            "## Format & Quality Analysis",
            "",
            "### Übersicht",
            "",
            f"- **Total Files:** {summary.get('total_files', 'N/A')}",
            f"- **Total Size:** {summary.get('total_size_mb', 'N/A')} MB",
            f"- **Avg. Quality Score:** {summary.get('avg_quality_score', 'N/A')}",
            f"- **OCR-Kandidaten:** {summary.get('files_needing_ocr', 'N/A')}",
            "",
            "### Dateitypen",
            "",
            "| Typ | Anzahl |",
            "|-----|--------|",
        ]

        for ft, count in sorted(by_type.items(), key=lambda x: -x[1]):
            lines.append(f"| {ft} | {count} |")

        lines.extend([
            "",
            "### Qualitätsverteilung",
            "",
            "| Level | Anzahl |",
            "|-------|--------|",
        ])

        for level in ['high', 'medium', 'low']:
            count = quality_dist.get(level, 0)
            lines.append(f"| {level} | {count} |")

        lines.extend(["", "---", ""])
        return lines

    def _section_rag_readiness(self) -> list:
        """Generiert die RAG-Readiness-Sektion."""
        rr = self.results.get('rag_readiness', {})
        summary = rr.get('summary', {})
        common_issues = rr.get('common_issues', {})
        recommendations = rr.get('preprocessing_recommendations', [])

        lines = [
            "## RAG Readiness Analysis",
            "",
            "### Übersicht",
            "",
            f"- **Avg. Readiness Score:** {summary.get('avg_readiness_score', 'N/A')}",
            "",
            "### Readiness-Verteilung",
            "",
            "| Level | Seiten |",
            "|-------|--------|",
        ]

        dist = summary.get('readiness_distribution', {})
        for level in ['high', 'medium', 'low']:
            count = dist.get(level, 0)
            lines.append(f"| {level} | {count} |")

        if common_issues:
            lines.extend([
                "",
                "### Häufige Probleme",
                "",
            ])
            for issue, count in list(common_issues.items())[:5]:
                lines.append(f"- **{issue}:** {count} Seiten")

        if recommendations:
            lines.extend([
                "",
                "### Preprocessing-Empfehlungen",
                "",
            ])
            for rec in recommendations:
                lines.append(f"- {rec}")

        lines.extend(["", "---", ""])
        return lines

    def _section_temporal(self) -> list:
        """Generiert die zeitliche Analyse-Sektion."""
        ta = self.results.get('temporal_analysis', {})
        summary = ta.get('summary', {})
        freshness_dist = ta.get('freshness_distribution', {})

        lines = [
            "## Temporal Analysis",
            "",
            "### Übersicht",
            "",
            f"- **Avg. Freshness Score:** {summary.get('avg_freshness_score', 'N/A')}",
            f"- **Archiviert:** {summary.get('archived_count', 'N/A')}",
            f"- **Zeitkritisch:** {summary.get('time_sensitive_count', 'N/A')}",
            f"- **Veraltete Referenzen:** {summary.get('pages_with_outdated_refs', 'N/A')}",
            "",
            "### Freshness-Verteilung",
            "",
            "| Kategorie | Seiten |",
            "|-----------|--------|",
        ]

        for cat in ['current', 'recent', 'outdated', 'archived', 'unknown']:
            count = freshness_dist.get(cat, 0)
            if count > 0:
                lines.append(f"| {cat} | {count} |")

        lines.extend(["", "---", ""])
        return lines

    def _section_queries(self) -> list:
        """Generiert die Query-Generierung-Sektion."""
        qg = self.results.get('query_generation', {})
        summary = qg.get('summary', {})
        by_type = qg.get('by_type', {})
        queries = qg.get('queries', [])

        lines = [
            "## Query Generation",
            "",
            "### Übersicht",
            "",
            f"- **Total Queries:** {summary.get('total_queries', 'N/A')}",
            f"- **Pages Sampled:** {summary.get('pages_sampled', 'N/A')}",
            f"- **Failed:** {summary.get('failed_generations', 'N/A')}",
            "",
            "### Nach Typ",
            "",
            "| Typ | Anzahl |",
            "|-----|--------|",
        ]

        for qt, count in by_type.items():
            lines.append(f"| {qt} | {count} |")

        if queries:
            lines.extend([
                "",
                "### Beispiel-Queries",
                "",
            ])
            for q in queries[:5]:
                lines.append(f"- **[{q.get('query_type', 'unknown')}]** {q.get('question', 'N/A')}")
                lines.append(f"  - *Source:* {q.get('source_page', 'N/A')}")
                lines.append("")

        lines.extend(["---", ""])
        return lines

    def _section_diploma_thesis(self) -> list:
        """Generiert die Diplomarbeits-Sektion."""
        fq = self.results.get('format_quality', {})
        thesis_files = fq.get('diploma_thesis', [])

        if not thesis_files:
            return []

        lines = [
            "## Diplomarbeiten (Separate Analyse)",
            "",
            "Die folgenden 7 Diplomarbeits-PDFs werden separat behandelt:",
            "",
            "| Datei | Größe (MB) | Quality Score |",
            "|-------|------------|---------------|",
        ]

        for t in thesis_files:
            lines.append(f"| {t.get('file_name', 'N/A')} | {t.get('size_mb', 'N/A')} | {t.get('quality_score', 'N/A')} |")

        lines.extend([
            "",
            "**Empfehlung:** Diese Dateien sollten in ein separates RAGFlow-Dataset mit",
            "`paper` Chunk-Methode und größerer Chunk-Size (1024 Token) indexiert werden.",
            "",
            "---",
            "",
        ])
        return lines

    def _section_recommendations(self) -> list:
        """Generiert die Empfehlungs-Sektion."""
        recommendations = self.results.get('recommendations', [])

        lines = [
            "## Empfehlungen für RAG-Preprocessing",
            "",
        ]

        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                lines.append(f"{i}. {rec}")
        else:
            lines.append("*Keine spezifischen Empfehlungen.*")

        lines.extend([
            "",
            "### Allgemeine Preprocessing-Schritte",
            "",
            "1. **Wiki-Syntax bereinigen:** DokuWiki-Markup in Plain-Text konvertieren",
            "2. **Metadaten anreichern:** Namespace, Freshness-Score, Access-Level hinzufügen",
            "3. **Teacher-Namespace separieren:** Für getrennte Zugriffssteuerung",
            "4. **Archiv markieren:** Niedrigere Gewichtung für archivierte Inhalte",
            "5. **OCR für gescannte PDFs:** Textextraktion vor Indexierung",
            "6. **Diplomarbeiten separat:** Eigenes Dataset mit optimiertem Chunking",
            "",
        ])

        return lines

    def generate_deep_analysis_report(self, output_dir: Path, deep_results: Dict[str, Any]) -> Path:
        """
        Generiert einen umfassenden Deep Analysis Report gemäß Microsoft RAG Guide.
        
        Args:
            output_dir: Ausgabeverzeichnis
            deep_results: Dictionary mit deep_analysis_results.json Inhalt
            
        Returns:
            Pfad zum generierten Report
        """
        timestamp = deep_results.get('timestamp', datetime.now().strftime('%Y%m%d_%H%M%S'))
        if len(timestamp) == 8:  # Nur Datum
            timestamp = f"{timestamp}_{datetime.now().strftime('%H%M%S')}"
        
        # Parse timestamp für Anzeige
        try:
            if '_' in timestamp:
                date_part, time_part = timestamp.split('_', 1)
                dt = datetime.strptime(f"{date_part}_{time_part}", '%Y%m%d_%H%M%S')
                date_display = dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                date_display = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        except:
            date_display = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        report_path = output_dir / f"ANALYSIS_REPORT_{timestamp}.md"
        
        lines = []
        
        # Header
        lines.extend([
            f"# Comprehensive DokuWiki Content Analysis Report",
            "",
            f"**Timestamp:** {timestamp}",
            f"**Date:** {date_display}",
            f"**Scope:** Deep Content Evaluation for RAG Pipeline Optimization",
            f"**Author:** {self.author}",
            f"**Institution:** {self.institution}",
            "",
            f"**Dataset:** {len(deep_results.get('wiki_pages', []))} Wiki Pages, "
            f"{len(deep_results.get('documents', []))} Documents, "
            f"{len(deep_results.get('media', []))} Images",
            "",
            "---",
            "",
        ])
        
        # 1. Solution Domain Definition
        lines.extend(self._section_solution_domain())
        
        # 2. Executive Summary
        lines.extend(self._section_deep_executive_summary(deep_results))
        
        # 3. Security Constraints Analysis
        lines.extend(self._section_security_constraints(deep_results))
        
        # 4. Wiki Page Cluster Analysis
        lines.extend(self._section_wiki_cluster_analysis(deep_results))
        
        # 5. Document Deep Dive
        lines.extend(self._section_document_deep_dive(deep_results))
        
        # 6. Visual Content Strategy
        lines.extend(self._section_visual_content_strategy(deep_results))
        
        # 7. Preprocessing Requirements (Microsoft Guide)
        lines.extend(self._section_preprocessing_requirements(deep_results))
        
        # 8. Preprocessing Strategy Recommendation
        lines.extend(self._section_preprocessing_strategy_recommendation(deep_results))
        
        # Footer
        lines.extend([
            "",
            "---",
            f"*Report generated automatically by Fetched Data Evaluation Suite (Deep Eval Mode)*",
            f"*Generated: {date_display}*"
        ])
        
        # Write file
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        return report_path
    
    def _section_solution_domain(self) -> list:
        """Solution Domain Definition gemäß Microsoft Guide."""
        return [
            "## 1. Solution Domain Definition",
            "",
            "### Business Requirements",
            "",
            "Die Wissensdatenbank dient einem schulinternen Model-Context-Protocol-Server, mit dem sowohl Schüler als auch Lehrer Informationen aus dem Schulwiki einfach, praktisch und schnell abfragen können.",
            "",
            "### Use Cases",
            "",
            "- **Schüler:** Schnelle Abfrage von Informationen zu Abläufen, Formularen, Terminen, Lehrplaninhalten",
            "- **Lehrer:** Zugriff auf alle Informationen inklusive teacher-restricted Inhalte",
            "- **MCP Server:** Bereitstellung strukturierter, durchsuchbarer Daten für RAG-basierte Abfragen",
            "",
            "### Technical Context",
            "",
            "- **RAG Pipeline:** RAGFlow (embedden, parsen, reranken)",
            "- **Authentication:** ScaleKit OAuth (später)",
            "- **Data Source:** DokuWiki (gefetchte Pages, Media-Files)",
            "",
            "---",
            "",
        ]
    
    def _section_deep_executive_summary(self, results: Dict[str, Any]) -> list:
        """Executive Summary für Deep Analysis."""
        wiki_pages = results.get('wiki_pages', [])
        documents = results.get('documents', [])
        media = results.get('media', [])
        
        return [
            "## 2. Executive Summary",
            "",
            "This report presents the findings of the deep content analysis utilizing **LLM-based semantic classification** and **Vision AI** to inspect the actual content of every file.",
            "",
            "**Key Findings:**",
            "",
            f"*   **Content is highly heterogeneous:** The dataset is a complex mix of structured knowledge, temporal news, and link portals.",
            f"*   **Hidden Gems in PDFs:** A significant portion of the actual 'knowledge' is locked in PDF attachments (Curricula, Legal Infos).",
            f"*   **Vision Viability:** The Informative Images (floor plans, network routes) contain critical information not found in text.",
            f"*   **Security Requirement:** Strict access control for the `teacher:` namespace is mandatory (see Security Constraints section).",
            "",
            "---",
            "",
        ]
    
    def _section_security_constraints(self, results: Dict[str, Any]) -> list:
        """Security Constraints Analysis - explizite Dokumentation."""
        config = self.config
        teacher_ns = config.teacher_namespaces
        public_ns = config.public_namespaces
        
        # Count teacher-restricted vs public content
        wiki_pages = results.get('wiki_pages', [])
        teacher_pages = sum(1 for p in wiki_pages if any(p.get('page_id', '').startswith(f"{ns}:") for ns in teacher_ns))
        public_pages = len(wiki_pages) - teacher_pages
        
        return [
            "## 3. Security Constraints Analysis",
            "",
            "### Access Control Requirements",
            "",
            "**Critical:** Die Zugriffssteuerung ist essentiell für die Compliance und den Datenschutz.",
            "",
            "#### Teacher Namespace (Restricted)",
            "",
            f"- **Namespaces:** {', '.join(teacher_ns)}",
            f"- **Zugriff:** Nur Lehrer",
            f"- **Inhalt:** {teacher_pages} Pages, alle Media-Files in diesen Namespaces",
            f"- **Implementierung:** ScaleKit OAuth (später)",
            "",
            "#### Public Namespaces",
            "",
            f"- **Namespaces:** {', '.join(public_ns) if public_ns else 'Alle anderen'}",
            f"- **Zugriff:** Schüler + Lehrer",
            f"- **Inhalt:** {public_pages} Pages",
            "",
            "### Metadata-Anreicherung",
            "",
            "**Empfehlung:** Alle Chunks müssen mit `access_level` Metadata angereichert werden:",
            "",
            '- `access_level: "teacher_only"` für teacher namespace Inhalte',
            '- `access_level: "public"` für alle anderen Inhalte',
            "",
            "Dies ermöglicht dem MCP Server eine effiziente Filterung basierend auf der Benutzerrolle.",
            "",
            "### Implementation Notes",
            "",
            "- **OAuth:** ScaleKit OAuth wird später implementiert",
            "- **Filtering:** MCP Server muss `access_level` Metadata bei jeder Query prüfen",
            "- **Performance:** Metadata-Filterung sollte auf Index-Ebene erfolgen (nicht post-retrieval)",
            "",
            "---",
            "",
        ]
    
    def _section_wiki_cluster_analysis(self, results: Dict[str, Any]) -> list:
        """Wiki Page Cluster Analysis."""
        wiki_pages = results.get('wiki_pages', [])
        wiki_cats = {}
        for p in wiki_pages:
            cat = p.get('semantic', {}).get('category', 'UNKNOWN')
            wiki_cats[cat] = wiki_cats.get(cat, 0) + 1
        
        lines = [
            "## 4. Wiki Page Cluster Analysis",
            "",
            f"The semantic analysis identified {len(wiki_cats)} distinct page types requiring different preprocessing strategies.",
            "",
            "| Category | Count | Description / Strategy |",
            "| :--- | :--- | :--- |",
        ]
        
        cat_descriptions = {
            "KNOWLEDGE": "Educational content, tutorials, legal info. -> **Recursive Header Chunking**.",
            "PORTAL": "Navigation hubs. Low text density. -> **Parent Context Indexing**.",
            "FORM_COLLECTION": "Collections of download links. -> **Metadata Extraction**.",
            "NEWS": "Ankündigungen, Termine. Time-sensitive. -> **Freshness Weighting**.",
            "EMPTY": "Test pages or placeholders. -> **Skip**.",
            "TABLE_DATA": "Mainly data tables. -> **Markdown Table Parsing**."
        }
        
        for cat, count in sorted(wiki_cats.items(), key=lambda x: -x[1]):
            desc = cat_descriptions.get(cat, "Generic content cluster.")
            lines.append(f"| **{cat}** | {count} | {desc} |")
        
        lines.extend([
            "",
            "**Insight:** Portals should not be indexed as primary content but used to enrich linked documents.",
            "",
            "---",
            "",
        ])
        
        return lines
    
    def _section_document_deep_dive(self, results: Dict[str, Any]) -> list:
        """Document Deep Dive Analysis."""
        documents = results.get('documents', [])
        doc_types = {}
        for d in documents:
            t = d.get('semantic', {}).get('type', 'UNKNOWN')
            doc_types[t] = doc_types.get(t, 0) + 1
        
        lines = [
            "## 5. Document Deep Dive (PDF/Office)",
            "",
            "Documents are not uniform and require specialized handlers.",
            "",
            "| Type | Count | Recommended Handler |",
            "| :--- | :--- | :--- |",
        ]
        
        handler_map = {
            "THESIS": "Scientific Paper Parser (Abstract/TOC aware)",
            "FORM": "Metadata-Only / Form Field Indexer",
            "CURRICULUM": "Table-aware PDF Parser",
            "REPORT": "Standard PDF Parser",
            "INFO_SHEET": "Standard PDF Parser"
        }
        
        for t, count in sorted(doc_types.items(), key=lambda x: -x[1]):
            handler = handler_map.get(t, "Form/Metadata Indexer")
            lines.append(f"| **{t}** | {count} | {handler} |")
        
        lines.extend(["", "---", ""])
        return lines
    
    def _section_visual_content_strategy(self, results: Dict[str, Any]) -> list:
        """Visual Content Strategy."""
        media = results.get('media', [])
        img_stats = {'informative': 0, 'decorative': 0, 'skipped': 0}
        
        for m in media:
            if m.get('status') in ['skipped_too_small', 'skipped_svg_format']:
                img_stats['skipped'] += 1
            elif m.get('vision_analysis', {}).get('utility_score', 0) >= 6:
                img_stats['informative'] += 1
            else:
                img_stats['decorative'] += 1
        
        return [
            "## 6. Visual Content Strategy",
            "",
            "Vision AI (Qwen2.5-VL) categorized images into distinct value buckets:",
            "",
            f"*   **Informative Images:** {img_stats['informative']} (High RAG value, e.g. floor plans, diagrams. **AI Captioning required**)",
            f"*   **Decorative/Low Value:** {img_stats['decorative']} (Logos, icons. **Skip indexing**)",
            f"*   **Skipped (Format/Size):** {img_stats['skipped']}",
            "",
            "---",
            "",
        ]
    
    def _section_preprocessing_requirements(self, results: Dict[str, Any]) -> list:
        """Preprocessing Requirements gemäß Microsoft Guide."""
        return [
            "## 7. Preprocessing Requirements (Microsoft RAG Guide)",
            "",
            "### Items to Ignore",
            "",
            "Die folgenden strukturellen Elemente können beim Chunking ignoriert werden:",
            "",
            "- **Table of Contents:** Automatisch generierte TOCs (nicht semantisch relevant)",
            "- **Headers/Footers:** Wiederholende Header/Footer in PDFs",
            "- **Copyrights/Disclaimers:** Standard-Legal-Text (nicht query-relevant)",
            "- **Footnotes/Endnotes:** Können optional ignoriert werden (abhängig vom Kontext)",
            "- **Watermarks:** Visuelle Wasserzeichen (nicht textuell relevant)",
            "- **Annotations/Comments:** Interne Kommentare (nicht für Endbenutzer)",
            "",
            "### Document Preprocessing",
            "",
            "**Struktur-Analyse erforderlich:**",
            "",
            "- **Multicolumn Content:** Muss anders geparst werden als Single-Column",
            "- **Header Structure:** Semantische Bedeutung aus Überschriften extrahieren",
            "- **Paragraph Length:** Variabilität analysieren für optimale Chunk-Größe",
            "- **Language Detection:** Deutsch als Hauptsprache, Unicode-Support",
            "- **Number Formatting:** Konsistenz prüfen (Kommas, Dezimalstellen)",
            "",
            "### Image Preprocessing",
            "",
            "- **Resolution Check:** Mindestauflösung für OCR/Text-Extraktion",
            "- **Text in Images:** OCR für Bilder mit eingebettetem Text",
            "- **Abstract Images:** Icons/Logos identifizieren und optional überspringen",
            "- **Image-Text Relationship:** Captions und umgebender Text für Kontext",
            "",
            "### Table & Chart Processing",
            "",
            "- **Complex Tables:** Nested Tables erkennen und speziell behandeln",
            "- **Table Captions:** Captions für Kontext beibehalten",
            "- **Long Tables:** Header-Repeat in Chunks für lange Tabellen",
            "- **Charts with Numbers:** Zahlen aus Charts extrahieren (falls möglich)",
            "",
            "---",
            "",
        ]
    
    def _section_preprocessing_strategy_recommendation(self, results: Dict[str, Any]) -> list:
        """Preprocessing Strategy Recommendation."""
        return [
            "## 8. Preprocessing Strategy Recommendation",
            "",
            "Based on the analysis, a **routing-based pipeline** is recommended.",
            "",
            "### Pipeline Architecture Recommendation",
            "",
            "1.  **Ingest:** Fetch raw data.",
            "2.  **Classify:** Use the generated `preprocessing_strategies.yaml` to route files.",
            "3.  **Route:**",
            "    *   *Route A (Text):* Knowledge Articles -> Text Cleaner -> Chunker -> Vector Store.",
            "    *   *Route B (Docs):* Theses -> SciParser -> Vector Store (Thesis Collection).",
            "    *   *Route C (Vision):* Info Images -> Captioning -> Vector Store.",
            "4.  **Enrich:** Inject `namespace` and `access_level` into ALL metadata.",
            "",
            "### Metadata Enrichment (Critical)",
            "",
            "Jeder Chunk muss folgende Metadata enthalten:",
            "",
            "- `namespace`: Namespace der Quelle (z.B. 'teacher', 'org', 'departm')",
            "- `access_level`: 'teacher_only' oder 'public'",
            "- `last_modified`: Letzte Änderung (für Freshness-Weighting)",
            "- `content_type`: Klassifizierung (z.B. 'KNOWLEDGE', 'PORTAL', 'FORM')",
            "- `source_page`: Original Page-ID",
            "",
            "### Next Steps",
            "",
            "1. Load `preprocessing_strategies.yaml` into the RAGFlow Preprocessor.",
            "2. Implement the routing logic defined above.",
            "3. Configure ScaleKit OAuth für Access Control.",
            "4. Test Query-Generation mit RAGAS.",
            "",
        ]

    def _generate_json_summary(self, output_dir: Path):
        """Generiert die JSON-Zusammenfassung."""
        run_name = self.results.get('run_name', 'evaluation')

        summary = {
            'run_name': run_name,
            'timestamp': self.results.get('timestamp'),
            'summary': self.results.get('summary', {}),
            'recommendations': self.results.get('recommendations', [])
        }

        json_path = output_dir / f"{run_name}_summary.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)


# =============================================================================
# Test
# =============================================================================

if __name__ == "__main__":
    # Test with sample data
    sample_results = {
        'run_name': 'test_eval',
        'timestamp': '20260103_120000',
        'summary': {
            'total_pages': 207,
            'total_media_files': 330,
            'teacher_restricted_pages': 79,
            'archived_pages': 9,
            'avg_rag_readiness': 0.65,
            'avg_freshness': 0.72,
            'files_needing_ocr': 5,
            'diploma_thesis_pdfs': 7
        },
        'recommendations': [
            "Wiki-Syntax-Bereinigung für 50 Seiten mit hohem Noise",
            "Absatz-basiertes Chunking für Seiten ohne Überschriften"
        ]
    }

    gen = ReportGenerator(results=sample_results)
    report_path = gen.generate(Path("./test_output"))
    print(f"Report generated: {report_path}")
