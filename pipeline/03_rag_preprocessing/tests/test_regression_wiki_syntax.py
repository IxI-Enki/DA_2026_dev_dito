"""T081: Regression test for DokuWiki syntax conversion accuracy.

Asserts < 1% DokuWiki syntax markers remain in converted output.
"""

from __future__ import annotations

import re

# DokuWiki-specific syntax patterns that should NOT survive conversion
_WIKI_PATTERNS = [
    r"={2,6}\s+.+\s+={2,6}",  # Headings: ====== H1 ======
    r"(?<!/)//.+?//(?!/)",  # Italic: //text//
    r"\[\[[^\]]+\]\]",  # Links: [[page|text]]
    r"\{\{[^}]+\}\}",  # Media: {{image.png}}
    r"^\s{2,}\*\s",  # Unordered list: "  * item" (wiki uses *)
    # Note: "  - item" is NOT checked because markdown nested unordered
    # lists also use "  - item" (valid markdown).
    r"<code[^>]*>",  # Code block open
    r"</code>",  # Code block close
    r"~~NOTOC~~",  # DokuWiki directive
    r"~~NOCACHE~~",  # DokuWiki directive
    r"<del>.+?</del>",  # Strikethrough (should be ~~text~~)
    r"\^\s.+?\s\^",  # Table header ^ Cell ^
]


SAMPLE_WIKI = r"""
====== Main Title ======

This is a //sample// DokuWiki page with **bold** and //italic// text.

===== Second Heading =====

  * Unordered item one
  * Unordered item two
    * Nested item

  - Ordered item one
  - Ordered item two

[[internal:page|Internal Link]] and [[https://example.com|External Link]]

{{media:image.png|Alt text}}

^ Header 1 ^ Header 2 ^
| Cell A   | Cell B   |

<code python>
print("hello")
</code>

~~NOTOC~~

<del>Deleted text</del>
"""


class TestWikiSyntaxRegression:
    """Ensure < 1% wiki syntax markers survive conversion."""

    def test_conversion_removes_almost_all_wiki_syntax(self) -> None:
        from page_processor import PageProcessor

        pp = PageProcessor()
        result = pp.convert(SAMPLE_WIKI, "test:regression")
        assert result.success

        md = result.markdown
        total_lines = len(md.splitlines())

        # Count lines that still contain DokuWiki syntax
        wiki_lines = 0
        for line in md.splitlines():
            for pat in _WIKI_PATTERNS:
                if re.search(pat, line):
                    wiki_lines += 1
                    break  # one match per line is enough

        ratio = wiki_lines / max(total_lines, 1)
        assert ratio < 0.01, (
            f"{wiki_lines}/{total_lines} lines ({ratio:.1%}) still contain "
            f"DokuWiki syntax (threshold: < 1%)"
        )

    def test_headings_fully_converted(self) -> None:
        from page_processor import PageProcessor

        pp = PageProcessor()
        result = pp.convert("====== Title ======\n===== Sub =====\n==== H3 ====")
        assert "# Title" in result.markdown
        assert "## Sub" in result.markdown
        assert "### H3" in result.markdown
        # No remaining ====
        assert "======" not in result.markdown
        assert "=====" not in result.markdown

    def test_links_fully_converted(self) -> None:
        from page_processor import PageProcessor

        pp = PageProcessor()
        result = pp.convert("[[page:test|Link Text]] and [[https://example.com]]")
        assert "[[" not in result.markdown
        assert "]]" not in result.markdown
        # Internal links keep colon namespace and are lowercased to match page_id
        assert "[Link Text](page:test)" in result.markdown

    def test_media_fully_converted(self) -> None:
        from page_processor import PageProcessor

        pp = PageProcessor()
        result = pp.convert("{{media:photo.jpg|My photo}}")
        assert "{{" not in result.markdown
        assert "}}" not in result.markdown
        # Media links keep colon namespace and are lowercased to match media_id
        assert "![My photo](media:photo.jpg)" in result.markdown
