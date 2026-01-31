"""
Resume interrupted wiki fetch.
Identifies failed pages/media and retries only those.

Usage:
    python resume_fetch.py <output_dir>
    python resume_fetch.py fetched_at_20251221_203927
"""
import os
import sys
import json
import time
import requests
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Set, Optional

# Add script directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from api_client import WikiAPIClient, PermanentError, TransientError, UserAbortError
from config import (
    OUTPUT_BASE_DIR, HEADERS, CA_CERT_PATH, TIMEOUT,
    API_FETCH_URL, get_fetch_config
)


def format_bytes(size_bytes: int) -> str:
    """Format bytes to human readable string"""
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


def sanitize_filename(name: str) -> str:
    """Sanitize page/media ID for use as filename"""
    return name.replace(":", "_").replace("/", "_").replace("\\", "_")


class ResumeFetcher:
    """Resumes an interrupted fetch by retrying failed items"""
    
    def __init__(self, output_dir: str, verbose: bool = True):
        self.base_path = Path(OUTPUT_BASE_DIR) / output_dir
        self.verbose = verbose
        self.config = get_fetch_config()
        self.client = WikiAPIClient(verbose=False, interactive=True)
        
        # Stats tracking
        self.resume_stats = {
            "resume_start": datetime.now().isoformat(),
            "original_fetch_dir": output_dir,
            "pages_retried": 0,
            "pages_recovered": 0,
            "pages_still_failed": 0,
            "media_retried": 0,
            "media_recovered": 0,
            "media_still_failed": 0,
            "new_errors": []
        }
        
        # Setup paths
        self.paths = {
            "page_content": self.base_path / "page_content",
            "page_metadata": self.base_path / "page_metadata",
            "page_html": self.base_path / "page_html",
            "page_links": self.base_path / "page_links",
            "raw_json": self.base_path / "raw_json",
            "media": self.base_path / "media",
            "media_metadata": self.base_path / "media" / "metadata",
        }
    
    def log(self, message: str):
        """Print message if verbose"""
        if self.verbose:
            print(message)
    
    def load_existing_stats(self) -> Optional[Dict]:
        """Load fetch_statistics.json from output directory"""
        stats_path = self.base_path / "fetch_statistics.json"
        if not stats_path.exists():
            self.log(f"ERROR: No fetch_statistics.json found in {self.base_path}")
            return None
        
        with open(stats_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def identify_failed_pages(self, stats: Dict) -> List[str]:
        """Extract page IDs that failed from errors list"""
        failed_pages = set()
        
        for error in stats.get("errors", []):
            error_type = error.get("type", "")
            if "page_fetch" in error_type:
                page_id = error.get("page_id", "")
                if page_id:
                    failed_pages.add(page_id)
        
        return sorted(failed_pages)
    
    def identify_failed_media(self, stats: Dict) -> List[str]:
        """Extract media IDs that failed from errors list"""
        failed_media = set()
        
        for error in stats.get("errors", []):
            error_type = error.get("type", "")
            if "media" in error_type:
                media_id = error.get("media_id", "")
                if media_id:
                    failed_media.add(media_id)
        
        return sorted(failed_media)
    
    def check_if_page_exists(self, page_id: str) -> bool:
        """Check if page content already exists"""
        safe_name = sanitize_filename(page_id)
        content_path = self.paths["page_content"] / f"{safe_name}.txt"
        return content_path.exists()
    
    def check_if_media_exists(self, media_id: str) -> bool:
        """Check if media file already exists"""
        # Media stored in namespace subdirectories
        if ":" in media_id:
            namespace = media_id.rsplit(":", 1)[0].replace(":", "/")
            filename = media_id.rsplit(":", 1)[1]
        else:
            namespace = ""
            filename = media_id
        
        media_path = self.paths["media"] / namespace / filename
        return media_path.exists()
    
    def retry_page(self, page_id: str) -> bool:
        """Retry fetching a single page"""
        safe_name = sanitize_filename(page_id)
        
        try:
            # Fetch page info
            page_info = self.client.get_page_info(page_id)
            
            # Save page info
            info_path = self.paths["page_metadata"] / f"{safe_name}_info.json"
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(page_info, f, indent=2, ensure_ascii=False)
            
            # Fetch content
            content = self.client.get_page_content(page_id)
            content_path = self.paths["page_content"] / f"{safe_name}.txt"
            with open(content_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Fetch HTML
            try:
                html = self.client.get_page_html(page_id)
                if html:
                    html_path = self.paths["page_html"] / f"{safe_name}.html"
                    with open(html_path, 'w', encoding='utf-8') as f:
                        f.write(html)
            except Exception:
                pass  # HTML optional
            
            # Fetch ACL
            try:
                acl_response = self.client.call("core.aclCheck", {"page": page_id})
                acl_level = acl_response.get("result", 0)
                acl_path = self.paths["page_metadata"] / f"{safe_name}_acl.json"
                with open(acl_path, 'w', encoding='utf-8') as f:
                    json.dump({"page_id": page_id, "permission_level": acl_level}, f, indent=2)
            except Exception:
                pass  # ACL optional
            
            return True
            
        except UserAbortError:
            raise
        except Exception as e:
            self.resume_stats["new_errors"].append({
                "type": "page_retry_failed",
                "page_id": page_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            return False
    
    def retry_media(self, media_id: str) -> bool:
        """Retry downloading a single media file"""
        # Determine namespace and filename
        if ":" in media_id:
            namespace = media_id.rsplit(":", 1)[0].replace(":", "/")
            filename = media_id.rsplit(":", 1)[1]
        else:
            namespace = ""
            filename = media_id
        
        # Create namespace directory
        ns_dir = self.paths["media"] / namespace
        ns_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = ns_dir / filename
        
        try:
            # Download via fetch.php
            url = f"{API_FETCH_URL}?media={media_id}"
            response = requests.get(
                url,
                headers=HEADERS,
                verify=CA_CERT_PATH,
                timeout=TIMEOUT * 2,  # Longer timeout for retry
                stream=True
            )
            response.raise_for_status()
            
            # Save file
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            file_size = file_path.stat().st_size
            
            # Save metadata
            safe_name = sanitize_filename(media_id)
            meta_path = self.paths["media_metadata"] / f"{safe_name}_info.json"
            metadata = {
                "id": media_id,
                "namespace": namespace,
                "filename": filename,
                "local_path": str(file_path.relative_to(self.base_path)),
                "size_bytes": file_size,
                "download_timestamp": datetime.now().isoformat(),
                "recovered_by": "resume_fetch"
            }
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            self.resume_stats["new_errors"].append({
                "type": "media_retry_failed",
                "media_id": media_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            return False
    
    def run_resume(self, retry_pages: bool = True, retry_media: bool = True) -> Dict:
        """Run the resume process"""
        self.log("=" * 60)
        self.log("RESUME FETCH")
        self.log("=" * 60)
        self.log(f"Output: {self.base_path}")
        self.log(f"Started: {self.resume_stats['resume_start']}")
        self.log("")
        
        # Load existing stats
        stats = self.load_existing_stats()
        if stats is None:
            return self.resume_stats
        
        original_errors = len(stats.get("errors", []))
        self.log(f"Original fetch had {original_errors} errors")
        self.log("")
        
        # Identify failed items
        failed_pages = self.identify_failed_pages(stats)
        failed_media = self.identify_failed_media(stats)
        
        self.log(f"Failed pages to retry: {len(failed_pages)}")
        self.log(f"Failed media to retry: {len(failed_media)}")
        self.log("")
        
        # Retry pages
        if retry_pages and failed_pages:
            self.log("[1/2] Retrying failed pages...")
            self.log("-" * 50)
            
            for i, page_id in enumerate(failed_pages, 1):
                # Skip if already recovered
                if self.check_if_page_exists(page_id):
                    self.log(f"  [{i}/{len(failed_pages)}] {page_id} - already exists, skipping")
                    continue
                
                self.log(f"  [{i}/{len(failed_pages)}] {page_id}...")
                self.resume_stats["pages_retried"] += 1
                
                try:
                    if self.retry_page(page_id):
                        self.resume_stats["pages_recovered"] += 1
                        self.log(f"    -> RECOVERED")
                    else:
                        self.resume_stats["pages_still_failed"] += 1
                        self.log(f"    -> STILL FAILED")
                except UserAbortError:
                    self.log("\nAborted by user")
                    break
                
                time.sleep(self.config.delay_between_requests)
        
        # Retry media
        if retry_media and failed_media:
            self.log("\n[2/2] Retrying failed media...")
            self.log("-" * 50)
            
            for i, media_id in enumerate(failed_media, 1):
                # Skip external URLs
                if media_id.startswith("http") or "%" in media_id:
                    self.log(f"  [{i}/{len(failed_media)}] {media_id[:50]} - external URL, skipping")
                    continue
                
                # Skip if already recovered
                if self.check_if_media_exists(media_id):
                    self.log(f"  [{i}/{len(failed_media)}] {media_id} - already exists, skipping")
                    continue
                
                self.log(f"  [{i}/{len(failed_media)}] {media_id}...")
                self.resume_stats["media_retried"] += 1
                
                if self.retry_media(media_id):
                    self.resume_stats["media_recovered"] += 1
                    self.log(f"    -> RECOVERED")
                else:
                    self.resume_stats["media_still_failed"] += 1
                    self.log(f"    -> STILL FAILED")
                
                time.sleep(self.config.delay_between_requests)
        
        # Save resume stats
        self.resume_stats["resume_end"] = datetime.now().isoformat()
        resume_stats_path = self.base_path / "resume_statistics.json"
        with open(resume_stats_path, 'w', encoding='utf-8') as f:
            json.dump(self.resume_stats, f, indent=2, ensure_ascii=False)
        
        # Print summary
        self.log("")
        self.log("=" * 60)
        self.log("RESUME COMPLETE")
        self.log("=" * 60)
        self.log(f"Pages: {self.resume_stats['pages_recovered']}/{self.resume_stats['pages_retried']} recovered")
        self.log(f"Media: {self.resume_stats['media_recovered']}/{self.resume_stats['media_retried']} recovered")
        self.log(f"New errors: {len(self.resume_stats['new_errors'])}")
        self.log(f"Stats saved: {resume_stats_path}")
        self.log("=" * 60)
        
        return self.resume_stats


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Resume interrupted wiki fetch")
    parser.add_argument("output_dir", help="Output directory name to resume (e.g. fetched_at_20251221_203927)")
    parser.add_argument("--no-pages", action="store_true", help="Skip retrying pages")
    parser.add_argument("--no-media", action="store_true", help="Skip retrying media")
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose output")
    
    args = parser.parse_args()
    
    fetcher = ResumeFetcher(args.output_dir, verbose=not args.quiet)
    
    try:
        stats = fetcher.run_resume(
            retry_pages=not args.no_pages,
            retry_media=not args.no_media
        )
        
        # Exit code based on success
        total_recovered = stats["pages_recovered"] + stats["media_recovered"]
        total_still_failed = stats["pages_still_failed"] + stats["media_still_failed"]
        
        return 0 if total_still_failed == 0 else 1
        
    except UserAbortError:
        print("\nFetch aborted by user")
        return 130


if __name__ == "__main__":
    sys.exit(main())
