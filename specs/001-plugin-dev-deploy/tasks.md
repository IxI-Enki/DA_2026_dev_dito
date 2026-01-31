# Task Breakdown: DokuWiki Plugin Dev Dito - Development & Deployment

**Feature Branch**: `001-plugin-dev-deploy`  
**Created**: 2026-01-31  
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)  
**Constitution**: v1.2.0

---

## Progress Tracker

| Phase | Tasks | Completed | Progress |
|-------|-------|-----------|----------|
| Phase 1: Config Infrastructure | 6 | 6 | [X][X][X][X][X][X] |
| Phase 2: Pipeline Integration | 4 | 3 | [X][X][X][ ] |
| Phase 3: Plugin Adaptation | 4 | 4 | [X][X][X][X] |
| Phase 4: Deploy & Verify | 4 | 4 | [X][X][X][X] |
| **Total** | **18** | **17** | **94%** |

---

## Phase 1: Config Infrastructure (User Story 4 - P1)

> Zentrale Konfiguration als Basis fuer alle weiteren Tasks

### Task 1.1: config/ Verzeichnisstruktur anlegen

**Priority**: P1-Critical | **Effort**: 15min | **Dependencies**: None

**Description**: Erstelle die Verzeichnisstruktur fuer die zentrale Konfiguration.

**Steps**:
1. Erstelle `config/` Verzeichnis im Repository-Root
2. Erstelle `config/secrets/` Unterverzeichnis
3. Erstelle leere Placeholder-Dateien

**Files to Create**:
```
config/
├── secrets/
│   ├── .gitkeep
│   └── README.md (Erklaerung welche Secrets hier hin gehoeren)
```

**Definition of Done**:
- [X] `config/` Verzeichnis existiert
- [X] `config/secrets/` Verzeichnis existiert
- [X] `config/secrets/README.md` dokumentiert benoetigte Secrets

---

### Task 1.2: PLACEHOLDER_env.yaml erstellen

**Priority**: P1-Critical | **Effort**: 30min | **Dependencies**: Task 1.1

**Description**: Erstelle das dokumentierte Template fuer env.yaml mit allen Konfigurationsoptionen.

**Steps**:
1. Kopiere Struktur aus Wiki Fetcher `PLACEHOLDER_env.yaml`
2. Erweitere um SERVICES und PLUGIN Sektionen
3. Dokumentiere jeden Wert mit Kommentaren

**File Content** (Auszug):
```yaml
# config/PLACEHOLDER_env.yaml
# ============================
# Kopiere diese Datei nach env.yaml und passe die Werte an.
# NIEMALS env.yaml committen!

APP:
  name: dev_dito
  version: "0.1.0"

PATHS:
  # Absoluter Pfad zum Repository-Root
  root_dir: D:/_Repositories/_Diploma_Thesis_Repositories/dev_dito
  config_dir: ${root_dir}/config
  secrets_dir: ${config_dir}/secrets
  output_dir: ${root_dir}/output

SOURCE_WIKI:
  name: "HTL Leonding LeoWiki"
  api:
    url: https://your-wiki.example.com/lib/exe/jsonrpc.php
    base_url: https://your-wiki.example.com
    fetch_url: https://your-wiki.example.com/lib/exe/fetch.php
  authentication:
    type: bearer
    token_file: ${secrets_dir}/json_rpc_api.token
  certificate: ${secrets_dir}/ssl.cert

SERVICES:
  mcp_server:
    url: http://wiki_dev_mcp_server:3000
    timeout: 30
  qdrant:
    host: qdrant_db
    port: 6333
    collection: wiki_embeddings
  openai:
    token_file: ${secrets_dir}/openai.token
    embedding_model: text-embedding-3-large
    dimensions: 3072

PIPELINE:
  fetcher:
    timeout: 30
    max_retries: 3
    delay_between_requests: 0.05
    max_namespace_depth: 3
    exclude_namespaces:
      - playground
      - wiki
  embedder:
    chunk_size: 512
    chunk_overlap: 50

PLUGIN:
  enabled: true
  panel_position: right
  search_results_limit: 5
```

**Definition of Done**:
- [X] `config/PLACEHOLDER_env.yaml` existiert
- [X] Alle Sektionen dokumentiert (APP, PATHS, SOURCE_WIKI, SERVICES, PIPELINE, PLUGIN)
- [X] Platzhalter-Syntax `${var}` korrekt verwendet
- [X] Secrets referenzieren `${secrets_dir}/` Pfade

