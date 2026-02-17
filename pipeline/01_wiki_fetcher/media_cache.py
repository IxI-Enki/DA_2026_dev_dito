"""
Media Cache Module for Fast-Mode Downloads.
Scans archived fetches and provides cached media files to avoid re-downloading.

Usage:
    from media_cache import MediaCache
    
    cache = MediaCache(archive_base_path)
    cache.build_index()
    
    # Check if file exists in cache
    cached_path = cache.get_cached_file(media_id)
    if cached_path:
        shutil.copy(cached_path, target_path)
"""

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class MediaCache:
    """Manages cached media files from archived fetches"""

    def __init__(
        self,
        content_output_dir: Path,
        archive_dirs: List[str] | None = None,
        hash_algorithm: str = "sha256",
        verbose: bool = True,
    ):
        """
        Initialize media cache.

        Args:
            content_output_dir: Base path for content_output
            archive_dirs: List of archive directory names to scan (default: ["archived_fetch_tests"])
            hash_algorithm: Hash algorithm to use ("sha256" or "md5")
            verbose: Print progress messages
        """
        self.content_output_dir = Path(content_output_dir)
        self.archive_dirs = archive_dirs or ["archived_fetch_tests"]
        self.hash_algorithm = hash_algorithm
        self.verbose = verbose

        # Index: {media_id: {"path": Path, "size": int, "hash": str}}
        self.index: Dict[str, Dict[str, Any]] = {}

        # Stats
        self.stats = {
            "files_indexed": 0,
            "total_size_bytes": 0,
            "archives_scanned": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "bytes_saved": 0,
        }

    def log(self, message: str):
        """Print message if verbose"""
        if self.verbose:
            print(message)

    def _compute_hash(self, file_path: Path) -> str:
        """Compute hash of a file"""
        if self.hash_algorithm == "md5":
            hasher = hashlib.md5()
        else:
            hasher = hashlib.sha256()

        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)

        return hasher.hexdigest()

    def _extract_media_id_from_path(self, file_path: Path, media_base: Path) -> str | None:
        """Extract media ID from file path (e.g., departm/forms/doc.pdf -> departm:forms:doc.pdf)"""
        try:
            relative = file_path.relative_to(media_base)
            # Convert path separators to colons
            parts = relative.parts
            if len(parts) >= 1:
                return ":".join(parts)
        except ValueError:
            pass
        return None

    def build_index(self, compute_hashes: bool = True) -> Dict[str, Dict]:
        """
        Scan archive directories and build index of available media files.

        Args:
            compute_hashes: Whether to compute file hashes (slower but more accurate)

        Returns:
            Index dictionary
        """
        self.log("Building media cache index...")
        self.index = {}

        for archive_dir_name in self.archive_dirs:
            archive_path = self.content_output_dir / archive_dir_name

            if not archive_path.exists():
                self.log(f"  Archive not found: {archive_path}")
                continue

            # Find all fetch directories in archive
            fetch_dirs = [
                d for d in archive_path.iterdir() if d.is_dir() and d.name.startswith("fetched_at_")
            ]

            self.log(f"  Scanning {archive_dir_name}: {len(fetch_dirs)} fetch(es)")

            for fetch_dir in sorted(fetch_dirs, reverse=True):  # Newest first
                media_dir = fetch_dir / "media"
                if not media_dir.exists():
                    continue

                self.stats["archives_scanned"] += 1

                # Scan all files in media directory (excluding metadata subfolder)
                for file_path in media_dir.rglob("*"):
                    if file_path.is_file() and "metadata" not in file_path.parts:
                        media_id = self._extract_media_id_from_path(file_path, media_dir)

                        if media_id and media_id not in self.index:
                            file_size = file_path.stat().st_size

                            entry = {
                                "path": file_path,
                                "size": file_size,
                                "source_fetch": fetch_dir.name,
                                "hash": None,
                            }

                            if compute_hashes:
                                try:
                                    entry["hash"] = self._compute_hash(file_path)
                                except Exception:
                                    pass

                            self.index[media_id] = entry
                            self.stats["files_indexed"] += 1
                            self.stats["total_size_bytes"] += file_size

        self.log(
            f"  Index built: {self.stats['files_indexed']} files, "
            f"{self.stats['total_size_bytes'] / (1024*1024):.1f} MB"
        )

        return self.index

    def get_cached_file(self, media_id: str) -> Path | None:
        """
        Check if media file exists in cache.

        Args:
            media_id: Media ID (e.g., "departm:forms:doc.pdf")

        Returns:
            Path to cached file if found, None otherwise
        """
        entry = self.index.get(media_id)
        if entry and entry["path"].exists():
            return entry["path"]
        return None

    def get_cached_hash(self, media_id: str) -> str | None:
        """Get cached file hash if available"""
        entry = self.index.get(media_id)
        if entry:
            return entry.get("hash")
        return None

    def copy_from_cache(self, media_id: str, target_path: Path, verify: bool = True) -> Dict | None:
        """
        Copy file from cache to target location.

        Args:
            media_id: Media ID
            target_path: Destination path
            verify: Verify hash after copy

        Returns:
            Dict with copy info if successful, None if not in cache
        """
        cached_path = self.get_cached_file(media_id)
        if not cached_path:
            self.stats["cache_misses"] += 1
            return None

        try:
            # Ensure target directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            shutil.copy2(cached_path, target_path)

            # Verify if requested
            if verify and self.index[media_id].get("hash"):
                target_hash = self._compute_hash(target_path)
                if target_hash != self.index[media_id]["hash"]:
                    # Hash mismatch - delete and return failure
                    target_path.unlink()
                    self.stats["cache_misses"] += 1
                    return None

            file_size = target_path.stat().st_size
            self.stats["cache_hits"] += 1
            self.stats["bytes_saved"] += file_size

            return {
                "source": str(cached_path),
                "target": str(target_path),
                "size": file_size,
                "source_fetch": self.index[media_id].get("source_fetch"),
                "verified": verify,
            }

        except Exception:
            self.stats["cache_misses"] += 1
            return None

    def save_index(self, output_path: Path):
        """Save index to JSON file for debugging/inspection"""
        index_data = {
            "timestamp": datetime.now().isoformat(),
            "stats": self.stats,
            "files": {
                media_id: {
                    "path": str(entry["path"]),
                    "size": entry["size"],
                    "hash": entry.get("hash"),
                    "source_fetch": entry.get("source_fetch"),
                }
                for media_id, entry in self.index.items()
            },
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            **self.stats,
            "hit_rate": (
                self.stats["cache_hits"]
                / max(1, self.stats["cache_hits"] + self.stats["cache_misses"])
                * 100
            ),
        }
