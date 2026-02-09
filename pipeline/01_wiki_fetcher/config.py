"""
Centralized Configuration Loader (Fetcher-Modul)
================================================
Dieses Modul nutzt die ZENTRALE Config aus dem Repository-Root.
Constitution Article II-B: Alle Konfiguration zentral in config/env.yaml.

Das Modul versucht zuerst die zentrale Config zu laden.
Falls nicht verfuegbar, wird auf lokale Config zurueckgegriffen.

Usage:
    from config import (
        API_URL, HEADERS, CA_CERT_PATH, TIMEOUT, settings,
        FETCH_CONFIG, get_fetch_config
    )
"""
import os
import re
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, TypedDict
from dataclasses import dataclass, field

import yaml


# =============================================================================
# Path Resolution
# =============================================================================

# Script directory
SCRIPT_DIR = Path(__file__).parent.resolve()

# Repository Root (3 Ebenen hoch: fetcher -> pipeline -> dev_dito)
REPO_ROOT = SCRIPT_DIR.parent.parent

# Single config location: central config/env.yaml
CONFIG_DIR = REPO_ROOT / "config"
ENV_YAML_PATH = CONFIG_DIR / "env.yaml"

if not ENV_YAML_PATH.exists():
    raise FileNotFoundError(
        f"Central config not found: {ENV_YAML_PATH}\n"
        f"All configuration must live in the repository root config/env.yaml"
    )

print(f"[config] Config: {CONFIG_DIR}")

# PROJECT_ROOT fuer Abwaertskompatibilitaet
PROJECT_ROOT = SCRIPT_DIR.parent


# =============================================================================
# Default Configuration Values
# =============================================================================

DEFAULT_FETCH_CONFIG: Dict[str, Any] = {
    # Performance
    "timeout": 30,
    "max_retries": 3,
    "retry_delay": 2,
    "delay_between_requests": 0.05,
    "batch_progress_interval": 20,
    
    # Namespace scanning
    "max_namespace_depth": 3,
    "scan_all_sub_namespaces": True,
    
    # Content selection
    "content": {
        "fetch_html": True,
        "fetch_acl": True,
        "fetch_links": True,
        "fetch_history": True,
        "fetch_backlinks": True,
        "fetch_recent_changes": True,
    },
    
    # Media options
    "media": {
        "enabled": True,
        "max_file_size_mb": 50,
        "from_listings": True,
        "from_page_links": True,
        "include_types": [],
        "exclude_types": [],
    },
    
    # Filtering
    "filter": {
        "include_namespaces": [],
        "exclude_namespaces": [],
        "exclude_pages": [],
    },
    
    # Output
    "output": {
        "directory_pattern": "fetched_at_{timestamp}",
        "save_raw_responses": True,
        "generate_report": True,
        "report_format": "txt",
    },
    
    # Quality
    "quality": {
        "validate_internal_links": True,
        "report_broken_links": True,
        "verify_media_integrity": False,
    },
    
    # Cache (Fast-Mode)
    "cache": {
        "enabled": True,
        "archive_dirs": ["archived_fetch_tests"],
        "hash_algorithm": "sha256",
        "verify_on_copy": True,
    },
}


# =============================================================================
# FetchConfig Dataclass
# =============================================================================

@dataclass
class ContentConfig:
    """Content fetching options"""
    fetch_html: bool = True
    fetch_acl: bool = True
    fetch_links: bool = True
    fetch_history: bool = True
    fetch_backlinks: bool = True
    fetch_recent_changes: bool = True


@dataclass
class MediaConfig:
    """Media fetching options"""
    enabled: bool = True
    max_file_size_mb: int = 50
    from_listings: bool = True
    from_page_links: bool = True
    include_types: List[str] = field(default_factory=list)
    exclude_types: List[str] = field(default_factory=list)
    
    def should_include_file(self, filename: str) -> bool:
        """Check if a file should be included based on type filters"""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        
        if self.include_types and ext not in self.include_types:
            return False
        if ext in self.exclude_types:
            return False
        return True


