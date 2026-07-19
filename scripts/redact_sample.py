"""Redact PII (email addresses) from a fetched-content file for public samples."""
from __future__ import annotations
import re
import sys
from pathlib import Path

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def redact_text(text: str) -> str:
    """Replace every email address with a neutral placeholder."""
    return _EMAIL.sub("redacted@example.org", text)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: python scripts/redact_sample.py <src> <dst>", file=sys.stderr)
        return 2
    src, dst = Path(argv[1]), Path(argv[2])
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(redact_text(src.read_text(encoding="utf-8")), encoding="utf-8")
    print(f"redacted {src} -> {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
