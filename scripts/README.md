# Dev Dito Scripts

Scripts für die Entwicklung und das Deployment der Dev Dito DokuWiki Extension.

## Verfügbare Scripts

### deploy-plugin.ps1

Deployed das Plugin zum lokalen Test-Wiki.

```powershell
# Standard-Deployment zum konfigurierten Test-Wiki
.\scripts\deploy-plugin.ps1

# Mit benutzerdefiniertem Ziel-Wiki
.\scripts\deploy-plugin.ps1 -TargetWiki "C:\path\to\wiki"

# Ohne PHP Syntax-Check (schneller, aber unsicherer)
.\scripts\deploy-plugin.ps1 -SkipSyntaxCheck
```

**Funktionen:**
- Prüft alle erforderlichen Plugin-Dateien
- Führt PHP Syntax-Check durch (`php -l`)
- Kopiert alle Dateien zum Ziel-Wiki
- Verifiziert die Installation
- Gibt Version und Datei­zähler aus

**Voraussetzungen:**
- PowerShell 7+
- PHP CLI im PATH (für Syntax-Check)
- Schreibrechte auf Ziel-Verzeichnis

## Ziel-Wiki Konfiguration

Das Standard-Ziel-Wiki ist:
```path
D:\_Repositories\year_2025_26\SYP_2025_26\leonie\internal_leonidas\development\first_own_dokuwiki
```

Das Wiki muss laufen damit Änderungen sichtbar werden:
```powershell
cd "D:\_Repositories\year_2025_26\SYP_2025_26\leonie\internal_leonidas\development\first_own_dokuwiki"
.\scripts\start.ps1
```

## Entwicklungs-Workflow

1. **Code ändern** in `dokuwiki_plugin/`
2. **Deploy ausführen**:
   ```powershell
   .\scripts\deploy-plugin.ps1
   ```
3. **Im Browser testen** (ggf. Hard-Refresh mit Ctrl+Shift+R)
4. **Bei Fehlern**: PHP Error-Log prüfen

## Plugin-Struktur

```text
dokuwiki_plugin/
├── plugin.info.txt     # Plugin-Metadaten (Pflicht)
├── action.php          # Action Plugin - Events & UI
├── admin.php           # Admin Plugin - Dashboard
├── logo.png            # Plugin-Logo (72x72)
├── conf/
│   ├── default.php     # Default-Konfiguration
│   └── metadata.php    # Konfigurationsschema
├── lang/
│   ├── de/             # Deutsche Übersetzungen
│   └── en/             # Englische Übersetzungen
├── dist/               # Kompilierte Assets
│   ├── devdito.min.css
│   └── devdito.min.js
└── lib/                # Hilfsklassen (optional)
```

## Troubleshooting

### PHP Syntax-Fehler
```powershell
# Manueller Check einer Datei
php -l dokuwiki_plugin\action.php
```

### Plugin erscheint nicht
1. Cache leeren: Admin -> Purge Caches
2. Browser-Cache leeren (Ctrl+Shift+R)
3. Plugin aktivieren: Admin -> Extension Manager

### CSS/JS-Änderungen nicht sichtbar
- Version in `plugin.info.txt` erhöhen
- Oder: `?purge=true` an URL anhängen