@dataclass
class FilterConfig:
    """Namespace and page filtering options"""
    include_namespaces: List[str] = field(default_factory=list)
    exclude_namespaces: List[str] = field(default_factory=list)
    exclude_pages: List[str] = field(default_factory=list)
    
    def should_include_namespace(self, namespace: str) -> bool:
        """Check if a namespace should be included"""
        if self.include_namespaces and namespace not in self.include_namespaces:
            # Check if it's a sub-namespace of an included one
            included = any(namespace.startswith(ns + ":") for ns in self.include_namespaces)
            if not included and namespace not in self.include_namespaces:
                return False
        
        if namespace in self.exclude_namespaces:
            return False
        if any(namespace.startswith(ns + ":") for ns in self.exclude_namespaces):
            return False
        
        return True
    
    def should_include_page(self, page_id: str) -> bool:
        """Check if a page should be included"""
        if page_id in self.exclude_pages:
            return False
        
        # Check namespace of page
        if ":" in page_id:
            namespace = page_id.rsplit(":", 1)[0]
            return self.should_include_namespace(namespace)
        
        return True


@dataclass
class OutputConfig:
    """Output options"""
    directory_pattern: str = "fetched_at_{timestamp}"
    save_raw_responses: bool = True
    generate_report: bool = True
    report_format: str = "txt"
    recent_changes_count: int = 30
    deepest_pages_count: int = 20


@dataclass
class QualityConfig:
    """Quality and validation options"""
    validate_internal_links: bool = True
    report_broken_links: bool = True
    verify_media_integrity: bool = False


@dataclass
class CacheConfig:
    """Cache (Fast-Mode) options for media downloading"""
    enabled: bool = True
    archive_dirs: List[str] = field(default_factory=lambda: ["archived_fetch_tests"])
    hash_algorithm: str = "sha256"
    verify_on_copy: bool = True


@dataclass
class FetchConfig:
    """Complete fetch configuration"""
    # Performance
    timeout: int = 30
    max_retries: int = 3
    retry_delay: int = 2
    delay_between_requests: float = 0.05
    batch_progress_interval: int = 20
    
    # Namespace scanning
    max_namespace_depth: int = 5
    scan_all_sub_namespaces: bool = True
    use_recursive_listing: bool = True
    use_search_discovery: bool = True
    
    # Sub-configs
    content: ContentConfig = field(default_factory=ContentConfig)
    media: MediaConfig = field(default_factory=MediaConfig)
    filter: FilterConfig = field(default_factory=FilterConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)


# =============================================================================
# Placeholder Resolution
# =============================================================================

