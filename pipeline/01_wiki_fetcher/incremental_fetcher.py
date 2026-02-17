"""
Incremental Fetcher
===================
Fetches only changed content based on manifest comparison.
Dramatically reduces sync time for typical updates.

Usage:
    from incremental_fetcher import IncrementalFetcher
    
    fetcher = IncrementalFetcher(manifest_path="data/fetched/fetch_123/fetch_manifest.json")
    stats = fetcher.run_incremental_fetch()
    
    # Or via CLI:
    python incremental_fetcher.py data/fetched/fetch_123/fetch_manifest.json
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from api_client import UserAbortError, WikiAPIClient
from change_detector import ChangeDetector, ChangeSummary
from manifest import ChangeType, EntryStatus, FetchManifest, MediaEntry, PageEntry

from config import API_BASE_URL, OUTPUT_BASE_DIR, get_fetch_config

# Shared CLI utilities
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shared"))
from cli_utils import add_no_color_arg, apply_color_from_args, register_sigint

# =============================================================================
# IncrementalFetcher Class
# =============================================================================


class IncrementalFetcher:
    """
    Performs incremental/delta fetching based on change detection.

    Workflow:
    1. Load previous manifest
    2. Detect changes against current wiki state
    3. Fetch only added/modified items
    4. Update manifest with new state
    5. Generate change report
    """

    def __init__(
        self,
        manifest_path: str | None = None,
        output_dir: str | None = None,
        verbose: bool = True,
        dry_run: bool = False,
        interactive: bool = True,
    ):
        self.verbose = verbose
        self.dry_run = dry_run
        self.config = get_fetch_config()

        # Load previous manifest
        if manifest_path:
            self.previous_manifest = FetchManifest.load(Path(manifest_path))
            self.log(f"Loaded previous manifest: {self.previous_manifest.fetch_id}")
        else:
            self.previous_manifest = FetchManifest(wiki_url=API_BASE_URL)
            self.log("No previous manifest - will fetch all")

        # Generate output directory
        if output_dir is None:
            pattern = self.config.output.directory_pattern
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = pattern.replace("{timestamp}", timestamp)

        self.output_dir = output_dir
        self.base_path = Path(OUTPUT_BASE_DIR) / output_dir

        # Create new manifest for this fetch
        self.manifest = FetchManifest(
            wiki_url=API_BASE_URL,
            fetch_id=output_dir,
        )

        # Setup paths
        self.paths = {
            "raw_json": self.base_path / "raw_json",
            "page_content": self.base_path / "page_content",
            "page_metadata": self.base_path / "page_metadata",
            "page_html": self.base_path / "page_html",
            "page_links": self.base_path / "page_links",
            "page_history": self.base_path / "page_history",
            "page_backlinks": self.base_path / "page_backlinks",
            "media": self.base_path / "media",
            "media_metadata": self.base_path / "media" / "metadata",
            "namespaces": self.base_path / "namespaces",
            "changes": self.base_path / "changes",
        }

        # API client
        self.client = WikiAPIClient(verbose=False, interactive=interactive)

        # Change detector
        self.detector = ChangeDetector(
            self.previous_manifest,
            self.client,
            verbose=verbose,
        )

        # Statistics
        self.stats = {
            "fetch_info": {
                "start_time": None,
                "end_time": None,
                "duration_seconds": 0,
                "fetch_type": "incremental",
                "previous_fetch_id": self.previous_manifest.fetch_id,
            },
            "pages": {
                "added": 0,
                "modified": 0,
                "deleted": 0,
                "unchanged": 0,
                "successful": 0,
                "failed": 0,
            },
            "media": {
                "added": 0,
                "modified": 0,
                "deleted": 0,
                "unchanged": 0,
                "downloaded": 0,
                "failed": 0,
            },
            "errors": [],
        }

        # Change summary
        self.changes: ChangeSummary | None = None

    def log(self, message: str):
        """Print if verbose"""
        if self.verbose:
            print(message)

    def setup_directories(self):
        """Create output directories"""
        self.log(f"\nSetting up output: {self.base_path}")
        for _name, path in self.paths.items():
            path.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # Change Detection
    # -------------------------------------------------------------------------

    def detect_changes(self, skip_media: bool = False) -> ChangeSummary:
        """
        Run change detection against wiki.

        Returns:
            ChangeSummary with all detected changes
        """
        self.changes = self.detector.detect_all_changes(skip_media=skip_media)

        # Update stats
        self.stats["pages"]["added"] = self.changes.pages_added
        self.stats["pages"]["modified"] = self.changes.pages_modified
        self.stats["pages"]["deleted"] = self.changes.pages_deleted
        self.stats["pages"]["unchanged"] = self.changes.pages_unchanged

        self.stats["media"]["added"] = self.changes.media_added
        self.stats["media"]["modified"] = self.changes.media_modified
        self.stats["media"]["deleted"] = self.changes.media_deleted
        self.stats["media"]["unchanged"] = self.changes.media_unchanged

        return self.changes

    # -------------------------------------------------------------------------
    # Page Fetching
    # -------------------------------------------------------------------------

    def fetch_changed_pages(self) -> int:
        """
        Fetch all pages that have changed.

        Returns:
            Number of pages successfully fetched
        """
        if not self.changes:
            self.log("[WARN] No changes detected yet - run detect_changes first")
            return 0

        pages_to_fetch = self.changes.get_pages_to_fetch()

        if not pages_to_fetch:
            self.log("\n[INFO] No pages to fetch")
            return 0

        self.log(f"\n[FETCH] Fetching {len(pages_to_fetch)} changed pages...")

        if self.dry_run:
            self.log("[DRY RUN] Would fetch:")
            for pid in pages_to_fetch[:20]:
                self.log(f"  - {pid}")
            if len(pages_to_fetch) > 20:
                self.log(f"  ... and {len(pages_to_fetch) - 20} more")
            return 0

        successful = 0
        failed = 0

        for i, page_id in enumerate(pages_to_fetch, 1):
            if i % 10 == 0 or i == len(pages_to_fetch):
                self.log(f"  Progress: {i}/{len(pages_to_fetch)}")

            try:
                success = self._fetch_single_page(page_id)
                if success:
                    successful += 1
                else:
                    failed += 1
            except UserAbortError:
                raise
            except Exception as e:
                failed += 1
                self.stats["errors"].append(
                    {
                        "type": "page_fetch",
                        "page_id": page_id,
                        "error": str(e),
                    }
                )

            time.sleep(self.config.delay_between_requests)

        self.stats["pages"]["successful"] = successful
        self.stats["pages"]["failed"] = failed

        self.log(f"  Successful: {successful}")
        self.log(f"  Failed: {failed}")

        return successful

    def _fetch_single_page(self, page_id: str) -> bool:
        """
        Fetch and save a single page.

        Returns:
            True if successful
        """
        safe_name = page_id.replace(":", "_").replace("/", "_")

        try:
            # Fetch page info
            page_info = self.client.get_page_info(page_id)

            # Save metadata
            info_path = self.paths["page_metadata"] / f"{safe_name}_info.json"
            with open(info_path, "w", encoding="utf-8") as f:
                json.dump(page_info, f, indent=2, ensure_ascii=False)

            # Fetch content
            content = self.client.get_page_content(page_id)
            content_path = self.paths["page_content"] / f"{safe_name}.txt"
            with open(content_path, "w", encoding="utf-8") as f:
                f.write(content)

            content_size = len(content.encode("utf-8"))

            # Fetch HTML (optional)
            html_size = 0
            if self.config.content.fetch_html:
                html = self.client.get_page_html(page_id)
                if html:
                    html_path = self.paths["page_html"] / f"{safe_name}.html"
                    with open(html_path, "w", encoding="utf-8") as f:
                        f.write(html)
                    html_size = len(html.encode("utf-8"))

            # Add to manifest
            entry = PageEntry(
                id=page_id,
                revision=page_info.get("revision", 0),
                content_hash=self.manifest.compute_content_hash(content),
                size_bytes=content_size,
                has_html=html_size > 0,
            )
            self.manifest.add_page(entry)

            return True

        except Exception as e:
            self.stats["errors"].append(
                {
                    "type": "page_fetch",
                    "page_id": page_id,
                    "error": str(e),
                }
            )
            return False

    # -------------------------------------------------------------------------
    # Media Fetching
    # -------------------------------------------------------------------------

    def fetch_changed_media(self) -> int:
        """
        Fetch all media that has changed.

        Returns:
            Number of media files successfully fetched
        """
        if not self.changes:
            self.log("[WARN] No changes detected yet")
            return 0

        media_to_fetch = self.changes.get_media_to_fetch()

        if not media_to_fetch:
            self.log("\n[INFO] No media to fetch")
            return 0

        self.log(f"\n[FETCH] Fetching {len(media_to_fetch)} changed media files...")

        if self.dry_run:
            self.log("[DRY RUN] Would fetch:")
            for mid in media_to_fetch[:20]:
                self.log(f"  - {mid}")
            return 0

        successful = 0
        failed = 0

        for i, media_id in enumerate(media_to_fetch, 1):
            if i % 10 == 0 or i == len(media_to_fetch):
                self.log(f"  Progress: {i}/{len(media_to_fetch)}")

            try:
                # Determine path
                if ":" in media_id:
                    parts = media_id.rsplit(":", 1)
                    namespace = parts[0].replace(":", "/")
                    filename = parts[1]
                else:
                    namespace = "root"
                    filename = media_id

                ns_dir = self.paths["media"] / namespace
                ns_dir.mkdir(parents=True, exist_ok=True)
                file_path = ns_dir / filename

                # Download via api_client session
                file_size = self.client.download_file(media_id, file_path)

                # Add to manifest
                entry = MediaEntry(
                    id=media_id,
                    size_bytes=file_size,
                    namespace=namespace.replace("/", ":"),
                    source="download",
                )
                self.manifest.add_media(entry)

                successful += 1

            except Exception as e:
                failed += 1
                self.stats["errors"].append(
                    {
                        "type": "media_fetch",
                        "media_id": media_id,
                        "error": str(e),
                    }
                )

            time.sleep(self.config.delay_between_requests)

        self.stats["media"]["downloaded"] = successful
        self.stats["media"]["failed"] = failed

        self.log(f"  Successful: {successful}")
        self.log(f"  Failed: {failed}")

        return successful

    # -------------------------------------------------------------------------
    # Manifest Handling
    # -------------------------------------------------------------------------

    def carry_forward_unchanged(self):
        """
        Copy unchanged entries from previous manifest to new manifest.

        This ensures the new manifest has complete state, not just changes.
        """
        self.log("\n[MANIFEST] Carrying forward unchanged entries...")

        if not self.changes:
            return

        # Unchanged items are NOT in page_changes - get them from previous manifest
        unchanged_pages = 0
        changed_page_ids = {c.page_id for c in self.changes.page_changes}
        for page_id, entry in self.previous_manifest.pages.items():
            if page_id not in changed_page_ids:
                self.manifest.add_page(entry)
                unchanged_pages += 1

        # Copy unchanged media
        unchanged_media = 0
        changed_media_ids = {c.media_id for c in self.changes.media_changes}
        for media_id, entry in self.previous_manifest.media.items():
            if media_id not in changed_media_ids:
                self.manifest.add_media(entry)
                unchanged_media += 1

        self.log(f"  Carried forward: {unchanged_pages} pages, {unchanged_media} media")

    def mark_deleted_items(self):
        """
        Mark deleted items in manifest (soft delete).
        """
        if not self.changes:
            return

        # Mark deleted pages
        for change in self.changes.page_changes:
            if change.change_type == ChangeType.DELETED:
                entry = self.previous_manifest.get_page(change.page_id)
                if entry:
                    entry.status = EntryStatus.DELETED.value
                    self.manifest.add_page(entry)

        # Mark deleted media
        for change in self.changes.media_changes:
            if change.change_type == ChangeType.DELETED:
                entry = self.previous_manifest.get_media(change.media_id)
                if entry:
                    entry.status = EntryStatus.DELETED.value
                    self.manifest.add_media(entry)

    def save_manifest(self):
        """Save the updated manifest"""
        self.log("\n[MANIFEST] Saving updated manifest...")

        # Update stats
        self.manifest.stats.fetch_type = "incremental"
        self.manifest.stats.started_at = self.stats["fetch_info"]["start_time"]
        self.manifest.stats.completed_at = self.stats["fetch_info"]["end_time"]
        self.manifest.stats.duration_seconds = self.stats["fetch_info"]["duration_seconds"]

        self.manifest.stats.pages_added = self.stats["pages"]["added"]
        self.manifest.stats.pages_modified = self.stats["pages"]["modified"]
        self.manifest.stats.pages_deleted = self.stats["pages"]["deleted"]
        self.manifest.stats.pages_successful = self.stats["pages"]["successful"]
        self.manifest.stats.pages_failed = self.stats["pages"]["failed"]

        self.manifest.stats.media_added = self.stats["media"]["added"]
        self.manifest.stats.media_modified = self.stats["media"]["modified"]
        self.manifest.stats.media_deleted = self.stats["media"]["deleted"]
        self.manifest.stats.media_downloaded = self.stats["media"]["downloaded"]
        self.manifest.stats.media_failed = self.stats["media"]["failed"]

        self.manifest.stats.error_count = len(self.stats["errors"])
        self.manifest.stats.errors = self.stats["errors"][:20]

        # Save
        manifest_path = self.base_path / "fetch_manifest.json"
        self.manifest.save(manifest_path)

        self.log(f"  Saved: {manifest_path}")
        self.log(f"  Pages: {self.manifest.page_count}")
        self.log(f"  Media: {self.manifest.media_count}")

    def save_change_report(self):
        """Save detailed change report"""
        if not self.changes:
            return

        self.log("\n[REPORT] Saving change report...")

        report = {
            "report_type": "incremental_fetch",
            "generated_at": datetime.now().isoformat(),
            "previous_fetch": {
                "fetch_id": self.previous_manifest.fetch_id,
                "created_at": self.previous_manifest.created_at,
                "pages": self.previous_manifest.page_count,
                "media": self.previous_manifest.media_count,
            },
            "current_fetch": {
                "fetch_id": self.manifest.fetch_id,
                "pages": self.manifest.page_count,
                "media": self.manifest.media_count,
            },
            "changes": self.changes.to_dict(),
            "fetch_stats": self.stats,
        }

        report_path = self.base_path / "change_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.log(f"  Saved: {report_path}")

    # -------------------------------------------------------------------------
    # Main Execution
    # -------------------------------------------------------------------------

    def run_incremental_fetch(
        self,
        skip_media: bool = False,
        fetch_media: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute incremental fetch.

        Args:
            skip_media: Skip media change detection
            fetch_media: Download media files (if False, only pages)

        Returns:
            Fetch statistics
        """
        self.stats["fetch_info"]["start_time"] = datetime.now().isoformat()

        self.log("\n" + "=" * 70)
        self.log("INCREMENTAL WIKI FETCH")
        self.log("=" * 70)
        self.log(f"Previous: {self.previous_manifest.fetch_id}")
        self.log(f"Output: {self.base_path}")
        self.log(f"Dry run: {self.dry_run}")

        # Setup
        if not self.dry_run:
            self.setup_directories()

        # Detect changes
        self.detect_changes(skip_media=skip_media)

        if not self.changes or not self.changes.has_changes:
            self.log("\n[OK] No changes detected - nothing to fetch")
            self.stats["fetch_info"]["end_time"] = datetime.now().isoformat()
            return self.stats

        # Fetch changed content
        self.fetch_changed_pages()

        if fetch_media and not skip_media:
            self.fetch_changed_media()

        # Update manifest
        if not self.dry_run:
            self.carry_forward_unchanged()
            self.mark_deleted_items()
            self.save_manifest()
            self.save_change_report()

        self.stats["fetch_info"]["end_time"] = datetime.now().isoformat()

        # Calculate duration
        start = datetime.fromisoformat(self.stats["fetch_info"]["start_time"])
        end = datetime.fromisoformat(self.stats["fetch_info"]["end_time"])
        self.stats["fetch_info"]["duration_seconds"] = (end - start).total_seconds()

        # Save stats
        if not self.dry_run:
            stats_path = self.base_path / "fetch_statistics.json"
            with open(stats_path, "w", encoding="utf-8") as f:
                json.dump(self.stats, f, indent=2, ensure_ascii=False)

        # Print summary
        self.print_summary()

        return self.stats

    def print_summary(self):
        """Print fetch summary"""
        self.log("\n" + "=" * 70)
        self.log("INCREMENTAL FETCH COMPLETE")
        self.log("=" * 70)

        self.log(f"\n[PAGES]")
        self.log(f"  Added:     {self.stats['pages']['added']}")
        self.log(f"  Modified:  {self.stats['pages']['modified']}")
        self.log(f"  Deleted:   {self.stats['pages']['deleted']}")
        self.log(f"  Unchanged: {self.stats['pages']['unchanged']}")
        self.log(f"  Fetched:   {self.stats['pages']['successful']}")
        self.log(f"  Failed:    {self.stats['pages']['failed']}")

        self.log(f"\n[MEDIA]")
        self.log(f"  Added:     {self.stats['media']['added']}")
        self.log(f"  Modified:  {self.stats['media']['modified']}")
        self.log(f"  Deleted:   {self.stats['media']['deleted']}")
        self.log(f"  Unchanged: {self.stats['media']['unchanged']}")
        self.log(f"  Downloaded: {self.stats['media']['downloaded']}")
        self.log(f"  Failed:    {self.stats['media']['failed']}")

        self.log(f"\n[TIMING]")
        self.log(f"  Duration: {self.stats['fetch_info']['duration_seconds']:.1f} seconds")

        if self.stats["errors"]:
            self.log(f"\n[ERRORS]: {len(self.stats['errors'])}")

        self.log("=" * 70)


