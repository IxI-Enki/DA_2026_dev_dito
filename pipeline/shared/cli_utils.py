"""Shared CLI utilities for all pipeline modules (US1).

Provides:
- ANSI color output with --no-color support
- Ctrl+C signal handler with abort banner
- 8-section help banner template
- Windows ANSI escape sequence enablement
"""
from __future__ import annotations

import os
import signal
import sys
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# Colour / styling
# ---------------------------------------------------------------------------

_use_color: bool = True

# ANSI escape codes (subset: keeps it portable and simple)
_COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "bright_red": "\033[91m",
    "bright_green": "\033[92m",
    "bright_yellow": "\033[93m",
    "bright_blue": "\033[94m",
    "bright_cyan": "\033[96m",
}


def enable_windows_ansi() -> None:
    """Enable ANSI escape sequences on Windows 10+.

    Calls ``SetConsoleMode`` with ``ENABLE_VIRTUAL_TERMINAL_PROCESSING``
    so that ANSI codes are rendered in ``cmd.exe`` and PowerShell.
    Safe no-op on non-Windows platforms.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        # STD_OUTPUT_HANDLE = -11
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


def set_use_color(enabled: bool) -> None:
    """Toggle ANSI colour output globally."""
    global _use_color
    _use_color = enabled


def get_use_color() -> bool:
    """Return current colour mode."""
    return _use_color


def style(text: str, *codes: str) -> str:
    """Wrap *text* with ANSI escape codes if colour is enabled.

    Args:
        text: The string to style.
        *codes: One or more colour/style names (e.g. ``"bold"``, ``"green"``).

    Returns:
        The styled (or plain) string.
    """
    if not _use_color or not codes:
        return text
    prefix = "".join(_COLORS.get(c, "") for c in codes)
    if not prefix:
        return text
    return f"{prefix}{text}{_COLORS['reset']}"


# ---------------------------------------------------------------------------
# Signal handling
# ---------------------------------------------------------------------------

def create_sigint_handler(
    script_name: str = "",
    callback: Optional[Callable[[], None]] = None,
) -> Callable:
    """Return a SIGINT handler that prints an abort banner and exits 130.

    Args:
        script_name: Shown in the banner (optional).
        callback: Called before exit (e.g. to flush data).

    Returns:
        A handler suitable for ``signal.signal(signal.SIGINT, handler)``.
    """

    def _handler(sig: int, frame: object) -> None:
        sep = "=" * 50
        label = f" ({script_name})" if script_name else ""
        banner = (
            f"\n{style(sep, 'yellow')}\n"
            f"  {style('ABGEBROCHEN', 'bright_yellow', 'bold')}{label}  (Ctrl+C)\n"
            f"{style(sep, 'yellow')}"
        )
        print(banner, file=sys.stderr)
        if callback:
            try:
                callback()
            except Exception:
                pass
        sys.exit(130)

    return _handler


def register_sigint(
    script_name: str = "",
    callback: Optional[Callable[[], None]] = None,
) -> None:
    """Convenience: create and register the SIGINT handler in one call."""
    signal.signal(signal.SIGINT, create_sigint_handler(script_name, callback))


# ---------------------------------------------------------------------------
# Help banner
# ---------------------------------------------------------------------------

def print_help_banner(
    *,
    what: str = "",
    usage: str = "",
    parameters: str = "",
    options: str = "",
    examples: str = "",
    configuration: str = "",
    output: str = "",
    exit_codes: str = "",
) -> None:
    """Print a standardised 8-section help template.

    Sections: What, Usage, Parameters, Options, Examples,
    Configuration, Output, Exit Codes.
    """
    sections = [
        ("What", what),
        ("Usage", usage),
        ("Parameters", parameters),
        ("Options", options),
        ("Examples", examples),
        ("Configuration", configuration),
        ("Output", output),
        ("Exit Codes", exit_codes),
    ]
    for title, body in sections:
        if body:
            print(f"\n{style(title, 'bold', 'cyan')}")
            for line in body.strip().splitlines():
                print(f"  {line}")
    print()


# ---------------------------------------------------------------------------
# Argument-parser helper
# ---------------------------------------------------------------------------

def add_no_color_arg(parser: object) -> None:
    """Add ``--no-color`` flag to an argparse parser.

    Also reads the ``NO_COLOR`` environment variable
    (see https://no-color.org/).
    """
    # type: ignore because callers pass argparse.ArgumentParser
    parser.add_argument(  # type: ignore[attr-defined]
        "--no-color",
        action="store_true",
        default=False,
        help="Disable coloured output (also honoured via NO_COLOR env var)",
    )


def apply_color_from_args(args: object) -> None:
    """Call after ``parse_args()`` to apply ``--no-color`` + ``NO_COLOR``."""
    no_color = getattr(args, "no_color", False) or os.environ.get("NO_COLOR", "") != ""
    if no_color:
        set_use_color(False)
    else:
        enable_windows_ansi()
