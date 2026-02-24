"""
Extract links from DokuWiki HTML pages
Identifies internal links, external links, and media references.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, cast

from bs4 import BeautifulSoup, Tag


class LinkExtractor:
    """Extracts various link types from DokuWiki HTML"""

    # DokuWiki CSS classes for different link types
    INTERNAL_LINK_CLASSES = ["wikilink1", "wikilink2"]  # wikilink1=exists, wikilink2=missing
    EXTERNAL_LINK_CLASS = "urlextern"
    MEDIA_LINK_CLASS = "media"
    INTERWIKI_CLASS = "interwiki"
    MAILTO_CLASS = "mail"

    def __init__(self):
        self.reset_stats()

    def reset_stats(self):
        """Reset extraction statistics"""
        self.stats = {
            "pages_processed": 0,
            "total_internal_links": 0,
            "total_external_links": 0,
            "total_media_links": 0,
            "total_interwiki_links": 0,
            "total_mailto_links": 0,
        }

    def extract_links(self, html: str, page_id: str = "") -> Dict[str, Any]:
        """
        Extract all links from HTML content.

        Args:
            html: HTML content from core.getPageHTML
            page_id: Optional page identifier for context

        Returns:
            Dictionary with categorized links
        """
        soup = BeautifulSoup(html, "html.parser")

        result = {
            "page_id": page_id,
            "extracted_from": "html",
            "extraction_timestamp": datetime.now().isoformat(),
            "internal_links": [],
            "external_links": [],
            "media_links": [],
            "interwiki_links": [],
            "mailto_links": [],
            "summary": {},
        }

        # Find all anchor tags
        all_links = soup.find_all("a")

        for element in all_links:
            link = cast(Tag, element)
            href = str(link.get("href") or "")
            text = link.get_text(strip=True)
            css_classes = list(link.get("class") or [])
            title = str(link.get("title") or "")

            if not href:
                continue

            # Categorize link by CSS class
            link_data: dict = {
                "href": href,
                "text": text,
                "title": title,
                "css_classes": css_classes,
            }

            # Internal wiki links
            if any(cls in css_classes for cls in self.INTERNAL_LINK_CLASSES):
                # Extract page ID from href
                target = self._extract_page_id_from_href(href)
                link_data["target"] = target
                link_data["exists"] = "wikilink1" in css_classes
                result["internal_links"].append(link_data)

            # External links
            elif self.EXTERNAL_LINK_CLASS in css_classes:
                result["external_links"].append(link_data)

            # Media links (images, files)
            elif self.MEDIA_LINK_CLASS in css_classes:
                media_id = self._extract_media_id_from_href(href)
                link_data["media_id"] = media_id
                result["media_links"].append(link_data)

            # Interwiki links
            elif self.INTERWIKI_CLASS in css_classes:
                result["interwiki_links"].append(link_data)

            # Mailto links
            elif self.MAILTO_CLASS in css_classes or href.startswith("mailto:"):
                result["mailto_links"].append(link_data)

        # Also find embedded images (not wrapped in links)
        for img_element in soup.find_all("img"):
            img = cast(Tag, img_element)
            src = str(img.get("src") or "")
            if src and "/lib/exe/fetch.php" in src:
                media_id = self._extract_media_id_from_src(src)
                if media_id:
                    result["media_links"].append(
                        {
                            "href": src,
                            "text": str(img.get("alt") or ""),
                            "title": str(img.get("title") or ""),
                            "css_classes": list(img.get("class") or []),
                            "media_id": media_id,
                            "type": "embedded_image",
                        }
                    )

        # Generate summary
        result["summary"] = {
            "internal_count": len(result["internal_links"]),
            "external_count": len(result["external_links"]),
            "media_count": len(result["media_links"]),
            "interwiki_count": len(result["interwiki_links"]),
            "mailto_count": len(result["mailto_links"]),
            "total_links": sum(
                [
                    len(result["internal_links"]),
                    len(result["external_links"]),
                    len(result["media_links"]),
                    len(result["interwiki_links"]),
                    len(result["mailto_links"]),
                ]
            ),
        }

        # Update global stats
        self.stats["pages_processed"] += 1
        self.stats["total_internal_links"] += result["summary"]["internal_count"]
        self.stats["total_external_links"] += result["summary"]["external_count"]
        self.stats["total_media_links"] += result["summary"]["media_count"]
        self.stats["total_interwiki_links"] += result["summary"]["interwiki_count"]
        self.stats["total_mailto_links"] += result["summary"]["mailto_count"]

        return result

    def _extract_page_id_from_href(self, href: str) -> str:
        """Extract DokuWiki page ID from href"""
        # Pattern: /doku.php?id=namespace:page or /doku.php/namespace:page

        # Try query parameter
        if "id=" in href:
            match = re.search(r"id=([^&]+)", href)
            if match:
                return match.group(1)

        # Try path format
        if "/doku.php/" in href:
            parts = href.split("/doku.php/")
            if len(parts) > 1:
                return parts[1].split("?")[0].split("#")[0]

        # Try anchor link (same page)
        if href.startswith("#"):
            return ""

        return href

    def _extract_media_id_from_href(self, href: str) -> str:
        """Extract media ID from href"""
        # Pattern: /lib/exe/fetch.php?media=namespace:filename
        if "media=" in href:
            match = re.search(r"media=([^&]+)", href)
            if match:
                return match.group(1)

        # Pattern: /lib/exe/detail.php?id=namespace:filename
        if "id=" in href and "/detail.php" in href:
            match = re.search(r"id=([^&]+)", href)
            if match:
                return match.group(1)

        return href

    def _extract_media_id_from_src(self, src: str) -> str:
        """Extract media ID from image src"""
        # Pattern: /lib/exe/fetch.php?media=namespace:filename
        if "media=" in src:
            match = re.search(r"media=([^&]+)", src)
            if match:
                return match.group(1)

        return ""

    def get_unique_internal_targets(self, links_data: Dict) -> List[str]:
        """Get list of unique internal link targets"""
        targets = set()
        for link in links_data.get("internal_links", []):
            target = link.get("target", "")
            if target:
                targets.add(target)
        return sorted(list(targets))

    def get_unique_external_domains(self, links_data: Dict) -> List[str]:
        """Get list of unique external domains"""
        domains = set()
        for link in links_data.get("external_links", []):
            href = link.get("href", "")
            match = re.search(r"https?://([^/]+)", href)
            if match:
                domains.add(match.group(1))
        return sorted(list(domains))

    def get_unique_media_ids(self, links_data: Dict) -> List[str]:
        """Get list of unique media IDs"""
        media_ids = set()
        for link in links_data.get("media_links", []):
            mid = link.get("media_id", "")
            if mid:
                media_ids.add(mid)
        return sorted(list(media_ids))

    def get_stats(self) -> Dict:
        """Get global extraction statistics"""
        return self.stats.copy()


def extract_links_from_html(html: str, page_id: str = "") -> Dict[str, Any]:
    """
    Convenience function to extract links from HTML.

    Args:
        html: HTML content
        page_id: Optional page identifier

    Returns:
        Dictionary with categorized links
    """
    extractor = LinkExtractor()
    return extractor.extract_links(html, page_id)


# For testing
if __name__ == "__main__":
    import sys

    sys.path.insert(0, ".")
    from api_client import WikiAPIClient

    print("Testing link extraction...")
    print("-" * 40)

    client = WikiAPIClient(verbose=False)
    extractor = LinkExtractor()

    # Test with start page
    test_page = "start"
    print(f"Fetching HTML for: {test_page}")

    try:
        html = client.get_page_html(test_page)
        if html:
            links = extractor.extract_links(html, test_page)

            print(f"\nResults for {test_page}:")
            print(f"  Internal links: {links['summary']['internal_count']}")
            print(f"  External links: {links['summary']['external_count']}")
            print(f"  Media links: {links['summary']['media_count']}")

            if links["internal_links"]:
                print(f"\n  Sample internal links:")
                for link in links["internal_links"][:5]:
                    print(f"    - {link['target']}: {link['text'][:50]}")

            if links["external_links"]:
                print(f"\n  Sample external links:")
                for link in links["external_links"][:5]:
                    print(f"    - {link['href'][:60]}")

            if links["media_links"]:
                print(f"\n  Sample media links:")
                for link in links["media_links"][:5]:
                    print(f"    - {link.get('media_id', link['href'][:60])}")
        else:
            print("Failed to fetch HTML")
    except Exception as e:
        print(f"Error: {str(e)}")