# =============================================================================
# CLI
# =============================================================================


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Incremental wiki fetch")
    parser.add_argument("manifest_path", nargs="?", help="Path to previous manifest")
    parser.add_argument("--output", "-o", help="Output directory name")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would change without fetching"
    )
    parser.add_argument("--skip-media", action="store_true", help="Skip media detection and fetch")
    parser.add_argument(
        "--no-media-download", action="store_true", help="Detect but don't download media"
    )
    parser.add_argument("--quiet", action="store_true", help="Reduce output")
    parser.add_argument(
        "--auto-skip", action="store_true", help="Auto-skip errors (non-interactive)"
    )
    add_no_color_arg(parser)

    args = parser.parse_args()
    apply_color_from_args(args)
    register_sigint("incremental_fetcher")

    # Find latest manifest if not specified
    manifest_path = args.manifest_path
    if not manifest_path:
        # Look for latest fetched directory
        fetched_dir = Path(OUTPUT_BASE_DIR)
        if fetched_dir.exists():
            fetch_dirs = sorted(
                [
                    d
                    for d in fetched_dir.iterdir()
                    if d.is_dir() and d.name.startswith("fetched_at_")
                ],
                reverse=True,
            )

            for d in fetch_dirs:
                manifest_file = d / "fetch_manifest.json"
                if manifest_file.exists():
                    manifest_path = str(manifest_file)
                    print(f"[INFO] Using latest manifest: {manifest_path}")
                    break

    if not manifest_path:
        print("[WARN] No previous manifest found - will perform full detection")

    fetcher = IncrementalFetcher(
        manifest_path=manifest_path,
        output_dir=args.output,
        verbose=not args.quiet,
        dry_run=args.dry_run,
        interactive=not args.auto_skip,
    )

    stats = fetcher.run_incremental_fetch(
        skip_media=args.skip_media,
        fetch_media=not args.no_media_download,
    )

    # Exit code based on success
    errors = stats.get("pages", {}).get("failed", 0) + stats.get("media", {}).get("failed", 0)
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
