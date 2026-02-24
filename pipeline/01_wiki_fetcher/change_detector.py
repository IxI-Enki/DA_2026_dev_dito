"""
Change Detection System
=======================
Detects changes between wiki state and local manifest.
Enables incremental/delta fetching.

Usage:
    from change_detector import ChangeDetector, ChangeSummary

    detector = ChangeDetector(manifest, api_client)
    changes = detector.detect_all_changes()

    print(f"Pages: {changes.pages_added} added, {changes.pages_modified} modified")
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Tuple

from api_client import PermanentError, SkipItemError, TransientError, WikiAPIClient
from manifest import ChangeMagnitude, ChangeType, FetchManifest

# =============================================================================
# Change Data Structures
# =============================================================================


@dataclass
class PageChange:
    """Represents a detected change for a single page"""

    page_id: str
    change_type: ChangeType
    old_revision: int = 0
    new_revision: int = 0
    magnitude: ChangeMagnitude = ChangeMagnitude.MINOR
    size_diff: int = 0  # Bytes difference
    detected_at: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.detected_at:
            self.detected_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_id": self.page_id,
            "change_type": self.change_type.value,
            "old_revision": self.old_revision,
            "new_revision": self.new_revision,
            "magnitude": self.magnitude.value,
            "size_diff": self.size_diff,
            "detected_at": self.detected_at,
            "details": self.details,
        }


@dataclass
class MediaChange:
    """Represents a detected change for a single media file"""

    media_id: str
    change_type: ChangeType
    old_hash: str = ""
    new_hash: str = ""
    old_size: int = 0
    new_size: int = 0
    detected_at: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.detected_at:
            self.detected_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "media_id": self.media_id,
            "change_type": self.change_type.value,
            "old_hash": self.old_hash,
            "new_hash": self.new_hash,
            "old_size": self.old_size,
            "new_size": self.new_size,
            "detected_at": self.detected_at,
            "details": self.details,
        }


@dataclass
class ChangeSummary:
    """Summary of all detected changes"""

    # Counts
    pages_added: int = 0
    pages_modified: int = 0
    pages_deleted: int = 0
    pages_unchanged: int = 0

    media_added: int = 0
    media_modified: int = 0
    media_deleted: int = 0
    media_unchanged: int = 0

    # Lists
    page_changes: List[PageChange] = field(default_factory=list)
    media_changes: List[MediaChange] = field(default_factory=list)

    # Metadata
    detection_started: str = ""
    detection_completed: str = ""
    detection_duration_ms: int = 0
    manifest_fetch_id: str = ""

    @property
    def total_pages_changed(self) -> int:
        return self.pages_added + self.pages_modified + self.pages_deleted

    @property
    def total_media_changed(self) -> int:
        return self.media_added + self.media_modified + self.media_deleted

    @property
    def has_changes(self) -> bool:
        return self.total_pages_changed > 0 or self.total_media_changed > 0

    def get_pages_to_fetch(self) -> List[str]:
        """Get list of page IDs that need to be fetched"""
        return [
            c.page_id
            for c in self.page_changes
            if c.change_type in (ChangeType.ADDED, ChangeType.MODIFIED)
        ]

    def get_media_to_fetch(self) -> List[str]:
        """Get list of media IDs that need to be fetched"""
        return [
            c.media_id
            for c in self.media_changes
            if c.change_type in (ChangeType.ADDED, ChangeType.MODIFIED)
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": {
                "pages": {
                    "added": self.pages_added,
                    "modified": self.pages_modified,
                    "deleted": self.pages_deleted,
                    "unchanged": self.pages_unchanged,
                    "total_changed": self.total_pages_changed,
                },
                "media": {
                    "added": self.media_added,
                    "modified": self.media_modified,
                    "deleted": self.media_deleted,
                    "unchanged": self.media_unchanged,
                    "total_changed": self.total_media_changed,
                },
                "has_changes": self.has_changes,
            },
            "metadata": {
                "detection_started": self.detection_started,
                "detection_completed": self.detection_completed,
                "detection_duration_ms": self.detection_duration_ms,
                "manifest_fetch_id": self.manifest_fetch_id,
            },
            "page_changes": [c.to_dict() for c in self.page_changes],
            "media_changes": [c.to_dict() for c in self.media_changes],
        }


# =============================================================================
# ChangeDetector Class
# =============================================================================


class ChangeDetector:
    """
    Detects changes between current wiki state and local manifest.

    Compares:
    - Page revisions (primary)
    - Content hashes (fallback)
    - Media file hashes
    """

    def __init__(
        self,
        manifest: FetchManifest,
        api_client: WikiAPIClient,
        verbose: bool = True,
        batch_size: int = 50,
        request_delay: float = 0.05,
    ):
        self.manifest = manifest
        self.client = api_client
        self.verbose = verbose
        self.batch_size = batch_size
        self.request_delay = request_delay

        # Cache for wiki state
        self._wiki_pages: Dict[str, Dict[str, Any]] = {}
        self._wiki_media: Dict[str, Dict[str, Any]] = {}

        # Results
        self.summary: ChangeSummary | None = None

    def log(self, message: str):
        """Print if verbose"""
        if self.verbose:
            print(message)

    # -------------------------------------------------------------------------
    # Page Change Detection
    # -------------------------------------------------------------------------

    def fetch_wiki_page_list(self) -> Dict[str, Dict[str, Any]]:
        """
        Fetch current page list from wiki with revision info.

        Returns:
            Dict mapping page_id to page info (including revision)
        """
        self.log("  Fetching current wiki page list...")

        pages: Dict[str, Dict[str, Any]] = {}

        # Method 1: core.listPages (includes revision)
        try:
            core_pages = self.client.get_all_pages()
            for page in core_pages:
                page_id = page.get("id", "")
                if page_id:
                    pages[page_id] = page
        except (SkipItemError, PermanentError, TransientError) as e:
            self.log(f"    Warning: core.listPages failed: {e}")

        # Method 2: Get revision for pages missing it
        pages_without_revision = [pid for pid, info in pages.items() if not info.get("revision")]

        if pages_without_revision:
            self.log(f"    Fetching revision for {len(pages_without_revision)} pages...")
            for page_id in pages_without_revision:
                try:
                    info = self.client.get_page_info(page_id)
                    pages[page_id].update(info)
                    time.sleep(self.request_delay)
                except (SkipItemError, PermanentError, TransientError):
                    pass

        self._wiki_pages = pages
        self.log(f"    Found {len(pages)} pages on wiki")

        return pages

    def detect_page_changes(self) -> Tuple[List[PageChange], Dict[str, int]]:
        """
        Detect page changes by comparing manifest to wiki.

        Returns:
            Tuple of (list of changes, dict of counts)
        """
        self.log("  Detecting page changes...")

        if not self._wiki_pages:
            self.fetch_wiki_page_list()

        changes: List[PageChange] = []
        counts = {"added": 0, "modified": 0, "deleted": 0, "unchanged": 0}

        manifest_ids = self.manifest.get_page_ids()
        wiki_ids = set(self._wiki_pages.keys())

        # Find added pages (in wiki but not in manifest)
        added_ids = wiki_ids - manifest_ids
        for page_id in added_ids:
            wiki_info = self._wiki_pages[page_id]
            change = PageChange(
                page_id=page_id,
                change_type=ChangeType.ADDED,
                new_revision=wiki_info.get("revision", 0),
            )
            changes.append(change)
            counts["added"] += 1

        # Find deleted pages (in manifest but not in wiki)
        deleted_ids = manifest_ids - wiki_ids
        for page_id in deleted_ids:
            manifest_entry = self.manifest.get_page(page_id)
            if manifest_entry:
                change = PageChange(
                    page_id=page_id,
                    change_type=ChangeType.DELETED,
                    old_revision=manifest_entry.revision,
                )
                changes.append(change)
                counts["deleted"] += 1

        # Check common pages for modifications
        common_ids = manifest_ids & wiki_ids
        for page_id in common_ids:
            manifest_entry = self.manifest.get_page(page_id)
            wiki_info = self._wiki_pages[page_id]

            if not manifest_entry:
                continue

            old_rev = manifest_entry.revision
            new_rev = wiki_info.get("revision", 0)

            if new_rev > old_rev:
                # Determine change magnitude
                magnitude = self._estimate_change_magnitude(old_rev, new_rev)

                change = PageChange(
                    page_id=page_id,
                    change_type=ChangeType.MODIFIED,
                    old_revision=old_rev,
                    new_revision=new_rev,
                    magnitude=magnitude,
                )
                changes.append(change)
                counts["modified"] += 1
            else:
                counts["unchanged"] += 1

        self.log(f"    Added: {counts['added']}")
        self.log(f"    Modified: {counts['modified']}")
        self.log(f"    Deleted: {counts['deleted']}")
        self.log(f"    Unchanged: {counts['unchanged']}")

        return changes, counts

    def _estimate_change_magnitude(self, old_rev: int, new_rev: int) -> ChangeMagnitude:
        """
        Estimate change magnitude based on revision difference.

        More sophisticated analysis would require fetching content.
        """
        # Simple heuristic: larger revision gap suggests bigger changes
        rev_diff = new_rev - old_rev

        # Less than 1 day difference (assuming ~daily revisions)
        if rev_diff < 86400:
            return ChangeMagnitude.MINOR
        # Less than 1 week
        elif rev_diff < 604800:
            return ChangeMagnitude.MAJOR
        else:
            return ChangeMagnitude.REWRITE

    # -------------------------------------------------------------------------
    # Media Change Detection
    # -------------------------------------------------------------------------

    def fetch_wiki_media_list(
        self, namespaces: List[str] | None = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Fetch current media list from wiki.

        Args:
            namespaces: List of namespaces to scan (uses manifest's if None)

        Returns:
            Dict mapping media_id to media info
        """
        self.log("  Fetching current wiki media list...")

        if namespaces is None:
            namespaces = self.manifest.namespaces or [""]

        media: Dict[str, Dict[str, Any]] = {}

        for ns in namespaces:
            try:
                media_list = self.client.get_all_media(
                    namespace=ns,
                    depth=0,
                    include_hash=True,
                )
                for m in media_list:
                    mid = m.get("id", "")
                    if mid:
                        media[mid] = m

                time.sleep(self.request_delay)
            except (SkipItemError, PermanentError, TransientError) as e:
                self.log(f"    Warning: Failed to list media in '{ns}': {e}")

        self._wiki_media = media
        self.log(f"    Found {len(media)} media files on wiki")

        return media

    def detect_media_changes(self) -> Tuple[List[MediaChange], Dict[str, int]]:
        """
        Detect media changes by comparing manifest to wiki.

        Returns:
            Tuple of (list of changes, dict of counts)
        """
        self.log("  Detecting media changes...")

        if not self._wiki_media:
            self.fetch_wiki_media_list()

        changes: List[MediaChange] = []
        counts = {"added": 0, "modified": 0, "deleted": 0, "unchanged": 0}

        manifest_ids = self.manifest.get_media_ids()
        wiki_ids = set(self._wiki_media.keys())

        # Find added media
        added_ids = wiki_ids - manifest_ids
        for media_id in added_ids:
            wiki_info = self._wiki_media[media_id]
            change = MediaChange(
                media_id=media_id,
                change_type=ChangeType.ADDED,
                new_hash=wiki_info.get("hash", ""),
                new_size=wiki_info.get("size", 0),
            )
            changes.append(change)
            counts["added"] += 1

        # Find deleted media
        deleted_ids = manifest_ids - wiki_ids
        for media_id in deleted_ids:
            manifest_entry = self.manifest.get_media(media_id)
            if manifest_entry:
                change = MediaChange(
                    media_id=media_id,
                    change_type=ChangeType.DELETED,
                    old_hash=manifest_entry.hash,
                    old_size=manifest_entry.size_bytes,
                )
                changes.append(change)
                counts["deleted"] += 1

        # Check common media for modifications
        common_ids = manifest_ids & wiki_ids
        for media_id in common_ids:
            manifest_entry = self.manifest.get_media(media_id)
            wiki_info = self._wiki_media[media_id]

            if not manifest_entry:
                continue

            old_hash = manifest_entry.hash
            new_hash = wiki_info.get("hash", "")
            old_size = manifest_entry.size_bytes
            new_size = wiki_info.get("size", 0)

            # Compare by hash (primary) or size (fallback)
            changed = False
            if old_hash and new_hash:
                changed = old_hash != new_hash
            elif old_size != new_size:
                changed = True

            if changed:
                change = MediaChange(
                    media_id=media_id,
                    change_type=ChangeType.MODIFIED,
                    old_hash=old_hash,
                    new_hash=new_hash,
                    old_size=old_size,
                    new_size=new_size,
                )
                changes.append(change)
                counts["modified"] += 1
            else:
                counts["unchanged"] += 1

        self.log(f"    Added: {counts['added']}")
        self.log(f"    Modified: {counts['modified']}")
        self.log(f"    Deleted: {counts['deleted']}")
        self.log(f"    Unchanged: {counts['unchanged']}")

        return changes, counts

    # -------------------------------------------------------------------------
    # Main Detection
    # -------------------------------------------------------------------------

    def detect_all_changes(self, skip_media: bool = False) -> ChangeSummary:
        """
        Detect all changes between wiki and manifest.

        Args:
            skip_media: If True, skip media change detection

        Returns:
            ChangeSummary with all detected changes
        """
        self.log("\n" + "=" * 60)
        self.log("CHANGE DETECTION")
        self.log("=" * 60)
        self.log(f"Manifest: {self.manifest.fetch_id}")
        self.log(f"  Pages: {self.manifest.page_count}")
        self.log(f"  Media: {self.manifest.media_count}")

        start_time = datetime.now()

        summary = ChangeSummary(
            detection_started=start_time.isoformat(),
            manifest_fetch_id=self.manifest.fetch_id,
        )

        # Detect page changes
        self.log("\n[1/2] Detecting page changes...")
        page_changes, page_counts = self.detect_page_changes()
        summary.page_changes = page_changes
        summary.pages_added = page_counts["added"]
        summary.pages_modified = page_counts["modified"]
        summary.pages_deleted = page_counts["deleted"]
        summary.pages_unchanged = page_counts["unchanged"]

        # Detect media changes (optional)
        if not skip_media:
            self.log("\n[2/2] Detecting media changes...")
            media_changes, media_counts = self.detect_media_changes()
            summary.media_changes = media_changes
            summary.media_added = media_counts["added"]
            summary.media_modified = media_counts["modified"]
            summary.media_deleted = media_counts["deleted"]
            summary.media_unchanged = media_counts["unchanged"]
        else:
            self.log("\n[2/2] Skipping media changes (--skip-media)")

        end_time = datetime.now()
        summary.detection_completed = end_time.isoformat()
        summary.detection_duration_ms = int((end_time - start_time).total_seconds() * 1000)

        self.summary = summary

        # Print summary
        self.log("\n" + "-" * 60)
        self.log("CHANGE SUMMARY")
        self.log("-" * 60)
        self.log(f"Pages to fetch: {len(summary.get_pages_to_fetch())}")
        self.log(f"Media to fetch: {len(summary.get_media_to_fetch())}")
        self.log(f"Detection time: {summary.detection_duration_ms}ms")

        if summary.has_changes:
            self.log("\n[INFO] Changes detected - incremental fetch recommended")
        else:
            self.log("\n[INFO] No changes detected - wiki is up to date")

        self.log("=" * 60)

        return summary

    def quick_check(self) -> bool:
        """
        Quick check if there are any changes without full detection.

        Uses recent changes API if available.

        Returns:
            True if changes are likely, False if no changes
        """
        self.log("Quick change check...")

        # Get most recent page from manifest
        latest_revision = 0
        for page in self.manifest.pages.values():
            if page.revision > latest_revision:
                latest_revision = page.revision

        if latest_revision == 0:
            return True  # No manifest data, assume changes

        # Check recent changes from wiki
        try:
            recent = self.client.get_recent_page_changes(timestamp=latest_revision)
            has_changes = len(recent) > 0
            self.log(f"  Recent changes since {latest_revision}: {len(recent)}")
            return has_changes
        except (SkipItemError, PermanentError, TransientError):
            # If API fails, assume there might be changes
            return True


# =============================================================================
# CLI for Testing
# =============================================================================

if __name__ == "__main__":
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Detect wiki changes")
    parser.add_argument("manifest_path", help="Path to manifest file")
    parser.add_argument("--quick", action="store_true", help="Quick check only")
    parser.add_argument("--skip-media", action="store_true", help="Skip media detection")
    parser.add_argument("--output", "-o", help="Output file for changes JSON")

    args = parser.parse_args()

    # Load manifest
    manifest = FetchManifest.load(Path(args.manifest_path))
    print(f"Loaded manifest: {manifest.fetch_id}")

    # Create API client
    client = WikiAPIClient(verbose=False)

    # Create detector
    detector = ChangeDetector(manifest, client)

    if args.quick:
        has_changes = detector.quick_check()
        print(f"\nQuick check result: {'Changes likely' if has_changes else 'No changes'}")
    else:
        summary = detector.detect_all_changes(skip_media=args.skip_media)

        if args.output:
            import json

            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(summary.to_dict(), f, indent=2, ensure_ascii=False)
            print(f"\nChanges written to: {args.output}")