def resolve_placeholders(data: Dict[str, Any], context: Dict[str, str] | None = None) -> Dict[str, Any]:
    """
    Recursively resolve ${var} placeholders in a dictionary.
    """
    if context is None:
        context = {}
    
    def resolve_string(s: str) -> str:
        """Resolve placeholders in a single string"""
        pattern = r'\$\{([^}]+)\}'
        
        def replacer(match: re.Match[str]) -> str:
            var_name = match.group(1)
            if var_name in context:
                return context[var_name]
            return match.group(0)
        
        result = s
        for _ in range(5):
            new_result = re.sub(pattern, replacer, result)
            if new_result == result:
                break
            result = new_result
        return result
    
    def resolve_value(value: Any) -> Any:
        """Recursively resolve a value"""
        if isinstance(value, str):
            return resolve_string(value)
        elif isinstance(value, dict):
            return {k: resolve_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [resolve_value(item) for item in value]
        return value
    
    # First pass: build context from PATHS section
    if "PATHS" in data:
        for key, value in data["PATHS"].items():
            if isinstance(value, str):
                resolved = resolve_string(value)
                context[key] = resolved
                data["PATHS"][key] = resolved
    
    return resolve_value(data)


# =============================================================================
# Config Loading
# =============================================================================

def load_yaml_config(yaml_path: Path) -> Dict[str, Any]:
    """Load and parse YAML config file"""
    if not yaml_path.exists():
        raise FileNotFoundError(f"Config file not found: {yaml_path}")
    
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    if not isinstance(data, dict):
        raise ValueError(f"Invalid config format in {yaml_path}")
    
    return data


def load_token(token_path: Path) -> str:
    """Load API token from file"""
    if not token_path.exists():
        raise FileNotFoundError(f"Token file not found: {token_path}")
    
    with open(token_path, "r", encoding="utf-8") as f:
        token = f.read().strip()
    
    # Handle KEY=token format (but not JWT tokens which may end with =)
    if "=" in token and not token.startswith("eyJ"):
        parts = token.split("=", 1)
        if len(parts) == 2 and parts[0].isupper():
            token = parts[1]
    
    return token


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries, override takes precedence"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config() -> Dict[str, Any]:
    """
    Load complete configuration:
    1. Load env.yaml (zentral oder lokal)
    2. Resolve placeholders
    3. Load token from file
    4. Merge with defaults
    5. Normalize config keys (SOURCE_WIKI -> JSONRPC, PIPELINE.fetcher -> FETCH)
    """
    # Load YAML
    raw_config = load_yaml_config(ENV_YAML_PATH)
    
    # Resolve placeholders
    config = resolve_placeholders(raw_config)
    
    # =========================================================================
    # Config-Key Normalisierung (Zentrale Config -> Lokale Struktur)
    # =========================================================================
    # Zentrale Config nutzt SOURCE_WIKI, lokale nutzt JSONRPC
    if "SOURCE_WIKI" in config and "JSONRPC" not in config:
        config["JSONRPC"] = {
            "api": {
                "url": config["SOURCE_WIKI"].get("api", {}).get("url", ""),
                "base_url": config["SOURCE_WIKI"].get("api", {}).get("base_url", ""),
                "fetch_url": config["SOURCE_WIKI"].get("api", {}).get("fetch_url", ""),
                "feed_url": config["SOURCE_WIKI"].get("api", {}).get("feed_url", ""),
                "authentication": config["SOURCE_WIKI"].get("authentication", {}),
                "certificate": config["SOURCE_WIKI"].get("certificate", ""),
            }
        }
    
    # Zentrale Config nutzt PIPELINE.fetcher, lokale nutzt FETCH
    if "PIPELINE" in config and "fetcher" in config["PIPELINE"] and "FETCH" not in config:
        config["FETCH"] = config["PIPELINE"]["fetcher"]
    
    # =========================================================================
    # Merge FETCH section with defaults
    # =========================================================================
    if "FETCH" in config:
        config["FETCH"] = deep_merge(DEFAULT_FETCH_CONFIG, config["FETCH"])
    else:
        config["FETCH"] = DEFAULT_FETCH_CONFIG.copy()
    
    # =========================================================================
    # Load token from file
    # In Docker: TOKEN_PATH environment variable takes precedence
    # =========================================================================
    auth = config.get("JSONRPC", {}).get("api", {}).get("authentication", {})
    token_path_str = os.environ.get("TOKEN_PATH", auth.get("token_file", ""))
    
    if token_path_str:
        token_path = Path(token_path_str)
        if token_path.exists():
            try:
                token = load_token(token_path)
                config["JSONRPC"]["api"]["authentication"]["token"] = token
            except Exception as e:
                print(f"[config] Error loading token: {e}")
                config["JSONRPC"]["api"]["authentication"]["token"] = ""
        else:
            print(f"[config] Token file not found: {token_path}")
            config["JSONRPC"]["api"]["authentication"]["token"] = ""
    
    return config


# =============================================================================
# Build FetchConfig from Dict
# =============================================================================

def build_fetch_config(config_dict: Dict[str, Any]) -> FetchConfig:
    """Build FetchConfig dataclass from dictionary"""
    fetch = config_dict.get("FETCH", DEFAULT_FETCH_CONFIG)
    
    content_dict = fetch.get("content", {})
    content = ContentConfig(
        fetch_html=content_dict.get("fetch_html", True),
        fetch_acl=content_dict.get("fetch_acl", True),
        fetch_links=content_dict.get("fetch_links", True),
        fetch_history=content_dict.get("fetch_history", True),
        fetch_backlinks=content_dict.get("fetch_backlinks", True),
        fetch_recent_changes=content_dict.get("fetch_recent_changes", True),
    )
    
    media_dict = fetch.get("media", {})
    media = MediaConfig(
        enabled=media_dict.get("enabled", True),
        max_file_size_mb=media_dict.get("max_file_size_mb", 50),
        from_listings=media_dict.get("from_listings", True),
        from_page_links=media_dict.get("from_page_links", True),
        include_types=media_dict.get("include_types", []) or [],
        exclude_types=media_dict.get("exclude_types", []) or [],
    )
    
    filter_dict = fetch.get("filter", {})
    filter_cfg = FilterConfig(
        include_namespaces=filter_dict.get("include_namespaces", []) or [],
        exclude_namespaces=filter_dict.get("exclude_namespaces", []) or [],
        exclude_pages=filter_dict.get("exclude_pages", []) or [],
    )
    
    output_dict = fetch.get("output", {})
    output = OutputConfig(
        directory_pattern=output_dict.get("directory_pattern", "fetched_at_{timestamp}"),
        save_raw_responses=output_dict.get("save_raw_responses", True),
        generate_report=output_dict.get("generate_report", True),
        report_format=output_dict.get("report_format", "txt"),
        recent_changes_count=output_dict.get("recent_changes_count", 30),
        deepest_pages_count=output_dict.get("deepest_pages_count", 20),
    )
    
    quality_dict = fetch.get("quality", {})
    quality = QualityConfig(
        validate_internal_links=quality_dict.get("validate_internal_links", True),
        report_broken_links=quality_dict.get("report_broken_links", True),
        verify_media_integrity=quality_dict.get("verify_media_integrity", False),
    )
    
    cache_dict = fetch.get("cache", {})
    cache = CacheConfig(
        enabled=cache_dict.get("enabled", True),
        archive_dirs=cache_dict.get("archive_dirs", ["archived_fetch_tests"]) or ["archived_fetch_tests"],
        hash_algorithm=cache_dict.get("hash_algorithm", "sha256"),
        verify_on_copy=cache_dict.get("verify_on_copy", True),
    )
    
    return FetchConfig(
        timeout=fetch.get("timeout", 30),
        max_retries=fetch.get("max_retries", 3),
        retry_delay=fetch.get("retry_delay", 2),
        delay_between_requests=fetch.get("delay_between_requests", 0.05),
        batch_progress_interval=fetch.get("batch_progress_interval", 20),
        max_namespace_depth=fetch.get("max_namespace_depth", 5),
        scan_all_sub_namespaces=fetch.get("scan_all_sub_namespaces", True),
        use_recursive_listing=fetch.get("use_recursive_listing", True),
        use_search_discovery=fetch.get("use_search_discovery", True),
        content=content,
        media=media,
        filter=filter_cfg,
        output=output,
        quality=quality,
        cache=cache,
    )


# =============================================================================
# Load Configuration
# =============================================================================

# Load config at module import
settings = load_config()

# Build typed FetchConfig
FETCH_CONFIG = build_fetch_config(settings)


# =============================================================================
# Helper Functions
# =============================================================================

def get_fetch_config() -> FetchConfig:
    """Get the typed fetch configuration"""
    return FETCH_CONFIG


def get_setting(path: str, default: Any = None) -> Any:
    """
    Get a nested setting by dot-separated path.
    
    Example:
        get_setting("FETCH.media.max_file_size_mb", 50)
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


# =============================================================================
# Backward-Compatible Exports (for existing scripts)
# =============================================================================

# API Configuration
_jsonrpc_api: Dict[str, Any] = settings.get("JSONRPC", {}).get("api", {})
API_URL: str = str(_jsonrpc_api.get("url", ""))
API_BASE_URL: str = str(_jsonrpc_api.get("base_url", ""))
API_FETCH_URL: str = str(_jsonrpc_api.get("fetch_url", ""))
API_FEED_URL: str = str(_jsonrpc_api.get("feed_url", ""))

# Authentication
API_TOKEN: str = str(_jsonrpc_api.get("authentication", {}).get("token", ""))

# SSL Certificate
# In Docker: SSL_CERT_PATH environment variable takes precedence
_cert_from_settings: str = str(_jsonrpc_api.get("certificate", ""))
CA_CERT_PATH: str = os.environ.get("SSL_CERT_PATH", _cert_from_settings)

# Request Headers
HEADERS: Dict[str, str] = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_TOKEN}"
}

# Output Directory
# In Docker: Environment variable OUTPUT_DIR takes precedence
# This allows container mounts to override Windows paths from env.yaml
_output_from_settings: str = str(settings.get("PATHS", {}).get("output_dir", str(PROJECT_ROOT / "content_output")))
OUTPUT_BASE_DIR: str = os.environ.get("OUTPUT_DIR", _output_from_settings)

# Fetch Configuration (flat exports for backward compatibility)
TIMEOUT: int = FETCH_CONFIG.timeout
MAX_RETRIES: int = FETCH_CONFIG.max_retries
RETRY_DELAY: int = FETCH_CONFIG.retry_delay
FEED_ENTRIES: int = int(settings.get("FETCH", {}).get("feed_entries", 100))
REQUEST_DELAY: float = FETCH_CONFIG.delay_between_requests

# New exports
MAX_NAMESPACE_DEPTH: int = FETCH_CONFIG.max_namespace_depth
BATCH_PROGRESS_INTERVAL: int = FETCH_CONFIG.batch_progress_interval

# Testing Configuration
_testing: Dict[str, Any] = settings.get("TESTING", {})
TEST_PAGE: str = str(_testing.get("default_page", "start"))
TEST_NAMESPACE: str = str(_testing.get("default_namespace", ""))
TEST_MEDIA: str = str(_testing.get("default_media", ""))


# =============================================================================
# Validation
# =============================================================================

def validate_config() -> bool:
    """Validate that essential config values are present"""
    errors = []
    
    if not API_URL:
        errors.append("JSONRPC.api.url is missing")
    if not API_TOKEN:
        errors.append("API token is missing or could not be loaded")
    if not CA_CERT_PATH or not Path(CA_CERT_PATH).exists():
        errors.append(f"SSL certificate not found: {CA_CERT_PATH}")
    
    if errors:
        print("[config] Validation errors:")
        for err in errors:
            print(f"  - {err}")
        return False
    
    return True


# Validate on import (warning only)
if not validate_config():
    print("[config] Warning: Some configuration values are missing or invalid")


# =============================================================================
# Debug Info
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("CONFIGURATION DEBUG")
    print("=" * 60)
    print(f"\nPaths:")
    print(f"  PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"  CONFIG_DIR:   {CONFIG_DIR}")
    print(f"  OUTPUT_DIR:   {OUTPUT_BASE_DIR}")
    print(f"\nAPI:")
    print(f"  URL:          {API_URL}")
    print(f"  BASE_URL:     {API_BASE_URL}")
    print(f"  TOKEN:        {API_TOKEN[:20]}..." if API_TOKEN else "  TOKEN: (missing)")
    print(f"  CA_CERT:      {CA_CERT_PATH}")
    print(f"\nFetch Settings:")
    print(f"  TIMEOUT:               {TIMEOUT}s")
    print(f"  MAX_RETRIES:           {MAX_RETRIES}")
    print(f"  RETRY_DELAY:           {RETRY_DELAY}s")
    print(f"  REQUEST_DELAY:         {REQUEST_DELAY}s")
    print(f"  BATCH_PROGRESS:        {BATCH_PROGRESS_INTERVAL}")
    print(f"  MAX_NAMESPACE_DEPTH:   {MAX_NAMESPACE_DEPTH}")
    print(f"\nContent Options:")
    print(f"  fetch_html:            {FETCH_CONFIG.content.fetch_html}")
    print(f"  fetch_acl:             {FETCH_CONFIG.content.fetch_acl}")
    print(f"  fetch_links:           {FETCH_CONFIG.content.fetch_links}")
    print(f"  fetch_history:         {FETCH_CONFIG.content.fetch_history}")
    print(f"  fetch_backlinks:       {FETCH_CONFIG.content.fetch_backlinks}")
    print(f"  fetch_recent_changes:  {FETCH_CONFIG.content.fetch_recent_changes}")
    print(f"\nMedia Options:")
    print(f"  enabled:               {FETCH_CONFIG.media.enabled}")
    print(f"  max_file_size_mb:      {FETCH_CONFIG.media.max_file_size_mb}")
    print(f"  from_listings:         {FETCH_CONFIG.media.from_listings}")
    print(f"  from_page_links:       {FETCH_CONFIG.media.from_page_links}")
    print(f"  include_types:         {FETCH_CONFIG.media.include_types or '(all)'}")
    print(f"  exclude_types:         {FETCH_CONFIG.media.exclude_types or '(none)'}")
    print(f"\nFilter Options:")
    print(f"  include_namespaces:    {FETCH_CONFIG.filter.include_namespaces or '(all)'}")
    print(f"  exclude_namespaces:    {FETCH_CONFIG.filter.exclude_namespaces or '(none)'}")
    print(f"  exclude_pages:         {FETCH_CONFIG.filter.exclude_pages or '(none)'}")
    print(f"\nQuality Options:")
    print(f"  validate_links:        {FETCH_CONFIG.quality.validate_internal_links}")
    print(f"  report_broken:         {FETCH_CONFIG.quality.report_broken_links}")
    print(f"  verify_media:          {FETCH_CONFIG.quality.verify_media_integrity}")
    print(f"\nCache Options (Fast-Mode):")
    print(f"  enabled:               {FETCH_CONFIG.cache.enabled}")
    print(f"  archive_dirs:          {FETCH_CONFIG.cache.archive_dirs}")
    print(f"  hash_algorithm:        {FETCH_CONFIG.cache.hash_algorithm}")
    print(f"  verify_on_copy:        {FETCH_CONFIG.cache.verify_on_copy}")
    print(f"\nTesting:")
    print(f"  TEST_PAGE:             {TEST_PAGE}")
    print(f"  TEST_NS:               {TEST_NAMESPACE}")
    print(f"\nValidation: {'OK' if validate_config() else 'FAILED'}")
    print("=" * 60)
