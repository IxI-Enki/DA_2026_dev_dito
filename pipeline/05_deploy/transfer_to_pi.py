#!/usr/bin/env python3
"""
Transfer Embeddings to Raspberry Pi via SSH/SCP
===============================================
Transfers the embedded_chunks.jsonl file to a remote Raspberry Pi
where Qdrant is running. Reads config from config.yaml (same dir);
resolves latest Stage 04 output: <embeddings_dir>/embedded_at_*/embedded_chunks.jsonl.

Usage:
    python transfer_to_pi.py                    # Use config.yaml, latest embeddings
    python transfer_to_pi.py --local-file path  # Explicit JSONL path
    python transfer_to_pi.py --host 192.168.1.100
    python transfer_to_pi.py --dry-run          # Show what would be done

Environment:
    SSH_KEY_PATH: Path to SSH private key (optional)
"""

import os
import sys
import argparse
import hashlib
import subprocess
from pathlib import Path
from typing import Optional
from datetime import datetime

# Shared CLI (colored banners, fixed-width separators)
_deploy_dir = Path(__file__).resolve().parent
if str(_deploy_dir.parent / "shared") not in sys.path:
    sys.path.insert(0, str(_deploy_dir.parent / "shared"))
from cli_utils import enable_windows_ansi, style

from deploy_config import (
    SCRIPT_DIR,
    get_defaults,
    load_config,
    find_latest_embeddings_file,
    get_local_embeddings_dir,
)

SEP_LEN = 60