---

### Task 1.3: config.py Root-Level Loader implementieren

**Priority**: P1-Critical | **Effort**: 1h | **Dependencies**: Task 1.2

**Description**: Implementiere den zentralen Config-Loader basierend auf dem Wiki Fetcher Pattern.

**Steps**:
1. Kopiere Basis-Struktur aus `pipeline/01_wiki_fetcher/config.py`
2. Passe Pfade an (Root-Level statt Modul-Level)
3. Implementiere `generate_settings_json()` Funktion
4. Fuege Validation hinzu

**File**: `config.py` (Repository-Root)

**Key Functions**:
```python
def load_config() -> Dict[str, Any]:
    """Load and validate env.yaml"""

def resolve_placeholders(data: Dict, context: Dict) -> Dict:
    """Resolve ${var} placeholders"""

def load_secrets(config: Dict) -> Dict:
    """Load secrets from separate files"""

def generate_settings_json(config: Dict) -> None:
    """Generate settings.json for PHP components"""

def validate_config(config: Dict) -> bool:
    """Validate required fields exist"""

# Typisierte Exports
settings = load_config()
SOURCE_WIKI_URL: str = settings["SOURCE_WIKI"]["api"]["url"]
MCP_SERVER_URL: str = settings["SERVICES"]["mcp_server"]["url"]
QDRANT_HOST: str = settings["SERVICES"]["qdrant"]["host"]
# ... etc
```

**Definition of Done**:
- [X] `config.py` existiert im Repository-Root
- [X] `load_config()` laedt env.yaml erfolgreich
- [X] Platzhalter werden korrekt aufgeloest
- [X] Secrets werden aus separaten Dateien geladen
- [X] `settings.json` wird generiert
- [X] Typisierte Exports vorhanden
- [X] `python config.py` laeuft ohne Fehler

---

### Task 1.4: .gitignore aktualisieren

**Priority**: P1-Critical | **Effort**: 10min | **Dependencies**: Task 1.1

**Description**: Stelle sicher dass alle Secrets und die aktive Config gitignored sind.

**Steps**:
1. Oeffne `.gitignore`
2. Fuege Config-Patterns hinzu

**Additions to .gitignore**:
```gitignore
# Zentrale Konfiguration (Article II-B, VI)
config/env.yaml
config/settings.json
config/secrets/*
!config/secrets/.gitkeep
!config/secrets/README.md

# Secret-Dateien (allgemein)
*.token
*.cert
*.key
*.pem
```

**Definition of Done**:
- [X] `config/env.yaml` ist gitignored
- [X] `config/settings.json` ist gitignored
- [X] `config/secrets/*` ist gitignored (ausser .gitkeep, README.md)
- [X] `git status` zeigt keine Secrets

---

### Task 1.5: env.yaml mit echten Werten erstellen

**Priority**: P1-Critical | **Effort**: 15min | **Dependencies**: Task 1.2, 1.4

**Description**: Erstelle die aktive env.yaml mit den echten Konfigurationswerten.

**Steps**:
1. Kopiere `PLACEHOLDER_env.yaml` nach `env.yaml`
2. Trage echte Pfade ein
3. Trage echte URLs ein

**Definition of Done**:
- [X] `config/env.yaml` existiert (lokal, nicht im Git)
- [X] Alle Pfade sind korrekt fuer lokale Entwicklung
- [X] Source-Wiki URL ist korrekt
- [X] Service-URLs sind korrekt

---

### Task 1.6: Secrets migrieren

**Priority**: P1-Critical | **Effort**: 15min | **Dependencies**: Task 1.1, 1.5

**Description**: Kopiere existierende Secrets aus `pipeline/01_wiki_fetcher/config/` in die zentrale Location.

**Steps**:
1. Kopiere `json_rpc_api.token` nach `config/secrets/`
2. Kopiere `ssl.cert` nach `config/secrets/`
3. Erstelle `openai.token` (falls vorhanden)
4. Aktualisiere `env.yaml` Pfade

**Definition of Done**:
- [X] `config/secrets/json_rpc_api.token` existiert
- [X] `config/secrets/ssl.cert` existiert
- [X] Alte Secrets in `pipeline/01_wiki_fetcher/config/` koennen geloescht werden
- [X] Config laesst sich laden ohne Fehler

---

## Phase 2: Pipeline Integration (User Story 5 - P2)

> Pipeline-Module auf zentrale Config umstellen

### Task 2.1: Wiki Fetcher auf zentrale Config umstellen

