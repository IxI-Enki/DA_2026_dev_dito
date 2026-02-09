"""
Change Report Generator
=======================
Generates detailed reports of changes between wiki fetches.
Provides human-readable summaries and machine-readable JSON.

Usage:
    from change_report import ChangeReportGenerator
    
    generator = ChangeReportGenerator(current_manifest, previous_manifest)
    report = generator.generate_report()
    generator.save_report(Path("data/logs/change_reports/"))
"""
import difflib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from manifest import FetchManifest, PageEntry, MediaEntry, ChangeType, ChangeMagnitude


# =============================================================================
# Report Data Structures
# =============================================================================

@dataclass
class PageDiff:
    """Detailed diff information for a page"""
    page_id: str
    change_type: ChangeType
    old_revision: int = 0
    new_revision: int = 0
    old_size: int = 0
    new_size: int = 0
    size_change: int = 0
    size_change_percent: float = 0.0
    magnitude: ChangeMagnitude = ChangeMagnitude.MINOR
    
    # Diff details (if content available)
    lines_added: int = 0
    lines_removed: int = 0
    lines_changed: int = 0
    
    # Structural changes
    headings_changed: bool = False
    links_changed: bool = False
    media_refs_changed: bool = False
    
    summary: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_id": self.page_id,
            "change_type": self.change_type.value,
            "old_revision": self.old_revision,
            "new_revision": self.new_revision,
            "old_size": self.old_size,
            "new_size": self.new_size,
            "size_change": self.size_change,
            "size_change_percent": round(self.size_change_percent, 2),
            "magnitude": self.magnitude.value,
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
            "lines_changed": self.lines_changed,
            "summary": self.summary,
        }


@dataclass
class MediaDiff:
    """Detailed diff information for a media file"""
    media_id: str
    change_type: ChangeType
    old_size: int = 0
    new_size: int = 0
    size_change: int = 0
    old_hash: str = ""
    new_hash: str = ""
    extension: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "media_id": self.media_id,
            "change_type": self.change_type.value,
            "old_size": self.old_size,
            "new_size": self.new_size,
            "size_change": self.size_change,
            "extension": self.extension,
        }


@dataclass
class ChangeReport:
    """Complete change report between two fetches"""
    report_id: str = ""
    generated_at: str = ""
    
    # Fetch info
    current_fetch_id: str = ""
    current_fetch_time: str = ""
    previous_fetch_id: str = ""
    previous_fetch_time: str = ""
    
    # Summary
    pages_added: int = 0
    pages_modified: int = 0
    pages_deleted: int = 0
    pages_unchanged: int = 0
    media_added: int = 0
    media_modified: int = 0
    media_deleted: int = 0
    media_unchanged: int = 0
    
    # Detailed changes
    page_diffs: List[PageDiff] = field(default_factory=list)
    media_diffs: List[MediaDiff] = field(default_factory=list)
    
    # Namespace breakdown
    changes_by_namespace: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.report_id:
            self.report_id = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if not self.generated_at:
            self.generated_at = datetime.now().isoformat()
    
    @property
    def total_pages_changed(self) -> int:
        return self.pages_added + self.pages_modified + self.pages_deleted
    
    @property
    def total_media_changed(self) -> int:
        return self.media_added + self.media_modified + self.media_deleted
    
    @property
    def has_changes(self) -> bool:
        return self.total_pages_changed > 0 or self.total_media_changed > 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at,
            "fetch_comparison": {
                "current": {
                    "fetch_id": self.current_fetch_id,
                    "fetch_time": self.current_fetch_time,
                },
                "previous": {
                    "fetch_id": self.previous_fetch_id,
                    "fetch_time": self.previous_fetch_time,
                },
            },
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
            "changes_by_namespace": self.changes_by_namespace,
            "page_diffs": [d.to_dict() for d in self.page_diffs],
            "media_diffs": [d.to_dict() for d in self.media_diffs],
        }


# =============================================================================
# ChangeReportGenerator Class
# =============================================================================

