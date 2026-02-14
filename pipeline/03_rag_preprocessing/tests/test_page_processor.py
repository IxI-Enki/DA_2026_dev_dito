"""T067: Tests for PageProcessor DokuWiki conversion + strategy routing."""

from __future__ import annotations

import pytest


class TestDokuWikiConversion:
    """Tests for basic DokuWiki -> Markdown conversion."""

    def test_heading_h1(self) -> None:
        from page_processor import PageProcessor

        pp = PageProcessor()
        r = pp.convert("====== Title ======")
        assert "# Title" in r.markdown

    def test_heading_h2(self) -> None:
        from page_processor import PageProcessor

        pp = PageProcessor()
        r = pp.convert("===== Sub Title =====")
        assert "## Sub Title" in r.markdown

    def test_bold_text(self) -> None:
        from page_processor import PageProcessor

        pp = PageProcessor()
        r = pp.convert("**bold text**")
        assert "**bold text**" in r.markdown

    def test_italic_text(self) -> None:
        from page_processor import PageProcessor

        pp = PageProcessor()
        r = pp.convert("//italic text//")
        assert "*italic text*" in r.markdown

    def test_internal_link(self) -> None:
        from page_processor import PageProcessor

        pp = PageProcessor()
        r = pp.convert("[[page|Link text]]")
        assert "[Link text](page)" in r.markdown

    def test_unordered_list(self) -> None:
        from page_processor import PageProcessor

        pp = PageProcessor()
        r = pp.convert("  * item one\n  * item two")
        assert "- item one" in r.markdown
        assert "- item two" in r.markdown

    def test_table_conversion(self) -> None:
        from page_processor import PageProcessor

        pp = PageProcessor()
        r = pp.convert("^ H1 ^ H2 ^\n| a | b |")
        assert "| H1 | H2 |" in r.markdown

    def test_empty_content_fails(self) -> None:
        from page_processor import PageProcessor

        pp = PageProcessor()
        r = pp.convert("")
        assert r.success is False


class TestStrategyAwareRouting:
    """T076: Tests for process_with_strategy method."""

    def test_knowledge_page(self) -> None:
        from page_processor import PageProcessor
        from strategy_loader import ContentType, PageStrategy

        pp = PageProcessor()
        strategy = PageStrategy(
            page_id="test:page",
            content_type=ContentType.KNOWLEDGE,
            rag_readiness=0.9,
            recommended_chunk_size=512,
            noise_level="low",
        )
        page = {"content": "====== Test ======\nSome content", "page_id": "test:page"}
        result = pp.process_with_strategy(page, strategy)
        assert "markdown" in result
        assert result["content_type"] == "knowledge"

    def test_news_page(self) -> None:
        from page_processor import PageProcessor
        from strategy_loader import ContentType, PageStrategy

        pp = PageProcessor()
        strategy = PageStrategy(
            page_id="news:latest",
            content_type=ContentType.NEWS,
            rag_readiness=0.4,
            recommended_chunk_size=256,
            noise_level="high",
        )
        page = {"content": "====== News ======\nSomething happened", "page_id": "news:latest"}
        result = pp.process_with_strategy(page, strategy)
        assert result["content_type"] == "news"

    def test_archived_page_marked_low_priority(self) -> None:
        from page_processor import PageProcessor
        from strategy_loader import ContentType, PageStrategy

        pp = PageProcessor()
        strategy = PageStrategy(
            page_id="archive:old",
            content_type=ContentType.ARCHIVED,
            rag_readiness=0.1,
            recommended_chunk_size=128,
            noise_level="medium",
        )
        page = {"content": "Old archived content", "page_id": "archive:old"}
        result = pp.process_with_strategy(page, strategy)
        assert result.get("priority") == "low"