**Priority**: P2-High | **Effort**: 1h | **Dependencies**: Phase 1 complete

**Description**: Stelle `pipeline/01_wiki_fetcher/` auf die zentrale Config um.

**Steps**:
1. Entferne lokale `config/env.yaml` Referenzen
2. Importiere vom Root-Level `config.py`
3. Ersetze alle hardcodierten Werte
4. Teste Fetcher mit neuer Config

**Changes in** `pipeline/01_wiki_fetcher/`:
```python
# ALT (in fetch_full_wiki_extended.py):
from config import API_URL, HEADERS, ...

# NEU:
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import SOURCE_WIKI_URL, settings
```

**Definition of Done**:
- [ ] Keine lokale `config.py` mehr im Fetcher-Modul
- [ ] Fetcher importiert vom Root-Level
- [ ] `python pipeline/01_wiki_fetcher/fetch_full_wiki_extended.py --help` funktioniert
- [ ] Keine hardcodierten URLs im Code

---

### Task 2.2: Verify kein Hardcoding in Pipeline

**Priority**: P2-High | **Effort**: 30min | **Dependencies**: Task 2.1

**Description**: Pruefe alle Pipeline-Module auf hardcodierte Werte.

**Steps**:
1. `grep -r "http://" pipeline/` ausfuehren
2. `grep -r ":3000\|:6333\|:8080" pipeline/` ausfuehren
3. Gefundene Hardcodings durch Config-Referenzen ersetzen

**Definition of Done**:
- [ ] Keine hardcodierten URLs ausser in Kommentaren/Doku
- [ ] Keine hardcodierten Ports
- [ ] Alle Werte kommen aus `settings`

---

### Task 2.3: Wiki Fetcher Dry-Run Test

**Priority**: P2-High | **Effort**: 30min | **Dependencies**: Task 2.1

**Description**: Teste den Wiki Fetcher mit der neuen Config ohne echten Fetch.

**Steps**:
1. Implementiere `--dry-run` Flag falls nicht vorhanden
2. Fuehre Dry-Run aus
3. Verifiziere dass Config korrekt geladen wird

**Command**:
```powershell
python pipeline/01_wiki_fetcher/fetch_full_wiki_extended.py --dry-run
```

**Definition of Done**:
- [ ] Dry-Run zeigt geladene Config-Werte
- [ ] Keine Verbindungsfehler (Config korrekt)
- [ ] API-Token wird korrekt geladen

---

### Task 2.4: Wiki Fetcher Live-Test (optional)

**Priority**: P3-Low | **Effort**: 30min | **Dependencies**: Task 2.3

**Description**: Fuehre einen echten Fetch-Test mit limitierten Daten durch.

**Steps**:
1. Konfiguriere `exclude_namespaces` um nur Test-Namespace zu fetchen
2. Fuehre Fetch aus
3. Verifiziere Output in `output/`

**Definition of Done**:
- [ ] Fetch laeuft ohne Fehler
- [ ] Output-Dateien werden erstellt
- [ ] Authentifizierung funktioniert

---

## Phase 3: Plugin Adaptation (User Story 1, 4)

> DokuWiki Plugin auf zentrale Config umstellen

### Task 3.1: PHP ConfigLoader erstellen

**Priority**: P2-High | **Effort**: 45min | **Dependencies**: Task 1.3

**Description**: Erstelle PHP-Klasse zum Laden der `settings.json`.

**File**: `dokuwiki_plugin/lib/ConfigLoader.php`