class ChangeReportGenerator:
    """
    Generates detailed change reports between wiki fetches.
    """
    
    def __init__(
        self,
        current_manifest: FetchManifest,
        previous_manifest: FetchManifest,
        current_content_path: Optional[Path] = None,
        previous_content_path: Optional[Path] = None,
    ):
        self.current = current_manifest
        self.previous = previous_manifest
        self.current_content_path = current_content_path
        self.previous_content_path = previous_content_path
        
        self.report: Optional[ChangeReport] = None
    
    def generate_report(self) -> ChangeReport:
        """
        Generate complete change report.
        
        Returns:
            ChangeReport with all changes
        """
        report = ChangeReport(
            current_fetch_id=self.current.fetch_id,
            current_fetch_time=self.current.created_at,
            previous_fetch_id=self.previous.fetch_id,
            previous_fetch_time=self.previous.created_at,
        )
        
        # Analyze page changes
        page_changes = self.current.get_page_changes(self.previous)
        report.pages_added = len(page_changes["added"])
        report.pages_modified = len(page_changes["modified"])
        report.pages_deleted = len(page_changes["deleted"])
        report.pages_unchanged = len(page_changes["unchanged"])
        
        # Generate page diffs
        for page_id in page_changes["added"]:
            diff = self._create_page_diff(page_id, ChangeType.ADDED)
            report.page_diffs.append(diff)
        
        for page_id in page_changes["modified"]:
            diff = self._create_page_diff(page_id, ChangeType.MODIFIED)
            report.page_diffs.append(diff)
        
        for page_id in page_changes["deleted"]:
            diff = self._create_page_diff(page_id, ChangeType.DELETED)
            report.page_diffs.append(diff)
        
        # Analyze media changes
        media_changes = self.current.get_media_changes(self.previous)
        report.media_added = len(media_changes["added"])
        report.media_modified = len(media_changes["modified"])
        report.media_deleted = len(media_changes["deleted"])
        report.media_unchanged = len(media_changes["unchanged"])
        
        # Generate media diffs
        for media_id in media_changes["added"]:
            diff = self._create_media_diff(media_id, ChangeType.ADDED)
            report.media_diffs.append(diff)
        
        for media_id in media_changes["modified"]:
            diff = self._create_media_diff(media_id, ChangeType.MODIFIED)
            report.media_diffs.append(diff)
        
        for media_id in media_changes["deleted"]:
            diff = self._create_media_diff(media_id, ChangeType.DELETED)
            report.media_diffs.append(diff)
        
        # Breakdown by namespace
        report.changes_by_namespace = self._analyze_by_namespace(report.page_diffs)
        
        self.report = report
        return report
    
    def _create_page_diff(self, page_id: str, change_type: ChangeType) -> PageDiff:
        """Create diff object for a page"""
        current_entry = self.current.get_page(page_id)
        previous_entry = self.previous.get_page(page_id)
        
        diff = PageDiff(
            page_id=page_id,
            change_type=change_type,
        )
        
        if current_entry:
            diff.new_revision = current_entry.revision
            diff.new_size = current_entry.size_bytes
        
        if previous_entry:
            diff.old_revision = previous_entry.revision
            diff.old_size = previous_entry.size_bytes
        
        # Calculate size change
        diff.size_change = diff.new_size - diff.old_size
        if diff.old_size > 0:
            diff.size_change_percent = (diff.size_change / diff.old_size) * 100
        
        # Estimate magnitude
        diff.magnitude = self._estimate_magnitude(diff)
        
        # Generate summary
        diff.summary = self._generate_page_summary(diff)
        
        # Try to compute detailed diff if content is available
        if change_type == ChangeType.MODIFIED:
            self._compute_content_diff(diff)
        
        return diff
    
    def _create_media_diff(self, media_id: str, change_type: ChangeType) -> MediaDiff:
        """Create diff object for a media file"""
        current_entry = self.current.get_media(media_id)
        previous_entry = self.previous.get_media(media_id)
        
        diff = MediaDiff(
            media_id=media_id,
            change_type=change_type,
        )
        
        if current_entry:
            diff.new_size = current_entry.size_bytes
            diff.new_hash = current_entry.hash
            diff.extension = current_entry.extension
        
        if previous_entry:
            diff.old_size = previous_entry.size_bytes
            diff.old_hash = previous_entry.hash
            if not diff.extension:
                diff.extension = previous_entry.extension
        
        diff.size_change = diff.new_size - diff.old_size
        
        return diff
    
    def _estimate_magnitude(self, diff: PageDiff) -> ChangeMagnitude:
        """Estimate change magnitude from size and revision changes"""
        if diff.change_type != ChangeType.MODIFIED:
            return ChangeMagnitude.MAJOR  # Added/deleted are always major
        
        # Use size change as primary indicator
        if abs(diff.size_change_percent) > 50:
            return ChangeMagnitude.REWRITE
        elif abs(diff.size_change_percent) > 20:
            return ChangeMagnitude.MAJOR
        else:
            return ChangeMagnitude.MINOR
    
    def _generate_page_summary(self, diff: PageDiff) -> str:
        """Generate human-readable summary for a page change"""
        if diff.change_type == ChangeType.ADDED:
            return f"New page ({diff.new_size} bytes)"
        elif diff.change_type == ChangeType.DELETED:
            return f"Page removed (was {diff.old_size} bytes)"
        elif diff.change_type == ChangeType.MODIFIED:
            if diff.size_change > 0:
                return f"Content expanded (+{diff.size_change} bytes, {diff.size_change_percent:.1f}%)"
            elif diff.size_change < 0:
                return f"Content reduced ({diff.size_change} bytes, {diff.size_change_percent:.1f}%)"
            else:
                return "Content modified (same size)"
        return ""
    
    def _compute_content_diff(self, diff: PageDiff) -> None:
        """Compute detailed line-level diff if content available"""
        if not self.current_content_path or not self.previous_content_path:
            return
        
        safe_name = diff.page_id.replace(":", "_").replace("/", "_")
        
        current_file = self.current_content_path / f"{safe_name}.txt"
        previous_file = self.previous_content_path / f"{safe_name}.txt"
        
        if not current_file.exists() or not previous_file.exists():
            return
        
        try:
            with open(current_file, "r", encoding="utf-8") as f:
                current_lines = f.readlines()
            with open(previous_file, "r", encoding="utf-8") as f:
                previous_lines = f.readlines()
            
            # Use difflib to compute changes
            differ = difflib.unified_diff(previous_lines, current_lines, lineterm="")
            
            added = 0
            removed = 0
            for line in differ:
                if line.startswith("+") and not line.startswith("+++"):
                    added += 1
                elif line.startswith("-") and not line.startswith("---"):
                    removed += 1
            
            diff.lines_added = added
            diff.lines_removed = removed
            diff.lines_changed = min(added, removed)
            
        except Exception:
            pass  # Silent fail for diff computation
    
    def _analyze_by_namespace(self, page_diffs: List[PageDiff]) -> Dict[str, Dict[str, int]]:
        """Analyze changes grouped by namespace"""
        by_ns: Dict[str, Dict[str, int]] = {}
        
        for diff in page_diffs:
            # Extract namespace
            if ":" in diff.page_id:
                ns = diff.page_id.split(":")[0]
            else:
                ns = "root"
            
            if ns not in by_ns:
                by_ns[ns] = {"added": 0, "modified": 0, "deleted": 0}
            
            if diff.change_type == ChangeType.ADDED:
                by_ns[ns]["added"] += 1
            elif diff.change_type == ChangeType.MODIFIED:
                by_ns[ns]["modified"] += 1
            elif diff.change_type == ChangeType.DELETED:
                by_ns[ns]["deleted"] += 1
        
        return by_ns
    
    # -------------------------------------------------------------------------
    # Output Methods
    # -------------------------------------------------------------------------
    
    def save_report(self, output_dir: Path, include_text: bool = True) -> Path:
        """
        Save report to JSON and optionally text format.
        
        Args:
            output_dir: Directory to save reports
            include_text: Also generate human-readable text report
            
        Returns:
            Path to JSON report
        """
        if not self.report:
            self.generate_report()
        assert self.report is not None

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save JSON
        json_path = output_dir / f"{self.report.report_id}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.report.to_dict(), f, indent=2, ensure_ascii=False)
        
        # Save text report
        if include_text:
            text_path = output_dir / f"{self.report.report_id}.txt"
            with open(text_path, "w", encoding="utf-8") as f:
                f.write(self.generate_text_report())
        
        return json_path
    
    def generate_text_report(self) -> str:
        """Generate human-readable text report"""
        if not self.report:
            self.generate_report()
        assert self.report is not None

        lines = [
            "=" * 70,
            "WIKI CHANGE REPORT",
            f"Generated: {self.report.generated_at}",
            "=" * 70,
            "",
            f"Comparing:",
            f"  Current:  {self.report.current_fetch_id} ({self.report.current_fetch_time})",
            f"  Previous: {self.report.previous_fetch_id} ({self.report.previous_fetch_time})",
            "",
            "-" * 70,
            "SUMMARY",
            "-" * 70,
            "",
            "Pages:",
            f"  Added:     {self.report.pages_added}",
            f"  Modified:  {self.report.pages_modified}",
            f"  Deleted:   {self.report.pages_deleted}",
            f"  Unchanged: {self.report.pages_unchanged}",
            "",
            "Media:",
            f"  Added:     {self.report.media_added}",
            f"  Modified:  {self.report.media_modified}",
            f"  Deleted:   {self.report.media_deleted}",
            f"  Unchanged: {self.report.media_unchanged}",
            "",
        ]
        
        if self.report.changes_by_namespace:
            lines.extend([
                "-" * 70,
                "CHANGES BY NAMESPACE",
                "-" * 70,
                "",
            ])
            for ns, counts in sorted(self.report.changes_by_namespace.items()):
                total = counts["added"] + counts["modified"] + counts["deleted"]
                lines.append(f"  {ns}: {total} changes (+{counts['added']}, ~{counts['modified']}, -{counts['deleted']})")
            lines.append("")
        
        if self.report.page_diffs:
            lines.extend([
                "-" * 70,
                "PAGE CHANGES",
                "-" * 70,
                "",
            ])
            
            # Group by type
            for change_type in [ChangeType.ADDED, ChangeType.MODIFIED, ChangeType.DELETED]:
                diffs = [d for d in self.report.page_diffs if d.change_type == change_type]
                if diffs:
                    lines.append(f"[{change_type.value.upper()}]")
                    for diff in diffs[:50]:  # Limit output
                        lines.append(f"  {diff.page_id}")
                        lines.append(f"    {diff.summary}")
                    if len(diffs) > 50:
                        lines.append(f"  ... and {len(diffs) - 50} more")
                    lines.append("")
        
        lines.extend([
            "=" * 70,
        ])
        
        return "\n".join(lines)


