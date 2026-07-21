---
title: Wiki Fetcher Pipeline Module
description: Stage 1 pipeline module for fetching complete DokuWiki content via JSON-RPC API with local storage of all responses, metadata, media, and namespace structures.
author:
  name: Jan Ritt
  github: 'https://github.com/IxI-Enki'
version: 1.0.0
created: 2025-12-01
updated: 2026-02-13
tags: [pipeline, wiki-fetcher, json-rpc, dokuwiki, api-client]
---

# Wiki Fetcher Pipeline Module

Stage 1 pipeline module for fetching complete DokuWiki content via JSON-RPC API with local storage of all responses.

## Quick Start

```powershell
# From repository root:
docker compose -p stack-g-devdito --profile pipeline run module_fetcher
```

## Überblick

Diese Scripts laden das **komplette Wiki** herunter und speichern:

- Rohe API-Responses (JSON)
- Page Content (raw wiki text)
- Page Metadata (Info-Objekte + ACL)
- Rendered HTML
- Extrahierte Links (internal, external, media)
- **Media-Dateien** (Bilder, PDFs, etc.) - mit Sub-Namespace Scanning
- Namespace-Struktur
- Detaillierte Statistiken & Analyse-Report

## Installation

```bash
pip install -r requirements.txt
```

## Konfiguration

Die Konfiguration erfolgt über Dateien im `config/` Verzeichnis:

```text
config/
├── PLACEHOLDER_api.token  ← API Bearer Token Beispiel
├── PLACEHOLDER_ssl.cert   ← PLACEHOLDER für SSL Zertifikat
├── PLACEHOLDER_env.yaml   ← Dokumentiertes Platzhalter-Beispiel
├── env.yaml               ← Haupt-Konfiguration (editieren!)
├── json_rpc_api.token     ← API Bearer Token
├── ssl.cert               ← SSL Zertifikat
└── settings.json          ← Auto-generiert (nicht editieren!)
```

### env.yaml - FETCH Sektion

Die `FETCH` Sektion enthält alle Performance- und Verhaltens-Optionen:

```yaml
FETCH:
  # === PERFORMANCE ===
  timeout: 2                     # Request timeout in Sekunden
  max_retries: 3                 # Wiederholungsversuche bei Fehlern
  retry_delay: 2                 # Wartezeit zwischen Retries (Sekunden)
  delay_between_requests: 0.05   # Pause zwischen Requests (server-freundlich)
  batch_progress_interval: 20    # Fortschrittsanzeige alle N Items

  # === NAMESPACE SCANNING ===
  max_namespace_depth: 3         # Maximale Tiefe für Sub-Namespace Media-Scan
  scan_all_sub_namespaces: true  # Alle Sub-Namespaces für Media scannen

  # === CONTENT SELECTION ===
  content:
    fetch_html: true             # HTML-Version der Seiten
    fetch_acl: true              # Zugriffsrechte pro Seite
    fetch_links: true            # Links aus HTML extrahieren
    fetch_recent_changes: true   # RSS-Feed für Recent Changes

  # === MEDIA OPTIONS ===
  media:
    enabled: true                # Media-Download aktivieren
    max_file_size_mb: 50         # Max. Dateigröße (0 = unbegrenzt)
    from_listings: true          # Media aus core.listMedia
    from_page_links: true        # Auch referenzierte Media aus Links
    include_types: []            # Nur diese Typen (leer = alle)
    exclude_types: []            # Diese Typen ausschließen

  # === FILTERING ===
  filter:
    include_namespaces: []       # Nur diese Namespaces (leer = alle)
    exclude_namespaces: []       # Diese Namespaces überspringen
    exclude_pages: []            # Einzelne Seiten ausschließen

  # === OUTPUT ===
  output:
    directory_pattern: "fetched_at_{timestamp}"
    save_raw_responses: true     # Rohe API-Responses speichern
    generate_report: true        # Analyse-Report erstellen
    report_format: "txt"         # Report-Format: txt, json, md

  # === QUALITY ===
  quality:
    validate_internal_links: true   # Interne Links validieren
    report_broken_links: true       # Broken Links im Report
    verify_media_integrity: false   # Media-Downloads verifizieren (langsam)
```

