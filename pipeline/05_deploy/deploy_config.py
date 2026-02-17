"""
Shared deploy configuration for 05_deploy scripts.
Loads config.yaml (same dir); used by transfer_to_pi.py and verify_transfer.py.
"""

from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_FILE = SCRIPT_DIR / "config.yaml"

# Fallback when config.yaml is missing
DEFAULT_CONFIG = {
    "ssh_host": "raspberry-pi.local",
    "ssh_user": "pi",
    "ssh_port": 22,
    "remote_embeddings_dir": "/home/pi/qdrant/data/embeddings/",
    "remote_embeddings_file": "/home/pi/qdrant/data/embeddings/embedded_chunks.jsonl",
    "qdrant_host": "localhost",
    "qdrant_port": 6333,
    "collection_name": "wiki_embeddings",
}


def load_config() -> dict | None:
    """Load config.yaml from script directory. Returns None if missing or invalid."""
    if not yaml or not CONFIG_FILE.exists():
        return None
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def get_defaults() -> dict:
    """Merge config.yaml with DEFAULT_CONFIG; config takes precedence."""
    out = dict(DEFAULT_CONFIG)
    cfg = load_config()
    if not cfg:
        return out
    if "ssh" in cfg:
        out["ssh_host"] = cfg["ssh"].get("host", out["ssh_host"])
        out["ssh_user"] = cfg["ssh"].get("user", out["ssh_user"])
        out["ssh_port"] = cfg["ssh"].get("port", out["ssh_port"])
    if "remote" in cfg and "embeddings_dir" in cfg["remote"]:
        d = cfg["remote"]["embeddings_dir"].rstrip("/")
        out["remote_embeddings_dir"] = d + "/"
        out["remote_embeddings_file"] = d + "/embedded_chunks.jsonl"
    if "qdrant" in cfg:
        out["qdrant_host"] = cfg["qdrant"].get("host", out["qdrant_host"])
        out["qdrant_port"] = cfg["qdrant"].get("port", out["qdrant_port"])
        out["collection_name"] = cfg["qdrant"].get("collection_name", out["collection_name"])
    return out


def find_latest_embeddings_file(base_dir: Path) -> Path | None:
    """
    Find embedded_chunks.jsonl in the latest embedded_at_YYYYMMDD_HHMMSS directory.
    Returns path to file or None if none found.
    """
    if not base_dir.is_dir():
        return None
    run_dirs = sorted(
        (p for p in base_dir.iterdir() if p.is_dir() and p.name.startswith("embedded_at_")),
        key=lambda p: p.name,
        reverse=True,
    )
    for run_dir in run_dirs:
        candidate = run_dir / "embedded_chunks.jsonl"
        if candidate.is_file():
            return candidate
    return None


def get_local_embeddings_dir() -> Path:
    """Resolve local embeddings base dir from config (for finding latest run)."""
    cfg = load_config()
    base = (SCRIPT_DIR / "../../data/embeddings").resolve()
    if cfg and "local" in cfg and "embeddings_dir" in cfg["local"]:
        base = (SCRIPT_DIR / cfg["local"]["embeddings_dir"]).resolve()
    return base