# =============================================================================
# Fetch History Manager
# =============================================================================

@dataclass
class FetchHistoryEntry:
    """Single entry in fetch history"""
    fetch_id: str
    fetch_type: str  # "full" or "incremental"
    created_at: str
    completed_at: str
    duration_seconds: float
    pages_total: int
    media_total: int
    pages_changed: int = 0
    media_changed: int = 0
    manifest_path: str = ""
    change_report_path: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "fetch_id": self.fetch_id,
            "fetch_type": self.fetch_type,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
            "pages_total": self.pages_total,
            "media_total": self.media_total,
            "pages_changed": self.pages_changed,
            "media_changed": self.media_changed,
            "manifest_path": self.manifest_path,
            "change_report_path": self.change_report_path,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FetchHistoryEntry":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class FetchHistory:
    """
    Manages history of fetch operations.
    
    Stores last N fetches with metadata for comparison and audit.
    """
    
    def __init__(
        self,
        history_file: Path,
        max_entries: int = 10,
        max_age_days: int = 30,
    ):
        self.history_file = Path(history_file)
        self.max_entries = max_entries
        self.max_age_days = max_age_days
        
        self.entries: List[FetchHistoryEntry] = []
        self._load()
    
    def _load(self):
        """Load history from file"""
        if not self.history_file.exists():
            return
        
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self.entries = [
                FetchHistoryEntry.from_dict(e) for e in data.get("entries", [])
            ]
        except (json.JSONDecodeError, KeyError):
            self.entries = []
    
    def _save(self):
        """Save history to file"""
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "updated_at": datetime.now().isoformat(),
            "entry_count": len(self.entries),
            "entries": [e.to_dict() for e in self.entries],
        }
        
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def add_entry(self, entry: FetchHistoryEntry):
        """Add new entry and enforce limits"""
        self.entries.insert(0, entry)  # Most recent first
        
        # Enforce max entries
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[:self.max_entries]
        
        # Enforce max age
        cutoff = datetime.now()
        self.entries = [
            e for e in self.entries
            if self._is_recent(e.created_at, cutoff)
        ]
        
        self._save()
    
    def _is_recent(self, date_str: str, cutoff: datetime) -> bool:
        """Check if date is within max_age_days"""
        try:
            date = datetime.fromisoformat(date_str)
            age = (cutoff - date).days
            return age <= self.max_age_days
        except ValueError:
            return False
    
    def get_latest(self) -> Optional[FetchHistoryEntry]:
        """Get most recent entry"""
        return self.entries[0] if self.entries else None
    
    def get_entry(self, fetch_id: str) -> Optional[FetchHistoryEntry]:
        """Get entry by fetch ID"""
        for entry in self.entries:
            if entry.fetch_id == fetch_id:
                return entry
        return None
    
    def list_entries(self, limit: int = 10) -> List[FetchHistoryEntry]:
        """List recent entries"""
        return self.entries[:limit]
    
    def cleanup_old_entries(self) -> int:
        """Remove entries older than max_age_days"""
        original_count = len(self.entries)
        cutoff = datetime.now()
        self.entries = [
            e for e in self.entries
            if self._is_recent(e.created_at, cutoff)
        ]
        removed = original_count - len(self.entries)
        if removed > 0:
            self._save()
        return removed
    
    @classmethod
    def from_manifest(cls, manifest: FetchManifest, history_file: Path) -> "FetchHistory":
        """Create or update history from a manifest"""
        history = cls(history_file)
        
        entry = FetchHistoryEntry(
            fetch_id=manifest.fetch_id,
            fetch_type=manifest.stats.fetch_type,
            created_at=manifest.created_at,
            completed_at=manifest.updated_at,
            duration_seconds=manifest.stats.duration_seconds,
            pages_total=manifest.page_count,
            media_total=manifest.media_count,
            pages_changed=manifest.stats.pages_added + manifest.stats.pages_modified + manifest.stats.pages_deleted,
            media_changed=manifest.stats.media_added + manifest.stats.media_modified + manifest.stats.media_deleted,
        )
        
        history.add_entry(entry)
        return history


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate change reports")
    parser.add_argument("current", help="Path to current manifest")
    parser.add_argument("previous", help="Path to previous manifest")
    parser.add_argument("--output", "-o", help="Output directory for reports")
    parser.add_argument("--text-only", action="store_true", help="Print text report only")
    
    args = parser.parse_args()
    
    current = FetchManifest.load(Path(args.current))
    previous = FetchManifest.load(Path(args.previous))
    
    generator = ChangeReportGenerator(current, previous)
    report = generator.generate_report()
    
    if args.text_only:
        print(generator.generate_text_report())
    else:
        output_dir = Path(args.output) if args.output else Path("data/logs/change_reports")
        report_path = generator.save_report(output_dir)
        print(f"[OK] Report saved: {report_path}")
