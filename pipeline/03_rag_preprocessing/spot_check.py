"""Spot-check script: sample 10 random pages and 10 random media from preprocessed output.

Run after preprocessing to verify improvements (linked_from, namespace, links_to,
chunking_method, etc.). Prints paths and a short summary for manual review.

Usage:
    python spot_check.py
    python spot_check.py data/preprocessed/preprocessed_at_20260216_164954
    python spot_check.py --count 5
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

# Ensure package is importable
_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))


def _find_latest_preprocessed(base: Path) -> Path | None:
    """Find the latest preprocessed_at_* directory."""
    if not base.exists():
        return None
    dirs = sorted(base.glob("preprocessed_at_*"), key=lambda p: p.name, reverse=True)
    return dirs[0] if dirs else None


def _read_frontmatter_summary(md_path: Path, max_lines: int = 15) -> str:
    """Read file and return first max_lines (frontmatter + start of body) for summary."""
    try:
        text = md_path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        return "\n".join(lines[:max_lines])
    except Exception as e:
        return f"[Error reading: {e}]"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Spot-check 10 random pages + 10 random media from preprocessed output."
    )
    parser.add_argument(
        "preprocessed_dir",
        nargs="?",
        type=Path,
        help="Preprocessed directory (e.g. data/preprocessed/preprocessed_at_YYYYMMDD_HHMMSS). "
        "Default: latest under data/preprocessed from config.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of random files per category (default: 10).",
    )
    args = parser.parse_args()

    preprocessed_dir = args.preprocessed_dir
    if preprocessed_dir is None:
        try:
            from config import get_config
            cfg = get_config()
            base = Path(cfg.output_dir)
        except Exception:
            base = Path("data/preprocessed")
        preprocessed_dir = _find_latest_preprocessed(base)
        if preprocessed_dir is None:
            print("[ERROR] No preprocessed directory found. Pass path explicitly.")
            return 1

    preprocessed_dir = Path(preprocessed_dir)
    if not preprocessed_dir.is_dir():
        print(f"[ERROR] Not a directory: {preprocessed_dir}")
        return 1

    pages_dir = preprocessed_dir / "pages"
    media_dir = preprocessed_dir / "media"
    if not pages_dir.is_dir():
        print(f"[ERROR] Missing pages dir: {pages_dir}")
        return 1
    if not media_dir.is_dir():
        print(f"[ERROR] Missing media dir: {media_dir}")
        return 1

    page_files = list(pages_dir.glob("*.md"))
    media_files = list(media_dir.glob("*.md"))
    n = args.count
    random.seed(42)
    sampled_pages = random.sample(page_files, min(n, len(page_files)))
    sampled_media = random.sample(media_files, min(n, len(media_files)))

    print(f"Spot-check: {preprocessed_dir.name}")
    print(f"Pages: {len(page_files)} total, showing {len(sampled_pages)} random.")
    print(f"Media: {len(media_files)} total, showing {len(sampled_media)} random.")
    print("-" * 60)

    print("\n[PAGES]")
    for p in sampled_pages:
        print(f"\n--- {p.relative_to(preprocessed_dir)} ---")
        print(_read_frontmatter_summary(p))

    print("\n" + "=" * 60)
    print("[MEDIA]")
    for m in sampled_media:
        print(f"\n--- {m.relative_to(preprocessed_dir)} ---")
        print(_read_frontmatter_summary(m))

    print("\n[OK] Spot-check list printed. Review for linked_from, namespace, links_to, chunking_method.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
