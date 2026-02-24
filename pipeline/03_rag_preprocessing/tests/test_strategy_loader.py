"""T064 + T013: Tests for StrategyLoader -- YAML + JSON support."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

# --- Fixtures ---


@pytest.fixture()
def yaml_strategies() -> dict:
    """Sample preprocessing_strategies.yaml matching Stage 2 output format."""
    return {
        "PIPELINE_STRATEGIES": {
            "wiki_pages": {
                "knowledge_articles": {
                    "description": "Standard Knowledge Base Artikel",
                    "chunking": "recursive_header",
                    "chunk_size": 1024,
                    "include_ids": [
                        "departm_electronics",
                        "it_bugs",
                        "exams_matura-d",
                    ],
                },
                "portals": {
                    "description": "Verteilerseiten",
                    "chunking": "parent_context",
                    "action": "index_as_context_only",
                    "include_ids": ["start", "teacher_start"],
                },
                "forms": {
                    "description": "Formularsammlungen",
                    "chunking": "table_row",
                    "action": "extract_links_and_metadata",
                    "include_ids": ["org_forms", "teacher_forms"],
                },
                "news": {
                    "description": "Zeitkritische News",
                    "chunking": "naive",
                    "freshness_weight": 0.5,
                    "include_ids": ["competitions_2526"],
                },
                "ignored": {
                    "description": "Irrelevanter Content",
                    "action": "skip",
                    "include_ids": ["abotest20210218", "departm_departm"],
                },
            },
            "documents": {
                "theses": {
                    "description": "Wissenschaftliche Arbeiten",
                    "parser": "pdf_scientific",
                    "chunk_size": 2048,
                    "files": ["diplomarbeit_vorlage.docx", "200403_main_final.pdf"],
                },
                "forms": {
                    "description": "Formulare",
                    "parser": "pdf_form_fields",
                    "action": "index_metadata_only",
                    "files": ["schulabmeldung.pdf", "sonderurlaub.pdf"],
                },
                "standard_docs": {
                    "description": "Allgemeine Dokumente",
                    "parser": "pdf_standard",
                    "chunk_size": 1024,
                    "files": ["werte_htl_leonding.pdf"],
                },
            },
            "media": {
                "informative_images": {
                    "description": "Bilder mit Info",
                    "action": "caption_and_index",
                    "vision_model": "qwen2.5-vl",
                    "files": ["gebaeude_eg.png", "hauptschalter.png"],
                },
                "decorative": {
                    "description": "Dekorativ",
                    "action": "skip",
                    "files": ["htllogo_2022_black_v2.png"],
                },
            },
        }
    }


@pytest.fixture()
def yaml_eval_dir(tmp_path: Path, yaml_strategies: dict) -> Path:
    """Create eval directory with preprocessing_strategies.yaml."""
    d = tmp_path / "evaluated"
    d.mkdir()
    yaml_file = d / "preprocessing_strategies.yaml"
    yaml_file.write_text(
        yaml.dump(yaml_strategies, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )
    return d


@pytest.fixture()
def json_eval_dir(tmp_path: Path) -> Path:
    """Create eval directory with legacy page_strategies.json."""
    d = tmp_path / "evaluated_legacy"
    d.mkdir()
    pages = [
        {
            "page_id": "departm:electronics",
            "content_type": "knowledge",
            "rag_readiness": 0.85,
            "recommended_chunk_size": 512,
            "noise_level": "low",
        },
        {
            "page_id": "start",
            "content_type": "portal",
            "rag_readiness": 0.2,
            "recommended_chunk_size": 128,
            "noise_level": "medium",
        },
    ]
    (d / "page_strategies.json").write_text(json.dumps(pages), encoding="utf-8")
    return d


# --- YAML Loading Tests ---


class TestStrategyLoaderYAML:
    """Test loading from preprocessing_strategies.yaml."""

    def test_load_yaml_finds_file(self, yaml_eval_dir: Path) -> None:
        from strategy_loader import StrategyLoader

        loader = StrategyLoader()
        loader.load(yaml_eval_dir)
        # Should have loaded strategies (not empty)
        s = loader.get_strategy("departm:electronics")
        assert s.page_id == "departm:electronics"

    def test_knowledge_articles_mapping(self, yaml_eval_dir: Path) -> None:
        """knowledge_articles -> KNOWLEDGE content_type + recursive_header chunking."""
        from strategy_loader import ContentType, StrategyLoader

        loader = StrategyLoader()
        loader.load(yaml_eval_dir)
        s = loader.get_strategy("departm:electronics")
        assert s.content_type == ContentType.KNOWLEDGE
        assert s.chunking_method == "recursive_header"

    def test_portals_mapping(self, yaml_eval_dir: Path) -> None:
        """portals -> PORTAL content_type + parent_context chunking."""
        from strategy_loader import ContentType, StrategyLoader

        loader = StrategyLoader()
        loader.load(yaml_eval_dir)
        s = loader.get_strategy("start")
        assert s.content_type == ContentType.PORTAL
        assert s.chunking_method == "parent_context"

    def test_news_mapping(self, yaml_eval_dir: Path) -> None:
        """news -> NEWS content_type + naive chunking."""
        from strategy_loader import ContentType, StrategyLoader

        loader = StrategyLoader()
        loader.load(yaml_eval_dir)
        s = loader.get_strategy("competitions:2526")
        assert s.content_type == ContentType.NEWS
        assert s.chunking_method == "naive"

    def test_forms_wiki_page_mapping(self, yaml_eval_dir: Path) -> None:
        """forms (wiki_pages) -> FORM content_type."""
        from strategy_loader import ContentType, StrategyLoader

        loader = StrategyLoader()
        loader.load(yaml_eval_dir)
        s = loader.get_strategy("org:forms")
        assert s.content_type == ContentType.FORM

    def test_ignored_pages_skipped(self, yaml_eval_dir: Path) -> None:
        """ignored pages have action=skip and is_ignored() returns True."""
        from strategy_loader import StrategyLoader

        loader = StrategyLoader()
        loader.load(yaml_eval_dir)
        assert loader.is_ignored("abotest20210218")
        assert loader.is_ignored("departm:departm")

    def test_non_ignored_pages_not_skipped(self, yaml_eval_dir: Path) -> None:
        from strategy_loader import StrategyLoader

        loader = StrategyLoader()
        loader.load(yaml_eval_dir)
        assert not loader.is_ignored("departm:electronics")
        assert not loader.is_ignored("start")

    def test_underscore_to_colon_conversion(self, yaml_eval_dir: Path) -> None:
        """YAML uses underscores (departm_electronics), loader converts to colons."""
        from strategy_loader import StrategyLoader

        loader = StrategyLoader()
        loader.load(yaml_eval_dir)
        # The YAML has "departm_electronics", but we look up "departm:electronics"
        s = loader.get_strategy("departm:electronics")
        assert s.page_id == "departm:electronics"

    def test_unknown_page_gets_default(self, yaml_eval_dir: Path) -> None:
        """Unknown pages get sensible defaults."""
        from strategy_loader import ContentType, StrategyLoader

        loader = StrategyLoader()
        loader.load(yaml_eval_dir)
        s = loader.get_strategy("nonexistent:page")
        assert s.content_type == ContentType.KNOWLEDGE
        assert s.chunking_method == "semantic"
        assert s.action == "process"


class TestMediaStrategy:
    """Test media strategy loading from YAML."""

    def test_informative_images_action(self, yaml_eval_dir: Path) -> None:
        from strategy_loader import StrategyLoader

        loader = StrategyLoader()
        loader.load(yaml_eval_dir)
        ms = loader.get_media_strategy("gebaeude_eg.png")
        assert ms.action == "caption_and_index"

    def test_decorative_images_skip(self, yaml_eval_dir: Path) -> None:
        from strategy_loader import StrategyLoader

        loader = StrategyLoader()
        loader.load(yaml_eval_dir)
        ms = loader.get_media_strategy("htllogo_2022_black_v2.png")
        assert ms.action == "skip"

    def test_document_strategy(self, yaml_eval_dir: Path) -> None:
        """Document files get a MediaStrategy with correct parser."""
        from strategy_loader import StrategyLoader

        loader = StrategyLoader()
        loader.load(yaml_eval_dir)
        ms = loader.get_media_strategy("schulabmeldung.pdf")
        assert ms.action == "index_metadata_only"
        assert ms.content_type == "FORM"

    def test_thesis_document(self, yaml_eval_dir: Path) -> None:
        from strategy_loader import StrategyLoader

        loader = StrategyLoader()
        loader.load(yaml_eval_dir)
        ms = loader.get_media_strategy("200403_main_final.pdf")
        assert ms.content_type == "KNOWLEDGE"
        assert ms.parser == "pdf_scientific"

    def test_unknown_media_gets_default(self, yaml_eval_dir: Path) -> None:
        from strategy_loader import StrategyLoader

        loader = StrategyLoader()
        loader.load(yaml_eval_dir)
        ms = loader.get_media_strategy("unknown_file.pdf")
        assert ms.action == "process"
        assert ms.content_type == "DOCUMENT"


class TestLegacyJSON:
    """Test backwards compatibility with page_strategies.json."""

    def test_json_fallback(self, json_eval_dir: Path) -> None:
        from strategy_loader import StrategyLoader

        loader = StrategyLoader()
        loader.load(json_eval_dir)
        s = loader.get_strategy("departm:electronics")
        assert s.page_id == "departm:electronics"

    def test_yaml_preferred_over_json(self, tmp_path: Path, yaml_strategies: dict) -> None:
        """When both files exist, YAML takes priority."""
        d = tmp_path / "both"
        d.mkdir()
        # Write YAML
        (d / "preprocessing_strategies.yaml").write_text(
            yaml.dump(yaml_strategies, default_flow_style=False, allow_unicode=True),
            encoding="utf-8",
        )
        # Write JSON (different data)
        (d / "page_strategies.json").write_text(
            json.dumps([{"page_id": "json:only", "content_type": "news"}]),
            encoding="utf-8",
        )
        from strategy_loader import StrategyLoader

        loader = StrategyLoader()
        loader.load(d)
        # YAML strategies should be loaded, not JSON
        s = loader.get_strategy("departm:electronics")
        assert s.page_id == "departm:electronics"

    def test_empty_dir_no_error(self, tmp_path: Path) -> None:
        from strategy_loader import StrategyLoader

        empty = tmp_path / "empty"
        empty.mkdir()
        loader = StrategyLoader()
        loader.load(empty)
        # Should return defaults for everything
        s = loader.get_strategy("any:page")
        assert s.page_id == "any:page"


class TestContentType:
    """Test ContentType enum values."""

    def test_all_types_exist(self) -> None:
        from strategy_loader import ContentType

        expected = {"KNOWLEDGE", "NEWS", "PORTAL", "FORM", "ARCHIVED", "IGNORED"}
        actual = {ct.value for ct in ContentType}
        assert expected == actual
