"""
Fetch Manifest System
=====================
Tracks the state of fetched wiki content for incremental updates.
Enables change detection and delta fetching.

Constitution Article III: Modular pipeline components.

Usage:
    from manifest import FetchManifest, PageEntry, MediaEntry
    
    # Create new manifest
    manifest = FetchManifest(wiki_url="https://wiki.example.com")
    
    # Add entries during fetch
    manifest.add_page(PageEntry(id="start", revision=1706789400, ...))
    manifest.add_media(MediaEntry(id="wiki:logo.png", hash="sha256:...", ...))
    
    # Save after fetch
    manifest.save(Path("data/fetched/fetch_123/fetch_manifest.json"))
    
    # Load for comparison
    old_manifest = FetchManifest.load(Path("data/fetched/fetch_122/fetch_manifest.json"))
"""

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Dict, List, Set

# =============================================================================
# Enums
# =============================================================================


class EntryStatus(StrEnum):
    """Status of a manifest entry"""

    CURRENT = "current"  # Active, successfully fetched
    DELETED = "deleted"  # Marked as deleted on wiki
    ERROR = "error"  # Failed to fetch
    SKIPPED = "skipped"  # Intentionally skipped (filter/size)


class ChangeType(StrEnum):
    """Type of change detected"""

    ADDED = "added"  # New item not in previous manifest
    MODIFIED = "modified"  # Item exists but changed
    DELETED = "deleted"  # Item was in previous but not in current wiki
    UNCHANGED = "unchanged"  # No change detected


class ChangeMagnitude(StrEnum):
    """Magnitude of content change"""

    MINOR = "minor"  # Small edits (typos, formatting)
    MAJOR = "major"  # Significant content changes
    REWRITE = "rewrite"  # Complete rewrite (>80% different)


# =============================================================================
# Entry Dataclasses
# =============================================================================


