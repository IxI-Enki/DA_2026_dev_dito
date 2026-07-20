# Comprehensive DokuWiki Content Analysis Report

**Timestamp:** 20260216_174929
**Date:** 2026-02-16 17:49:29
**Scope:** Deep Content Evaluation for RAG Pipeline Optimization
**Author:** Jan Ritt
**Institution:** HTL Leonding

**Dataset:** 204 Wiki Pages, 241 Documents, 93 Images

---

## 1. Solution Domain Definition

### Business Requirements

Die Wissensdatenbank dient einem schulinternen Model-Context-Protocol-Server, mit dem sowohl Schüler als auch Lehrer Informationen aus dem Schulwiki einfach, praktisch und schnell abfragen können.

### Use Cases

- **Schüler:** Schnelle Abfrage von Informationen zu Abläufen, Formularen, Terminen, Lehrplaninhalten
- **Lehrer:** Zugriff auf alle Informationen inklusive teacher-restricted Inhalte
- **MCP Server:** Bereitstellung strukturierter, durchsuchbarer Daten für RAG-basierte Abfragen

### Technical Context

- **RAG Pipeline:** RAGFlow (embedden, parsen, reranken)
- **Authentication:** ScaleKit OAuth (später)
- **Data Source:** DokuWiki (gefetchte Pages, Media-Files)

---

## 2. Executive Summary

This report presents the findings of the deep content analysis utilizing **LLM-based semantic classification** and **Vision AI** to inspect the actual content of every file.

**Key Findings:**

*   **Content is highly heterogeneous:** The dataset is a complex mix of structured knowledge, temporal news, and link portals.
*   **Hidden Gems in PDFs:** A significant portion of the actual 'knowledge' is locked in PDF attachments (Curricula, Legal Infos).
*   **Vision Viability:** The Informative Images (floor plans, network routes) contain critical information not found in text.
*   **Security Requirement:** Strict access control for the `teacher:` namespace is mandatory (see Security Constraints section).

---

## 3. Security Constraints Analysis

### Access Control Requirements

**Critical:** Die Zugriffssteuerung ist essentiell für die Compliance und den Datenschutz.

#### Teacher Namespace (Restricted)

- **Namespaces:** teacher
- **Zugriff:** Nur Lehrer
- **Inhalt:** 0 Pages, alle Media-Files in diesen Namespaces
- **Implementierung:** ScaleKit OAuth (später)

#### Public Namespaces

- **Namespaces:** org, departm, exams, it, competitions, archive, department, werkstaette, class, wiki, playground, software, tutorial, wocheninfo, special, root
- **Zugriff:** Schüler + Lehrer
- **Inhalt:** 204 Pages

### Metadata-Anreicherung

**Empfehlung:** Alle Chunks müssen mit `access_level` Metadata angereichert werden:

- `access_level: "teacher_only"` für teacher namespace Inhalte
- `access_level: "public"` für alle anderen Inhalte

Dies ermöglicht dem MCP Server eine effiziente Filterung basierend auf der Benutzerrolle.

### Implementation Notes

- **OAuth:** ScaleKit OAuth wird später implementiert
- **Filtering:** MCP Server muss `access_level` Metadata bei jeder Query prüfen
- **Performance:** Metadata-Filterung sollte auf Index-Ebene erfolgen (nicht post-retrieval)

---

## 4. Wiki Page Cluster Analysis

The semantic analysis identified 6 distinct page types requiring different preprocessing strategies.

| Category | Count | Description / Strategy |
| :--- | :--- | :--- |
| **KNOWLEDGE** | 86 | Educational content, tutorials, legal info. -> **Recursive Header Chunking**. |
| **PORTAL** | 41 | Navigation hubs. Low text density. -> **Parent Context Indexing**. |
| **FORM_COLLECTION** | 34 | Collections of download links. -> **Metadata Extraction**. |
| **NEWS** | 31 | Ankündigungen, Termine. Time-sensitive. -> **Freshness Weighting**. |
| **EMPTY** | 8 | Test pages or placeholders. -> **Skip**. |
| **TABLE_DATA** | 4 | Mainly data tables. -> **Markdown Table Parsing**. |

**Insight:** Portals should not be indexed as primary content but used to enrich linked documents.

---

## 5. Document Deep Dive (PDF/Office)

Documents are not uniform and require specialized handlers.

