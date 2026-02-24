#!/usr/bin/env python3
"""Deploy Embeddings - Run Entry Point (Stage 05).

Unified entry point for deploying embeddings to a Raspberry Pi via SCP
or directly to a Qdrant instance. Auto-discovers the latest Stage 04
output: data/embeddings/embedded_at_*/embedded_chunks.jsonl.

Usage:
    python pipeline/05_deploy/run_deploy.py transfer               # SCP to Pi (default)
    python pipeline/05_deploy/run_deploy.py transfer --dry-run     # Show what would happen
    python pipeline/05_deploy/run_deploy.py qdrant                 # Direct Qdrant upload
    python pipeline/05_deploy/run_deploy.py qdrant --dry-run       # Validate only
    python pipeline/05_deploy/run_deploy.py verify                 # Verify previous transfer

Configuration:
    pipeline/05_deploy/config.yaml (SSH host, remote paths, Qdrant settings)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add script directory to path for imports
script_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(script_dir))
# Shared CLI utilities (color, sigint, --no-color)
sys.path.insert(0, str(script_dir.parent / "shared"))
from cli_utils import (
    enable_windows_ansi,
    print_help_banner,
    set_use_color,
    style,
)


def main() -> int:
    """Route to the appropriate deploy subcommand."""
    # Show help if no args or explicit -h/--help
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        set_use_color("--no-color" not in sys.argv)
        enable_windows_ansi()
        print_help_banner(
            what=(
                "Deploy embeddings from Stage 04 to a remote Raspberry Pi (SCP)\n"
                "or directly to a Qdrant vector database."
            ),
            usage="python run_deploy.py <command> [OPTIONS]",
            parameters=(
                "transfer   Transfer embeddings to Raspberry Pi via SCP\n"
                "qdrant     Upload embeddings directly to Qdrant\n"
                "verify     Verify a previous transfer (checksum comparison)"
            ),
            options=(
                "-h, --help     Show this help and exit.\n"
                "--no-color     Disable colored output.\n"
                "\nPass --help after <command> for command-specific options:\n"
                "  python run_deploy.py transfer --help\n"
                "  python run_deploy.py qdrant --help\n"
                "  python run_deploy.py verify --help"
            ),
            examples=(
                "# Transfer latest embeddings to Pi (auto-discovers latest file)\n"
                "python run_deploy.py transfer\n"
                "\n"
                "# Dry run: show what would be transferred\n"
                "python run_deploy.py transfer --dry-run\n"
                "\n"
                "# Transfer a specific file\n"
                "python run_deploy.py transfer --local-file path/to/embedded_chunks.jsonl\n"
                "\n"
                "# Upload directly to Qdrant\n"
                "python run_deploy.py qdrant --jsonl path/to/embedded_chunks.jsonl\n"
                "\n"
                "# Verify transfer integrity\n"
                "python run_deploy.py verify"
            ),
            configuration="pipeline/05_deploy/config.yaml (SSH, remote paths, Qdrant settings).",
            output="Transfer log with MD5 checksums, timestamps, file sizes.",
            exit_codes=(
                "0   Success.\n"
                "1   Config error, SSH failure, or transfer failed.\n"
                "130 Interrupted (Ctrl+C)."
            ),
        )
        return 0

    command = sys.argv[1]
    # Remove the subcommand from argv so the sub-script sees its own args
    sys.argv = [sys.argv[0]] + sys.argv[2:]

    if command == "transfer":
        from transfer_to_pi import main as transfer_main

        return transfer_main()

    if command == "qdrant":
        from deploy_qdrant import main as qdrant_main

        return qdrant_main()

    if command == "verify":
        from verify_transfer import main as verify_main

        return verify_main()

    enable_windows_ansi()
    print(style(f"[ERROR] Unknown command: '{command}'", "red"))
    print("  Available commands: transfer, qdrant, verify")
    print("  Run with --help for usage information.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