**Content**:
```php
<?php
declare(strict_types=1);

namespace dokuwiki\plugin\devdito\lib;

/**
 * ConfigLoader - Loads centralized configuration from settings.json
 * 
 * Constitution Article II-B: All config from central env.yaml
 */
class ConfigLoader
{
    private static ?array $config = null;
    
    /**
     * Get configuration array
     * @return array Configuration values
     */
    public static function getConfig(): array
    {
        if (self::$config === null) {
            self::$config = self::loadConfig();
        }
        return self::$config;
    }
    
    /**
     * Get specific config value by dot-notation path
     * @param string $path e.g. "SERVICES.mcp_server.url"
     * @param mixed $default Default value if not found
     * @return mixed Config value
     */
    public static function get(string $path, $default = null)
    {
        $keys = explode('.', $path);
        $value = self::getConfig();
        
        foreach ($keys as $key) {
            if (!isset($value[$key])) {
                return $default;
            }
            $value = $value[$key];
        }
        
        return $value;
    }
    
    private static function loadConfig(): array
    {
        $configPath = dirname(__DIR__, 2) . '/config/settings.json';
        
        if (!file_exists($configPath)) {
            // Fallback: Try to generate
            self::generateSettingsJson();
        }
        
        if (!file_exists($configPath)) {
            throw new \RuntimeException(
                "Config file not found: $configPath\n" .
                "Run 'python config.py' to generate settings.json"
            );
        }
        
        $json = file_get_contents($configPath);
        $config = json_decode($json, true);
        
        if (json_last_error() !== JSON_ERROR_NONE) {
            throw new \RuntimeException(
                "Invalid JSON in config file: " . json_last_error_msg()
            );
        }
        
        return $config;
    }
    
    private static function generateSettingsJson(): void
    {
        $pythonScript = dirname(__DIR__, 2) . '/config.py';
        if (file_exists($pythonScript)) {
            exec("python \"$pythonScript\"", $output, $returnCode);
        }
    }
}
```

**Definition of Done**:
- [ ] `dokuwiki_plugin/lib/ConfigLoader.php` existiert
- [ ] PSR-12 konform
- [ ] `declare(strict_types=1)` vorhanden
- [ ] PHPDoc vollstaendig
- [ ] Dot-Notation Zugriff funktioniert

---

### Task 3.2: action.php auf ConfigLoader umstellen

**Priority**: P2-High | **Effort**: 30min | **Dependencies**: Task 3.1

**Description**: Ersetze hardcodierte Werte in action.php durch ConfigLoader.

**Changes**:
```php
// ALT:
$mcpUrl = $this->getConf('devdito_mcp_url');

// NEU:
use dokuwiki\plugin\devdito\lib\ConfigLoader;
$mcpUrl = ConfigLoader::get('SERVICES.mcp_server.url');
```

**Definition of Done**:
- [ ] MCP URL kommt aus ConfigLoader
- [ ] Timeout kommt aus ConfigLoader
- [ ] Keine hardcodierten Service-URLs mehr
- [ ] Plugin funktioniert nach Aenderung

---

### Task 3.3: admin.php auf ConfigLoader umstellen

**Priority**: P2-High | **Effort**: 30min | **Dependencies**: Task 3.1

**Description**: Ersetze hardcodierte Werte in admin.php durch ConfigLoader.

**Changes**:
- Qdrant Host/Port aus Config
- MCP URL aus Config
- Service-Timeouts aus Config

**Definition of Done**:
- [ ] Alle Service-URLs aus ConfigLoader
- [ ] Dashboard zeigt Config-Werte korrekt an
- [ ] Test-Buttons funktionieren

---

### Task 3.4: DokuWiki conf/default.php vereinfachen

**Priority**: P3-Low | **Effort**: 15min | **Dependencies**: Task 3.2, 3.3

**Description**: Reduziere DokuWiki-eigene Config auf UI-relevante Settings.

**Steps**:
1. Entferne `devdito_mcp_url` (kommt jetzt aus settings.json)
2. Behalte nur UI-Settings: `devdito_enabled`, `devdito_panel_position`

**Definition of Done**:
- [ ] `conf/default.php` enthaelt nur UI-Settings
- [ ] `conf/metadata.php` entsprechend angepasst
- [ ] Plugin laeuft ohne Fehler

---

## Phase 4: Deploy & Verify

> Finales Deployment und Verifikation

### Task 4.1: deploy-plugin.ps1 aktualisieren

**Priority**: P1-Critical | **Effort**: 30min | **Dependencies**: Phase 3 complete

**Description**: Aktualisiere Deploy-Script fuer neue Struktur.

**Steps**:
1. Fuege `lib/ConfigLoader.php` zu kopierten Dateien hinzu
2. Pruefe dass `config/settings.json` existiert vor Deploy
3. Aktualisiere File-Count Validierung

**Definition of Done**:
- [ ] Script kopiert `lib/ConfigLoader.php`
- [ ] Script warnt wenn `settings.json` fehlt
- [ ] Alle Dateien werden korrekt deployed

---

### Task 4.2: Generate settings.json vor Deploy

**Priority**: P1-Critical | **Effort**: 15min | **Dependencies**: Task 1.3

**Description**: Stelle sicher dass settings.json vor jedem Deploy generiert wird.

**Options**:
1. Manuell: `python config.py` vor Deploy
2. Automatisch: Deploy-Script ruft `python config.py` auf

