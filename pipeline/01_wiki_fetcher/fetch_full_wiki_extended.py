"""
Extended full wiki fetch with ACL, links, and media.
Creates comprehensive local copy with 100% coverage goal.
Includes detailed statistics about wiki structure and content.

Uses centralized configuration from config.py and config/env.yaml
"""
from __future__ import annotations

import os
import sys
import json
import time
import signal
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from api_client import WikiAPIClient, SkipItemError, PermanentError, TransientError, UserAbortError
from extract_links_from_html import LinkExtractor
from media_cache import MediaCache
from config import (
    OUTPUT_BASE_DIR, API_BASE_URL,
    FETCH_CONFIG, get_fetch_config, get_setting
)
from manifest import FetchManifest, PageEntry, MediaEntry, EntryStatus
from utils import format_bytes, sanitize_filename

# Shared CLI utilities
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shared"))
from cli_utils import (
    add_no_color_arg, apply_color_from_args, enable_windows_ansi,
    print_help_banner, register_sigint, set_use_color, style,
)

from progress_tracker import ProgressTracker, create_tracker_from_env

# Global fetcher reference for signal handler
_current_fetcher: Optional["ExtendedWikiFetcher"] = None


def _sigint_handler(sig, frame):
    """Handle Ctrl+C gracefully with quick exit"""
    sep = style("=" * 50, "yellow")
    print(f"\n\n{sep}")
    print(f"  {style('FETCH ABGEBROCHEN', 'bright_yellow', 'bold')}  (Ctrl+C)")
    print(sep)
    
    if _current_fetcher and hasattr(_current_fetcher, 'stats'):
        stats = _current_fetcher.stats
        pages_done = stats.get("pages", {}).get("successful", 0)
        pages_total = stats.get("pages", {}).get("total", "?")
        media_done = stats.get("media", {}).get("downloaded", 0)
        media_total = stats.get("media", {}).get("total", "?")
        
        print(f"  Seiten:  {pages_done}/{pages_total}")
        print(f"  Media:   {media_done}/{media_total}")
    
    print(sep)
    sys.exit(130)


def get_file_extension(filename: str) -> str:
    """Extract file extension from filename"""
    if "." in filename:
        return filename.rsplit(".", 1)[-1].lower()
    return "unknown"


