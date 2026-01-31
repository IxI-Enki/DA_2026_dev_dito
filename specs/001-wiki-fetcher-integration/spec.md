# Feature Specification: Wiki Fetcher Pipeline Integration und Testing

**Feature Branch**: `001-wiki-fetcher-integration`  
**Created**: 2026-01-31  
**Status**: Draft  
**Input**: User description: "Wiki Fetcher Pipeline Integration und Testing"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Vollstaendiger Wiki Fetch (Priority: P1)

Als Entwickler moechte ich das gesamte DokuWiki ueber die JSON-RPC API fetchen koennen, um alle Wiki-Inhalte lokal fuer die Embedding-Pipeline verfuegbar zu haben.

**Why this priority**: Der Wiki Fetch ist der erste Schritt in der gesamten Pipeline. Ohne gefetchte Daten koennen keine Embeddings erstellt werden.

**Independent Test**: Kann durch Ausfuehren von `fetch_full_wiki_extended.py` mit einem Test-Timestamp getestet werden. Erfolg = Output-Verzeichnis mit `fetch_statistics.json` und gefetchten Seiten.

**Acceptance Scenarios**:

1. **Given** DokuWiki API ist erreichbar und konfiguriert (`config/env.yaml`, `config/ssl.cert`, `config/json_rpc_api.token`), **When** `python fetch_full_wiki_extended.py "test_fetch"` ausgefuehrt wird, **Then** wird ein Verzeichnis `data/fetched/test_fetch/` erstellt mit:
   - `fetch_statistics.json` (Statistiken)
   - `wiki_inventory.json` (Inventar)
   - `wiki_analysis_report.txt` (Analyse-Report)
   - `page_content/` (Raw Wiki Text)
   - `page_metadata/` (Info + ACL)
   - `page_html/` (Rendered HTML)
   - `page_links/` (Extrahierte Links)

2. **Given** API Token ist ungueltig oder abgelaufen, **When** Fetch gestartet wird, **Then** wird eine verstaendliche Fehlermeldung ausgegeben mit Hinweis auf Token-Konfiguration

3. **Given** SSL-Zertifikat fehlt oder ist ungueltig, **When** Fetch gestartet wird, **Then** wird Fehler mit Hinweis auf `config/ssl.cert` angezeigt

---

### User Story 2 - Media Download (Priority: P2)

Als Entwickler moechte ich alle Media-Dateien (Bilder, PDFs, etc.) aus dem Wiki herunterladen koennen, um diese spaeter in die Embeddings einzubeziehen.

**Why this priority**: Media-Dateien sind wichtig fuer vollstaendige Wiki-Inhalte, aber der Haupt-Content (Seiten) hat Prioritaet.

**Independent Test**: Kann durch Fetch mit `--no-media` vs. ohne Flag verglichen werden. Mit Media-Flag sollte `media/` Verzeichnis gefuellt sein.

**Acceptance Scenarios**:

1. **Given** Wiki-Fetch ohne `--no-media` Flag, **When** Fetch abgeschlossen, **Then** enthaelt `media/` Verzeichnis:
   - Dateien nach Namespace organisiert
   - `media_inventory.json` mit Typ-Statistiken
   - `metadata/` mit Info-JSONs pro Datei

2. **Given** Media-Cache aus vorherigem Fetch vorhanden, **When** neuer Fetch gestartet, **Then** werden bereits gecachte Dateien wiederverwendet (schnellerer Fetch)

3. **Given** `--no-media` Flag gesetzt, **When** Fetch abgeschlossen, **Then** ist `media/` Verzeichnis leer aber `media_inventory.json` existiert mit Listing

---

### User Story 3 - Inkrementeller Fetch / Resume (Priority: P3)

Als Entwickler moechte ich einen abgebrochenen Fetch fortsetzen koennen, um bei Netzwerkproblemen nicht von vorne beginnen zu muessen.

**Why this priority**: Nice-to-have fuer Robustheit, aber nicht kritisch fuer MVP.

**Independent Test**: Fetch starten, mit Ctrl+C abbrechen, dann `resume_fetch.py` ausfuehren.

**Acceptance Scenarios**:

1. **Given** Fetch wurde mit Ctrl+C abgebrochen, **When** `resume_fetch.py` mit gleichem Output-Dir ausgefuehrt wird, **Then** werden nur fehlende Seiten nachgeholt

2. **Given** Fetch wurde vollstaendig abgeschlossen, **When** `resume_fetch.py` ausgefuehrt wird, **Then** meldet "Fetch bereits vollstaendig"

---

### Edge Cases

- Was passiert bei sehr grossen Wikis (>1000 Seiten)? → Batch-Progress alle N Items
- Wie verhaelt sich das System bei Wiki-Seiten mit Sonderzeichen im Namen? → Sanitize filename
- Was passiert bei gleichzeitigem Fetch von zwei Instanzen? → File-Locking oder Warning
- Wie werden ACL-geschuetzte Seiten behandelt? → Fetch mit verfuegbaren Rechten, ACL-Info im Metadata

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUSS alle Wiki-Seiten ueber `core.listPages` und `wiki.getAllPages` abrufen fuer 100% Coverage
- **FR-002**: System MUSS Page Content, HTML, Metadata und ACL pro Seite speichern
- **FR-003**: System MUSS Links aus HTML extrahieren (internal, external, media)
- **FR-004**: System MUSS Media-Dateien ueber Direct HTTP Download abrufen
- **FR-005**: System MUSS Konfiguration aus `config/env.yaml` laden
- **FR-006**: System MUSS detaillierte Statistiken in `fetch_statistics.json` speichern
- **FR-007**: System MUSS bei Fehler eines Items weiterlaufen (Graceful Error Handling)
- **FR-008**: System MUSS Ctrl+C sauber behandeln und bisherigen Fortschritt speichern
- **FR-009**: System MUSS bereits gefetchte Media-Dateien cachen koennen (optional via `--no-cache`)

### Key Entities

- **Page**: Wiki-Seite mit id, content, html, metadata (revision, size, permission), acl, links
- **Media**: Media-Datei mit id, namespace, filename, size, type, discovery_method (listing/link)
- **Namespace**: Wiki-Namespace mit page_count, media_count, has_start_page
- **FetchStatistics**: Aggregierte Statistiken ueber Pages, Media, Links, ACL, Errors

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Fetch von 200+ Seiten Wiki in unter 10 Minuten (ohne Media)
- **SC-002**: Fetch von 200+ Seiten Wiki inkl. Media in unter 15 Minuten
- **SC-003**: Page Success Rate >= 99% (nur fehlende ACL-Rechte als Fehler akzeptiert)
- **SC-004**: HTML Coverage >= 99% (fast alle Seiten haben gerendertes HTML)
- **SC-005**: Media Coverage >= 95% (Referenced Media vs. Downloaded)
- **SC-006**: Output ist vollstaendig selbst-dokumentierend (`wiki_analysis_report.txt`)