### Wichtige Optionen erklärt

| Option                      | Beschreibung                                                                      | Default |
| --------------------------- | --------------------------------------------------------------------------------- | ------- |
| `max_namespace_depth`       | Tiefe für Media-Suche in Sub-Namespaces. 3 bedeutet: `ns`, `ns:sub`, `ns:sub:sub` | 3       |
| `media.from_page_links`     | Zusätzlich Media aus Seitenlinks sammeln (100% Coverage)                          | true    |
| `filter.exclude_namespaces` | Namespaces komplett überspringen                                                  | []      |
| `media.max_file_size_mb`    | Große Dateien überspringen (0 = alle)                                             | 50      |

## Scripts

### Haupt-Scripts

| Script                        | Beschreibung                                                          |
| ----------------------------- | --------------------------------------------------------------------- |
| `fetch_full_wiki_extended.py` | **Haupt-Script** - Vollständiger Fetch mit ACL, Links, Media-Download |
| `download_media_only.py`      | Nur Media-Dateien für bestehenden Fetch nachladen                     |
| `create_wiki_inventory.py`    | Erstellt Wiki-Inventar mit allen Seiten, Media, ACL                   |
| `test_all_api_methods.py`     | Testet alle verfügbaren API-Methoden                                  |

### Hilfs-Scripts

| Script                       | Beschreibung                                 |
| ---------------------------- | -------------------------------------------- |
| `fetch_full_wiki.py`         | Basis-Fetch (nur Content + HTML, ohne Media) |
| `extract_links_from_html.py` | Link-Extraktion aus HTML                     |
| `fetch_recent_changes.py`    | RSS-Feed Parser für Recent Changes           |
| `analyze_fetched_data.py`    | Analyse der gefetchten Daten                 |
| `api_client.py`              | API-Client Bibliothek                        |
| `config.py`                  | Konfiguration (API-URL, Token, Pfade)        |

## Verwendung

### 1. Vollständiger Fetch (empfohlen)

```powershell
# From the repository root:
python pipeline/01_wiki_fetcher/fetch_full_wiki_extended.py
```

**Features:**

- 100% Coverage Ziel
- ACL-Daten pro Seite
- Link-Extraktion aus HTML
- **Media-Download** mit Sub-Namespace-Scanning
- Media aus Seitenlinks (Fallback für 100% Coverage)
- Namespace-Struktur mit Tiefenanalyse
- Detaillierte Statistiken (Dateitypen, Größenverteilung, etc.)
- Analyse-Report als Text-Datei

**Output:** `../content_output/fetched_at_yyyyMMdd_HHmmss/`

**Optionen:**

```powershell
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss';

# Mit custom Output-Verzeichnis
python fetch_full_wiki_extended.py "fetched_at_$timestamp"

# Ohne Media-Download (schneller)
python fetch_full_wiki_extended.py --no-media "fetched_at_$timestamp"

# Quiet Mode
python fetch_full_wiki_extended.py --quiet "fetched_at_$timestamp"
```

### 2. Nur Media nachladen

```powershell
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss';
python download_media_only.py "fetched_at_$timestamp"
```

Lädt Media-Dateien für einen bestehenden Fetch nach.

### 3. Wiki-Inventar erstellen

```powershell
python create_wiki_inventory.py
```

**Output:** `../content_output/inventory/`

### 4. API-Methoden testen

```powershell
python test_all_api_methods.py
```

**Output:** `api_method_test_results.json`

## Output-Struktur (Extended Fetch)