class ExtendedWikiFetcher:
    """Extended wiki fetcher with ACL, links, and media support"""
    
    def __init__(self, output_dir: str | None = None, verbose: bool = True, 
                 use_cache: bool = True, interactive: bool = True,
                 job_id: str | None = None):
        # Load config
        self.config = get_fetch_config()
        
        # Initialize progress tracker if job_id provided
        self.tracker: ProgressTracker | None = None
        if job_id:
            self.tracker = ProgressTracker(job_id=job_id, stage="fetch")
        else:
            self.tracker = create_tracker_from_env()
        
        # Generate output directory name if not provided
        if output_dir is None:
            pattern = self.config.output.directory_pattern
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = pattern.replace("{timestamp}", timestamp)
        
        self.output_dir = output_dir
        self.verbose = verbose
        self.use_cache = use_cache and self.config.cache.enabled
        self.client = WikiAPIClient(verbose=False, interactive=interactive)
        self.link_extractor = LinkExtractor()
        
        # Media cache for fast-mode downloads
        self.media_cache: MediaCache | None = None
        
        # Fetch manifest for incremental updates
        self.manifest = FetchManifest(
            wiki_url=API_BASE_URL,
            fetch_id=output_dir or self._generate_manifest_id()
        )
        
        # Setup paths
        self.base_path = Path(OUTPUT_BASE_DIR) / output_dir
        self.paths = {
            "raw_json": self.base_path / "raw_json",
            "page_content": self.base_path / "page_content",
            "page_metadata": self.base_path / "page_metadata",
            "page_html": self.base_path / "page_html",
            "page_links": self.base_path / "page_links",
            "page_history": self.base_path / "page_history",
            "page_backlinks": self.base_path / "page_backlinks",
            "media": self.base_path / "media",
            "media_metadata": self.base_path / "media_metadata",
            "namespaces": self.base_path / "namespaces",
            "changes": self.base_path / "changes"
        }
        
        # Statistics - comprehensive tracking
        self.stats = {
            "fetch_info": {
                "start_time": None,
                "end_time": None,
                "duration_seconds": 0,
                "api_url": API_BASE_URL,
                "fetch_version": "3.0",
                "config": {
                    "max_namespace_depth": self.config.max_namespace_depth,
                    "scan_all_sub_namespaces": self.config.scan_all_sub_namespaces,
                    "media_from_listings": self.config.media.from_listings,
                    "media_from_page_links": self.config.media.from_page_links,
                }
            },
            "pages": {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "with_html": 0,
                "with_acl": 0,
                "with_links": 0,
                "with_history": 0,
                "with_backlinks": 0,
                "total_content_bytes": 0,
                "total_html_bytes": 0,
                "avg_content_size": 0,
                "avg_html_size": 0,
                "largest_page": {"id": "", "size": 0},
                "smallest_page": {"id": "", "size": float("inf")},
                "empty_pages": 0,
                "size_distribution": {
                    "tiny_0_1kb": 0,
                    "small_1_5kb": 0,
                    "medium_5_20kb": 0,
                    "large_20_100kb": 0,
                    "huge_100kb_plus": 0
                },
                "filtered_out": 0
            },
            "media": {
                "total": 0,
                "listed": 0,
                "from_links": 0,
                "downloaded": 0,
                "download_failed": 0,
                "download_skipped": 0,
                "total_size_bytes": 0,
                "failed_to_list": 0,
                "by_extension": {},
                "by_type": {
                    "images": {"count": 0, "size": 0, "extensions": []},
                    "documents": {"count": 0, "size": 0, "extensions": []},
                    "spreadsheets": {"count": 0, "size": 0, "extensions": []},
                    "presentations": {"count": 0, "size": 0, "extensions": []},
                    "archives": {"count": 0, "size": 0, "extensions": []},
                    "other": {"count": 0, "size": 0, "extensions": []}
                },
                "largest_file": {"id": "", "size": 0},
                "smallest_file": {"id": "", "size": float("inf")},
                "namespaces_scanned": 0
            },
            "namespaces": {
                "total": 0,
                "list": [],
                "by_namespace": {},
                "max_depth": 0,
                "depth_distribution": {},
                "all_scanned": []  # All namespaces scanned for media
            },
            "links": {
                "internal_total": 0,
                "external_total": 0,
                "media_total": 0,
                "interwiki_total": 0,
                "mailto_total": 0,
                "broken_links": 0,
                "external_domains": {},
                "most_linked_pages": {},
                "pages_with_most_links": [],
                "avg_links_per_page": 0
            },
            "acl_summary": {
                "permission_distribution": {},
                "teacher_likely_pages": 0,
                "public_pages": 0,
                "by_namespace": {}
            },
            "wiki_structure": {
                "has_start_page": False,
                "orphan_pages": [],
                "namespaces_with_start": [],
                "namespaces_without_start": []
            },
            "errors": []
        }
        
        # Tracking for detailed analysis
        self._page_sizes: List[Dict[str, Any]] = []
        self._internal_link_targets: Dict[str, int] = defaultdict(int)
        self._external_domains: Dict[str, int] = defaultdict(int)
        self._page_link_counts: List[Dict[str, Any]] = []
        self._all_media_ids: Set[str] = set()  # Track all discovered media
        self._media_from_links: Set[str] = set()  # Media found in page links
    
    def _generate_manifest_id(self) -> str:
        """Generate unique manifest ID from timestamp"""
        pattern = self.config.output.directory_pattern
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return pattern.replace("{timestamp}", timestamp)
    
    def log(self, message: str):
        """Print if verbose"""
        if self.verbose:
            print(message)
    
    def setup_directories(self):
        """Create all output directories"""
        self.log(f"\nSetting up output directory: {self.base_path}")
        
        for name, path in self.paths.items():
            path.mkdir(parents=True, exist_ok=True)
            self.log(f"  Created: {name}/")
    
    def fetch_all_pages(self) -> List[Dict]:
        """Fetch complete page list using multiple methods for 100% coverage"""
        if self.tracker:
            self.tracker.set_step("[1/10] Fetching page list", 1)
        self.log("\n[1/10] Fetching page list...")
        self.log("-" * 50)
        
        page_dict: Dict[str, Dict] = {}
        
        # Method 1: core.listPages
        self.log("  Method 1: core.listPages")
        core_pages = self.client.get_all_pages()
        for page in core_pages:
            page_id = page.get("id", "")
            if page_id:
                page_dict[page_id] = page
        self.log(f"    Found: {len(core_pages)} pages")
        
        # Method 2: wiki.getAllPages
        self.log("  Method 2: wiki.getAllPages")
        try:
            response = self.client.call("wiki.getAllPages")
            wiki_pages = response.get("result", [])
            for page in wiki_pages:
                page_id = page.get("id", "")
                if page_id and page_id not in page_dict:
                    page_dict[page_id] = page
            self.log(f"    Found: {len(wiki_pages)} pages (+{len(wiki_pages) - len([p for p in wiki_pages if p.get('id') in page_dict])} new)")
        except UserAbortError:
            raise  # User chose to abort - propagate
        except (SkipItemError, Exception) as e:
            self.log(f"    Skipped (not available): {str(e)[:50]}")
        
        # Method 3: Recursive namespace listing (if enabled)
        if self.config.use_recursive_listing:
            self.log("  Method 3: wiki.getPagelist (recursive)")
            recursive_pages = self._fetch_pages_recursive()
            new_count = 0
            for page in recursive_pages:
                page_id = page.get("id", "")
                if page_id and page_id not in page_dict:
                    page_dict[page_id] = page
                    new_count += 1
            self.log(f"    Found: {len(recursive_pages)} pages (+{new_count} new)")
        
        # Method 4: Search API discovery (if enabled)
        if self.config.use_search_discovery:
            self.log("  Method 4: Search API discovery")
            search_pages = self._search_hidden_pages()
            new_count = 0
            for page_id in search_pages:
                if page_id and page_id not in page_dict:
                    page_dict[page_id] = {"id": page_id, "discovery": "search"}
                    new_count += 1
            self.log(f"    Found: {len(search_pages)} pages (+{new_count} new)")
        
        pages = list(page_dict.values())
        
        # Apply filtering
        filtered_pages = self._filter_pages(pages)
        
        self.stats["pages"]["total"] = len(filtered_pages)
        self.stats["pages"]["filtered_out"] = len(pages) - len(filtered_pages)
        
        self.log(f"\n  Total unique pages: {len(pages)}")
        if self.stats["pages"]["filtered_out"] > 0:
            self.log(f"  Filtered out: {self.stats['pages']['filtered_out']}")
        self.log(f"  Processing: {len(filtered_pages)} pages")
        
        return filtered_pages
    
    def _fetch_pages_recursive(self) -> List[Dict]:
        """Fetch pages recursively using wiki.getPagelist with depth=0"""
        all_pages: List[Dict] = []
        seen_ids: Set[str] = set()
        
        # Try root namespace first
        namespaces_to_try = [""]
        
        # Add known top-level namespaces
        try:
            response = self.client.call("core.listPages")
            for page in response.get("result", []):
                page_id = page.get("id", "")
                if ":" in page_id:
                    ns = page_id.split(":")[0]
                    if ns not in namespaces_to_try:
                        namespaces_to_try.append(ns)
        except UserAbortError:
            raise
        except (SkipItemError, Exception):
            pass
        
        for ns in namespaces_to_try:
            try:
                response = self.client.call("wiki.getPagelist", {
                    "namespace": ns,
                    "options": {"depth": 0}  # Unlimited depth
                })
                for page in response.get("result", []):
                    page_id = page.get("id", "")
                    if page_id and page_id not in seen_ids:
                        seen_ids.add(page_id)
                        page["discovery"] = "recursive"
                        all_pages.append(page)
            except UserAbortError:
                raise
            except (SkipItemError, Exception):
                pass  # Graceful handling - method may not exist
        
        return all_pages
    
    def _search_hidden_pages(self) -> Set[str]:
        """Use search API to find pages not in listings"""
        found_pages: Set[str] = set()
        
        # Search terms to try
        search_terms = [
            "form", "template", "info", "start", "index",
            "teacher", "student", "exam", "class", "org"
        ]
        
        for term in search_terms:
            # Try core.search
            try:
                response = self.client.call("core.search", {"query": term})
                for result in response.get("result", []):
                    page_id = result.get("id", "") if isinstance(result, dict) else str(result)
                    if page_id:
                        found_pages.add(page_id)
            except UserAbortError:
                raise
            except (SkipItemError, Exception):
                pass  # Method may not exist
            
            # Try wiki.search
            try:
                response = self.client.call("wiki.search", {"query": term})
                for result in response.get("result", []):
                    page_id = result.get("id", "") if isinstance(result, dict) else str(result)
                    if page_id:
                        found_pages.add(page_id)
            except UserAbortError:
                raise
            except (SkipItemError, Exception):
                pass  # Method may not exist
        
        return found_pages
    
    def _filter_pages(self, pages: List[Dict]) -> List[Dict]:
        """Apply namespace and page filters"""
        if not self.config.filter.include_namespaces and not self.config.filter.exclude_namespaces and not self.config.filter.exclude_pages:
            return pages
        
        filtered = []
        for page in pages:
            page_id = page.get("id", "")
            if self.config.filter.should_include_page(page_id):
                filtered.append(page)
        
        return filtered
    
    def extract_namespaces(self, pages: List[Dict]) -> Dict[str, List[str]]:
        """Extract namespace structure with detailed analysis"""
        if self.tracker:
            self.tracker.set_step("[2/10] Analyzing namespaces", 2)
        self.log("\n[2/10] Analyzing namespaces...")
        self.log("-" * 50)
        
        namespaces: Dict[str, List[str]] = {}
        depth_counts: Dict[int, int] = defaultdict(int)
        max_depth = 0
        
        for page in pages:
            page_id = page.get("id", "")
            
            # Calculate namespace depth
            depth = page_id.count(":")
            depth_counts[depth] += 1
            max_depth = max(max_depth, depth)
            
            # Extract top-level namespace
            if ":" in page_id:
                ns = page_id.split(":")[0]
            else:
                ns = "root"
            
            if ns not in namespaces:
                namespaces[ns] = []
            namespaces[ns].append(page_id)
        
        # Update stats
        self.stats["namespaces"]["total"] = len(namespaces)
        self.stats["namespaces"]["list"] = sorted(namespaces.keys())
        self.stats["namespaces"]["max_depth"] = max_depth
        self.stats["namespaces"]["depth_distribution"] = dict(depth_counts)
        
        # Detailed namespace stats
        for ns, pages_list in namespaces.items():
            has_start = f"{ns}:start" in pages_list or (ns == "root" and "start" in [p for p in pages_list])
            self.stats["namespaces"]["by_namespace"][ns] = {
                "page_count": len(pages_list),
                "has_start_page": has_start
            }
            if has_start:
                self.stats["wiki_structure"]["namespaces_with_start"].append(ns)
            else:
                self.stats["wiki_structure"]["namespaces_without_start"].append(ns)
        
        # Check for main start page
        self.stats["wiki_structure"]["has_start_page"] = "start" in [p.get("id") for p in pages]
        
        self.log(f"  Found {len(namespaces)} top-level namespaces")
        self.log(f"  Max depth: {max_depth}")
        
        # Save namespace tree
        namespace_tree = {
            "timestamp": datetime.now().isoformat(),
            "total_namespaces": len(namespaces),
            "max_depth": max_depth,
            "depth_distribution": dict(depth_counts),
            "namespaces": {
                ns: {
                    "page_count": len(pages_list),
                    "has_start_page": self.stats["namespaces"]["by_namespace"][ns]["has_start_page"],
                    "pages": sorted(pages_list)
                }
                for ns, pages_list in sorted(namespaces.items())
            }
        }
        
        tree_path = self.paths["namespaces"] / "namespace_tree.json"
        with open(tree_path, 'w', encoding='utf-8') as f:
            json.dump(namespace_tree, f, indent=2, ensure_ascii=False)
        
        return namespaces
    
    def extract_all_namespaces_for_media(self, pages: List[Dict]) -> Set[str]:
        """
        Extract ALL namespace prefixes up to configured depth.
        
        This ensures we scan sub-namespaces like "teacher:forms" 
        and not just "teacher" for media files.
        """
        max_depth = self.config.max_namespace_depth
        if self.tracker:
            self.tracker.set_step("[3/10] Extracting namespaces for media", 3)
        self.log(f"\n[3/10] Extracting namespaces for media scanning (depth={max_depth})...")
        self.log("-" * 50)
        
        namespaces: Set[str] = set([""])  # Include root namespace
        
        for page in pages:
            page_id = page.get("id", "")
            parts = page_id.split(":")
            
            # Build namespace prefixes at each depth level
            for depth in range(1, min(len(parts), max_depth + 1)):
                ns = ":".join(parts[:depth])
                namespaces.add(ns)
        
        # Sort for consistent output
        sorted_ns = sorted(namespaces)
        self.stats["namespaces"]["all_scanned"] = sorted_ns
        
        self.log(f"  Found {len(namespaces)} namespace prefixes to scan")
        if len(namespaces) <= 20:
            for ns in sorted_ns:
                self.log(f"    - {ns or '(root)'}")
        else:
            for ns in sorted_ns[:10]:
                self.log(f"    - {ns or '(root)'}")
            self.log(f"    ... and {len(namespaces) - 10} more")
        
        return namespaces
    
    def fetch_media_inventory(self, namespaces_to_scan: Set[str]) -> List[Dict]:
        """Fetch media files for ALL namespaces with detailed type analysis"""
        if self.tracker:
            self.tracker.set_step("[4/10] Fetching media inventory", 4)
        self.log("\n[4/10] Fetching media inventory...")
        self.log("-" * 50)
        
        if not self.config.media.from_listings:
            self.log("  Skipped: media.from_listings is disabled")
            return []
        
        # File type mappings
        IMAGE_EXTS = {"jpg", "jpeg", "png", "gif", "svg", "webp", "bmp", "ico"}
        DOC_EXTS = {"pdf", "doc", "docx", "odt", "txt", "rtf"}
        SHEET_EXTS = {"xls", "xlsx", "ods", "csv"}
        PRES_EXTS = {"ppt", "pptx", "odp"}
        ARCHIVE_EXTS = {"zip", "rar", "7z", "tar", "gz"}
        
        all_media: List[Dict] = []
        media_ids: Set[str] = set()
        ext_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"count": 0, "size": 0})
        ns_media_counts: Dict[str, int] = defaultdict(int)
        
        total_ns = len(namespaces_to_scan)
        progress_interval = self.config.batch_progress_interval
        
        for i, ns in enumerate(sorted(namespaces_to_scan), 1):
            if i % progress_interval == 0 or i == total_ns:
                self.log(f"  Scanning namespace {i}/{total_ns}: {ns or '(root)'}")
            
            try:
                # Use get_all_media with hash and author parameters for complete metadata
                media_list = self.client.get_all_media(
                    namespace=ns,
                    depth=0,  # Unlimited depth within namespace
                    include_hash=True,
                    include_author=True
                )
                for m in media_list:
                    mid = m.get("id", "")
                    if mid and mid not in media_ids:
                        media_ids.add(mid)
                        m["source_namespace"] = ns
                        m["discovery_method"] = "listing"
                        all_media.append(m)
            except UserAbortError:
                raise
            except (SkipItemError, Exception):
                self.stats["media"]["failed_to_list"] += 1
        
        self.stats["media"]["namespaces_scanned"] = total_ns
        
        # Analyze media files
        for media in all_media:
            media_id = media.get("id", "")
            size = media.get("size", 0)
            
            # Determine namespace from media_id
            if ":" in media_id:
                ns = media_id.rsplit(":", 1)[0]
            else:
                ns = "root"
            
            # Extract extension
            ext = get_file_extension(media_id)
            ext_stats[ext]["count"] += 1
            ext_stats[ext]["size"] += size
            
            # Count per namespace
            ns_media_counts[ns] += 1
            
            # Categorize by type
            if ext in IMAGE_EXTS:
                self.stats["media"]["by_type"]["images"]["count"] += 1
                self.stats["media"]["by_type"]["images"]["size"] += size
                if ext not in self.stats["media"]["by_type"]["images"]["extensions"]:
                    self.stats["media"]["by_type"]["images"]["extensions"].append(ext)
            elif ext in DOC_EXTS:
                self.stats["media"]["by_type"]["documents"]["count"] += 1
                self.stats["media"]["by_type"]["documents"]["size"] += size
                if ext not in self.stats["media"]["by_type"]["documents"]["extensions"]:
                    self.stats["media"]["by_type"]["documents"]["extensions"].append(ext)
            elif ext in SHEET_EXTS:
                self.stats["media"]["by_type"]["spreadsheets"]["count"] += 1
                self.stats["media"]["by_type"]["spreadsheets"]["size"] += size
                if ext not in self.stats["media"]["by_type"]["spreadsheets"]["extensions"]:
                    self.stats["media"]["by_type"]["spreadsheets"]["extensions"].append(ext)
            elif ext in PRES_EXTS:
                self.stats["media"]["by_type"]["presentations"]["count"] += 1
                self.stats["media"]["by_type"]["presentations"]["size"] += size
                if ext not in self.stats["media"]["by_type"]["presentations"]["extensions"]:
                    self.stats["media"]["by_type"]["presentations"]["extensions"].append(ext)
            elif ext in ARCHIVE_EXTS:
                self.stats["media"]["by_type"]["archives"]["count"] += 1
                self.stats["media"]["by_type"]["archives"]["size"] += size
                if ext not in self.stats["media"]["by_type"]["archives"]["extensions"]:
                    self.stats["media"]["by_type"]["archives"]["extensions"].append(ext)
            else:
                self.stats["media"]["by_type"]["other"]["count"] += 1
                self.stats["media"]["by_type"]["other"]["size"] += size
                if ext not in self.stats["media"]["by_type"]["other"]["extensions"]:
                    self.stats["media"]["by_type"]["other"]["extensions"].append(ext)
            
            # Track largest/smallest
            if size > self.stats["media"]["largest_file"]["size"]:
                self.stats["media"]["largest_file"] = {"id": media_id, "size": size}
            if size < self.stats["media"]["smallest_file"]["size"] and size > 0:
                self.stats["media"]["smallest_file"] = {"id": media_id, "size": size}
        
        # Update namespace media counts
        for ns in self.stats["namespaces"]["by_namespace"]:
            self.stats["namespaces"]["by_namespace"][ns]["media_count"] = ns_media_counts.get(ns, 0)
        
        self.stats["media"]["listed"] = len(all_media)
        self.stats["media"]["by_extension"] = dict(ext_stats)
        
        # Track all media IDs for later
        self._all_media_ids = media_ids

        if self.stats["media"]["smallest_file"]["size"] == float("inf"):
            self.stats["media"]["smallest_file"] = {"id": "", "size": 0}
        
        self.log(f"  Found {len(all_media)} media files from listings")
        self.log(f"  Images: {self.stats['media']['by_type']['images']['count']}")
        self.log(f"  Documents: {self.stats['media']['by_type']['documents']['count']}")
        self.log(f"  Spreadsheets: {self.stats['media']['by_type']['spreadsheets']['count']}")
        
        return all_media
    
    def _is_valid_media_id(self, media_id: str) -> bool:
        """
        Check if a media_id is a valid media file reference.
        
        Filters out:
        - URLs like doku.php?id=...
        - Query strings
        - IDs without file extension
        """
        if not media_id:
            return False
        
        # Skip URLs and query strings
        invalid_patterns = ["doku.php", "?", "=", "http://", "https://", "//"]
        for pattern in invalid_patterns:
            if pattern in media_id:
                return False
        
        # Must have a file extension
        if "." not in media_id.split(":")[-1]:
            return False
        
        return True
    
    def collect_media_from_page_links(self) -> List[Dict]:
        """
        Collect media files referenced in page links that weren't found in listings.
        
        This catches media files in deep sub-namespaces that core.listMedia missed.
        """
        if not self.config.media.from_page_links:
            return []
        
        self.log("\n[5/10] Collecting media from page links...")
        self.log("-" * 50)
        
        links_dir = self.paths["page_links"]
        if not links_dir.exists():
            self.log("  No page_links directory found yet")
            return []
        
        new_media: List[Dict] = []
        skipped_invalid = 0
        
        for links_file in links_dir.glob("*_links.json"):
            try:
                with open(links_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for link in data.get("media_links", []):
                    media_id = link.get("media_id", "")
                    
                    # Validate media_id
                    if not self._is_valid_media_id(media_id):
                        skipped_invalid += 1
                        continue
                    
                    if media_id not in self._all_media_ids:
                        self._all_media_ids.add(media_id)
                        self._media_from_links.add(media_id)
                        
                        new_media.append({
                            "id": media_id,
                            "discovery_method": "page_link",
                            "source_page": link.get("source_page", ""),
                            "size": 0  # Unknown until downloaded
                        })
            except Exception:
                pass
        
        self.stats["media"]["from_links"] = len(new_media)
        
        if new_media:
            self.log(f"  Found {len(new_media)} additional media from page links")
        if skipped_invalid > 0:
            self.log(f"  Skipped {skipped_invalid} invalid media references")
        if not new_media and skipped_invalid == 0:
            self.log("  No additional media found in page links")
        
        return new_media
    
    def _init_media_cache(self) -> None:
        """Initialize media cache from archived fetches"""
        if not self.use_cache:
            return
        
        self.log("\n[5.5/10] Building media cache index...")
        self.log("-" * 50)
        
        content_output_dir = Path(OUTPUT_BASE_DIR)
        self.media_cache = MediaCache(
            content_output_dir=content_output_dir,
            archive_dirs=self.config.cache.archive_dirs,
            hash_algorithm=self.config.cache.hash_algorithm,
            verbose=self.verbose
        )
        self.media_cache.build_index(compute_hashes=True)
        
        # Initialize cache stats
        if "cache" not in self.stats["media"]:
            self.stats["media"]["cache"] = {
                "hits": 0,
                "misses": 0,
                "bytes_saved": 0
            }
    
    def download_media_files(self, media_list: List[Dict]) -> None:
        """Download actual media files via direct HTTP requests with cache support"""
        if not self.config.media.enabled:
            self.log("  Skipping media downloads (media.enabled=False)")
            return
        
        # Initialize cache if enabled
        if self.use_cache and self.media_cache is None:
            self._init_media_cache()
        
        if self.tracker:
            self.tracker.set_step("[6/10] Downloading media files", 6)
        self.log("\n[6/10] Downloading media files...")
        self.log("-" * 50)
        if self.use_cache and self.media_cache:
            self.log(f"  Cache: ENABLED ({self.media_cache.stats['files_indexed']} files indexed)")
        else:
            self.log("  Cache: DISABLED (--no-cache)")
        
        total = len(media_list)
        max_size_bytes = self.config.media.max_file_size_mb * 1024 * 1024 if self.config.media.max_file_size_mb > 0 else float("inf")
        request_delay = self.config.delay_between_requests
        progress_interval = self.config.batch_progress_interval
        
        cached_count = 0
        downloaded_count = 0
        
        for i, media in enumerate(media_list, 1):
            media_id = media.get("id", "")
            if not media_id:
                continue
            
            # Validate media_id (skip invalid ones)
            if not self._is_valid_media_id(media_id):
                self.stats["media"]["download_skipped"] += 1
                continue
            
            # Check file type filter
            if not self.config.media.should_include_file(media_id):
                self.stats["media"]["download_skipped"] += 1
                continue
            
            # Determine namespace and filename
            if ":" in media_id:
                parts = media_id.rsplit(":", 1)
                namespace = parts[0].replace(":", "/")
                filename = parts[1]
            else:
                namespace = "root"
                filename = media_id
            
            # Sanitize namespace path (remove invalid characters)
            namespace = re.sub(r'[<>:"|?*]', '_', namespace)
            filename = re.sub(r'[<>:"|?*]', '_', filename)
            
            # Create namespace directory
            ns_dir = self.paths["media"] / namespace
            ns_dir.mkdir(parents=True, exist_ok=True)
            
            # Target file path
            file_path = ns_dir / filename
            
            # Progress
            if i % progress_interval == 0 or i == total:
                cache_status = f" [Cache: {cached_count} hits]" if cached_count > 0 else ""
                self.log(f"  Progress: {i}/{total} media files...{cache_status}")
                # Update progress tracker
                if self.tracker:
                    self.tracker.update_progress(i, total, f"Media: {i}/{total}{cache_status}")
            
            # Try cache first
            if self.use_cache and self.media_cache:
                copy_result = self.media_cache.copy_from_cache(
                    media_id, 
                    file_path, 
                    verify=self.config.cache.verify_on_copy
                )
                if copy_result:
                    # Cache hit!
                    file_size = copy_result["size"]
                    cached_count += 1
                    self.stats["media"]["downloaded"] += 1
                    self.stats["media"]["total_size_bytes"] += file_size
                    self.stats["media"]["cache"]["hits"] += 1
                    self.stats["media"]["cache"]["bytes_saved"] += file_size
                    
                    # Save metadata with cache info
                    metadata = {
                        "id": media_id,
                        "namespace": namespace,
                        "filename": filename,
                        "local_path": str(file_path.relative_to(self.base_path)),
                        "size_bytes": file_size,
                        "download_timestamp": datetime.now().isoformat(),
                        "discovery_method": media.get("discovery_method", "listing"),
                        "source": "cache",
                        "cache_source": copy_result.get("source_fetch"),
                        "original_metadata": media
                    }
                    
                    safe_name = sanitize_filename(media_id)
                    meta_path = self.paths["media_metadata"] / f"{safe_name}_info.json"
                    with open(meta_path, 'w', encoding='utf-8') as f:
                        json.dump(metadata, f, indent=2, ensure_ascii=False)
                    
                    # Add to manifest (cache hit)
                    media_entry = MediaEntry(
                        id=media_id,
                        hash=copy_result.get("hash", ""),
                        size_bytes=file_size,
                        namespace=namespace.replace("/", ":"),
                        discovery_method=media.get("discovery_method", "listing"),
                        source="cache",
                    )
                    self.manifest.add_media(media_entry)
                    
                    continue  # Skip download, file came from cache
            
            # Cache miss - download from server
            try:
                file_size = self.client.download_file(media_id, file_path)
                downloaded_count += 1
                self.stats["media"]["downloaded"] += 1
                self.stats["media"]["total_size_bytes"] += file_size
                if self.use_cache:
                    self.stats["media"]["cache"]["misses"] += 1
                
                # Save metadata
                metadata = {
                    "id": media_id,
                    "namespace": namespace,
                    "filename": filename,
                    "local_path": str(file_path.relative_to(self.base_path)),
                    "size_bytes": file_size,
                    "download_timestamp": datetime.now().isoformat(),
                    "discovery_method": media.get("discovery_method", "listing"),
                    "source": "download",
                    "original_metadata": media
                }
                
                safe_name = sanitize_filename(media_id)
                meta_path = self.paths["media_metadata"] / f"{safe_name}_info.json"
                with open(meta_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
                
                # Add to manifest (fresh download)
                media_entry = MediaEntry(
                    id=media_id,
                    hash=media.get("hash", ""),
                    size_bytes=file_size,
                    namespace=namespace.replace("/", ":"),
                    discovery_method=media.get("discovery_method", "listing"),
                    source="download",
                )
                self.manifest.add_media(media_entry)
                
                # Small delay to be nice to the server
                time.sleep(request_delay)
                
            except Exception as e:
                self.stats["media"]["download_failed"] += 1
                self.stats["errors"].append({
                    "type": "media_download",
                    "media_id": media_id,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
        
        self.stats["media"]["total"] = len(media_list)
        self.log(f"  Downloaded: {self.stats['media']['downloaded']}/{total}")
        if self.use_cache:
            self.log(f"    - From cache: {cached_count} (saved {format_bytes(self.stats['media']['cache']['bytes_saved'])})")
            self.log(f"    - Fresh downloads: {downloaded_count}")
        self.log(f"  Skipped (filter/size): {self.stats['media']['download_skipped']}")
        self.log(f"  Failed: {self.stats['media']['download_failed']}")
        self.log(f"  Total size: {self.stats['media']['total_size_bytes'] / (1024*1024):.2f} MB")
    
    def fetch_and_save_page(self, page: Dict) -> bool:
        """Fetch and save all data for a single page with detailed stats"""
        page_id = page.get("id", "")
        safe_name = sanitize_filename(page_id)
        
        try:
            # 1. Save page list entry (if raw responses enabled)
            if self.config.output.save_raw_responses:
                list_path = self.paths["raw_json"] / f"{safe_name}_list.json"
                with open(list_path, 'w', encoding='utf-8') as f:
                    json.dump(page, f, indent=2, ensure_ascii=False)
            
            # 2. Fetch and save page info
            page_info = self.client.get_page_info(page_id)
            
            # Add human-readable last_modified date from revision timestamp
            revision = page_info.get("revision", 0)
            if revision and isinstance(revision, (int, float)) and revision > 0:
                try:
                    page_info["last_modified"] = datetime.fromtimestamp(revision).isoformat()
                except (ValueError, OSError):
                    page_info["last_modified"] = None
            else:
                page_info["last_modified"] = None
            
            info_path = self.paths["page_metadata"] / f"{safe_name}_info.json"
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(page_info, f, indent=2, ensure_ascii=False)
            
            # 3. Fetch and save page content
            page_content = self.client.get_page_content(page_id)
            content_path = self.paths["page_content"] / f"{safe_name}.txt"
            with open(content_path, 'w', encoding='utf-8') as f:
                f.write(page_content)
            
            # Track content size statistics
            content_size = len(page_content.encode('utf-8'))
            self.stats["pages"]["total_content_bytes"] += content_size
            self._page_sizes.append({"id": page_id, "size": content_size})
            
            # Size distribution
            if content_size == 0:
                self.stats["pages"]["empty_pages"] += 1
            elif content_size < 1024:
                self.stats["pages"]["size_distribution"]["tiny_0_1kb"] += 1
            elif content_size < 5120:
                self.stats["pages"]["size_distribution"]["small_1_5kb"] += 1
            elif content_size < 20480:
                self.stats["pages"]["size_distribution"]["medium_5_20kb"] += 1
            elif content_size < 102400:
                self.stats["pages"]["size_distribution"]["large_20_100kb"] += 1
            else:
                self.stats["pages"]["size_distribution"]["huge_100kb_plus"] += 1
            
            # Track largest/smallest
            if content_size > self.stats["pages"]["largest_page"]["size"]:
                self.stats["pages"]["largest_page"] = {"id": page_id, "size": content_size}
            if content_size < self.stats["pages"]["smallest_page"]["size"] and content_size > 0:
                self.stats["pages"]["smallest_page"] = {"id": page_id, "size": content_size}
            
            # 4. Fetch and save ACL (if enabled)
            if self.config.content.fetch_acl:
                acl_response = self.client.call("core.aclCheck", {"page": page_id})
                permission = acl_response.get("result", 0)
                
                # Determine namespace and teacher-likelihood
                # Only teacher:* namespace is restricted, all others are public
                namespace = page_id.split(":")[0] if ":" in page_id else "root"
                is_teacher_likely = namespace.lower() == "teacher"
                
                acl_data = {
                    "page_id": page_id,
                    "check_timestamp": datetime.now().isoformat(),
                    "permission_level": permission,
                    "permission_name": self._permission_name(permission),
                    "namespace": namespace,
                    "is_teacher_content": is_teacher_likely
                }
                
                acl_path = self.paths["page_metadata"] / f"{safe_name}_acl.json"
                with open(acl_path, 'w', encoding='utf-8') as f:
                    json.dump(acl_data, f, indent=2, ensure_ascii=False)
                
                self.stats["pages"]["with_acl"] += 1
                
                # Update ACL stats
                perm_key = str(permission)
                if perm_key not in self.stats["acl_summary"]["permission_distribution"]:
                    self.stats["acl_summary"]["permission_distribution"][perm_key] = 0
                self.stats["acl_summary"]["permission_distribution"][perm_key] += 1
                
                # ACL by namespace
                if namespace not in self.stats["acl_summary"]["by_namespace"]:
                    self.stats["acl_summary"]["by_namespace"][namespace] = {"pages": 0, "permission_levels": {}}
                self.stats["acl_summary"]["by_namespace"][namespace]["pages"] += 1
                ns_perms = self.stats["acl_summary"]["by_namespace"][namespace]["permission_levels"]
                ns_perms[perm_key] = ns_perms.get(perm_key, 0) + 1
                
                if is_teacher_likely:
                    self.stats["acl_summary"]["teacher_likely_pages"] += 1
                else:
                    self.stats["acl_summary"]["public_pages"] += 1
            
            # 4.5 Fetch and save page history (revision history)
            if self.config.content.fetch_history:
                page_history = self.client.get_page_history(page_id)
                if page_history:
                    history_data = {
                        "page_id": page_id,
                        "fetch_timestamp": datetime.now().isoformat(),
                        "revision_count": len(page_history),
                        "revisions": page_history
                    }
                    history_path = self.paths["page_history"] / f"{safe_name}_history.json"
                    with open(history_path, 'w', encoding='utf-8') as f:
                        json.dump(history_data, f, indent=2, ensure_ascii=False)
                    self.stats["pages"]["with_history"] += 1
            
            # 4.6 Fetch and save page backlinks (incoming links)
            if self.config.content.fetch_backlinks:
                backlinks = self.client.get_page_backlinks(page_id)
                backlinks_data = {
                    "page_id": page_id,
                    "fetch_timestamp": datetime.now().isoformat(),
                    "backlink_count": len(backlinks),
                    "backlinks": backlinks
                }
                backlinks_path = self.paths["page_backlinks"] / f"{safe_name}_backlinks.json"
                with open(backlinks_path, 'w', encoding='utf-8') as f:
                    json.dump(backlinks_data, f, indent=2, ensure_ascii=False)
                self.stats["pages"]["with_backlinks"] += 1
                
                # Track backlinks for orphan page detection
                for linking_page in backlinks:
                    self._internal_link_targets[page_id] += 1
            
            # 5. Fetch HTML and extract links (if enabled)
            html_size = 0
            if self.config.content.fetch_html:
                page_html = self.client.get_page_html(page_id)
                if page_html:
                    html_size = len(page_html.encode('utf-8'))
                    self.stats["pages"]["total_html_bytes"] += html_size
                    
                    # Save HTML
                    html_path = self.paths["page_html"] / f"{safe_name}.html"
                    with open(html_path, 'w', encoding='utf-8') as f:
                        f.write(page_html)
                    self.stats["pages"]["with_html"] += 1
                    
                    # Extract and save links (if enabled)
                    if self.config.content.fetch_links:
                        links_data = self.link_extractor.extract_links(page_html, page_id)
                        links_path = self.paths["page_links"] / f"{safe_name}_links.json"
                        with open(links_path, 'w', encoding='utf-8') as f:
                            json.dump(links_data, f, indent=2, ensure_ascii=False)
                        
                        self.stats["pages"]["with_links"] += 1
                        
                        # Detailed link statistics
                        internal_count = links_data["summary"]["internal_count"]
                        external_count = links_data["summary"]["external_count"]
                        media_count = links_data["summary"]["media_count"]
                        interwiki_count = links_data["summary"].get("interwiki_count", 0)
                        mailto_count = links_data["summary"].get("mailto_count", 0)
                        total_links = links_data["summary"].get("total_links", internal_count + external_count + media_count)
                        
                        self.stats["links"]["internal_total"] += internal_count
                        self.stats["links"]["external_total"] += external_count
                        self.stats["links"]["media_total"] += media_count
                        self.stats["links"]["interwiki_total"] += interwiki_count
                        self.stats["links"]["mailto_total"] += mailto_count
                        
                        # Track page link counts
                        self._page_link_counts.append({"id": page_id, "total": total_links, "internal": internal_count})
                        
                        # Track internal link targets
                        for link in links_data.get("internal_links", []):
                            target = link.get("target", "")
                            if target:
                                self._internal_link_targets[target] += 1
                            # Track broken links
                            if not link.get("exists", True):
                                self.stats["links"]["broken_links"] += 1
                        
                        # Track external domains
                        for link in links_data.get("external_links", []):
                            href = link.get("href", "")
                            match = re.search(r'https?://([^/]+)', href)
                            if match:
                                domain = match.group(1)
                                self._external_domains[domain] += 1
            
            # 6. Save combined raw response (if enabled)
            if self.config.output.save_raw_responses:
                combined_data = {
                    "page_id": page_id,
                    "fetch_time": datetime.now().isoformat(),
                    "list_entry": page,
                    "page_info": page_info,
                    "content_length": content_size,
                    "html_length": html_size,
                }
                complete_path = self.paths["raw_json"] / f"{safe_name}_complete.json"
                with open(complete_path, 'w', encoding='utf-8') as f:
                    json.dump(combined_data, f, indent=2, ensure_ascii=False)
            
            self.stats["pages"]["successful"] += 1
            
            # Add to manifest
            page_entry = PageEntry(
                id=page_id,
                revision=page_info.get("revision", 0),
                content_hash=self.manifest.compute_content_hash(page_content),
                size_bytes=content_size,
                namespace=page_id.split(":")[0] if ":" in page_id else "root",
                has_html=self.config.content.fetch_html and html_size > 0,
                has_history=self.config.content.fetch_history,
                has_backlinks=self.config.content.fetch_backlinks,
            )
            self.manifest.add_page(page_entry)
            
            return True
        
        except UserAbortError:
            raise  # User chose to abort - propagate
        except PermanentError as e:
            # HTTP 4xx - API method not available
            self.stats["pages"]["failed"] += 1
            self.stats["errors"].append({
                "type": "page_fetch_permanent",
                "page_id": page_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            return False
        except TransientError as e:
            # Timeout/network - might work later
            self.stats["pages"]["failed"] += 1
            self.stats["errors"].append({
                "type": "page_fetch_transient",
                "page_id": page_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            return False
        except SkipItemError as e:
            # Generic skip
            self.stats["pages"]["failed"] += 1
            self.stats["errors"].append({
                "type": "page_fetch_skipped",
                "page_id": page_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            return False
        except Exception as e:
            self.stats["pages"]["failed"] += 1
            self.stats["errors"].append({
                "type": "page_fetch",
                "page_id": page_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            return False
    
    def _permission_name(self, level: int) -> str:
        """Convert permission level to name"""
        names = {0: "none", 1: "read", 2: "edit", 4: "create", 8: "upload", 16: "delete", 255: "admin"}
        return names.get(level, f"unknown-{level}")
    
    def collect_recent_changes(self, timestamp: int = 0) -> None:
        """
        Collect wiki-wide recent changes for pages and media.
        
        Args:
            timestamp: Only show changes newer than this Unix timestamp (0 = all)
        """
        if not self.config.content.fetch_recent_changes:
            return
        
        self.log("\n[7.5/10] Collecting wiki-wide recent changes...")
        self.log("-" * 50)
        
        # Collect recent page changes
        page_changes = self.client.get_recent_page_changes(timestamp)
        page_changes_data = {
            "fetch_timestamp": datetime.now().isoformat(),
            "since_timestamp": timestamp,
            "total_changes": len(page_changes),
            "changes": page_changes
        }
        
        page_changes_path = self.paths["changes"] / "recent_page_changes.json"
        with open(page_changes_path, 'w', encoding='utf-8') as f:
            json.dump(page_changes_data, f, indent=2, ensure_ascii=False)
        
        self.log(f"  Page changes: {len(page_changes)}")
        
        # Collect recent media changes
        media_changes = self.client.get_recent_media_changes(timestamp)
        media_changes_data = {
            "fetch_timestamp": datetime.now().isoformat(),
            "since_timestamp": timestamp,
            "total_changes": len(media_changes),
            "changes": media_changes
        }
        
        media_changes_path = self.paths["changes"] / "recent_media_changes.json"
        with open(media_changes_path, 'w', encoding='utf-8') as f:
            json.dump(media_changes_data, f, indent=2, ensure_ascii=False)
        
        self.log(f"  Media changes: {len(media_changes)}")
        
        # Update stats
        self.stats["changes"] = {
            "page_changes": len(page_changes),
            "media_changes": len(media_changes),
            "since_timestamp": timestamp
        }
    
    def run_full_fetch(self, download_media: bool = True):
        """Execute the complete fetch process
        
        Args:
            download_media: If True, download actual media files (can be slow for large wikis)
        """
        self.stats["fetch_info"]["start_time"] = datetime.now().isoformat()
        
        # Start progress tracking
        if self.tracker:
            self.tracker.start(total_steps=10)
        
        self.log("=" * 60)
        self.log("EXTENDED WIKI FETCH - 100% Coverage Goal")
        self.log("=" * 60)
        self.log(f"Output: {self.base_path}")
        self.log(f"Started: {self.stats['fetch_info']['start_time']}")
        self.log(f"\nConfiguration:")
        self.log(f"  Max namespace depth: {self.config.max_namespace_depth}")
        self.log(f"  Media from listings: {self.config.media.from_listings}")
        self.log(f"  Media from page links: {self.config.media.from_page_links}")
        self.log(f"  Download media files: {download_media}")
        
        # Setup
        self.setup_directories()
        
        # 1. Fetch pages
        pages = self.fetch_all_pages()
        
        # 2. Extract top-level namespaces (for stats)
        namespaces = self.extract_namespaces(pages)
        
        # 3. Extract ALL namespace prefixes for media scanning
        all_namespaces = self.extract_all_namespaces_for_media(pages)
        
        # 4. Fetch media inventory from all namespaces
        media = self.fetch_media_inventory(all_namespaces)
        
        # Save media inventory with stats
        inventory_path = self.paths["media"] / "media_inventory.json"
        with open(inventory_path, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "total_from_listings": len(media),
                "namespaces_scanned": len(all_namespaces),
                "by_extension": self.stats["media"]["by_extension"],
                "by_type": self.stats["media"]["by_type"],
                "media": media
            }, f, indent=2, ensure_ascii=False)
        
        # 5. Fetch all page data first (to get links)
        if self.tracker:
            self.tracker.set_step("[7/10] Fetching page content", 7)
        self.log("\n[7/10] Fetching page content, metadata, ACL, and links...")
        self.log("-" * 50)
        
        total = len(pages)
        progress_interval = self.config.batch_progress_interval
        request_delay = self.config.delay_between_requests
        
        for i, page in enumerate(pages, 1):
            if i % progress_interval == 0 or i == total:
                self.log(f"  Progress: {i}/{total} pages...")
                # Update progress tracker
                if self.tracker:
                    self.tracker.update_progress(i, total, f"Seiten: {i}/{total}")
            
            self.fetch_and_save_page(page)
            time.sleep(request_delay)
        
        # 6. Collect additional media from page links
        extra_media = self.collect_media_from_page_links()
        all_media = media + extra_media
        
        # 7. Download media files (optional but recommended)
        if download_media:
            self.download_media_files(all_media)
        else:
            self.log("\n[6/9] Skipping media downloads (--no-media)")
        
        # 7.5 Collect wiki-wide recent changes
        self.collect_recent_changes()
        
        # 8. Finalize statistics
        if self.tracker:
            self.tracker.set_step("[8/10] Finalizing statistics", 8)
        self.log("\n[8/10] Finalizing statistics...")
        self.log("-" * 50)
        self._finalize_statistics()
        
        # 9. Create wiki inventory and reports
        if self.tracker:
            self.tracker.set_step("[9/10] Creating inventory and reports", 9)
        self.log("\n[9/10] Creating inventory and reports...")
        self.log("-" * 50)
        self._create_wiki_inventory()
        
        self.stats["fetch_info"]["end_time"] = datetime.now().isoformat()
        
        # Calculate duration
        start = datetime.fromisoformat(self.stats["fetch_info"]["start_time"])
        end = datetime.fromisoformat(self.stats["fetch_info"]["end_time"])
        self.stats["fetch_info"]["duration_seconds"] = (end - start).total_seconds()
        
        # Save main statistics
        stats_path = self.base_path / "fetch_statistics.json"
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)
        
        # Save fetch manifest for incremental updates
        self._save_manifest()
        
        # Save detailed analysis report
        if self.config.output.generate_report:
            self._save_analysis_report()
        
        # Print summary
        self.print_summary()
        
        # Mark progress as complete
        if self.tracker:
            final_stats = {
                "pages_total": self.stats["pages"]["total"],
                "pages_successful": self.stats["pages"]["successful"],
                "pages_failed": self.stats["pages"]["failed"],
                "media_total": self.stats["media"]["total"],
                "media_downloaded": self.stats["media"]["downloaded"],
                "duration_seconds": self.stats["fetch_info"]["duration_seconds"]
            }
            success = self.stats["pages"]["failed"] == 0
            self.tracker.complete(stats=final_stats, success=success)
        
        return self.stats
    
    def _finalize_statistics(self):
        """Finalize and calculate derived statistics"""
        # Page size averages
        if self.stats["pages"]["successful"] > 0:
            self.stats["pages"]["avg_content_size"] = (
                self.stats["pages"]["total_content_bytes"] / self.stats["pages"]["successful"]
            )
            self.stats["pages"]["avg_html_size"] = (
                self.stats["pages"]["total_html_bytes"] / self.stats["pages"]["with_html"]
                if self.stats["pages"]["with_html"] > 0 else 0
            )

        if self.stats["pages"]["smallest_page"]["size"] == float("inf"):
            self.stats["pages"]["smallest_page"] = {"id": "", "size": 0}
        
        # Link statistics
        if self.stats["pages"]["with_links"] > 0:
            total_links = (
                self.stats["links"]["internal_total"] + 
                self.stats["links"]["external_total"] + 
                self.stats["links"]["media_total"]
            )
            self.stats["links"]["avg_links_per_page"] = total_links / self.stats["pages"]["with_links"]
        
        # Most linked pages (top 20)
        sorted_targets = sorted(
            self._internal_link_targets.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:20]
        self.stats["links"]["most_linked_pages"] = dict(sorted_targets)
        
        # External domains (top 20)
        sorted_domains = sorted(
            self._external_domains.items(),
            key=lambda x: x[1],
            reverse=True
        )[:20]
        self.stats["links"]["external_domains"] = dict(sorted_domains)
        
        # Pages with most links (top 10)
        sorted_pages = sorted(
            self._page_link_counts,
            key=lambda x: x["total"],
            reverse=True
        )[:10]
        self.stats["links"]["pages_with_most_links"] = sorted_pages
        
        # Find orphan pages (pages not linked from anywhere)
        all_page_ids = set(p["id"] for p in self._page_sizes)
        linked_pages = set(self._internal_link_targets.keys())
        orphan_pages = all_page_ids - linked_pages - {"start"}
        self.stats["wiki_structure"]["orphan_pages"] = sorted(list(orphan_pages))[:50]
        
        self.log(f"  Calculated averages and rankings")
        
        # Build media usage index
        self._build_media_usage_index()
    
    def _build_media_usage_index(self) -> None:
        """Build index mapping media files to pages that reference them"""
        self.log(f"  Building media usage index...")
        
        # Collect all media references from page_links
        media_usage: Dict[str, Dict[str, Any]] = {}
        
        # Also track media from listings (no page reference)
        listed_media: Set[str] = set()
        for media_file in self.paths["media_metadata"].glob("*_info.json"):
            try:
                with open(media_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    media_id = data.get("id", "")
                    if media_id:
                        listed_media.add(media_id)
                        if media_id not in media_usage:
                            media_usage[media_id] = {
                                "referenced_by": [],
                                "reference_count": 0,
                                "discovery_method": data.get("discovery_method", "listing"),
                                "size_bytes": data.get("size_bytes", 0)
                            }
            except (json.JSONDecodeError, IOError):
                pass
        
        # Scan all page_links files for media references
        total_references = 0
        for links_file in self.paths["page_links"].glob("*_links.json"):
            try:
                with open(links_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                page_id = data.get("page_id", "")
                media_links = data.get("media_links", [])
                
                for link in media_links:
                    media_id = link.get("media_id", "")
                    if not media_id:
                        continue
                    
                    if media_id not in media_usage:
                        media_usage[media_id] = {
                            "referenced_by": [],
                            "reference_count": 0,
                            "discovery_method": "link",
                            "size_bytes": 0
                        }
                    
                    if page_id and page_id not in media_usage[media_id]["referenced_by"]:
                        media_usage[media_id]["referenced_by"].append(page_id)
                    media_usage[media_id]["reference_count"] += 1
                    total_references += 1
                    
            except (json.JSONDecodeError, IOError):
                pass
        
        # Find orphan media (in listings but never referenced)
        orphan_media = []
        for media_id, usage in media_usage.items():
            if usage["reference_count"] == 0 and media_id in listed_media:
                orphan_media.append(media_id)
        
        # Most referenced media (top 20)
        most_referenced = sorted(
            [(mid, info["reference_count"]) for mid, info in media_usage.items() if info["reference_count"] > 0],
            key=lambda x: x[1],
            reverse=True
        )[:20]
        
        # Build index file
        index = {
            "generated_at": datetime.now().isoformat(),
            "total_media": len(media_usage),
            "total_references": total_references,
            "media_with_references": sum(1 for u in media_usage.values() if u["reference_count"] > 0),
            "orphan_count": len(orphan_media),
            "media_usage": media_usage,
            "orphan_media": sorted(orphan_media)[:50],  # Limit to 50
            "most_referenced": [{"id": mid, "count": cnt} for mid, cnt in most_referenced]
        }
        
        # Save index
        index_path = self.base_path / "media_usage_index.json"
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        
        self.log(f"    Total media: {len(media_usage)}, with references: {index['media_with_references']}, orphans: {len(orphan_media)}")
    
    def _create_wiki_inventory(self):
        """Create comprehensive wiki inventory"""
        inventory = {
            "fetch_timestamp": datetime.now().isoformat(),
            "wiki_url": self.stats["fetch_info"]["api_url"],
            "config_used": self.stats["fetch_info"]["config"],
            "summary": {
                "total_pages": self.stats["pages"]["total"],
                "successful_pages": self.stats["pages"]["successful"],
                "failed_pages": self.stats["pages"]["failed"],
                "filtered_out": self.stats["pages"]["filtered_out"],
                "total_namespaces": self.stats["namespaces"]["total"],
                "namespaces_scanned_for_media": self.stats["media"]["namespaces_scanned"],
                "total_media_from_listings": self.stats["media"]["listed"],
                "total_media_from_links": self.stats["media"]["from_links"],
                "total_media": self.stats["media"]["total"],
                "total_content_bytes": self.stats["pages"]["total_content_bytes"],
                "total_media_bytes": self.stats["media"]["total_size_bytes"]
            },
            "namespaces": self.stats["namespaces"]["by_namespace"],
            "acl_summary": self.stats["acl_summary"],
            "media_summary": {
                "by_type": self.stats["media"]["by_type"],
                "by_extension": self.stats["media"]["by_extension"]
            },
            "link_summary": {
                "internal_total": self.stats["links"]["internal_total"],
                "external_total": self.stats["links"]["external_total"],
                "media_total": self.stats["links"]["media_total"],
                "broken_links": self.stats["links"]["broken_links"],
                "avg_per_page": self.stats["links"]["avg_links_per_page"]
            },
            "wiki_structure": self.stats["wiki_structure"]
        }
        
        inventory_path = self.base_path / "wiki_inventory.json"
        with open(inventory_path, 'w', encoding='utf-8') as f:
            json.dump(inventory, f, indent=2, ensure_ascii=False)
        
        self.log(f"  Saved wiki inventory")
    
    def _get_recent_changes(self, limit: int = 30) -> List[Dict[str, Any]]:
        """Get most recently modified pages from metadata"""
        pages_with_dates: List[Dict[str, Any]] = []
        
        try:
            for info_file in self.paths["page_metadata"].glob("*_info.json"):
                if "_acl" in info_file.name:
                    continue
                try:
                    with open(info_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    # core.getPageInfo returns 'revision' as Unix timestamp
                    modified = data.get("revision", data.get("modified", data.get("lastModified", 0)))
                    # API returns 'id', fallback to 'name' or filename
                    page_id = data.get("id", data.get("name", info_file.stem.replace("_info", "").replace("_", ":")))
                    if modified:
                        pages_with_dates.append({
                            "id": page_id,
                            "modified": modified,
                            "modified_date": datetime.fromtimestamp(modified).strftime("%Y-%m-%d %H:%M") if modified else "unknown"
                        })
                except Exception:
                    pass
        except Exception:
            pass
        
        # Sort by modified descending
        sorted_pages = sorted(pages_with_dates, key=lambda x: x.get("modified", 0), reverse=True)
        return sorted_pages[:limit]
    
    def _get_missing_media(self) -> List[str]:
        """Find media referenced but not downloaded"""
        downloaded_ids: Set[str] = set()
        
        try:
            for meta_file in self.paths["media_metadata"].glob("*_info.json"):
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    media_id = data.get("id", "")
                    if media_id:
                        downloaded_ids.add(media_id)
                except Exception:
                    pass
        except Exception:
            pass
        
        missing = self._media_from_links - downloaded_ids
        return sorted(list(missing))
    
    def _analyze_missing_media(self) -> List[Dict[str, str]]:
        """Analyze missing media and categorize by reason"""
        missing_list = self._get_missing_media()
        analyzed = []
        
        for media_id in missing_list:
            status = "UNKNOWN"
            reason = ""
            
            # Check if it's an external URL
            if media_id.startswith("http") or "%" in media_id:
                status = "EXTERNAL"
                reason = "External URL, not hosted on wiki"
            # Check if namespace suggests older/archived content
            elif ":archive:" in media_id or media_id.startswith("archive:"):
                status = "ARCHIVED"
                reason = "In archive namespace, may be intentionally removed"
            # Check if file extension suggests replacement (versioned files)
            elif any(v in media_id.lower() for v in ["_v1", "_v2", "_old", "_backup"]):
                status = "REPLACED"
                reason = "Likely replaced by newer version"
            # Check for common patterns of deleted content
            elif any(d in media_id.lower() for d in ["draft", "temp", "test"]):
                status = "DELETED"
                reason = "Temporary/test file, likely intentionally removed"
            else:
                status = "MISSING"
                reason = "Referenced but not available for download"
            
            analyzed.append({
                "media_id": media_id,
                "status": status,
                "reason": reason
            })
        
        return analyzed
    
    def _get_deepest_pages(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get pages with deepest namespace paths"""
        pages_with_depth = [
            {"id": p["id"], "depth": p["id"].count(":")}
            for p in self._page_sizes
        ]
        return sorted(pages_with_depth, key=lambda x: x["depth"], reverse=True)[:limit]
    
    def _save_manifest(self):
        """Save fetch manifest for incremental updates"""
        self.log("\n[9.5/10] Saving fetch manifest...")
        
        # Update manifest stats from fetch stats
        self.manifest.stats.fetch_type = "full"
        self.manifest.stats.started_at = self.stats["fetch_info"]["start_time"]
        self.manifest.stats.completed_at = self.stats["fetch_info"]["end_time"]
        self.manifest.stats.duration_seconds = self.stats["fetch_info"]["duration_seconds"]
        
        self.manifest.stats.pages_total = self.stats["pages"]["total"]
        self.manifest.stats.pages_successful = self.stats["pages"]["successful"]
        self.manifest.stats.pages_failed = self.stats["pages"]["failed"]
        
        self.manifest.stats.media_total = self.stats["media"]["total"]
        self.manifest.stats.media_downloaded = self.stats["media"]["downloaded"]
        self.manifest.stats.media_failed = self.stats["media"]["download_failed"]
        self.manifest.stats.media_skipped = self.stats["media"]["download_skipped"]
        
        if "cache" in self.stats["media"]:
            self.manifest.stats.media_from_cache = self.stats["media"]["cache"]["hits"]
        
        self.manifest.stats.total_content_bytes = self.stats["pages"]["total_content_bytes"]
        self.manifest.stats.total_media_bytes = self.stats["media"]["total_size_bytes"]
        
        self.manifest.stats.error_count = len(self.stats["errors"])
        self.manifest.stats.errors = self.stats["errors"][:20]  # Limit stored errors
        
        # Update namespaces
        self.manifest.namespaces = self.stats["namespaces"]["list"]
        
        # Save manifest
        manifest_path = self.base_path / "fetch_manifest.json"
        self.manifest.save(manifest_path)
        
        self.log(f"  Saved manifest: {manifest_path}")
        self.log(f"    Pages: {self.manifest.page_count}")
        self.log(f"    Media: {self.manifest.media_count}")
    
    def _save_analysis_report(self):
        """Save detailed human-readable analysis report"""
        report_lines = [
            "=" * 70,
            "LEOWIKI ANALYSIS REPORT",
            f"Generated: {datetime.now().isoformat()}",
            "=" * 70,
            "",
            "## CONFIGURATION",
            f"Max namespace depth: {self.config.max_namespace_depth}",
            f"Recursive listing: {self.config.use_recursive_listing}",
            f"Search discovery: {self.config.use_search_discovery}",
            f"Media from listings: {self.config.media.from_listings}",
            f"Media from page links: {self.config.media.from_page_links}",
            "",
            "## OVERVIEW",
            f"Total Pages: {self.stats['pages']['total']}",
            f"Total Media Files: {self.stats['media']['total']}",
            f"  - From listings: {self.stats['media']['listed']}",
            f"  - From page links: {self.stats['media']['from_links']}",
            f"Total Namespaces: {self.stats['namespaces']['total']}",
            f"Namespaces Scanned for Media: {self.stats['media']['namespaces_scanned']}",
            f"Total Content Size: {format_bytes(self.stats['pages']['total_content_bytes'])}",
            f"Total Media Size: {format_bytes(self.stats['media']['total_size_bytes'])}",
            "",
            "## PAGE STATISTICS",
            f"Successful: {self.stats['pages']['successful']}",
            f"Failed: {self.stats['pages']['failed']}",
            f"Filtered Out: {self.stats['pages']['filtered_out']}",
            f"Empty Pages: {self.stats['pages']['empty_pages']}",
            f"Average Content Size: {format_bytes(int(self.stats['pages']['avg_content_size']))}",
            f"Largest Page: {self.stats['pages']['largest_page']['id']} ({format_bytes(self.stats['pages']['largest_page']['size'])})",
            f"Smallest Page: {self.stats['pages']['smallest_page']['id']} ({format_bytes(self.stats['pages']['smallest_page']['size'])})",
            "",
            "Size Distribution:",
            f"  Tiny (0-1KB): {self.stats['pages']['size_distribution']['tiny_0_1kb']}",
            f"  Small (1-5KB): {self.stats['pages']['size_distribution']['small_1_5kb']}",
            f"  Medium (5-20KB): {self.stats['pages']['size_distribution']['medium_5_20kb']}",
            f"  Large (20-100KB): {self.stats['pages']['size_distribution']['large_20_100kb']}",
            f"  Huge (100KB+): {self.stats['pages']['size_distribution']['huge_100kb_plus']}",
            "",
            "## MEDIA FILES",
            f"Total Files: {self.stats['media']['total']}",
            f"Downloaded: {self.stats['media']['downloaded']}",
            f"Skipped: {self.stats['media']['download_skipped']}",
            f"Failed: {self.stats['media']['download_failed']}",
            f"Total Size: {format_bytes(self.stats['media']['total_size_bytes'])}",
            "",
            "By Type:",
        ]
        
        for type_name, type_data in self.stats["media"]["by_type"].items():
            if type_data["count"] > 0:
                report_lines.append(
                    f"  {type_name.title()}: {type_data['count']} files ({format_bytes(type_data['size'])})"
                )
                if type_data["extensions"]:
                    report_lines.append(f"    Extensions: {', '.join(type_data['extensions'])}")
        
        # Detailed extension breakdown
        report_lines.extend([
            "",
            "By Extension (detailed):",
        ])
        
        # Sort extensions by count descending
        ext_data = self.stats["media"]["by_extension"]
        sorted_exts = sorted(ext_data.items(), key=lambda x: x[1]["count"], reverse=True)
        
        # Header
        report_lines.append(f"  {'Ext':<8} {'Count':>6} {'Total Size':>12} {'Avg Size':>10}")
        report_lines.append(f"  {'-'*8} {'-'*6} {'-'*12} {'-'*10}")
        
        for ext, data in sorted_exts:
            count = data["count"]
            total_size = data["size"]
            avg_size = total_size // count if count > 0 else 0
            report_lines.append(
                f"  {ext:<8} {count:>6} {format_bytes(total_size):>12} {format_bytes(avg_size):>10}"
            )
        
        report_lines.extend([
            "",
            "## NAMESPACES",
            f"Total Top-Level: {self.stats['namespaces']['total']}",
            f"Max Depth: {self.stats['namespaces']['max_depth']}",
            f"Total Scanned for Media: {self.stats['media']['namespaces_scanned']}",
            "",
            "Pages per Namespace:",
        ])
        
        for ns, data in sorted(self.stats["namespaces"]["by_namespace"].items(), 
                               key=lambda x: x[1]["page_count"], reverse=True):
            has_start = "[start]" if data.get("has_start_page") else ""
            media_count = data.get("media_count", 0)
            report_lines.append(f"  {ns}: {data['page_count']} pages, {media_count} media {has_start}")
        
        report_lines.extend([
            "",
            "## LINK ANALYSIS",
            f"Internal Links: {self.stats['links']['internal_total']}",
            f"External Links: {self.stats['links']['external_total']}",
            f"Media References: {self.stats['links']['media_total']}",
            f"Broken Links: {self.stats['links']['broken_links']}",
            f"Average Links per Page: {self.stats['links']['avg_links_per_page']:.1f}",
            "",
            "Most Linked Pages (Top 10):",
        ])
        
        for page, count in list(self.stats["links"]["most_linked_pages"].items())[:10]:
            report_lines.append(f"  {page}: {count} incoming links")
        
        report_lines.extend([
            "",
            "External Domains (Top 10):",
        ])
        
        for domain, count in list(self.stats["links"]["external_domains"].items())[:10]:
            report_lines.append(f"  {domain}: {count} links")
        
        if self.stats["wiki_structure"]["orphan_pages"]:
            report_lines.extend([
                "",
                f"Orphan Pages (not linked from anywhere, first 20):",
            ])
            for page in self.stats["wiki_structure"]["orphan_pages"][:20]:
                report_lines.append(f"  - {page}")
        
        report_lines.extend([
            "",
            "## ACL SUMMARY",
            f"Teacher-likely Pages: {self.stats['acl_summary']['teacher_likely_pages']}",
            f"Public Pages: {self.stats['acl_summary']['public_pages']}",
            "",
            "ACL by Namespace:",
        ])
        
        # Detailed ACL per namespace
        for ns, data in sorted(self.stats["acl_summary"]["by_namespace"].items()):
            perm_levels = data.get("permission_levels", {})
            perm_str = ", ".join([f"lvl{k}:{v}" for k, v in sorted(perm_levels.items())])
            report_lines.append(f"  {ns}: {data.get('pages', 0)} pages ({perm_str})")
        
        # Recent changes section
        report_lines.extend([
            "",
            f"## RECENT CHANGES (Top {self.config.output.recent_changes_count})",
        ])
        
        recent_changes = self._get_recent_changes(self.config.output.recent_changes_count)
        if recent_changes:
            for change in recent_changes:
                report_lines.append(f"  {change['modified_date']} - {change['id']}")
        else:
            report_lines.append("  No modification timestamps available")
        
        # Deepest pages section
        report_lines.extend([
            "",
            f"## DEEPEST NAMESPACE PATHS (Top {self.config.output.deepest_pages_count})",
        ])
        
        deepest_pages = self._get_deepest_pages(self.config.output.deepest_pages_count)
        if deepest_pages:
            for page in deepest_pages:
                report_lines.append(f"  [{page['depth']}] {page['id']}")
        else:
            report_lines.append("  No pages with namespace depth found")
        
        # Missing media section with detailed analysis
        report_lines.extend([
            "",
            "## MISSING MEDIA ANALYSIS",
        ])
        
        missing_analyzed = self._analyze_missing_media()
        if missing_analyzed:
            # Group by status
            by_status: Dict[str, List] = {}
            for item in missing_analyzed:
                status = item["status"]
                if status not in by_status:
                    by_status[status] = []
                by_status[status].append(item)
            
            report_lines.append(f"  Total missing: {len(missing_analyzed)}")
            report_lines.append("")
            
            # Status counts
            for status, items in sorted(by_status.items()):
                report_lines.append(f"  {status}: {len(items)}")
            
            report_lines.append("")
            report_lines.append(f"  {'Media ID':<45} {'Status':<10} {'Reason'}")
            report_lines.append(f"  {'-'*45} {'-'*10} {'-'*30}")
            
            for item in missing_analyzed[:25]:
                media_short = item["media_id"][:43] if len(item["media_id"]) > 43 else item["media_id"]
                report_lines.append(
                    f"  {media_short:<45} {item['status']:<10} {item['reason'][:30]}"
                )
            
            if len(missing_analyzed) > 25:
                report_lines.append(f"  ... and {len(missing_analyzed) - 25} more")
        else:
            report_lines.append("  All referenced media downloaded successfully!")
        
        # Errors section
        report_lines.extend([
            "",
            "## ERRORS",
            f"Total Errors: {len(self.stats['errors'])}",
        ])
        
        if self.stats["errors"]:
            for err in self.stats["errors"][:10]:
                err_type = err.get("type", "unknown")
                err_id = err.get("page_id", err.get("media_id", "unknown"))
                report_lines.append(f"  [{err_type}] {err_id}: {err.get('error', 'unknown')[:60]}")
        
        report_lines.extend([
            "",
            "=" * 70,
        ])
        
        report_path = self.base_path / "wiki_analysis_report.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(report_lines))
        
        self.log(f"  Saved analysis report")
    
    def print_summary(self):
        """Print comprehensive fetch summary with colored section headers."""
        sep = "=" * 70
        self.log("\n" + style(sep, "cyan"))
        self.log(style("FETCH COMPLETE - SUMMARY", "bold", "bright_cyan"))
        self.log(style(sep, "cyan"))
        
        self.log(style("\n[PAGES]", "cyan"))
        self.log(f"   Total: {self.stats['pages']['total']}")
        self.log(f"   Successful: {self.stats['pages']['successful']}")
        self.log(f"   Failed: {self.stats['pages']['failed']}")
        self.log(f"   Filtered out: {self.stats['pages']['filtered_out']}")
        self.log(f"   With history: {self.stats['pages']['with_history']}")
        self.log(f"   With backlinks: {self.stats['pages']['with_backlinks']}")
        self.log(f"   Content size: {format_bytes(self.stats['pages']['total_content_bytes'])}")
        self.log(f"   Avg size: {format_bytes(int(self.stats['pages']['avg_content_size']))}")
        self.log(f"   Largest: {self.stats['pages']['largest_page']['id']} ({format_bytes(self.stats['pages']['largest_page']['size'])})")
        
        self.log(style("\n[MEDIA FILES]", "cyan"))
        self.log(f"   From listings: {self.stats['media']['listed']}")
        self.log(f"   From page links: {self.stats['media']['from_links']}")
        self.log(f"   Total: {self.stats['media']['total']}")
        self.log(f"   Downloaded: {self.stats['media']['downloaded']}")
        self.log(f"   Skipped: {self.stats['media']['download_skipped']}")
        self.log(f"   Failed: {self.stats['media']['download_failed']}")
        self.log(f"   Total size: {format_bytes(self.stats['media']['total_size_bytes'])}")
        
        # Media by type summary
        for type_name, data in self.stats["media"]["by_type"].items():
            if data["count"] > 0:
                self.log(f"   {type_name.title()}: {data['count']} ({format_bytes(data['size'])})")
        
        self.log(style("\n[NAMESPACES]", "cyan"))
        self.log(f"   Top-level: {self.stats['namespaces']['total']}")
        self.log(f"   Max depth: {self.stats['namespaces']['max_depth']}")
        self.log(f"   Scanned for media: {self.stats['media']['namespaces_scanned']}")
        
        self.log(style("\n[LINKS]", "cyan"))
        self.log(f"   Internal: {self.stats['links']['internal_total']}")
        self.log(f"   External: {self.stats['links']['external_total']}")
        self.log(f"   Media refs: {self.stats['links']['media_total']}")
        self.log(f"   Broken: {self.stats['links']['broken_links']}")
        self.log(f"   Avg per page: {self.stats['links']['avg_links_per_page']:.1f}")
        
        self.log(style("\n[ACL]", "cyan"))
        self.log(f"   Teacher-likely: {self.stats['acl_summary']['teacher_likely_pages']}")
        self.log(f"   Public: {self.stats['acl_summary']['public_pages']}")
        
        if "changes" in self.stats:
            self.log(style("\n[RECENT CHANGES]", "cyan"))
            self.log(f"   Page changes: {self.stats['changes'].get('page_changes', 0)}")
            self.log(f"   Media changes: {self.stats['changes'].get('media_changes', 0)}")
        
        self.log(style("\n[TIMING]", "cyan"))
        self.log(f"   Duration: {self.stats['fetch_info']['duration_seconds']:.1f} seconds")
        self.log(f"   Output: {self.base_path}")
        
        if self.stats["errors"]:
            self.log(style(f"\n[ERRORS]: {len(self.stats['errors'])}", "red"))
            for err in self.stats["errors"][:5]:
                err_id = err.get('page_id', err.get('media_id', 'unknown'))
                self.log(f"   - {err_id}: {err['error'][:50]}")
        
        self.log("\n" + style(sep, "cyan"))
        self.log("See wiki_analysis_report.txt for detailed analysis")
        self.log(style(sep, "cyan"))


def main():
    """Main entry point"""
    global _current_fetcher
    import argparse

    if "-h" in sys.argv or "--help" in sys.argv:
        set_use_color("--no-color" not in sys.argv)
        enable_windows_ansi()
        print_help_banner(
            what="Fetches a full DokuWiki via JSON-RPC: pages, ACL, links, history, backlinks, media. Writes to data/fetched/<dir>. Ctrl+C shows progress.",
            usage="python fetch_full_wiki_extended.py [output_dir] [OPTIONS]",
            parameters="output_dir   Optional. Name of output dir under data/fetched. Default: fetched_at_<YYYYMMDD_HHMMSS>.",
            options="-h, --help       Show this help and exit.\n--no-media       Do not download media; only build media inventory.\n--no-cache       Disable cache (always download fresh).\n--quiet          Suppress verbose output.\n--auto-skip      Non-interactive: auto-skip permanent errors (4xx).\n--no-color       Disable colored output.\n--show-manifest PATH   Show manifest summary and exit.\n--verify-manifest PATH   Verify manifest integrity and exit.\n--compare-manifests CURRENT PREVIOUS   Compare two manifests.",
            examples="# Full fetch, auto-named output dir\npython fetch_full_wiki_extended.py\n# Pages only, no media\npython fetch_full_wiki_extended.py --no-media\n# Help\npython fetch_full_wiki_extended.py -h",
            configuration="config/env.yaml (API URL, token, timeouts, output pattern).",
            output="data/fetched/<output_dir>/: page_content, media, namespaces, fetch_manifest.json, wiki_analysis_report.txt.",
            exit_codes="0   All pages fetched successfully.\n1   One or more pages failed.\n130 Interrupted (Ctrl+C).",
        )
        sys.exit(0)

    # Register Ctrl+C handler for clean exit
    signal.signal(signal.SIGINT, _sigint_handler)

    parser = argparse.ArgumentParser(description="Extended wiki fetch with full coverage")
    parser.add_argument("output_dir", nargs="?", default=None,
                        help="Output directory name (default: auto-generated from pattern)")
    parser.add_argument("--no-media", action="store_true",
                        help="Skip downloading media files (only create inventory)")
    parser.add_argument("--no-cache", action="store_true",
                        help="Disable cache (always download fresh, ignore archived files)")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress verbose output")
    parser.add_argument("--auto-skip", action="store_true",
                        help="Non-interactive mode: auto-skip all permanent errors (4xx)")
    parser.add_argument("--job-id", type=str, default=None,
                        help="Job ID for progress tracking (used by orchestrator)")
    parser.add_argument("--no-manifest", action="store_true",
                        help="Skip manifest generation (for testing)")
    parser.add_argument("--show-manifest", type=str, metavar="PATH",
                        help="Show manifest summary and exit")
    parser.add_argument("--verify-manifest", type=str, metavar="PATH",
                        help="Verify manifest integrity and exit")
    parser.add_argument("--compare-manifests", nargs=2, metavar=("CURRENT", "PREVIOUS"),
                        help="Compare two manifests and show changes")
    add_no_color_arg(parser)
    
    args = parser.parse_args()
    apply_color_from_args(args)
    
    # Handle manifest-only commands
    if args.show_manifest:
        from manifest import FetchManifest
        manifest = FetchManifest.load(Path(args.show_manifest))
        summary = manifest.get_summary()
        sep60 = "=" * 60
        print(style(sep60, "cyan"))
        print(style(f"MANIFEST: {summary['fetch_id']}", "bold", "bright_cyan"))
        print(style(sep60, "cyan"))
        print(f"Wiki URL:     {summary['wiki_url']}")
        print(f"Created:      {summary['created_at']}")
        print(f"Updated:      {summary['updated_at']}")
        print(f"Pages:        {summary['pages']['total']}")
        print(f"  By status:  {summary['pages']['by_status']}")
        print(f"Media:        {summary['media']['total']}")
        print(f"  By status:  {summary['media']['by_status']}")
        print(f"Namespaces:   {summary['namespaces']}")
        print(style(sep60, "cyan"))
        return 0
    
    if args.verify_manifest:
        from manifest import FetchManifest
        manifest = FetchManifest.load(Path(args.verify_manifest))
        errors = manifest.validate()
        if errors:
            print(style("[ERROR] Manifest validation failed:", "red", "bold"))
            for err in errors:
                print(f"  - {err}")
            return 1
        print(style(f"[OK] Manifest valid: {manifest.fetch_id}", "green"))
        print(f"     Pages: {manifest.page_count}, Media: {manifest.media_count}")
        return 0
    
    if args.compare_manifests:
        from manifest import FetchManifest
        current = FetchManifest.load(Path(args.compare_manifests[0]))
        previous = FetchManifest.load(Path(args.compare_manifests[1]))
        
        page_changes = current.get_page_changes(previous)
        media_changes = current.get_media_changes(previous)
        
        sep60 = "=" * 60
        print(style(sep60, "cyan"))
        print(style("MANIFEST COMPARISON", "bold", "bright_cyan"))
        print(style(sep60, "cyan"))
        print(f"Current:  {current.fetch_id} ({current.page_count} pages)")
        print(f"Previous: {previous.fetch_id} ({previous.page_count} pages)")
        print()
        print(style("PAGE CHANGES:", "cyan"))
        print(f"  Added:     {len(page_changes['added'])}")
        print(f"  Modified:  {len(page_changes['modified'])}")
        print(f"  Deleted:   {len(page_changes['deleted'])}")
        print(f"  Unchanged: {len(page_changes['unchanged'])}")
        print()
        print(style("MEDIA CHANGES:", "cyan"))
        print(f"  Added:     {len(media_changes['added'])}")
        print(f"  Modified:  {len(media_changes['modified'])}")
        print(f"  Deleted:   {len(media_changes['deleted'])}")
        print(f"  Unchanged: {len(media_changes['unchanged'])}")
        print(style(sep60, "cyan"))
        return 0
    
    # Get job_id from args or environment
    job_id = args.job_id or os.environ.get("JOB_ID")
    
    fetcher = ExtendedWikiFetcher(
        output_dir=args.output_dir, 
        verbose=not args.quiet,
        use_cache=not args.no_cache,
        interactive=not args.auto_skip,
        job_id=job_id
    )
    _current_fetcher = fetcher  # Set global reference for signal handler
    
    stats = fetcher.run_full_fetch(download_media=not args.no_media)
    
    # Exit code based on success
    return 0 if stats["pages"]["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