@dataclass
class PageEntry:
    """Manifest entry for a wiki page"""

    id: str  # Page ID (e.g., "teacher:forms:start")
    revision: int  # Wiki revision timestamp (Unix epoch)
    content_hash: str = ""  # SHA256 of page content
    size_bytes: int = 0  # Content size in bytes
    last_fetched: str = ""  # ISO timestamp of last fetch
    status: str = EntryStatus.CURRENT.value  # Entry status
    namespace: str = ""  # Top-level namespace
    has_html: bool = False  # Whether HTML was fetched
    has_history: bool = False  # Whether history was fetched
    has_backlinks: bool = False  # Whether backlinks were fetched
    link_count: int = 0  # Number of outgoing links
    backlink_count: int = 0  # Number of incoming links

    def __post_init__(self):
        """Auto-extract namespace if not provided"""
        if not self.namespace and ":" in self.id:
            self.namespace = self.id.split(":")[0]
        elif not self.namespace:
            self.namespace = "root"

        if not self.last_fetched:
            self.last_fetched = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PageEntry":
        """Create from dictionary"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class MediaEntry:
    """Manifest entry for a media file"""

    id: str  # Media ID (e.g., "wiki:logo.png")
    hash: str = ""  # File hash (SHA256 or MD5 from wiki)
    size_bytes: int = 0  # File size
    last_fetched: str = ""  # ISO timestamp of last fetch
    status: str = EntryStatus.CURRENT.value  # Entry status
    namespace: str = ""  # Namespace containing media
    extension: str = ""  # File extension
    discovery_method: str = "listing"  # How it was discovered
    source: str = "download"  # "download" or "cache"
    reference_count: int = 0  # Number of pages referencing this

    def __post_init__(self):
        """Auto-extract namespace and extension if not provided"""
        if not self.namespace and ":" in self.id:
            self.namespace = self.id.rsplit(":", 1)[0]
        elif not self.namespace:
            self.namespace = "root"

        if not self.extension and "." in self.id:
            self.extension = self.id.rsplit(".", 1)[-1].lower()

        if not self.last_fetched:
            self.last_fetched = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MediaEntry":
        """Create from dictionary"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class FetchRunStats:
    """Statistics for a single fetch run"""

    fetch_id: str = ""  # Unique fetch run identifier
    fetch_type: str = "full"  # "full" or "incremental"
    started_at: str = ""  # ISO timestamp
    completed_at: str = ""  # ISO timestamp
    duration_seconds: float = 0.0  # Total duration

    # Page stats
    pages_total: int = 0
    pages_successful: int = 0
    pages_failed: int = 0
    pages_skipped: int = 0

    # Media stats
    media_total: int = 0
    media_downloaded: int = 0
    media_from_cache: int = 0
    media_failed: int = 0
    media_skipped: int = 0

    # Size stats
    total_content_bytes: int = 0
    total_media_bytes: int = 0

    # Change stats (for incremental)
    pages_added: int = 0
    pages_modified: int = 0
    pages_deleted: int = 0
    media_added: int = 0
    media_modified: int = 0
    media_deleted: int = 0

    # Errors
    error_count: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FetchRunStats":
        """Create from dictionary"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# =============================================================================
# FetchManifest Class
# =============================================================================


class FetchManifest:
    """
    Tracks the complete state of a wiki fetch.

    Enables:
    - Change detection between fetches
    - Incremental/delta fetching
    - Fetch history and audit trail
    """

    VERSION = "1.0"

    def __init__(
        self,
        wiki_url: str = "",
        fetch_id: str = "",
        created_at: str = "",
    ):
        self.version = self.VERSION
        self.wiki_url = wiki_url
        self.fetch_id = fetch_id or self._generate_fetch_id()
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = self.created_at

        # Page and media entries
        self._pages: Dict[str, PageEntry] = {}
        self._media: Dict[str, MediaEntry] = {}

        # Fetch run statistics
        self.stats = FetchRunStats(fetch_id=self.fetch_id)

        # Metadata
        self.namespaces: List[str] = []
        self.config_hash: str = ""

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def page_count(self) -> int:
        """Number of pages in manifest"""
        return len(self._pages)

    @property
    def media_count(self) -> int:
        """Number of media files in manifest"""
        return len(self._media)

    @property
    def pages(self) -> Dict[str, PageEntry]:
        """All page entries (read-only view)"""
        return self._pages.copy()

    @property
    def media(self) -> Dict[str, MediaEntry]:
        """All media entries (read-only view)"""
        return self._media.copy()

    # -------------------------------------------------------------------------
    # Page Operations
    # -------------------------------------------------------------------------

    def add_page(self, entry: PageEntry) -> None:
        """Add or update a page entry"""
        self._pages[entry.id] = entry
        self.updated_at = datetime.now().isoformat()

    def get_page(self, page_id: str) -> PageEntry | None:
        """Get a page entry by ID"""
        return self._pages.get(page_id)

    def remove_page(self, page_id: str) -> PageEntry | None:
        """Remove a page entry, returns the removed entry"""
        entry = self._pages.pop(page_id, None)
        if entry:
            self.updated_at = datetime.now().isoformat()
        return entry

    def mark_page_deleted(self, page_id: str) -> bool:
        """Mark a page as deleted (soft delete)"""
        if page_id in self._pages:
            self._pages[page_id].status = EntryStatus.DELETED.value
            self.updated_at = datetime.now().isoformat()
            return True
        return False

    def has_page(self, page_id: str) -> bool:
        """Check if page exists in manifest"""
        return page_id in self._pages

    def get_page_ids(self) -> Set[str]:
        """Get all page IDs"""
        return set(self._pages.keys())

    def get_pages_by_namespace(self, namespace: str) -> List[PageEntry]:
        """Get all pages in a namespace"""
        return [p for p in self._pages.values() if p.namespace == namespace]

    def get_pages_by_status(self, status: EntryStatus) -> List[PageEntry]:
        """Get all pages with a specific status"""
        return [p for p in self._pages.values() if p.status == status.value]

    # -------------------------------------------------------------------------
    # Media Operations
    # -------------------------------------------------------------------------

    def add_media(self, entry: MediaEntry) -> None:
        """Add or update a media entry"""
        self._media[entry.id] = entry
        self.updated_at = datetime.now().isoformat()

    def get_media(self, media_id: str) -> MediaEntry | None:
        """Get a media entry by ID"""
        return self._media.get(media_id)

    def remove_media(self, media_id: str) -> MediaEntry | None:
        """Remove a media entry, returns the removed entry"""
        entry = self._media.pop(media_id, None)
        if entry:
            self.updated_at = datetime.now().isoformat()
        return entry

    def mark_media_deleted(self, media_id: str) -> bool:
        """Mark media as deleted (soft delete)"""
        if media_id in self._media:
            self._media[media_id].status = EntryStatus.DELETED.value
            self.updated_at = datetime.now().isoformat()
            return True
        return False

    def has_media(self, media_id: str) -> bool:
        """Check if media exists in manifest"""
        return media_id in self._media

    def get_media_ids(self) -> Set[str]:
        """Get all media IDs"""
        return set(self._media.keys())

    def get_media_by_extension(self, extension: str) -> List[MediaEntry]:
        """Get all media with a specific extension"""
        ext = extension.lower().lstrip(".")
        return [m for m in self._media.values() if m.extension == ext]

    # -------------------------------------------------------------------------
    # Bulk Operations
    # -------------------------------------------------------------------------

    def add_pages(self, entries: List[PageEntry]) -> int:
        """Add multiple page entries, returns count added"""
        for entry in entries:
            self._pages[entry.id] = entry
        self.updated_at = datetime.now().isoformat()
        return len(entries)

    def add_media_entries(self, entries: List[MediaEntry]) -> int:
        """Add multiple media entries, returns count added"""
        for entry in entries:
            self._media[entry.id] = entry
        self.updated_at = datetime.now().isoformat()
        return len(entries)

    def update_namespaces(self) -> List[str]:
        """Update namespace list from current entries"""
        ns_set: Set[str] = set()
        for page in self._pages.values():
            ns_set.add(page.namespace)
        for media in self._media.values():
            ns_set.add(media.namespace)
        self.namespaces = sorted(list(ns_set))
        return self.namespaces

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Convert manifest to dictionary for JSON serialization"""
        self.update_namespaces()

        return {
            "version": self.version,
            "wiki_url": self.wiki_url,
            "fetch_id": self.fetch_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "config_hash": self.config_hash,
            "summary": {
                "page_count": self.page_count,
                "media_count": self.media_count,
                "namespaces": self.namespaces,
            },
            "stats": self.stats.to_dict(),
            "pages": [entry.to_dict() for entry in self._pages.values()],
            "media": [entry.to_dict() for entry in self._media.values()],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FetchManifest":
        """Create manifest from dictionary"""
        manifest = cls(
            wiki_url=data.get("wiki_url", ""),
            fetch_id=data.get("fetch_id", ""),
            created_at=data.get("created_at", ""),
        )

        manifest.version = data.get("version", cls.VERSION)
        manifest.updated_at = data.get("updated_at", manifest.created_at)
        manifest.config_hash = data.get("config_hash", "")
        manifest.namespaces = data.get("summary", {}).get("namespaces", [])

        # Load stats
        if "stats" in data:
            manifest.stats = FetchRunStats.from_dict(data["stats"])

        # Load pages
        for page_data in data.get("pages", []):
            entry = PageEntry.from_dict(page_data)
            manifest._pages[entry.id] = entry

        # Load media
        for media_data in data.get("media", []):
            entry = MediaEntry.from_dict(media_data)
            manifest._media[entry.id] = entry

        return manifest

    def save(self, path: Path) -> None:
        """Save manifest to JSON file"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: Path) -> "FetchManifest":
        """Load manifest from JSON file"""
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Manifest not found: {path}")

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        return cls.from_dict(data)

    @classmethod
    def load_or_create(cls, path: Path, wiki_url: str = "") -> "FetchManifest":
        """Load existing manifest or create new one"""
        try:
            return cls.load(path)
        except (FileNotFoundError, json.JSONDecodeError):
            return cls(wiki_url=wiki_url)

    # -------------------------------------------------------------------------
    # Comparison & Change Detection
    # -------------------------------------------------------------------------

    def get_page_changes(self, other: "FetchManifest") -> Dict[str, List[str]]:
        """
        Compare this manifest to another and return page changes.

        Args:
            other: Previous manifest to compare against

        Returns:
            Dict with 'added', 'modified', 'deleted', 'unchanged' page ID lists
        """
        current_ids = self.get_page_ids()
        other_ids = other.get_page_ids()

        added = current_ids - other_ids
        deleted = other_ids - current_ids
        common = current_ids & other_ids

        modified = set()
        unchanged = set()

        for page_id in common:
            current = self.get_page(page_id)
            previous = other.get_page(page_id)

            if current and previous:
                # Compare by revision (primary) or hash (fallback)
                if current.revision != previous.revision:
                    modified.add(page_id)
                elif current.content_hash and previous.content_hash:
                    if current.content_hash != previous.content_hash:
                        modified.add(page_id)
                    else:
                        unchanged.add(page_id)
                else:
                    unchanged.add(page_id)

        return {
            "added": sorted(list(added)),
            "modified": sorted(list(modified)),
            "deleted": sorted(list(deleted)),
            "unchanged": sorted(list(unchanged)),
        }

    def get_media_changes(self, other: "FetchManifest") -> Dict[str, List[str]]:
        """
        Compare this manifest to another and return media changes.

        Args:
            other: Previous manifest to compare against

        Returns:
            Dict with 'added', 'modified', 'deleted', 'unchanged' media ID lists
        """
        current_ids = self.get_media_ids()
        other_ids = other.get_media_ids()

        added = current_ids - other_ids
        deleted = other_ids - current_ids
        common = current_ids & other_ids

        modified = set()
        unchanged = set()

        for media_id in common:
            current = self.get_media(media_id)
            previous = other.get_media(media_id)

            if current and previous:
                # Compare by hash (primary) or size (fallback)
                if current.hash and previous.hash:
                    if current.hash != previous.hash:
                        modified.add(media_id)
                    else:
                        unchanged.add(media_id)
                elif current.size_bytes != previous.size_bytes:
                    modified.add(media_id)
                else:
                    unchanged.add(media_id)

        return {
            "added": sorted(list(added)),
            "modified": sorted(list(modified)),
            "deleted": sorted(list(deleted)),
            "unchanged": sorted(list(unchanged)),
        }

    def merge_from(self, other: "FetchManifest", overwrite: bool = True) -> Dict[str, int]:
        """
        Merge entries from another manifest into this one.

        Args:
            other: Manifest to merge from
            overwrite: If True, overwrite existing entries

        Returns:
            Dict with counts of merged pages and media
        """
        pages_merged = 0
        media_merged = 0

        for page_id, entry in other._pages.items():
            if overwrite or page_id not in self._pages:
                self._pages[page_id] = entry
                pages_merged += 1

        for media_id, entry in other._media.items():
            if overwrite or media_id not in self._media:
                self._media[media_id] = entry
                media_merged += 1

        self.updated_at = datetime.now().isoformat()

        return {
            "pages_merged": pages_merged,
            "media_merged": media_merged,
        }

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    def _generate_fetch_id(self) -> str:
        """Generate unique fetch ID from timestamp"""
        return f"fetch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def compute_content_hash(self, content: str) -> str:
        """Compute SHA256 hash of content"""
        return f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}"

    def get_summary(self) -> Dict[str, Any]:
        """Get manifest summary statistics"""
        page_statuses = {}
        for page in self._pages.values():
            status = page.status
            page_statuses[status] = page_statuses.get(status, 0) + 1

        media_statuses = {}
        for media in self._media.values():
            status = media.status
            media_statuses[status] = media_statuses.get(status, 0) + 1

        return {
            "fetch_id": self.fetch_id,
            "wiki_url": self.wiki_url,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "pages": {
                "total": self.page_count,
                "by_status": page_statuses,
            },
            "media": {
                "total": self.media_count,
                "by_status": media_statuses,
            },
            "namespaces": len(self.namespaces),
        }

    def validate(self) -> List[str]:
        """
        Validate manifest integrity.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not self.fetch_id:
            errors.append("Missing fetch_id")

        if not self.created_at:
            errors.append("Missing created_at timestamp")

        # Check for duplicate entries (should not happen with dict storage)
        page_ids = list(self._pages.keys())
        if len(page_ids) != len(set(page_ids)):
            errors.append("Duplicate page IDs detected")

        media_ids = list(self._media.keys())
        if len(media_ids) != len(set(media_ids)):
            errors.append("Duplicate media IDs detected")

        # Validate entries
        for page_id, page in self._pages.items():
            if page_id != page.id:
                errors.append(f"Page ID mismatch: key={page_id}, entry.id={page.id}")

        for media_id, media in self._media.items():
            if media_id != media.id:
                errors.append(f"Media ID mismatch: key={media_id}, entry.id={media.id}")

        return errors

    def __repr__(self) -> str:
        return (
            f"FetchManifest(fetch_id='{self.fetch_id}', "
            f"pages={self.page_count}, media={self.media_count})"
        )


# =============================================================================
# Schema Validation (JSON Schema)
# =============================================================================

MANIFEST_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "FetchManifest",
    "type": "object",
    "required": ["version", "fetch_id", "created_at", "pages", "media"],
    "properties": {
        "version": {"type": "string"},
        "wiki_url": {"type": "string"},
        "fetch_id": {"type": "string"},
        "created_at": {"type": "string", "format": "date-time"},
        "updated_at": {"type": "string", "format": "date-time"},
        "config_hash": {"type": "string"},
        "summary": {
            "type": "object",
            "properties": {
                "page_count": {"type": "integer"},
                "media_count": {"type": "integer"},
                "namespaces": {"type": "array", "items": {"type": "string"}},
            },
        },
        "stats": {"type": "object"},
        "pages": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "revision"],
                "properties": {
                    "id": {"type": "string"},
                    "revision": {"type": "integer"},
                    "content_hash": {"type": "string"},
                    "size_bytes": {"type": "integer"},
                    "last_fetched": {"type": "string"},
                    "status": {"type": "string"},
                    "namespace": {"type": "string"},
                },
            },
        },
        "media": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id"],
                "properties": {
                    "id": {"type": "string"},
                    "hash": {"type": "string"},
                    "size_bytes": {"type": "integer"},
                    "last_fetched": {"type": "string"},
                    "status": {"type": "string"},
                    "namespace": {"type": "string"},
                    "extension": {"type": "string"},
                },
            },
        },
    },
}


