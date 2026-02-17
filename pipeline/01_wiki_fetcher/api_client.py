"""
Simple API client for DokuWiki JSON-RPC
Focused on fetching and saving raw responses

Features:
- Intelligent retry logic distinguishing permanent vs transient errors
- Interactive error handling with user prompts
- Separate skip modes for different error types
"""

import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from config import API_FETCH_URL, API_URL, CA_CERT_PATH, HEADERS, MAX_RETRIES, RETRY_DELAY, TIMEOUT


class SkipItemError(Exception):
    """Raised when user chooses to skip an item"""

    pass


class PermanentError(SkipItemError):
    """HTTP 4xx - API method doesn't exist or invalid params, retry won't help"""

    pass


class TransientError(SkipItemError):
    """Timeout/5xx - Network issue, might work on retry"""

    pass


class UserAbortError(Exception):
    """Raised when user chooses to abort the entire fetch"""

    pass


class WikiAPIClient:
    """Client for fetching from DokuWiki API with intelligent retry logic"""

    # Methods where failure is page/item-specific, not method-wide.
    # A 400 on core.getPage("bad_page") does NOT mean core.getPage is broken.
    _PAGE_SPECIFIC_METHODS = frozenset(
        {
            "core.getPage",
            "core.getPageHTML",
            "core.getPageInfo",
            "core.getPageHistory",
            "core.getPageLinks",
            "core.getPageBackLinks",
            "core.aclCheck",
            "core.getMediaInfo",
            "core.getMediaUsage",
            "core.getMediaHistory",
        }
    )

    def __init__(self, verbose: bool = True, interactive: bool = True):
        self.api_url = API_URL
        self.headers = HEADERS
        # Use configured cert path if it exists, otherwise system CA bundle
        if CA_CERT_PATH and Path(CA_CERT_PATH).exists():
            self.ca_cert = CA_CERT_PATH
        else:
            self.ca_cert = True
        self.timeout = TIMEOUT
        self.max_retries = MAX_RETRIES
        self.retry_delay = RETRY_DELAY
        self.verbose = verbose
        self.interactive = interactive
        self.request_id = 0

        # HTTP session for connection pooling (TCP/TLS reuse)
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.verify = self.ca_cert

        # Separate skip modes for different error types
        self.skip_permanent_errors = False  # HTTP 4xx - API doesn't support method
        self.skip_transient_errors = False  # Timeouts - network issues

        # Track methods the API genuinely does not support (not page-specific failures)
        self._unsupported_methods: set = set()

    def _is_permanent_error(self, error: Exception) -> bool:
        """Check if error is permanent (no point retrying)"""
        if isinstance(error, requests.exceptions.HTTPError) and error.response is not None:
            return 400 <= error.response.status_code < 500
        return False

    def _is_transient_error(self, error: Exception) -> bool:
        """Check if error is transient (might work on retry)"""
        if isinstance(error, (requests.exceptions.Timeout, requests.exceptions.ConnectionError)):
            return True
        if isinstance(error, requests.exceptions.HTTPError) and error.response is not None:
            return error.response.status_code >= 500
        return False

    def _prompt_on_permanent_error(self, method: str, error_msg: str) -> str:
        """
        Prompt user for action on permanent error (HTTP 4xx).

        Returns:
            's' - skip this item
            'a' - skip all permanent errors
            'q' - quit/abort
        """
        if not self.interactive or self.skip_permanent_errors:
            return "s"

        print("\n" + "=" * 60)
        print(f"  PERMANENT ERROR: {method}")
        print(f"  {error_msg[:70]}")
        print("  (API-Methode nicht verfuegbar - Retry sinnlos)")
        print("=" * 60)
        print()
        print("  Optionen:")
        print("    [s] Skip    - Dieses Item ueberspringen")
        print("    [a] All     - Alle HTTP 4xx Errors auto-skippen")
        print("    [q] Quit    - Fetch abbrechen")
        print()

        while True:
            try:
                choice = input("  Auswahl [s/a/q]: ").strip().lower()
                if choice in ("s", "a", "q", ""):
                    return choice if choice else "s"
            except EOFError:
                return "s"

    def _prompt_on_transient_error(self, method: str, error_msg: str, attempt: int) -> str:
        """
        Prompt user for action on transient error (timeout/5xx).

        Returns:
            'r' - retry now
            's' - skip this item
            'a' - skip all transient errors
            'q' - quit/abort
        """
        if not self.interactive:
            return "s"
        if self.skip_transient_errors:
            return "s"

        print("\n" + "=" * 60)
        print(f"  NETWORK ERROR: {method} (Versuch {attempt})")
        print(f"  {error_msg[:70]}")
        print("  (Timeout/Verbindungsproblem - Retry koennte helfen)")
        print("=" * 60)
        print()
        print("  Optionen:")
        print("    [r] Retry   - Nochmal versuchen (mit laengerem Timeout)")
        print("    [s] Skip    - Dieses Item ueberspringen")
        print("    [a] All     - Alle Netzwerk-Errors auto-skippen")
        print("    [q] Quit    - Fetch abbrechen")
        print()

        while True:
            try:
                choice = input("  Auswahl [r/s/a/q]: ").strip().lower()
                if choice in ("r", "s", "a", "q", ""):
                    return choice if choice else "r"  # Default: retry
            except EOFError:
                return "s"

    def call(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make a JSON-RPC call with intelligent retry logic.

        - HTTP 4xx: Skip immediately (PermanentError)
        - Timeout/5xx: Retry with backoff, then prompt (TransientError)

        Args:
            method: API method to call
            params: Optional parameters

        Returns:
            Raw JSON-RPC response

        Raises:
            PermanentError: HTTP 4xx errors (method not available)
            TransientError: Timeout/network errors after retries exhausted
            UserAbortError: User chose to abort
        """
        # Skip methods the API genuinely does not support
        if method in self._unsupported_methods:
            raise PermanentError(f"Method '{method}' not supported by this wiki, skipping")

        self.request_id += 1

        payload: dict = {
            "jsonrpc": "2.0",
            "id": f"request_{self.request_id}",
            "method": method,
        }

        if params:
            payload["params"] = params

        attempt = 0
        current_timeout = self.timeout

        while True:
            attempt += 1

            try:
                if self.verbose and attempt > 1:
                    print(
                        f"  Retry {attempt-1}/{self.max_retries} (timeout: {current_timeout}s)..."
                    )

                response = self.session.post(self.api_url, json=payload, timeout=current_timeout)

                response.raise_for_status()
                result = response.json()

                # Check for JSON-RPC errors
                if "error" in result:
                    error = result["error"]
                    raise ValueError(f"JSON-RPC Error {error.get('code')}: {error.get('message')}")

                return result

            except requests.exceptions.HTTPError as e:
                error_msg = str(e)

                # HTTP 4xx - Permanent error, no retry
                if self._is_permanent_error(e):
                    if method not in self._PAGE_SPECIFIC_METHODS:
                        self._unsupported_methods.add(method)
                    return self._handle_permanent_error(method, error_msg)

                # HTTP 5xx - Server error, retry
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * attempt)
                    current_timeout = min(current_timeout * 1.5, 120)
                    continue

                return self._handle_transient_error(method, error_msg, attempt)

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                error_msg = str(e)

                # Auto-skip if in skip mode
                if self.skip_transient_errors:
                    raise TransientError(f"Skipped (auto): {error_msg}") from e

                # Retry with backoff
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * attempt)
                    current_timeout = min(current_timeout * 1.5, 120)
                    continue

                # Max retries reached - prompt user
                return self._handle_transient_error(method, error_msg, attempt)

            except ValueError as e:
                # JSON-RPC error - treat as permanent
                if method not in self._PAGE_SPECIFIC_METHODS:
                    self._unsupported_methods.add(method)
                return self._handle_permanent_error(method, str(e))

    def _handle_permanent_error(self, method: str, error_msg: str):
        """Handle permanent error (HTTP 4xx) - prompt or auto-skip"""
        if self.skip_permanent_errors:
            raise PermanentError(f"Skipped (auto): {error_msg}")

        choice = self._prompt_on_permanent_error(method, error_msg)

        if choice == "q":
            raise UserAbortError("Fetch abgebrochen durch User")
        elif choice == "a":
            self.skip_permanent_errors = True
            raise PermanentError(f"Skipped (auto): {error_msg}")
        else:  # 's'
            raise PermanentError(f"Skipped: {error_msg}")

    def _handle_transient_error(self, method: str, error_msg: str, attempt: int):
        """Handle transient error (timeout) - prompt with retry option"""
        if self.skip_transient_errors:
            raise TransientError(f"Skipped (auto): {error_msg}")

        choice = self._prompt_on_transient_error(method, error_msg, attempt)

        if choice == "q":
            raise UserAbortError("Fetch abgebrochen durch User")
        elif choice == "a":
            self.skip_transient_errors = True
            raise TransientError(f"Skipped (auto): {error_msg}")
        elif choice == "r":
            # Retry with longer timeout
            return self.call(method, None)  # Recursive retry
        else:  # 's'
            raise TransientError(f"Skipped: {error_msg}")

    def get_all_pages(self, namespace: str = "", depth: int = 0, include_hash: bool = True) -> list:
        """
        Get list of all pages with optional hash.

        Args:
            namespace: Namespace to list (empty for all)
            depth: How deep to recurse (0 = unlimited)
            include_hash: Include content hash for each page

        Returns:
            List of page dictionaries with id, revision, size, permission, hash
        """
        if self.verbose:
            print("Fetching page list...")
        response = self.call(
            "core.listPages", {"namespace": namespace, "depth": depth, "hash": include_hash}
        )
        return response.get("result", [])

    def get_page_info(
        self, page_id: str, include_author: bool = True, include_hash: bool = True
    ) -> Dict:
        """
        Get page metadata with author and hash.

        Args:
            page_id: Page identifier (e.g., "teacher:start")
            include_author: Include last author information
            include_hash: Include content hash

        Returns:
            Dict with id, revision, size, title, permission, hash, author
        """
        response = self.call(
            "core.getPageInfo", {"page": page_id, "author": include_author, "hash": include_hash}
        )
        return response.get("result", {})

    def get_page_content(self, page_id: str) -> str:
        """Get raw page content"""
        response = self.call("core.getPage", {"page": page_id})
        return response.get("result", "")

    def get_page_html(self, page_id: str) -> str | None:
        """Get rendered HTML (may not be available)"""
        try:
            response = self.call("core.getPageHTML", {"page": page_id})
            return response.get("result", "")
        except (PermanentError, TransientError):
            return None

    def get_page_history(self, page_id: str, first: int = 0) -> list:
        """
        Get page revision history.

        Args:
            page_id: Page identifier
            first: Skip this many revisions from the beginning

        Returns:
            List of revision dicts with: id, revision, author, ip, summary, type, sizechange
            Type codes: C=created, E=edited, e=minor edit, D=deleted, R=reverted
        """
        try:
            response = self.call("core.getPageHistory", {"page": page_id, "first": first})
            return response.get("result", [])
        except (PermanentError, TransientError):
            return []

    def get_page_links(self, page_id: str) -> list:
        """
        Get links from a page (API-based, more reliable than HTML parsing).

        Args:
            page_id: Page identifier

        Returns:
            List of link dicts with: type (local/extern), page, href
        """
        try:
            response = self.call("core.getPageLinks", {"page": page_id})
            return response.get("result", [])
        except (PermanentError, TransientError):
            return []

    def get_page_backlinks(self, page_id: str) -> list:
        """
        Get pages that link TO this page (incoming links).

        Args:
            page_id: Page identifier

        Returns:
            List of page IDs that link to this page
        """
        try:
            response = self.call("core.getPageBackLinks", {"page": page_id})
            return response.get("result", [])
        except (PermanentError, TransientError):
            return []

    def get_recent_page_changes(self, timestamp: int = 0) -> list:
        """
        Get recent page changes across the wiki.

        Args:
            timestamp: Only show changes newer than this Unix timestamp (0 = all)

        Returns:
            List of change dicts with: id, revision, author, ip, summary, type, sizechange
        """
        try:
            response = self.call("core.getRecentPageChanges", {"timestamp": timestamp})
            return response.get("result", [])
        except (PermanentError, TransientError):
            return []

    # =========================================================================
    # Media Methods
    # =========================================================================

    def get_all_media(
        self,
        namespace: str = "",
        pattern: str = "",
        depth: int = 0,
        include_hash: bool = True,
        include_author: bool = True,
    ) -> list:
        """
        Get list of all media files with full metadata.

        Args:
            namespace: Namespace to list (empty for all)
            pattern: Regex pattern to filter files
            depth: How deep to recurse (0 = unlimited)
            include_hash: Include file hash
            include_author: Include uploader information

        Returns:
            List of media dicts with: id, revision, size, permission, isimage, hash, author
        """
        try:
            response = self.call(
                "core.listMedia",
                {
                    "namespace": namespace,
                    "pattern": pattern,
                    "depth": depth,
                    "hash": include_hash,
                    "author": include_author,
                },
            )
            return response.get("result", [])
        except (PermanentError, TransientError):
            return []

    def get_media_info(
        self,
        media_id: str,
        revision: int = 0,
        include_author: bool = True,
        include_hash: bool = True,
    ) -> Dict:
        """
        Get detailed media file information.

        Args:
            media_id: Media identifier (e.g., "namespace:filename.pdf")
            revision: Specific revision (0 = current)
            include_author: Include uploader information
            include_hash: Include file hash

        Returns:
            Dict with: id, revision, size, permission, isimage, hash, author
        """
        try:
            response = self.call(
                "core.getMediaInfo",
                {
                    "media": media_id,
                    "rev": revision,
                    "author": include_author,
                    "hash": include_hash,
                },
            )
            return response.get("result", {})
        except (PermanentError, TransientError):
            return {}

    def get_media_usage(self, media_id: str) -> list:
        """
        Get pages that use/reference this media file.

        Args:
            media_id: Media identifier

        Returns:
            List of page IDs that reference this media
        """
        try:
            response = self.call("core.getMediaUsage", {"media": media_id})
            return response.get("result", [])
        except (PermanentError, TransientError):
            return []

    def get_media_history(self, media_id: str, first: int = 0) -> list:
        """
        Get media file revision history.

        Args:
            media_id: Media identifier
            first: Skip this many revisions from the beginning

        Returns:
            List of revision dicts with: id, revision, author, ip, summary, type, sizechange
        """
        try:
            response = self.call("core.getMediaHistory", {"media": media_id, "first": first})
            return response.get("result", [])
        except (PermanentError, TransientError):
            return []

    def get_recent_media_changes(self, timestamp: int = 0) -> list:
        """
        Get recent media changes across the wiki.

        Args:
            timestamp: Only show changes newer than this Unix timestamp (0 = all)

        Returns:
            List of change dicts with: id, revision, author, ip, summary, type, sizechange
        """
        try:
            response = self.call("core.getRecentMediaChanges", {"timestamp": timestamp})
            return response.get("result", [])
        except (PermanentError, TransientError):
            return []

    # =========================================================================
    # File Downloads
    # =========================================================================

    def download_file(
        self,
        media_id: str,
        target_path: "Path",
        timeout_multiplier: float = 1.0,
    ) -> int:
        """
        Download a media file via fetch.php using the shared session.

        Args:
            media_id: Media identifier (e.g. "namespace:file.pdf")
            target_path: Local path to save the file to
            timeout_multiplier: Multiply base timeout (useful for retries)

        Returns:
            Size in bytes of the downloaded file

        Raises:
            requests.exceptions.RequestException on download failure
        """
        url = f"{API_FETCH_URL}?media={media_id}"
        response = self.session.get(
            url,
            timeout=self.timeout * timeout_multiplier,
            stream=True,
        )
        response.raise_for_status()

        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return target_path.stat().st_size
