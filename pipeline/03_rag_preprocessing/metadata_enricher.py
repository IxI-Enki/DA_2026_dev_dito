"""
Metadata Enricher
=================
Generates YAML frontmatter from multiple metadata sources.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FreshnessResult:
    """Freshness calculation result with both score and category."""

    score: float  # 0.0 - 1.0
    category: str  # fresh / recent / outdated / archived / unknown


class MetadataEnricher:
    """Generates YAML frontmatter from various metadata sources."""

    def __init__(self, wiki_base_url: str = ""):
        self.wiki_base_url = wiki_base_url
        self.evaluation_data: Dict[str, Any] = {}

    def load_evaluation(self, evaluation_file: Path) -> None:
        """Load evaluation results from Stage 2."""
        if not evaluation_file or not evaluation_file.exists():
            logger.warning(f"Evaluation file not found: {evaluation_file}")
            return

        try:
            with open(evaluation_file, encoding="utf-8") as f:
                data = json.load(f)

            # Store page-level data if available
            self.evaluation_data = data
            logger.info(
                f"Loaded evaluation data: {len(data.get('flagged_pages', []))} flagged pages"
            )
        except Exception as e:
            logger.error(f"Failed to load evaluation: {e}")

    def get_page_evaluation(self, page_id: str) -> Dict[str, Any]:
        """Get evaluation data for a specific page."""
        # Check if page is flagged
        flagged_pages = self.evaluation_data.get("flagged_pages", [])
        is_flagged = page_id in flagged_pages or page_id.replace(":", "_") in flagged_pages

        # Determine recommendation based on quality distribution
        self.evaluation_data.get("quality_distribution", {})
        recommendations = self.evaluation_data.get("recommendations", {})

        return {
            "is_flagged": is_flagged,
            "overall_quality": self.evaluation_data.get("overall", {}).get("quality_score", 0.5),
            "recommendations": recommendations,
        }

    def generate_frontmatter(
        self,
        page_id: str,
        title: str,
        raw_metadata: Optional[Dict[str, Any]] = None,
        links_data: Optional[Dict[str, Any]] = None,
        fetch_timestamp: Optional[str] = None,
        backlinks: Optional[List[str]] = None,
    ) -> str:
        """
        Generate YAML frontmatter for a page.

        Args:
            page_id: Wiki page identifier (e.g., 'namespace:pagename')
            title: Extracted page title
            raw_metadata: Metadata from raw_json/*_complete.json
            links_data: Links from page_links/*_links.json
            fetch_timestamp: Timestamp of the fetch operation

        Returns:
            YAML frontmatter string (including --- markers)
        """
        # Build frontmatter dict
        fm = {}

        # Core identification
        fm["title"] = title or page_id.split(":")[-1].replace("_", " ").title()
        fm["page_id"] = page_id.replace("_", ":")

        # Extract namespace
        if ":" in page_id:
            fm["namespace"] = page_id.rsplit(":", 1)[0].replace("_", ":")
        else:
            fm["namespace"] = ""

        # Source URL
        wiki_id = page_id.replace("_", ":")
        fm["source"] = f"{self.wiki_base_url}{wiki_id}"

        # Process raw metadata if available
        if raw_metadata:
            page_info = raw_metadata.get("page_info", {})

            # Access level based on permission
            permission = page_info.get("permission", 1)
            fm["access_level"] = "teacher_only" if permission > 1 else "public"

            # Timestamps
            if page_info.get("last_modified"):
                fm["last_modified"] = page_info["last_modified"]

            # Author
            if page_info.get("author"):
                fm["author"] = page_info["author"]

            # Revision info
            fm["revision"] = page_info.get("revision", 0)
            fm["size"] = page_info.get("size", 0)
        else:
            fm["access_level"] = "public"

        # Fetch and preprocessing timestamps
        if fetch_timestamp:
            fm["fetched_at"] = fetch_timestamp
        fm["preprocessed_at"] = datetime.now().isoformat()

        # Links data
        if links_data:
            internal_links = links_data.get("internal_links", [])
            external_links = links_data.get("external_links", [])
            media_links = links_data.get("media_links", [])

            # Extract link targets
            if internal_links:
                fm["links_to"] = [
                    link.get("target", "") for link in internal_links[:20]
                ]  # Limit to 20

            if media_links:
                fm["media_refs"] = [link.get("target", "") for link in media_links[:20]]

            # Summary
            fm["link_summary"] = {
                "internal": len(internal_links),
                "external": len(external_links),
                "media": len(media_links),
            }

        # Ensure links_to is always present (even if empty)
        if "links_to" not in fm:
            fm["links_to"] = []

        # Backlinks -> linked_from
        fm["linked_from"] = list(backlinks) if backlinks else []

        # Evaluation data
        eval_data = self.get_page_evaluation(page_id)
        if eval_data.get("is_flagged"):
            fm["quality_flag"] = "review_needed"

        # Content type (default - can be enhanced with NLP later)
        fm["content_type"] = self._classify_content_type(page_id, fm.get("namespace", ""))

        # Generate YAML
        return self._to_yaml(fm)

    # ------------------------------------------------------------------
    # Freshness & Access Level (T077-T078)
    # ------------------------------------------------------------------

    def calculate_freshness_score(self, last_modified: str) -> str:
        """Classify page freshness based on age relative to current date.

        Uses same thresholds as calculate_freshness (loosened for school-wiki content).

        Args:
            last_modified: ISO-8601 date/datetime string.

        Returns:
            ``'fresh'`` (<365d), ``'recent'`` (<730d),
            ``'outdated'`` (<1460d), ``'archived'`` (>=1460d),
            or ``'unknown'`` if parsing fails.
        """
        try:
            if "T" in last_modified:
                dt = datetime.fromisoformat(last_modified.replace("Z", "+00:00"))
            else:
                dt = datetime.fromisoformat(last_modified)
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
            age_days = (datetime.now() - dt).days
        except (ValueError, TypeError):
            return "unknown"

        if age_days < 90:
            return "fresh"
        if age_days < 365:
            return "fresh"
        if age_days < 730:
            return "recent"
        if age_days < 1460:
            return "outdated"
        return "archived"

    def calculate_freshness(self, last_modified: str, namespace: str = "") -> FreshnessResult:
        """Calculate freshness using loosened thresholds for school-wiki content.

        If namespace starts with ``archive``, always returns category="archived".
        Otherwise content is scored so that curricula/tutorials valid for years
        are not aggressively penalized.

        Thresholds (loosened):
            < 90 days:    score=1.00, category="fresh"
            < 365 days:   score=0.85, category="fresh"
            < 730 days:   score=0.70, category="recent"
            < 1460 days:  score=0.50, category="outdated" (4 years)
            >= 1460 days: score=0.30, category="stale"
        Archive namespace: always score=0.20, category="archived".

        Returns:
            FreshnessResult with score (float) and category (str).
            On invalid input: score=0.5, category="unknown".
        """
        ns = (namespace or "").strip().lower()
        if ns.startswith("archive"):
            return FreshnessResult(score=0.20, category="archived")

        try:
            if "T" in last_modified:
                dt = datetime.fromisoformat(last_modified.replace("Z", "+00:00"))
            else:
                dt = datetime.fromisoformat(last_modified)
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
            age_days = (datetime.now() - dt).days
        except (ValueError, TypeError):
            return FreshnessResult(score=0.5, category="unknown")

        if age_days < 90:
            return FreshnessResult(score=1.0, category="fresh")
        if age_days < 365:
            return FreshnessResult(score=0.85, category="fresh")
        if age_days < 730:
            return FreshnessResult(score=0.70, category="recent")
        if age_days < 1460:
            return FreshnessResult(score=0.50, category="outdated")
        return FreshnessResult(score=0.30, category="stale")

    def determine_access_level(self, namespace: str) -> str:
        """Determine access level based on DokuWiki namespace.

        Args:
            namespace: DokuWiki namespace string.

        Returns:
            ``'teacher_only'`` if namespace starts with ``'teacher:'``
            or ``'lehrer:'``, else ``'public'``.
        """
        ns = namespace.lower()
        if (
            ns.startswith("teacher:")
            or ns.startswith("lehrer:")
            or ns == "teacher"
            or ns == "lehrer"
        ):
            return "teacher_only"
        return "public"

    def _classify_content_type(self, page_id: str, namespace: str) -> str:
        """
        Classify content type based on page_id and namespace.
        Returns: KNOWLEDGE, PORTAL, NEWS, FORM, TABLE_DATA, etc.
        """
        page_id_lower = page_id.lower()
        namespace_lower = namespace.lower()

        # Forms
        if "forms" in page_id_lower or "form" in namespace_lower:
            return "FORM_COLLECTION"

        # Start/Index pages are usually portals
        if page_id_lower.endswith(":start") or page_id_lower.endswith("_start"):
            return "PORTAL"
        if page_id_lower == "start":
            return "PORTAL"

        # Competitions/News
        if "competitions" in namespace_lower or "wocheninfo" in namespace_lower:
            return "NEWS"

        # Archive
        if "archive" in namespace_lower:
            return "ARCHIVE"

        # Tutorials
        if "tutorial" in namespace_lower:
            return "TUTORIAL"

        # IT/Technical
        if namespace_lower in ["it", "software", "wiki"]:
            return "TECHNICAL"

        # Teacher content
        if "teacher" in namespace_lower:
            return "TEACHER_ONLY"

        # Department info
        if "departm" in namespace_lower or "department" in namespace_lower:
            return "DEPARTMENT"

        # Exams
        if "exams" in namespace_lower:
            return "EXAM_INFO"

        # Organization
        if "org" in namespace_lower:
            return "ORGANIZATION"

        # Default
        return "KNOWLEDGE"

    def _to_yaml(self, data: Dict[str, Any]) -> str:
        """Convert dict to YAML frontmatter string."""
        # Use safe dump with specific formatting
        yaml_content = yaml.dump(
            data,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=1000,  # Prevent line wrapping
        )

        return f"---\n{yaml_content}---\n"


class MediaMetadataEnricher:
    """Generates YAML frontmatter for media files (Qdrant-compatible schema)."""

    def __init__(self, wiki_base_url: str = ""):
        self.wiki_base_url = wiki_base_url

    def generate_frontmatter(
        self,
        media_id: str,
        file_path: Path,
        file_size: int = 0,
        referenced_by: Optional[List[str]] = None,
        fetch_timestamp: Optional[str] = None,
        content_type: str = "",
        freshness_score: float = 0.5,
        freshness_category: str = "recent",
        chunking_method: str = "metadata_only",
        last_modified: str = "",
        author: str = "",
    ) -> str:
        """Generate YAML frontmatter for a media file.

        Produces the same Qdrant-compatible schema as page frontmatter,
        using ``media_id`` instead of ``page_id``.
        """
        fm: Dict[str, Any] = {}

        # Core identification (Qdrant-schema aligned)
        fm["title"] = file_path.stem.replace("_", " ").title()
        if ":" in media_id:
            fm["namespace"] = media_id.rsplit(":", 1)[0]
        else:
            fm["namespace"] = ""
        fm["source"] = (
            f"{self.wiki_base_url}lib/exe/fetch.php?media={media_id}" if self.wiki_base_url else ""
        )
        fm["media_id"] = media_id
        fm["access_level"] = "public"
        fm["content_type"] = content_type or self._classify_media_type(file_path.suffix.lower())
        fm["freshness_score"] = freshness_score
        fm["freshness_category"] = freshness_category
        fm["chunking_method"] = chunking_method
        fm["last_modified"] = last_modified
        fm["author"] = author
        # content_hash is computed by the Exporter from the body
        fm["links_to"] = []
        fm["linked_from"] = []

        # Generate YAML
        yaml_content = yaml.dump(
            fm,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

        return f"---\n{yaml_content}---\n"

    def _classify_media_type(self, extension: str) -> str:
        """Classify media type based on file extension."""
        ext = extension.lstrip(".")

        if ext in ["pdf"]:
            return "DOCUMENT"
        if ext in ["doc", "docx", "odt"]:
            return "DOCUMENT"
        if ext in ["xls", "xlsx", "ods"]:
            return "DOCUMENT"
        if ext in ["ppt", "pptx", "odp"]:
            return "DOCUMENT"
        if ext in ["jpg", "jpeg", "png", "gif", "svg", "webp"]:
            return "IMAGE"
        if ext in ["txt", "md", "rst"]:
            return "DOCUMENT"

        return "DOCUMENT"
