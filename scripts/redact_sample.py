"""Redact PII (email addresses) from a fetched-content file for public samples."""
from __future__ import annotations
import re
import subprocess
import sys
from pathlib import Path

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# The redaction token itself is never a real address.
_SAFE_TOKEN = "redacted@example.org"

# Substrings that mark a match as an obvious placeholder/example, not a real
# address (e.g. "VORNAME.NACHNAME@...", "noreply@...", "user@service.v1...").
_PLACEHOLDER_PATTERNS = (
    "vorname",
    "nachname",
    "your_",
    "ihr_",
    "example",
    "noreply",
    "@v1",
)

# Known, deliberately-published maintainer/author contact addresses (GPL
# license headers, plugin.info.txt, Docker LABEL maintainer). This is the
# project author disclosing their own contact info, not third-party PII
# scraped from the wiki, so it is intentionally allowed through the guard.
_KNOWN_AUTHOR_EMAILS = frozenset(
    {
        "j.ritt@htl-leonding.ac.at",
        "dev@htl-leonding.ac.at",
    }
)

# Path prefixes excluded from the --check scan.
_EXCLUDED_PATH_PARTS = ("tests/",)


def scan_for_emails(text: str) -> list[str]:
    """Return every email-address-shaped match found in `text`."""
    return _EMAIL.findall(text)


def redact_text(text: str) -> str:
    """Replace every email address with a neutral placeholder."""
    return _EMAIL.sub(_SAFE_TOKEN, text)


def _is_excluded_path(path: str) -> bool:
    if path.endswith(".md"):
        return True
    parts = path.split("/")
    if "samples" in parts and "data" in parts:
        # data/<stage>/samples/... — already-redacted curated samples.
        try:
            data_idx = parts.index("data")
            if parts[data_idx + 2] == "samples":
                return True
        except (ValueError, IndexError):
            pass
    for prefix in _EXCLUDED_PATH_PARTS:
        if path.startswith(prefix) or f"/{prefix}" in path:
            return True
    return False


def _is_placeholder_match(match: str) -> bool:
    if match == _SAFE_TOKEN:
        return True
    if match in _KNOWN_AUTHOR_EMAILS:
        return True
    lowered = match.lower()
    return any(pattern in lowered for pattern in _PLACEHOLDER_PATTERNS)


def check_tracked_files() -> list[tuple[str, str]]:
    """Scan every git-tracked file for real (non-placeholder) email addresses.

    Returns a list of (path, email) findings; empty means the tracked
    surface is clean.
    """
    result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        check=True,
    )
    findings: list[tuple[str, str]] = []
    for path in result.stdout.splitlines():
        path = path.strip()
        if not path or _is_excluded_path(path):
            continue
        file_path = Path(path)
        if not file_path.is_file():
            continue
        try:
            text = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for match in scan_for_emails(text):
            if not _is_placeholder_match(match):
                findings.append((path, match))
    return findings


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[1] == "--check":
        findings = check_tracked_files()
        if findings:
            print("Found real email addresses in tracked files:", file=sys.stderr)
            for path, email in findings:
                print(f"  {path}: {email}", file=sys.stderr)
            return 1
        print("no-real-emails: tracked surface is clean")
        return 0

    if len(argv) != 3:
        print("usage: python scripts/redact_sample.py <src> <dst>", file=sys.stderr)
        print("       python scripts/redact_sample.py --check", file=sys.stderr)
        return 2
    src, dst = Path(argv[1]), Path(argv[2])
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(redact_text(src.read_text(encoding="utf-8")), encoding="utf-8")
    print(f"redacted {src} -> {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
