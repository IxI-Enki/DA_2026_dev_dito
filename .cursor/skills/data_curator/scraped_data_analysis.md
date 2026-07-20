---
description: Analysiert frisch gefetchte DokuWiki-Daten aus fetched_at_* Ordnern. Parsing von fetch_statistics.json, Namespace-Analyse, Duplicate-Content-Identifikation, Media-Type-Verteilung.
globs: ["**/fetch_statistics.json", "**/pages/**/*.txt", "**/media/**/*"]
alwaysApply: false
---

# Scraped Data Analysis

**Zweck:** Analysiert frisch gefetchte DokuWiki-Daten aus `fetched_at_*` Ordnern fuer die Vorbereitung des RAGAS Testkorpus.

## Funktionen

- **Parsing von fetch_statistics.json** – Liest Statistik-Datei aus dem Fetch-Output
- **Namespace-Analyse** – Welche Bereiche (departm, teacher, org, etc.) am besten dokumentiert sind
- **Identifikation von Duplicate Content** – Doppelte oder nahezu identische Seiten erkennen
- **Media-Type-Verteilung** – PDF, DOCX, Bilder, XLSX etc. pro Namespace

## Skript

Rufe das programmatische Skript auf (token-effizient, reproduzierbar):

```bash
python evaluation/ragas_agents/scripts/analyze_scraped_data.py --input <path_to_fetched_at_*> [--output <output_dir>]
```

## Eingaben

- Pfad zu einem `fetched_at_YYYYMMDD_HHMMSS` Ordner (z.B. aus techstack/dokuwiki/fetcher_json_rpc_api/content_output/)
- Optional: `fetch_statistics.json` direkt

## Ausgaben

- Zusammenfassung: Gesamtanzahl Pages/Media, Namespace-Verteilung, Media-Typen
- Optional: JSON-Report fuer nachfolgende Skills (Test Corpus Selection)

## Hinweise

- Bei mehreren Workspaces: Absoluten oder relativen Pfad zum techstack-Repo angeben
- Output dient als Input fuer Document Quality Assessment und Test Corpus Selection
