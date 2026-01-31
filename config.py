"""
Dev Dito - Zentrale Konfiguration
=================================
Laedt Settings aus config/env.yaml, loest Platzhalter auf,
liest Secrets aus separaten Dateien und generiert settings.json.

Constitution Article II-B: Alle Konfiguration zentral hier.

Usage:
    from config import settings, SOURCE_WIKI_URL, MCP_SERVER_URL
    # oder
    from config import get_setting
    url = get_setting("SERVICES.mcp_server.url")
"""
import json
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


# =============================================================================
# Path Resolution
# =============================================================================

# Repository Root = Verzeichnis dieser Datei
REPO_ROOT = Path(__file__).parent.resolve()
CONFIG_DIR = REPO_ROOT / "config"
SECRETS_DIR = CONFIG_DIR / "secrets"

# Config file paths
ENV_YAML_PATH = CONFIG_DIR / "env.yaml"
PLACEHOLDER_PATH = CONFIG_DIR / "PLACEHOLDER_env.yaml"
SETTINGS_JSON_PATH = CONFIG_DIR / "settings.json"


# =============================================================================
# Placeholder Resolution
# =============================================================================

def resolve_placeholders(data: Dict[str, Any], context: Dict[str, str] | None = None) -> Dict[str, Any]:
    """
    Rekursiv ${var} Platzhalter in einem Dictionary aufloesen.
    
    Args:
        data: Dictionary mit Platzhaltern
        context: Kontext-Dictionary mit bekannten Variablen
    
    Returns:
        Dictionary mit aufgeloesten Werten
    """
    if context is None:
        context = {}
    
    def resolve_string(s: str) -> str:
        """Loest Platzhalter in einem einzelnen String auf"""
        pattern = r'\$\{([^}]+)\}'
        
        def replacer(match: re.Match[str]) -> str:
            var_name = match.group(1)
            if var_name in context:
                return context[var_name]
            return match.group(0)
        
        result = s
        # Max 5 Iterationen fuer verschachtelte Platzhalter
        for _ in range(5):
            new_result = re.sub(pattern, replacer, result)
            if new_result == result:
                break
            result = new_result
        return result
    
    def resolve_value(value: Any) -> Any:
        """Rekursiv einen Wert aufloesen"""
        if isinstance(value, str):
            return resolve_string(value)
        elif isinstance(value, dict):
            return {k: resolve_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [resolve_value(item) for item in value]
        return value
    
    # Erster Pass: Kontext aus PATHS aufbauen
    if "PATHS" in data:
        for key, value in data["PATHS"].items():
            if isinstance(value, str):
                resolved = resolve_string(value)
                context[key] = resolved
                data["PATHS"][key] = resolved
    
    return resolve_value(data)


# =============================================================================
# Secret Loading
# =============================================================================

def load_secret_file(file_path: str | Path) -> str:
    """
    Laedt ein Secret aus einer Datei.
    
    Args:
        file_path: Pfad zur Secret-Datei
    
    Returns:
        Secret-Inhalt (getrimmt)
    """
    path = Path(file_path)
    if not path.exists():
        return ""
    
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    
    # Handle KEY=value Format (aber nicht JWT Tokens die mit = enden koennen)
    if "=" in content and not content.startswith("eyJ"):
        parts = content.split("=", 1)
        if len(parts) == 2 and parts[0].isupper():
            content = parts[1]
    
    return content


def load_all_secrets(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Laedt alle Secrets aus den referenzierten Dateien.
    
    Durchsucht die Config nach *_file Eintraegen und laedt diese.
    """
    def process_dict(d: Dict[str, Any]) -> Dict[str, Any]:
        result = {}
        for key, value in d.items():
            if isinstance(value, dict):
                result[key] = process_dict(value)
            elif key.endswith("_file") and isinstance(value, str):
                # Lade Secret und speichere unter Key ohne _file Suffix
                secret_key = key.replace("_file", "")
                secret_value = load_secret_file(value)
                result[key] = value  # Behalte original Pfad
                if secret_value:
                    result[secret_key] = secret_value
            else:
                result[key] = value
        return result
    
    return process_dict(config)


# =============================================================================
# Config Loading
# =============================================================================

def load_yaml_config(yaml_path: Path) -> Dict[str, Any]:
    """Laedt und parst eine YAML Config Datei"""
    if not yaml_path.exists():
        raise FileNotFoundError(f"Config Datei nicht gefunden: {yaml_path}")
    
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    if not isinstance(data, dict):
        raise ValueError(f"Ungueltiges Config-Format in {yaml_path}")
    
    return data


def compute_config_hash(config: Dict[str, Any]) -> str:
    """Berechnet Hash der Config fuer Change Detection"""
    # Entferne Meta-Daten vor Hash-Berechnung
    config_copy = {k: v for k, v in config.items() if k != "_meta"}
    json_str = json.dumps(config_copy, sort_keys=True)
    return hashlib.md5(json_str.encode()).hexdigest()


def save_settings_json(config: Dict[str, Any], config_hash: str) -> None:
    """Speichert settings.json mit Metadaten"""
    output_config = config.copy()
    output_config["_meta"] = {
        "generated_at": datetime.now().isoformat(),
        "source": "config/env.yaml",
        "hash": config_hash,
        "version": config.get("APP", {}).get("version", "unknown")
    }
    
    # Entferne sensitive Daten aus settings.json (keine Token-Werte!)
    def sanitize(d: Dict[str, Any]) -> Dict[str, Any]:
        result = {}
        for key, value in d.items():
            # Ueberspringe geladene Token-Werte, behalte nur _file Pfade
            if key in ("token", "api_key", "secret") and not key.endswith("_file"):
                continue
            elif isinstance(value, dict):
                result[key] = sanitize(value)
            else:
                result[key] = value
        return result
    
    sanitized = sanitize(output_config)
    
    SETTINGS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(sanitized, f, indent=2, ensure_ascii=False)


def load_config() -> Dict[str, Any]:
    """
    Laedt die komplette Konfiguration:
    1. Laedt env.yaml (oder Fallback zu PLACEHOLDER)
    2. Loest Platzhalter auf
    3. Laedt Secrets aus Dateien
    4. Generiert/aktualisiert settings.json
    
    Returns:
        Vollstaendige Config als Dictionary
    """
    # Bestimme Config-Pfad
    if ENV_YAML_PATH.exists():
        config_path = ENV_YAML_PATH
    elif PLACEHOLDER_PATH.exists():
        print(f"[config] WARNING: Nutze PLACEHOLDER_env.yaml - bitte env.yaml erstellen!")
        config_path = PLACEHOLDER_PATH
    else:
        raise FileNotFoundError(
            f"Keine Config gefunden!\n"
            f"Erwartet: {ENV_YAML_PATH}\n"
            f"Kopiere PLACEHOLDER_env.yaml nach env.yaml und passe die Werte an."
        )
    
    # Lade YAML
    raw_config = load_yaml_config(config_path)
    
    # Loese Platzhalter auf
    config = resolve_placeholders(raw_config)
    
    # Lade Secrets
    config = load_all_secrets(config)
    
    # Generiere/aktualisiere settings.json
    config_hash = compute_config_hash(config)
    
    existing_hash = None
    if SETTINGS_JSON_PATH.exists():
        try:
            with open(SETTINGS_JSON_PATH, "r", encoding="utf-8") as f:
                existing = json.load(f)
                existing_hash = existing.get("_meta", {}).get("hash")
        except (json.JSONDecodeError, KeyError):
            pass
    
    if existing_hash != config_hash:
        save_settings_json(config, config_hash)
        print(f"[config] settings.json aktualisiert (hash: {config_hash[:8]})")
    
    return config


# =============================================================================
# Helper Functions
# =============================================================================

def get_setting(path: str, default: Any = None) -> Any:
    """
    Holt einen verschachtelten Wert per Punkt-separiertem Pfad.
    
    Args:
        path: z.B. "SERVICES.mcp_server.url"
        default: Fallback-Wert
    
    Returns:
        Konfigurationswert oder default
    
    Example:
        url = get_setting("SERVICES.mcp_server.url", "http://localhost:3000")
    """
    keys = path.split(".")
    value = settings
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return default
        if value is None:
            return default
    return value


def validate_config() -> tuple[bool, List[str]]:
    """
    Validiert dass essentielle Config-Werte vorhanden sind.
    
    Returns:
        Tuple (valid: bool, errors: List[str])
    """
    errors: List[str] = []
    
    # Pflicht-Felder pruefen
    required_paths = [
        "PATHS.root_dir",
        "SOURCE_WIKI.api.url",
        "SERVICES.mcp_server.url",
        "SERVICES.qdrant.host",
    ]
    
    for path in required_paths:
        if not get_setting(path):
            errors.append(f"{path} ist nicht konfiguriert")
    
    # Token-Datei pruefen
    token_file = get_setting("SOURCE_WIKI.authentication.token_file")
    if token_file and not Path(token_file).exists():
        errors.append(f"Token-Datei nicht gefunden: {token_file}")
    
    # SSL Zertifikat pruefen
    cert_file = get_setting("SOURCE_WIKI.certificate")
    if cert_file and not Path(cert_file).exists():
        errors.append(f"SSL Zertifikat nicht gefunden: {cert_file}")
    
    return len(errors) == 0, errors


# =============================================================================
# Load Configuration at Import
# =============================================================================

try:
    settings = load_config()
except FileNotFoundError as e:
    print(f"[config] ERROR: {e}")
    # Erstelle leere Settings damit Import nicht fehlschlaegt
    settings = {
        "APP": {"name": "dev_dito", "version": "0.0.0"},
        "PATHS": {},
        "SOURCE_WIKI": {"api": {}, "authentication": {}},
        "SERVICES": {"mcp_server": {}, "qdrant": {}},
        "PIPELINE": {},
        "PLUGIN": {},
    }


# =============================================================================
# Typed Exports (fuer bequemen Import)
# =============================================================================

# Projekt-Pfade
REPO_ROOT_DIR: str = get_setting("PATHS.root_dir", str(REPO_ROOT))
CONFIG_DIR_PATH: str = get_setting("PATHS.config_dir", str(CONFIG_DIR))
SECRETS_DIR_PATH: str = get_setting("PATHS.secrets_dir", str(SECRETS_DIR))
OUTPUT_DIR: str = get_setting("PATHS.output_dir", str(REPO_ROOT / "output"))
DATA_DIR: str = get_setting("PATHS.data_dir", str(REPO_ROOT / "data"))

# Source Wiki (JSON-RPC API)
SOURCE_WIKI_URL: str = get_setting("SOURCE_WIKI.api.url", "")
SOURCE_WIKI_BASE_URL: str = get_setting("SOURCE_WIKI.api.base_url", "")
SOURCE_WIKI_FETCH_URL: str = get_setting("SOURCE_WIKI.api.fetch_url", "")
SOURCE_WIKI_TOKEN: str = get_setting("SOURCE_WIKI.authentication.token", "")
SOURCE_WIKI_CERT: str = get_setting("SOURCE_WIKI.certificate", "")

# Services (extern)
MCP_SERVER_URL: str = get_setting("SERVICES.mcp_server.url", "http://wiki_dev_mcp_server:3000")
MCP_SERVER_TIMEOUT: int = get_setting("SERVICES.mcp_server.timeout", 30)

QDRANT_HOST: str = get_setting("SERVICES.qdrant.host", "qdrant_db")
QDRANT_PORT: int = get_setting("SERVICES.qdrant.port", 6333)
QDRANT_COLLECTION: str = get_setting("SERVICES.qdrant.collection", "wiki_embeddings")

OPENAI_TOKEN: str = get_setting("SERVICES.openai.token", "")
EMBEDDING_MODEL: str = get_setting("SERVICES.openai.embedding_model", "text-embedding-3-large")
EMBEDDING_DIMENSIONS: int = get_setting("SERVICES.openai.dimensions", 3072)

# Pipeline Settings
FETCHER_TIMEOUT: int = get_setting("PIPELINE.fetcher.timeout", 30)
FETCHER_MAX_RETRIES: int = get_setting("PIPELINE.fetcher.max_retries", 3)
FETCHER_DELAY: float = get_setting("PIPELINE.fetcher.delay_between_requests", 0.05)

EMBEDDER_CHUNK_SIZE: int = get_setting("PIPELINE.embedder.chunk_size", 512)
EMBEDDER_CHUNK_OVERLAP: int = get_setting("PIPELINE.embedder.chunk_overlap", 50)

# Plugin Settings
PLUGIN_ENABLED: bool = get_setting("PLUGIN.enabled", True)
PLUGIN_PANEL_POSITION: str = get_setting("PLUGIN.panel_position", "right")
PLUGIN_SEARCH_LIMIT: int = get_setting("PLUGIN.search_results_limit", 5)


# =============================================================================
# Main - Debug Output
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("DEV DITO - ZENTRALE KONFIGURATION")
    print("=" * 70)
    
    print(f"\n[Pfade]")
    print(f"  REPO_ROOT:     {REPO_ROOT_DIR}")
    print(f"  CONFIG_DIR:    {CONFIG_DIR_PATH}")
    print(f"  SECRETS_DIR:   {SECRETS_DIR_PATH}")
    print(f"  OUTPUT_DIR:    {OUTPUT_DIR}")
    print(f"  DATA_DIR:      {DATA_DIR}")
    
    print(f"\n[Source Wiki]")
    print(f"  URL:           {SOURCE_WIKI_URL}")
    print(f"  BASE_URL:      {SOURCE_WIKI_BASE_URL}")
    print(f"  TOKEN:         {'*****' + SOURCE_WIKI_TOKEN[-4:] if SOURCE_WIKI_TOKEN else '(nicht gesetzt)'}")
    print(f"  CERT:          {SOURCE_WIKI_CERT}")
    
    print(f"\n[Services - Externe Verbindungen]")
    print(f"  MCP Server:    {MCP_SERVER_URL} (timeout: {MCP_SERVER_TIMEOUT}s)")
    print(f"  Qdrant:        {QDRANT_HOST}:{QDRANT_PORT} (collection: {QDRANT_COLLECTION})")
    print(f"  OpenAI:        {'*****' + OPENAI_TOKEN[-4:] if OPENAI_TOKEN else '(nicht gesetzt)'}")
    print(f"  Embedding:     {EMBEDDING_MODEL} ({EMBEDDING_DIMENSIONS}d)")
    
    print(f"\n[Pipeline]")
    print(f"  Fetcher:       timeout={FETCHER_TIMEOUT}s, retries={FETCHER_MAX_RETRIES}, delay={FETCHER_DELAY}s")
    print(f"  Embedder:      chunk={EMBEDDER_CHUNK_SIZE}, overlap={EMBEDDER_CHUNK_OVERLAP}")
    
    print(f"\n[Plugin]")
    print(f"  enabled:       {PLUGIN_ENABLED}")
    print(f"  panel:         {PLUGIN_PANEL_POSITION}")
    print(f"  search_limit:  {PLUGIN_SEARCH_LIMIT}")
    
    # Validierung
    valid, errors = validate_config()
    print(f"\n[Validierung]")
    if valid:
        print("  [OK] Alle Pflichtfelder gesetzt")
    else:
        print("  [ERROR] Fehler gefunden:")
        for err in errors:
            print(f"    - {err}")
    
    print("\n" + "=" * 70)
    print(f"settings.json: {SETTINGS_JSON_PATH}")
    print("=" * 70)