| Type | Count | Recommended Handler |
| :--- | :--- | :--- |
| **FORM** | 130 | Metadata-Only / Form Field Indexer |
| **CURRICULUM** | 52 | Table-aware PDF Parser |
| **REPORT** | 27 | Standard PDF Parser |
| **THESIS** | 12 | Scientific Paper Parser (Abstract/TOC aware) |
| **UNKNOWN** | 9 | Form/Metadata Indexer |
| **PRESENTATION** | 5 | Form/Metadata Indexer |
| **INFO_SHEET** | 5 | Standard PDF Parser |
| **None** | 1 | Form/Metadata Indexer |

---

## 6. Visual Content Strategy

Vision AI (Qwen2.5-VL) categorized images into distinct value buckets:

*   **Informative Images:** 85 (High RAG value, e.g. floor plans, diagrams. **AI Captioning required**)
*   **Decorative/Low Value:** 3 (Logos, icons. **Skip indexing**)
*   **Skipped (Format/Size):** 5

---

## 7. Preprocessing Requirements (Microsoft RAG Guide)

### Items to Ignore

Die folgenden strukturellen Elemente können beim Chunking ignoriert werden:

- **Table of Contents:** Automatisch generierte TOCs (nicht semantisch relevant)
- **Headers/Footers:** Wiederholende Header/Footer in PDFs
- **Copyrights/Disclaimers:** Standard-Legal-Text (nicht query-relevant)
- **Footnotes/Endnotes:** Können optional ignoriert werden (abhängig vom Kontext)
- **Watermarks:** Visuelle Wasserzeichen (nicht textuell relevant)
- **Annotations/Comments:** Interne Kommentare (nicht für Endbenutzer)

### Document Preprocessing

**Struktur-Analyse erforderlich:**

- **Multicolumn Content:** Muss anders geparst werden als Single-Column
- **Header Structure:** Semantische Bedeutung aus Überschriften extrahieren
- **Paragraph Length:** Variabilität analysieren für optimale Chunk-Größe
- **Language Detection:** Deutsch als Hauptsprache, Unicode-Support
- **Number Formatting:** Konsistenz prüfen (Kommas, Dezimalstellen)

### Image Preprocessing

- **Resolution Check:** Mindestauflösung für OCR/Text-Extraktion
- **Text in Images:** OCR für Bilder mit eingebettetem Text
- **Abstract Images:** Icons/Logos identifizieren und optional überspringen
- **Image-Text Relationship:** Captions und umgebender Text für Kontext

### Table & Chart Processing

- **Complex Tables:** Nested Tables erkennen und speziell behandeln
- **Table Captions:** Captions für Kontext beibehalten
- **Long Tables:** Header-Repeat in Chunks für lange Tabellen
- **Charts with Numbers:** Zahlen aus Charts extrahieren (falls möglich)

---

## 8. Preprocessing Strategy Recommendation

Based on the analysis, a **routing-based pipeline** is recommended.

### Pipeline Architecture Recommendation

1.  **Ingest:** Fetch raw data.
2.  **Classify:** Use the generated `preprocessing_strategies.yaml` to route files.
3.  **Route:**
    *   *Route A (Text):* Knowledge Articles -> Text Cleaner -> Chunker -> Vector Store.
    *   *Route B (Docs):* Theses -> SciParser -> Vector Store (Thesis Collection).
    *   *Route C (Vision):* Info Images -> Captioning -> Vector Store.
4.  **Enrich:** Inject `namespace` and `access_level` into ALL metadata.

### Metadata Enrichment (Critical)

Jeder Chunk muss folgende Metadata enthalten:

- `namespace`: Namespace der Quelle (z.B. 'teacher', 'org', 'departm')
- `access_level`: 'teacher_only' oder 'public'
- `last_modified`: Letzte Änderung (für Freshness-Weighting)
- `content_type`: Klassifizierung (z.B. 'KNOWLEDGE', 'PORTAL', 'FORM')
- `source_page`: Original Page-ID

### Next Steps

1. Load `preprocessing_strategies.yaml` into the RAGFlow Preprocessor.
2. Implement the routing logic defined above.
3. Configure ScaleKit OAuth für Access Control.
4. Test Query-Generation mit RAGAS.


---
*Report generated automatically by Fetched Data Evaluation Suite (Deep Eval Mode)*
*Generated: 2026-02-16 17:49:29*