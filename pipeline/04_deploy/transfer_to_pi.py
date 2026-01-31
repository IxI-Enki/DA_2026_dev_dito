#!/usr/bin/env python3
"""
Transfer Embeddings to Raspberry Pi via SSH/SCP
===============================================
Transfers the embedded_chunks.jsonl file to a remote Raspberry Pi
where Qdrant is running.

Usage:
    python transfer_to_pi.py                    # Use default config
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
from datetime import datetime

# Default configuration
DEFAULT_CONFIG = {
    "ssh_host": "raspberry-pi.local",
    "ssh_user": "pi",
    "ssh_port": 22,
    "remote_path": "/home/pi/qdrant/data/embeddings/",
    "local_file": "../03_embeddings_creator/output/embedded_chunks.jsonl",
}


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


def test_ssh_connection(host: str, user: str, port: int, key_path: str = None) -> bool:
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
    key_path: str = None,
    dry_run: bool = False
) -> bool:
    """Transfer file via SCP."""
    
    if not local_path.exists():
        print(f"[ERROR] Local file not found: {local_path}")
        return False
    
    file_size = get_file_size(local_path)
    file_hash = get_file_hash(local_path)
    
    print(f"\n{'='*60}")
    print("FILE TRANSFER")
    print(f"{'='*60}")
    print(f"  Local:  {local_path}")
    print(f"  Remote: {remote_user}@{remote_host}:{remote_path}")
    print(f"  Size:   {file_size}")
    print(f"  MD5:    {file_hash}")
    print(f"{'='*60}\n")
    
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
            print(f"[OK] Transfer completed in {elapsed:.1f}s")
            
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
            print(f"[ERROR] Transfer failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Transfer error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Transfer embeddings to Raspberry Pi via SSH/SCP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--host", "-H",
        default=DEFAULT_CONFIG["ssh_host"],
        help=f"SSH host (default: {DEFAULT_CONFIG['ssh_host']})"
    )
    parser.add_argument(
        "--user", "-u",
        default=DEFAULT_CONFIG["ssh_user"],
        help=f"SSH user (default: {DEFAULT_CONFIG['ssh_user']})"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=DEFAULT_CONFIG["ssh_port"],
        help=f"SSH port (default: {DEFAULT_CONFIG['ssh_port']})"
    )
    parser.add_argument(
        "--remote-path", "-r",
        default=DEFAULT_CONFIG["remote_path"],
        help=f"Remote path (default: {DEFAULT_CONFIG['remote_path']})"
    )
    parser.add_argument(
        "--local-file", "-f",
        default=DEFAULT_CONFIG["local_file"],
        help=f"Local file to transfer (default: {DEFAULT_CONFIG['local_file']})"
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
    
    print("="*60)
    print("DEV DITO - RASPBERRY PI TRANSFER")
    print("="*60)
    
    # Resolve local file path
    script_dir = Path(__file__).parent
    local_path = Path(args.local_file)
    if not local_path.is_absolute():
        local_path = (script_dir / local_path).resolve()
    
    # Test SSH connection first
    if not args.skip_test and not args.dry_run:
        if not test_ssh_connection(args.host, args.user, args.port, args.key):
            print("\n[ERROR] Cannot establish SSH connection. Aborting.")
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
        print("\n[OK] Transfer completed successfully!")
        if not args.dry_run:
            print("\nNext steps:")
            print(f"  1. SSH into Pi: ssh {args.user}@{args.host}")
            print("  2. Run Qdrant init: docker-compose up qdrant_init")
            print("  3. Or use: python verify_transfer.py --host " + args.host)
    else:
        print("\n[ERROR] Transfer failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
