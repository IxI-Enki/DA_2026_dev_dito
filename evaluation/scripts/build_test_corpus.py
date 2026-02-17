"""Build a stratified test corpus by sampling from preprocessed pages and media.

Copies ~N random files from preprocessed_at_*/pages and preprocessed_at_*/media
into evaluation/test_corpus with a good distribution of:
  - source: pages vs media (well mixed)
  - namespace: first segment of filename (before first "_")
  - extension: for pages always .md; for media the original extension before .md

Excludes:
  - "archive" namespace (outdated content, not useful for evaluation).
  - Image files (jpg, png, gif, webp, svg, bmp, tiff) -- their preprocessed
    content is just an AI-generated image description, which produces unusable
    ground-truth questions.  Images remain in the main Qdrant index as
    distractors but are not worth evaluating against.

Always includes current Termine pages (org_termine-2026.md, org_termine-2027.md)
when present.

Filename convention:
  <namespace>_<rest>.<ext>  (pages: .md only; media: .ext.md for preprocessed text)

Usage::
  python -m evaluation.scripts.build_test_corpus
  python -m evaluation.scripts.build_test_corpus --target 75 --seed 42
  python -m evaluation.scripts.build_test_corpus --preprocessed-dir data/preprocessed/preprocessed_at_20260216_192955
  python -m evaluation.scripts.build_test_corpus --include-images
"""

from __future__ import annotations

import argparse
import logging
import random
import shutil
import sys
from collections import defaultdict
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
EVAL_ROOT = SCRIPT_DIR.parent
REPO_ROOT = EVAL_ROOT.parent

DEFAULT_PREPROCESSED_DIR = REPO_ROOT / "data" / "preprocessed" / "preprocessed_at_20260216_192955"
DEFAULT_TARGET = 75
DEFAULT_SEED = 20260217

# Namespace to exclude from sampling (e.g. archived content)
EXCLUDE_NAMESPACE = "archive"

# Image extensions to exclude (AI-generated descriptions are not useful for Q&A)
IMAGE_EXTENSIONS = frozenset({"jpg", "jpeg", "png", "gif", "webp", "svg", "bmp", "tiff"})

# Page basenames to always include if present (current / canonical pages)
ALWAYS_INCLUDE_PAGES = ["org_termine-2026.md", "org_termine-2027.md"]


def parse_file_attrs(source: str, filename: str) -> tuple[str, str]:
    """Extract namespace and extension from a preprocessed filename.

    Namespace: first segment (before first "_").
    Extension: for pages always "md"; for media the part after the last dot before .md
    (e.g. teacher_foo.docx.md -> docx).

    Returns:
        (namespace, extension)
    """
    stem = filename
    if stem.endswith(".md"):
        stem = stem[:-3]  # remove .md
    parts = stem.split("_", 1)
    namespace = parts[0] if parts else "unknown"
    if source == "pages":
        ext = "md"
    else:
        # media: stem may be like "teacher_foo_bar.docx" or "tutorial_foo.jpg"
        ext = "md"
        if "." in stem:
            ext = stem.rsplit(".", 1)[-1].lower()
    return namespace, ext


def collect_files(pages_dir: Path, media_dir: Path) -> list[tuple[Path, str, str, str]]:
    """List all files from pages and media with (path, source, namespace, extension)."""
    result: list[tuple[Path, str, str, str]] = []
    for dir_path, source in [(pages_dir, "pages"), (media_dir, "media")]:
        if not dir_path.is_dir():
            logger.warning("Directory not found: %s", dir_path)
            continue
        for f in dir_path.iterdir():
            if f.is_file():
                ns, ext = parse_file_attrs(source, f.name)
                result.append((f, source, ns, ext))
    return result


