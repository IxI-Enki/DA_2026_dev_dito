---
description: Generiert Evaluation-Reports (MD, JSON, HTML). Executive Summary, Metriken-Tabellen (Kap. 6), Vergleichstabellen FF1/FF3/J2/J4/J6, Visualisierungen, Lessons Learned.
globs: ["**/evaluation_results_*.json", "**/statistical_analysis_*.json"]
alwaysApply: false
---

# Report Generation

**Zweck:** Automatische Generierung von Evaluation-Reports fuer die Diplomarbeit und Dokumentation.

## Formate

- **Markdown** – Fuer GitHub, Dokumentation, Kap. 6-Entwurf
- **JSON** – Maschinenlesbar, fuer weitere Verarbeitung
- **HTML** – Interaktiv mit eingebetteten Plots (optional)

## Inhalte

- **Executive Summary** – Kurze Zusammenfassung: beste Modelle/Strategien, Hauptmetriken
- **Metriken-Tabellen** – FF1 (Suchqualitaet), FF3 (Embedding-Modell), J2 (Modellvergleich), J4 (Chunk-Groesse), J6 (Hybrid vs Dense)
- **Vergleichstabellen** – Tabellarische Gegenueberstellung wie in Forschungsfragen gefordert
- **Visualisierungen** – Einbettung oder Verlinkung der Plots aus Statistical Analysis
- **Lessons Learned** – Optional: Limitierungen, Fehleranalyse, Empfehlungen

## Skript

```bash
python evaluation/ragas_agents/scripts/generate_report.py --results-dir <evaluation_results_dir> --stats <statistical_analysis_*.json> [--format md,json,html] [--output-dir evaluation/ragas_agents/output/reports]
```

## Eingaben

- Verzeichnis mit `evaluation_results_*.json` und optional `statistical_analysis_*.json`
- Optional: Einzelne JSON-Dateien, Plot-Pfade
- Config: Template-Pfad, Format-Optionen

## Ausgaben

- **evaluation_report.md** – Hauptreport (Executive Summary, Tabellen, Verweise auf Plots)
- **evaluation_report.json** – Strukturierte Daten
- **evaluation_report.html** – Optional, mit eingebetteten Diagrammen
- Optional: Einzelne Abschnitte (z.B. nur J2-Tabelle) als Snippets

## Hinweise

- Reports dienen als Grundlage fuer Kap. 6 (Embedding, Retrieval, Auth, Deploy) und Anhang
- Bei Aenderungen an Metriken oder Konfiguration: Report erneut generieren (reproduzierbar)