**Definition of Done**:
- [ ] `config/settings.json` wird vor Deploy generiert
- [ ] Veraltete settings.json wird erkannt

---

### Task 4.3: Full Integration Test

**Priority**: P1-Critical | **Effort**: 1h | **Dependencies**: All previous tasks

**Description**: Teste das komplette System End-to-End.

**Test Checklist**:
1. [ ] `python config.py` generiert settings.json
2. [ ] `deploy-plugin.ps1` kopiert alle Dateien
3. [ ] Plugin erscheint im Wiki Admin
4. [ ] Dashboard zeigt korrekte Service-URLs
5. [ ] Search-Funktion nutzt MCP URL aus Config
6. [ ] Wiki Fetcher laeuft mit zentraler Config

**Definition of Done**:
- [ ] Alle Tests bestehen
- [ ] Keine hardcodierten Werte mehr im Code
- [ ] Constitution Article II-B ist erfuellt

---

### Task 4.4: Dokumentation finalisieren

**Priority**: P2-High | **Effort**: 30min | **Dependencies**: Task 4.3

**Description**: Aktualisiere README und Dokumentation.

**Steps**:
1. Aktualisiere `README.md` mit Config-Setup Anweisungen
2. Dokumentiere wie man `env.yaml` einrichtet
3. Beschreibe den Workflow: env.yaml → config.py → settings.json

**Definition of Done**:
- [ ] README enthaelt Config-Setup Sektion
- [ ] Neuer Entwickler kann System mit README einrichten
- [ ] Alle Dateien dokumentiert

---

## Task Dependencies Diagram

```
Phase 1: Config Infrastructure
┌─────────┐
│ Task 1.1│ ─────────────────────────────────────┐
│ Dirs    │                                      │
└────┬────┘                                      │
     │                                           │
     ▼                                           ▼
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ Task 1.2│───►│ Task 1.3│    │ Task 1.4│    │ Task 1.6│
│PLACEHOLDER│   │config.py│    │.gitignore│   │ Secrets │
└────┬────┘    └────┬────┘    └─────────┘    └─────────┘
     │              │
     ▼              │
┌─────────┐         │
│ Task 1.5│◄────────┘
│ env.yaml│
└────┬────┘
     │
     ▼
Phase 2: Pipeline Integration
┌─────────┐    ┌─────────┐    ┌─────────┐
│ Task 2.1│───►│ Task 2.2│───►│ Task 2.3│───► Task 2.4
│ Fetcher │    │ Verify  │    │Dry-Run  │    (optional)
└────┬────┘    └─────────┘    └─────────┘
     │
     ▼
Phase 3: Plugin Adaptation
┌─────────┐    ┌─────────┐    ┌─────────┐
│ Task 3.1│───►│ Task 3.2│───►│ Task 3.4│
│ConfigLdr│    │action.php│   │simplify │
└────┬────┘    └─────────┘    └─────────┘
     │
     ├────────►┌─────────┐
     │         │ Task 3.3│
     │         │admin.php│
     │         └────┬────┘
     │              │
     ▼              ▼
Phase 4: Deploy & Verify
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ Task 4.1│───►│ Task 4.2│───►│ Task 4.3│───►│ Task 4.4│
│ deploy  │    │ gen json│    │ test    │    │ docs    │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
```

---

## Effort Summary

| Phase | Tasks | Total Effort |
|-------|-------|--------------|
| Phase 1 | 6 | ~2.5h |
| Phase 2 | 4 | ~2.5h |
| Phase 3 | 4 | ~2h |
| Phase 4 | 4 | ~2.5h |
| **Total** | **18** | **~9.5h** |

---

## Implementation Order (Empfohlen)

1. **Tag 1** (3-4h): Phase 1 komplett (Config Infrastructure)
2. **Tag 2** (2-3h): Phase 2 (Pipeline Integration)
3. **Tag 3** (2h): Phase 3 (Plugin Adaptation)
4. **Tag 4** (2-3h): Phase 4 (Deploy & Verify)

---

## Quality Gates (Constitution Compliance)

Vor Abschluss jeder Phase pruefen:

- [ ] **Article II-B**: Keine hardcodierten Werte im Code
- [ ] **Article IV**: `ruff check` + `phpcs --standard=PSR12` bestehen
- [ ] **Article VI**: Keine Secrets in Git (`git diff` pruefen)
- [ ] **Article V**: READMEs aktualisiert

---

*Generated by `/tasks` command | 2026-01-31*
