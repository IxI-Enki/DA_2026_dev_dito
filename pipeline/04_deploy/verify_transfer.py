#!/usr/bin/env python3
"""
Verify Transfer to Raspberry Pi
================================
Verifies that the embeddings file was correctly transferred
by comparing MD5 checksums.

Usage:
    python verify_transfer.py                    # Use default config
    python verify_transfer.py --host 192.168.1.100
"""

import os
import sys
import argparse
import hashlib
import subprocess
from pathlib import Path
from typing import Optional

# Default configuration (same as transfer_to_pi.py)
DEFAULT_CONFIG = {
    "ssh_host": "raspberry-pi.local",
    "ssh_user": "pi",
    "ssh_port": 22,
    "remote_path": "/home/pi/qdrant/data/embeddings/embedded_chunks.jsonl",
    "local_file": "../03_embeddings_creator/output/embedded_chunks.jsonl",
}


def get_local_hash(filepath: Path) -> Optional[str]:
    """Calculate MD5 hash of local file. Returns None if file does not exist."""
    if not filepath.exists():
        return None
    
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_remote_hash(host: str, user: str, port: int, remote_path: str, key_path: Optional[str] = None) -> Optional[str]:
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
        else:
            print(f"[ERROR] Failed to get remote hash: {result.stderr}")
            return None
    except Exception as e:
        print(f"[ERROR] SSH error: {e}")
        return None


def get_remote_file_info(host: str, user: str, port: int, remote_path: str, key_path: Optional[str] = None) -> dict:
    """Get file info from remote host."""
    cmd = ["ssh"]
    if key_path:
        cmd.extend(["-i", key_path])
    cmd.extend(["-p", str(port), f"{user}@{host}", f"ls -la {remote_path} && wc -l {remote_path}"])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            # Parse ls output for size
            ls_parts = lines[0].split()
            size = ls_parts[4] if len(ls_parts) > 4 else "unknown"
            # Parse wc output for line count
            line_count = lines[1].split()[0] if len(lines) > 1 else "unknown"
            return {"size": size, "lines": line_count, "exists": True}
        else:
            return {"exists": False, "error": result.stderr}
    except Exception as e:
        return {"exists": False, "error": str(e)}


def verify_qdrant_collection(host: str, user: str, port: int, key_path: Optional[str] = None) -> dict:
    """Check Qdrant collection status on remote host."""
    cmd = ["ssh"]
    if key_path:
        cmd.extend(["-i", key_path])
    cmd.extend([
        "-p", str(port), 
        f"{user}@{host}", 
        "curl -s http://localhost:18334/collections/wiki_embeddings || echo 'QDRANT_NOT_RUNNING'"
    ])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if "QDRANT_NOT_RUNNING" in result.stdout:
            return {"status": "not_running", "error": "Qdrant not accessible"}
        elif result.returncode == 0:
            import json
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
        else:
            return {"status": "error", "error": result.stderr}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def main():
    parser = argparse.ArgumentParser(
        description="Verify embeddings transfer to Raspberry Pi",
    )
    
    parser.add_argument("--host", "-H", default=DEFAULT_CONFIG["ssh_host"])
    parser.add_argument("--user", "-u", default=DEFAULT_CONFIG["ssh_user"])
    parser.add_argument("--port", "-p", type=int, default=DEFAULT_CONFIG["ssh_port"])
    parser.add_argument("--remote-path", "-r", default=DEFAULT_CONFIG["remote_path"])
    parser.add_argument("--local-file", "-f", default=DEFAULT_CONFIG["local_file"])
    parser.add_argument("--key", "-k", default=os.environ.get("SSH_KEY_PATH"))
    parser.add_argument("--check-qdrant", action="store_true", help="Also check Qdrant collection")
    
    args = parser.parse_args()
    
    print("="*60)
    print("DEV DITO - TRANSFER VERIFICATION")
    print("="*60)
    
    # Resolve local file path
    script_dir = Path(__file__).parent
    local_path = Path(args.local_file)
    if not local_path.is_absolute():
        local_path = (script_dir / local_path).resolve()
    
    # Get local hash
    print(f"\n[1/3] Calculating local file hash...")
    print(f"      File: {local_path}")
    local_hash = get_local_hash(local_path)
    if local_hash:
        print(f"      MD5:  {local_hash}")
    else:
        print(f"      [ERROR] Local file not found!")
        sys.exit(1)
    
    # Get remote hash
    print(f"\n[2/3] Getting remote file hash...")
    print(f"      Host: {args.user}@{args.host}:{args.port}")
    print(f"      Path: {args.remote_path}")
    remote_hash = get_remote_hash(args.host, args.user, args.port, args.remote_path, args.key)
    if remote_hash:
        print(f"      MD5:  {remote_hash}")
    else:
        print(f"      [ERROR] Could not get remote hash!")
        sys.exit(1)
    
    # Compare hashes
    print(f"\n[3/3] Comparing checksums...")
    if local_hash == remote_hash:
        print("      [OK] Checksums match! Transfer verified.")
        
        # Get additional remote file info
        remote_info = get_remote_file_info(args.host, args.user, args.port, args.remote_path, args.key)
        if remote_info.get("exists"):
            print(f"\n      Remote file info:")
            print(f"        Size:  {remote_info.get('size', 'unknown')} bytes")
            print(f"        Lines: {remote_info.get('lines', 'unknown')}")
    else:
        print("      [ERROR] Checksums DO NOT match!")
        print(f"        Local:  {local_hash}")
        print(f"        Remote: {remote_hash}")
        sys.exit(1)
    
    # Optional: Check Qdrant collection
    if args.check_qdrant:
        print(f"\n[EXTRA] Checking Qdrant collection...")
        qdrant_status = verify_qdrant_collection(args.host, args.user, args.port, args.key)
        if qdrant_status["status"] == "ok":
            print(f"        [OK] Qdrant collection accessible")
            if "points_count" in qdrant_status:
                print(f"        Points: {qdrant_status['points_count']}")
        else:
            print(f"        [WARN] Qdrant: {qdrant_status.get('error', 'unknown error')}")
    
    print("\n" + "="*60)
    print("[OK] Verification complete!")
    print("="*60)


if __name__ == "__main__":
    main()