```text
content_output/
├── README.md
├── .gitignore
│
├── archived_fetch_tests/
│   └── ...
│
└── fetched_at_TIMESTAMP/
    ├── fetch_statistics.json     # Detaillierte Statistiken
    ├── wiki_inventory.json       # Wiki-Übersicht
    ├── wiki_analysis_report.txt  # Lesbarer Report
    │
    ├── page_content/             # Raw wiki text
    │   └── {page_id}.txt
    │
    ├── page_metadata/            # Page info + ACL
    │   ├── {page_id}_info.json
    │   └── {page_id}_acl.json
    │
    ├── page_html/                # Rendered html
    │   └── {page_id}.html
    │
    ├── page_links/               # Extracted links
    │   └── {page_id}_links.json
    │
    ├── media/                    # Media files
    │   ├── media_inventory.json  # Inventory with type statistics
    │   ├── {namespace}/          # Files by namespace
    │   │   └── {filename}
    │   └── metadata/
    │       └── {media_id}_info.json
    │
    ├── namespaces/               # Namespace structure
    │   └── namespace_tree.json
    │
    ├── raw_json/                 # Raw API responses
    │   ├── {page_id}_list.json
    │   └── {page_id}_complete.json
    │
    └── changes/                  # Recent changes (via RSS)
```

## Statistiken (fetch_statistics.json)

Das erweiterte Skript erfasst umfangreiche Statistiken:

### Pages

- Größenverteilung (tiny/small/medium/large/huge)
- Größte/kleinste Seite
- Durchschnittliche Content-Größe
- Leere Seiten
- Gefilterte Seiten

### Media

- **Nach Dateityp**: images, documents, spreadsheets, presentations, archives
- **Nach Extension**: pdf, jpg, png, xlsx, docx, etc.
- **Quellen**: listings vs. page_links
- Größte/kleinste Datei
- Gesamtgröße
- Gescannte Namespaces

### Links

- Meistverlinkte Seiten (Top 20)
- Externe Domains (Top 20)
- Broken Links (wikilink2)
- Durchschnitt Links pro Seite

### Namespaces

- Tiefenverteilung
- Pages/Media pro Namespace
- Start-Pages vorhanden?
- Alle gescannten Sub-Namespaces

## API-Methoden Status

### Funktionierende Methoden (7/26)

| Methode            | Beschreibung                                 |
| ------------------ | -------------------------------------------- |
| `core.listPages`   | Alle Seiten auflisten (112 Seiten)           |
| `core.getPage`     | Seiten-Inhalt abrufen                        |
| `core.getPageInfo` | Seiten-Metadaten inkl. Revision-Timestamp    |
| `core.getPageHTML` | Gerendertes HTML                             |
| `core.aclCheck`    | Berechtigungen prüfen                        |
| `core.listMedia`   | Media-Dateien pro Namespace auflisten        |
| `wiki.getAllPages` | Alle Seiten (207 - mehr als core.listPages!) |

### Nicht verfügbar (Workarounds)

| Methode                 | Workaround          |
| ----------------------- | ------------------- |
| `core.getRecentChanges` | RSS-Feed parsing    |
| `core.listLinks`        | HTML-Parsing        |
| `core.getBacklinks`     | Aus Links berechnen |
| `core.getMedia`         | Direct URL Download |

## Performance

### Testergebnisse (207 Seiten, 325 Media)

| Metrik                  | Wert                            |
| ----------------------- | ------------------------------- |
| Seiten                  | 207                             |
| Media-Dateien           | 325 (260 listings + 65 links)   |
| Media-Größe             | ~255 MB                         |
| Fetch-Dauer             | ~9.5 min (574s mit Media)       |
| HTML Coverage           | 99.5% (206/207)                 |
| ACL Coverage            | 100% (207/207)                  |
| Sub-Namespaces gescannt | 35                              |
| Broken Links            | 12                              |
| Orphan Pages            | 19                              |

## Troubleshooting

### Fetch schlägt fehl

1. Netzwerkverbindung prüfen
2. API Token prüfen: `config/json_rpc_api.token`
3. SSL Zertifikat prüfen: `config/ssl.cert`
4. `FETCH.timeout` in `config/env.yaml` erhöhen

### Media-Download langsam

Normal bei ~255 MB. Für schnelleren Fetch: `--no-media` Flag verwenden.

### Fehlende Media-Dateien

1. `max_namespace_depth` erhöhen (default: 3)
2. `media.from_page_links: true` aktivieren
3. Überprüfen ob Media in tieferen Sub-Namespaces liegt

## Siehe auch

- `../config/PLACEHOLDER_env.yaml` - Vollständig dokumentierte Beispiel-Konfiguration
- `../content_output/` - Gespeicherte Wiki-Daten
