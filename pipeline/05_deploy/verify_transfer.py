#!/usr/bin/env python3
"""Verify Transfer to Raspberry Pi.

Verifies that the embeddings file was correctly transferred
by comparing MD5 checksums. Reads config from config.yaml (same dir);
Qdrant URL and paths come from config when present.

Usage:
    python verify_transfer.py                    # Use config.yaml
    python verify_transfer.py --host 192.168.1.100
    python verify_transfer.py --check-qdrant     # Also check Qdrant collection
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

# Shared CLI (colored banners, fixed-width separators)
_deploy_dir = Path(__file__).resolve().parent
if str(_deploy_dir.parent / "shared") not in sys.path:
    sys.path.insert(0, str(_deploy_dir.parent / "shared"))
from cli_utils import (
    add_no_color_arg,
    apply_color_from_args,
    register_sigint,
    style,
)
from deploy_config import (
    SCRIPT_DIR,
    find_latest_embeddings_file,
    get_defaults,
    get_local_embeddings_dir,
)

SEP_LEN = 60


def get_local_hash(filepath: Path) -> str | None:
    """Calculate MD5 hash of local file. Returns None if file does not exist."""
    if not filepath.exists():
        return None

    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_remote_hash(
    host: str, user: str, port: int, remote_path: str, key_path: str | None = None
) -> str | None:
    """Get MD5 hash of remote file via SSH. Returns None on failure."""
    cmd = ["ssh"]
    if key_path:
        cmd.extend(["-i", key_path])
    cmd.extend(["-p", str(port), f"{user}@{host}", f"md5sum {remote_path}"])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            # md5sum output format: "hash  filename"
            return result.stdout.strip().split()[0]
        print(style(f"[ERROR] Failed to get remote hash: {result.stderr}", "red"))
        return None
    except Exception as e:
        print(style(f"[ERROR] SSH error: {e}", "red"))
        return None


def get_remote_file_info(
    host: str, user: str, port: int, remote_path: str, key_path: str | None = None
) -> dict:
    """Get file info from remote host."""
    cmd = ["ssh"]
    if key_path:
        cmd.extend(["-i", key_path])
    cmd.extend(
        [
            "-p",
            str(port),
            f"{user}@{host}",
            f"ls -la {remote_path} && wc -l {remote_path}",
        ]
    )

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            ls_parts = lines[0].split()
            size = ls_parts[4] if len(ls_parts) > 4 else "unknown"
            line_count = lines[1].split()[0] if len(lines) > 1 else "unknown"
            return {"size": size, "lines": line_count, "exists": True}
        return {"exists": False, "error": result.stderr}
    except Exception as e:
        return {"exists": False, "error": str(e)}


def verify_qdrant_collection(
    ssh_host: str,
    ssh_user: str,
    ssh_port: int,
    qdrant_host: str,
    qdrant_port: int,
    collection_name: str,
    key_path: str | None = None,
) -> dict:
    """Check Qdrant collection status on remote host (via SSH + curl on Pi)."""
    url = f"http://{qdrant_host}:{qdrant_port}/collections/{collection_name}"
    curl_cmd = f"curl -s {url} || echo 'QDRANT_NOT_RUNNING'"
    cmd = ["ssh"]
    if key_path:
        cmd.extend(["-i", key_path])
    cmd.extend(["-p", str(ssh_port), f"{ssh_user}@{ssh_host}", curl_cmd])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if "QDRANT_NOT_RUNNING" in result.stdout:
            return {"status": "not_running", "error": "Qdrant not accessible"}
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                if "result" in data:
                    return {
                        "status": "ok",
                        "points_count": data["result"].get("points_count", 0),
                        "vectors_count": data["result"].get("vectors_count", 0),
                    }
            except json.JSONDecodeError:
                pass
            return {"status": "ok", "raw": result.stdout}
        return {"status": "error", "error": result.stderr}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def main() -> int:
    """CLI entry point for transfer verification."""
    defaults = get_defaults()
    parser = argparse.ArgumentParser(
        description="Verify embeddings transfer to Raspberry Pi",
    )
    parser.add_argument("--host", "-H", default=defaults["ssh_host"])
    parser.add_argument("--user", "-u", default=defaults["ssh_user"])
    parser.add_argument("--port", "-p", type=int, default=defaults["ssh_port"])
    parser.add_argument(
        "--remote-path", "-r", default=defaults["remote_embeddings_file"]
    )
    parser.add_argument(
        "--local-file",
        "-f",
        default=None,
        metavar="PATH",
        help="Local JSONL (default: latest from config)",
    )
    parser.add_argument("--key", "-k", default=os.environ.get("SSH_KEY_PATH"))
    parser.add_argument(
        "--check-qdrant",
        action="store_true",
        help="Also check Qdrant collection on Pi",
    )
    add_no_color_arg(parser)

    args = parser.parse_args()
    apply_color_from_args(args)
    register_sigint("verify_transfer")

    sep = "=" * SEP_LEN
    print(style(sep, "cyan"))
    print(style("  DEV DITO - TRANSFER VERIFICATION", "bold", "bright_cyan"))
    print(style(sep, "cyan"))

    # Resolve local file path: explicit or latest from config
    if args.local_file is not None:
        local_path = Path(args.local_file)
        if not local_path.is_absolute():
            local_path = (SCRIPT_DIR / local_path).resolve()
    else:
        base_dir = get_local_embeddings_dir()
        latest = find_latest_embeddings_file(base_dir)
        if latest is None:
            print(style("[ERROR] No local embeddings file found.", "red"))
            print(f"  Looked for: {base_dir}/embedded_at_*/embedded_chunks.jsonl")
            print("  Use --local-file PATH to specify.")
            return 1
        local_path = latest
        print(style("[INFO] Using latest local file: ", "cyan") + str(local_path))

    # Get local hash
    print("\n[1/3] Calculating local file hash...")
    print(f"      File: {local_path}")
    local_hash = get_local_hash(local_path)
    if local_hash:
        print(f"      MD5:  {local_hash}")
    else:
        print(style("      [ERROR] Local file not found!", "red"))
        return 1

    # Get remote hash
    print("\n[2/3] Getting remote file hash...")
    print(f"      Host: {args.user}@{args.host}:{args.port}")
    print(f"      Path: {args.remote_path}")
    remote_hash = get_remote_hash(
        args.host, args.user, args.port, args.remote_path, args.key
    )
    if remote_hash:
        print(f"      MD5:  {remote_hash}")
    else:
        print(style("      [ERROR] Could not get remote hash!", "red"))
        return 1

    # Compare hashes
    print("\n[3/3] Comparing checksums...")
    if local_hash == remote_hash:
        print(style("      [OK] Checksums match! Transfer verified.", "bright_green"))

        remote_info = get_remote_file_info(
            args.host, args.user, args.port, args.remote_path, args.key
        )
        if remote_info.get("exists"):
            print("\n      Remote file info:")
            print(f"        Size:  {remote_info.get('size', 'unknown')} bytes")
            print(f"        Lines: {remote_info.get('lines', 'unknown')}")
    else:
        print(style("      [ERROR] Checksums DO NOT match!", "red"))
        print(f"        Local:  {local_hash}")
        print(f"        Remote: {remote_hash}")
        return 1

    # Optional: Check Qdrant collection on Pi
    if args.check_qdrant:
        print("\n[EXTRA] Checking Qdrant collection...")
        qdrant_status = verify_qdrant_collection(
            ssh_host=args.host,
            ssh_user=args.user,
            ssh_port=args.port,
            qdrant_host=defaults["qdrant_host"],
            qdrant_port=defaults["qdrant_port"],
            collection_name=defaults["collection_name"],
            key_path=args.key,
        )
        if qdrant_status["status"] == "ok":
            print(
                style("        [OK] Qdrant collection accessible", "bright_green")
            )
            if "points_count" in qdrant_status:
                print(f"        Points: {qdrant_status['points_count']}")
        else:
            print(
                style(
                    f"        [WARN] Qdrant: {qdrant_status.get('error', 'unknown error')}",
                    "yellow",
                )
            )

    print("")
    print(style(sep, "green"))
    print(style("  VERIFICATION COMPLETE", "bold", "bright_green"))
    print(style(sep, "green"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