def save_schema(path: Path) -> None:
    """Save JSON schema to file"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(MANIFEST_SCHEMA, f, indent=2)


# =============================================================================
# CLI for Testing
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="FetchManifest utilities")
    parser.add_argument(
        "command", choices=["show", "verify", "schema", "compare"], help="Command to execute"
    )
    parser.add_argument("path", nargs="?", help="Path to manifest file")
    parser.add_argument("--other", help="Path to second manifest for comparison")

    args = parser.parse_args()

    if args.command == "schema":
        schema_path = Path("manifest_schema.json")
        save_schema(schema_path)
        print(f"[OK] Schema saved to {schema_path}")

    elif args.command == "show":
        if not args.path:
            print("[ERROR] Path required for show command")
            exit(1)

        manifest = FetchManifest.load(Path(args.path))
        summary = manifest.get_summary()

        print("=" * 60)
        print(f"MANIFEST: {manifest.fetch_id}")
        print("=" * 60)
        print(f"Wiki URL:     {summary['wiki_url']}")
        print(f"Created:      {summary['created_at']}")
        print(f"Updated:      {summary['updated_at']}")
        print(f"Pages:        {summary['pages']['total']}")
        print(f"  By status:  {summary['pages']['by_status']}")
        print(f"Media:        {summary['media']['total']}")
        print(f"  By status:  {summary['media']['by_status']}")
        print(f"Namespaces:   {summary['namespaces']}")
        print("=" * 60)

    elif args.command == "verify":
        if not args.path:
            print("[ERROR] Path required for verify command")
            exit(1)

        manifest = FetchManifest.load(Path(args.path))
        errors = manifest.validate()

        if errors:
            print("[ERROR] Manifest validation failed:")
            for err in errors:
                print(f"  - {err}")
            exit(1)
        else:
            print(f"[OK] Manifest valid: {manifest.fetch_id}")
            print(f"     Pages: {manifest.page_count}, Media: {manifest.media_count}")

    elif args.command == "compare":
        if not args.path or not args.other:
            print("[ERROR] Both --path and --other required for compare command")
            exit(1)

        current = FetchManifest.load(Path(args.path))
        previous = FetchManifest.load(Path(args.other))

        page_changes = current.get_page_changes(previous)
        media_changes = current.get_media_changes(previous)

        print("=" * 60)
        print("MANIFEST COMPARISON")
        print("=" * 60)
        print(f"Current:  {current.fetch_id} ({current.page_count} pages)")
        print(f"Previous: {previous.fetch_id} ({previous.page_count} pages)")
        print()
        print("PAGE CHANGES:")
        print(f"  Added:     {len(page_changes['added'])}")
        print(f"  Modified:  {len(page_changes['modified'])}")
        print(f"  Deleted:   {len(page_changes['deleted'])}")
        print(f"  Unchanged: {len(page_changes['unchanged'])}")
        print()
        print("MEDIA CHANGES:")
        print(f"  Added:     {len(media_changes['added'])}")
        print(f"  Modified:  {len(media_changes['modified'])}")
        print(f"  Deleted:   {len(media_changes['deleted'])}")
        print(f"  Unchanged: {len(media_changes['unchanged'])}")
        print("=" * 60)