def stratified_sample(
    files: list[tuple[Path, str, str, str]],
    target: int,
    seed: int,
) -> list[Path]:
    """Sample target files with good distribution across source, namespace, and extension.

    Strategy:
      1. Ensure minimum representation: at least 1 file per (source, namespace) and
         for media at least 1 per extension where possible.
      2. Split target roughly 50/50 between pages and media (or proportional if one
         source has far fewer files).
      3. Within each source, sample proportionally by namespace; cap per namespace
         so we do not take everything from one namespace.
      4. For media, within each namespace try to vary extensions.
    """
    rng = random.Random(seed)
    by_source = defaultdict(list)
    for item in files:
        path, source, ns, ext = item
        by_source[source].append(item)

    n_pages = len(by_source["pages"])
    n_media = len(by_source["media"])
    total = n_pages + n_media
    if total == 0:
        return []

    # Target counts per source: aim for 50/50 mix when both exist, respect availability
    if n_pages == 0:
        target_pages, target_media = 0, min(target, n_media)
    elif n_media == 0:
        target_pages, target_media = min(target, n_pages), 0
    else:
        half = target // 2
        target_pages = min(n_pages, max(1, half))
        target_media = min(n_media, target - target_pages)
        if target_media < 1:
            target_media = 1
            target_pages = min(n_pages, target - 1)
        if target_pages < 1:
            target_pages = 1
            target_media = min(n_media, target - 1)

    chosen: list[Path] = []

    def sample_from_pool(
        items: list[tuple[Path, str, str, str]],
        k: int,
        prefer_diverse: bool = True,
    ) -> list[Path]:
        if k <= 0 or not items:
            return []
        if k >= len(items):
            return [p for p, *_ in items]
        if not prefer_diverse:
            return [p for p, *_ in rng.sample(items, k)]
        by_ns = defaultdict(list)
        for item in items:
            by_ns[item[2]].append(item)
        # Take at least 1 from each namespace (if k >= num namespaces), then fill
        namespaces = list(by_ns.keys())
        rng.shuffle(namespaces)
        selected_paths: set[Path] = set()
        # First pass: one per namespace
        for ns in namespaces:
            if len(selected_paths) >= k:
                break
            pool = by_ns[ns]
            idx = rng.randint(0, len(pool) - 1) if len(pool) > 1 else 0
            selected_paths.add(pool[idx][0])
        # Second pass: fill remaining proportionally
        remaining = k - len(selected_paths)
        if remaining > 0:
            available = [it for it in items if it[0] not in selected_paths]
            if available:
                add = rng.sample(available, min(remaining, len(available)))
                for it in add:
                    selected_paths.add(it[0])
        return list(selected_paths)

    # Sample pages
    if by_source["pages"] and target_pages > 0:
        chosen.extend(
            sample_from_pool(by_source["pages"], target_pages, prefer_diverse=True)
        )

    # Sample media (diverse namespaces and extensions)
    if by_source["media"] and target_media > 0:
        media_items = by_source["media"]
        by_ns_ext: dict[tuple[str, str], list[tuple[Path, str, str, str]]] = defaultdict(list)
        for it in media_items:
            by_ns_ext[(it[2], it[3])].append(it)
        # Ensure we get variety of extensions: sample from (namespace, ext) strata
        strata = list(by_ns_ext.keys())
        rng.shuffle(strata)
        selected = set()
        # Take one per stratum until we have enough or run out
        for (ns, ext) in strata:
            if len(selected) >= target_media:
                break
            pool = by_ns_ext[(ns, ext)]
            pick = pool[rng.randint(0, len(pool) - 1)] if pool else None
            if pick:
                selected.add(pick[0])
        # Fill to target_media with random from media
        still_need = target_media - len(selected)
        if still_need > 0:
            available = [it[0] for it in media_items if it[0] not in selected]
            if available:
                add = rng.sample(available, min(still_need, len(available)))
                selected.update(add)
        chosen.extend(list(selected))

    rng.shuffle(chosen)
    return chosen


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build stratified test corpus from preprocessed pages and media"
    )
    parser.add_argument(
        "--preprocessed-dir",
        type=Path,
        default=DEFAULT_PREPROCESSED_DIR,
        help="Root of preprocessed data (contains pages/ and media/)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=EVAL_ROOT / "test_corpus",
        help="Output directory for test corpus",
    )
    parser.add_argument(
        "--target",
        type=int,
        default=DEFAULT_TARGET,
        help="Target number of files to copy (default %s)" % DEFAULT_TARGET,
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--include-images",
        action="store_true",
        help="Include image files (jpg, png, ...) -- excluded by default",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print what would be copied, do not copy",
    )
    args = parser.parse_args()

    preprocessed = Path(args.preprocessed_dir).resolve()
    pages_dir = preprocessed / "pages"
    media_dir = preprocessed / "media"
    out_dir = Path(args.output_dir).resolve()

    if not pages_dir.is_dir() and not media_dir.is_dir():
        logger.error("Neither pages nor media directory found under %s", preprocessed)
        return 1

    files = collect_files(pages_dir, media_dir)
    if not files:
        logger.error("No files found in %s or %s", pages_dir, media_dir)
        return 1

    logger.info("Collected %d files (pages: %d, media: %d)",
                len(files),
                sum(1 for _, s, _, _ in files if s == "pages"),
                sum(1 for _, s, _, _ in files if s == "media"))

    # Mandatory: always-include pages (e.g. current Termine)
    mandatory_paths: list[Path] = []
    for name in ALWAYS_INCLUDE_PAGES:
        p = pages_dir / name
        if p.is_file():
            mandatory_paths.append(p)
            logger.info("Always include: %s", p.name)
        else:
            logger.debug("Always-include not found: %s", p)

    # Exclude archive namespace, images (unless --include-images), and mandatory paths
    n_images_skipped = 0
    pool: list[tuple[Path, str, str, str]] = []
    for (path, source, ns, ext) in files:
        if ns == EXCLUDE_NAMESPACE:
            continue
        if path in mandatory_paths:
            continue
        if not args.include_images and ext in IMAGE_EXTENSIONS:
            n_images_skipped += 1
            continue
        pool.append((path, source, ns, ext))

    n_excluded = len(files) - len(pool) - len(mandatory_paths)
    if n_excluded:
        logger.info(
            "Excluded %d files (namespace=%s: %d, images: %d)",
            n_excluded,
            EXCLUDE_NAMESPACE,
            n_excluded - n_images_skipped,
            n_images_skipped,
        )

    n_to_sample = max(0, args.target - len(mandatory_paths))
    sampled = stratified_sample(pool, n_to_sample, args.seed)
    selected = list(mandatory_paths) + list(sampled)
    rng = random.Random(args.seed)
    rng.shuffle(selected)
    logger.info("Selected %d files for test corpus (%d mandatory + %d sampled)",
                len(selected), len(mandatory_paths), len(sampled))

    if args.dry_run:
        for p in selected:
            rel = p.relative_to(preprocessed) if preprocessed in p.parents else p.name
            logger.info("  [DRY-RUN] %s -> %s", p, out_dir / p.name)
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    for src in selected:
        dest = out_dir / src.name
        if dest.resolve() == src.resolve():
            continue
        try:
            shutil.copy2(src, dest)
        except OSError as e:
            logger.error("Failed to copy %s: %s", src, e)
            return 1

    logger.info("Copied %d files to %s", len(selected), out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