def get_file_hash(filepath: Path) -> str:
    """Calculate MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_file_size(filepath: Path) -> str:
    """Get human-readable file size."""
    size = filepath.stat().st_size
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


def test_ssh_connection(host: str, user: str, port: int, key_path: Optional[str] = None) -> bool:
    """Test SSH connection to remote host."""
    print(f"[INFO] Testing SSH connection to {user}@{host}:{port}...")
    
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]
    if key_path:
        cmd.extend(["-i", key_path])
    cmd.extend(["-p", str(port), f"{user}@{host}", "echo 'Connection OK'"])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            print("[OK] SSH connection successful")
            return True
        else:
            print(f"[ERROR] SSH connection failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("[ERROR] SSH connection timed out")
        return False
    except Exception as e:
        print(f"[ERROR] SSH connection error: {e}")
        return False


def transfer_file(
    local_path: Path,
    remote_host: str,
    remote_user: str,
    remote_path: str,
    port: int = 22,
    key_path: Optional[str] = None,
    dry_run: bool = False
) -> bool:
    """Transfer file via SCP."""
    
    if not local_path.exists():
        print(style(f"[ERROR] Local file not found: {local_path}", "red"))
        return False
    
    file_size = get_file_size(local_path)
    file_hash = get_file_hash(local_path)
    
    sep = "=" * SEP_LEN
    print(f"\n{style(sep, 'cyan')}")
    print(style("  FILE TRANSFER", "bold", "bright_cyan"))
    print(style(sep, "cyan"))
    print(f"  Local:  {local_path}")
    print(f"  Remote: {remote_user}@{remote_host}:{remote_path}")
    print(f"  Size:   {file_size}")
    print(f"  MD5:    {file_hash}")
    print(f"{style(sep, 'cyan')}\n")
    
    if dry_run:
        print("[DRY-RUN] Would transfer file (no actual transfer)")
        return True
    
    # Build SCP command
    cmd = ["scp", "-o", "StrictHostKeyChecking=accept-new"]
    if key_path:
        cmd.extend(["-i", key_path])
    cmd.extend(["-P", str(port)])
    cmd.append(str(local_path))
    cmd.append(f"{remote_user}@{remote_host}:{remote_path}")
    
    print("[INFO] Starting transfer...")
    start_time = datetime.now()
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            print(style(f"[OK] Transfer completed in {elapsed:.1f}s", "bright_green"))
            
            # Save transfer log
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "local_file": str(local_path),
                "remote_host": remote_host,
                "remote_path": remote_path,
                "file_size": file_size,
                "md5_hash": file_hash,
                "duration_seconds": elapsed,
                "status": "success"
            }
            print(f"\n[INFO] Transfer details:")
            for key, value in log_entry.items():
                print(f"  {key}: {value}")
            
            return True
        else:
            print(style(f"[ERROR] Transfer failed: {result.stderr}", "red"))
            return False

    except Exception as e:
        print(style(f"[ERROR] Transfer error: {e}", "red"))
        return False


def main():
    enable_windows_ansi()
    defaults = get_defaults()
    parser = argparse.ArgumentParser(
        description="Transfer embeddings to Raspberry Pi via SSH/SCP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--host", "-H",
        default=defaults["ssh_host"],
        help=f"SSH host (default from config or {defaults['ssh_host']})",
    )
    parser.add_argument(
        "--user", "-u",
        default=defaults["ssh_user"],
        help=f"SSH user (default from config or {defaults['ssh_user']})",
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=defaults["ssh_port"],
        help=f"SSH port (default from config or {defaults['ssh_port']})",
    )
    parser.add_argument(
        "--remote-path", "-r",
        default=defaults["remote_embeddings_dir"],
        help="Remote directory on Pi (default from config.yaml)",
    )
    parser.add_argument(
        "--local-file", "-f",
        default=None,
        metavar="PATH",
        help="Embeddings JSONL file (default: latest from config local.embeddings_dir)",
    )
    parser.add_argument(
        "--key", "-k",
        default=os.environ.get("SSH_KEY_PATH"),
        help="Path to SSH private key (default: SSH_KEY_PATH env var)"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be done without actually transferring"
    )
    parser.add_argument(
        "--skip-test",
        action="store_true",
        help="Skip SSH connection test"
    )
    
    args = parser.parse_args()

    sep = "=" * SEP_LEN
    print(style(sep, "cyan"))
    print(style("  DEV DITO - RASPBERRY PI TRANSFER", "bold", "bright_cyan"))
    print(style(sep, "cyan"))

    # Resolve local file path: explicit --local-file or latest from config
    if args.local_file is not None:
        local_path = Path(args.local_file)
        if not local_path.is_absolute():
            local_path = (SCRIPT_DIR / local_path).resolve()
    else:
        base_dir = get_local_embeddings_dir()
        latest = find_latest_embeddings_file(base_dir)
        if latest is None:
            print(style("[ERROR] No embeddings file found.", "red"))
            print(f"  Looked for: {base_dir}/embedded_at_*/embedded_chunks.jsonl")
            print("  Use --local-file PATH to specify the JSONL file.")
            sys.exit(1)
        local_path = latest
        print(style("[INFO] Using latest embeddings: ", "cyan") + str(local_path))
    
    # Test SSH connection first
    if not args.skip_test and not args.dry_run:
        if not test_ssh_connection(args.host, args.user, args.port, args.key):
            print(style("\n[ERROR] Cannot establish SSH connection. Aborting.", "red"))
            sys.exit(1)
    
    # Transfer file
    success = transfer_file(
        local_path=local_path,
        remote_host=args.host,
        remote_user=args.user,
        remote_path=args.remote_path,
        port=args.port,
        key_path=args.key,
        dry_run=args.dry_run
    )
    
    if success:
        print("")
        print(style(sep, "green"))
        print(style("  TRANSFER COMPLETE", "bold", "bright_green"))
        print(style(sep, "green"))
        print(style("\n[OK] Transfer completed successfully!", "bright_green"))
        if not args.dry_run:
            print("\nNext steps:")
            print(f"  1. SSH into Pi: ssh {args.user}@{args.host}")
            print("  2. Run Qdrant init: docker-compose up qdrant_init")
            print("  3. Or use: python verify_transfer.py --host " + args.host)
    else:
        print(style("\n[ERROR] Transfer failed!", "red"))
        sys.exit(1)


if __name__ == "__main__":
    main()
