"""
Konfiguration für die Fetched Data Evaluation.

Lädt alle Einstellungen aus config/env.yaml - KEINE hardcoded Werte!
"""

import os
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path
import yaml


# =============================================================================
# YAML Loading with Variable Resolution
# =============================================================================

def resolve_variables(value: Any, variables: Dict[str, str]) -> Any:
    """Resolves ${var} placeholders in strings."""
    if isinstance(value, str):
        pattern = r'\$\{([^}]+)\}'
        matches = re.findall(pattern, value)
        for match in matches:
            if match in variables:
                value = value.replace(f'${{{match}}}', variables[match])
        return value
    elif isinstance(value, dict):
        return {k: resolve_variables(v, variables) for k, v in value.items()}
    elif isinstance(value, list):
        return [resolve_variables(item, variables) for item in value]
    return value


def load_env_yaml(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Lädt env.yaml und löst Variablen auf.

    Args:
        config_path: Pfad zur env.yaml (default: config/env.yaml)

    Returns:
        Dictionary mit allen Konfigurationen
    """
    if config_path is None:
        script_dir = Path(__file__).parent
        # 02_deep_evaluation -> pipeline -> dev_dito (root)
        repo_root = script_dir.parent.parent
        # Prefer pipeline-local env.yaml (has PATHS for this pipeline)
        local_env = script_dir / "env.yaml"
        if local_env.exists():
            config_path = local_env
        else:
            config_path = repo_root / "config" / "env.yaml"
        if not config_path.exists():
            config_path = script_dir.parent / "config" / "env.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        raw_config = yaml.safe_load(f)

    # Build variables dict for resolution
    variables = {}

    # Extract PATHS variables first
    paths = raw_config.get('PATHS', {})
    for key, value in paths.items():
        if isinstance(value, str) and '${' not in value:
            variables[key] = value

    # Resolve variables in multiple passes (for nested references)
    for _ in range(5):  # 5 passes for deep nesting
        paths = resolve_variables(paths, variables)
        for key, value in paths.items():
            if isinstance(value, str):
                variables[key] = value

    # Resolve all variables in config
    resolved_config = resolve_variables(raw_config, variables)

    return resolved_config


def get_latest_fetch_dir(fetched_base: Path) -> Optional[Path]:
    """Find the latest fetched_at_* directory under the given base.

    Used when env.yaml points to a non-existent fetched_data_dir (e.g. after a
    new fetch); deep eval then uses the most recent fetch automatically.
    """
    if not fetched_base.exists():
        return None
    fetch_dirs = sorted(
        [d for d in fetched_base.iterdir() if d.is_dir() and d.name.startswith("fetched_at_")],
        key=lambda x: x.name,
        reverse=True,
    )
    return fetch_dirs[0] if fetch_dirs else None


# =============================================================================
# Configuration Dataclasses
# =============================================================================

@dataclass
class LLMConfig:
    """LLM Konfiguration für Query-Generierung."""
    provider: str = "LM-Studio"
    base_url: str = ""  # Muss aus env.yaml geladen werden
    model: str = ""
    api_key: str = "not-needed"
    temperature: float = 0.3
    max_tokens: int = 200
    top_p: float = 0.9


@dataclass
class QueryGenerationConfig:
    """Konfiguration für Query-Generierung."""
    enabled: bool = True
    llm: LLMConfig = field(default_factory=LLMConfig)
    pages_per_namespace: int = 3
    chunks_per_page: int = 2
    min_chunk_length: int = 200
    output_format: str = "json"
    include_source: bool = True
    include_context: bool = True


@dataclass
class DiplomaThesisConfig:
    """Konfiguration für Diplomarbeits-Behandlung."""
    enabled: bool = True
    separate_analysis: bool = True
    files: List[str] = field(default_factory=list)


@dataclass
class ReportsConfig:
    """Report-Konfiguration."""
    author: str = "Jan Ritt"
    institution: str = "HTL Leonding"
    generate_markdown: bool = True
    generate_json: bool = True
    generate_html: bool = False


@dataclass
class EvaluationConfig:
    """Haupt-Konfiguration für die Evaluation."""
    # Pfade
    root_dir: Optional[Path] = None
    config_dir: Optional[Path] = None
    script_dir: Optional[Path] = None
    results_dir: Optional[Path] = None
    fetched_data_dir: Optional[Path] = None

    # Spezifische Pfade
    page_content_dir: Optional[Path] = None
    page_metadata_dir: Optional[Path] = None
    page_html_dir: Optional[Path] = None
    page_links_dir: Optional[Path] = None
    media_dir: Optional[Path] = None
    wiki_analysis_report: Optional[Path] = None

    # Sub-Konfigurationen
    query_generation: QueryGenerationConfig = field(default_factory=QueryGenerationConfig)
    diploma_thesis: DiplomaThesisConfig = field(default_factory=DiplomaThesisConfig)
    reports: ReportsConfig = field(default_factory=ReportsConfig)

    # Content Classification
    teacher_namespaces: List[str] = field(default_factory=list)
    public_namespaces: List[str] = field(default_factory=list)

    # Quality Thresholds
    min_page_chars: int = 50
    max_page_chars: int = 100000
    min_page_words: int = 10

    # Processing
    batch_size: int = 50
    max_workers: int = 4
    continue_on_error: bool = True
    show_progress: bool = True
    log_level: str = "INFO"

    # Raw config for access to all settings
    raw_config: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Convert string paths to Path objects
        path_attrs = [
            'root_dir', 'config_dir', 'script_dir', 'results_dir',
            'fetched_data_dir', 'page_content_dir', 'page_metadata_dir',
            'page_html_dir', 'page_links_dir', 'media_dir',
            'wiki_analysis_report'
        ]
        for attr in path_attrs:
            val = getattr(self, attr, None)
            if val and isinstance(val, str):
                setattr(self, attr, Path(val))

    @classmethod
    def from_yaml(cls, config_path: Optional[Path] = None) -> "EvaluationConfig":
        """
        Erstellt Konfiguration aus env.yaml.

        Args:
            config_path: Pfad zur env.yaml
        """
        env = load_env_yaml(config_path)

        paths = env.get('PATHS', {})
        # Auto-detect latest fetch dir if configured path does not exist
        fetched_dir_val = paths.get('fetched_data_dir')
        fetched_base_val = paths.get('fetched_data_base')
        if fetched_dir_val and fetched_base_val:
            fetched_dir = Path(fetched_dir_val)
            fetched_base = Path(fetched_base_val)
            if not fetched_dir.exists() and fetched_base.exists():
                latest = get_latest_fetch_dir(fetched_base)
                if latest:
                    paths['fetched_data_dir'] = str(latest)
                    paths['page_content_dir'] = str(latest / 'page_content')
                    paths['page_metadata_dir'] = str(latest / 'page_metadata')
                    paths['page_html_dir'] = str(latest / 'page_html')
                    paths['page_links_dir'] = str(latest / 'page_links')
                    paths['page_backlinks_dir'] = str(latest / 'page_backlinks')
                    paths['page_history_dir'] = str(latest / 'page_history')
                    paths['media_dir'] = str(latest / 'media')
                    paths['namespaces_dir'] = str(latest / 'namespaces')
                    paths['changes_dir'] = str(latest / 'changes')
                    paths['raw_json_dir'] = str(latest / 'raw_json')
                    paths['wiki_analysis_report'] = str(latest / 'wiki_analysis_report.txt')
                    paths['media_usage_index'] = str(latest / 'media_usage_index.json')

        query_cfg = env.get('QUERY_GENERATION', {})
        diploma_cfg = env.get('DIPLOMA_THESIS', {})
        reports_cfg = env.get('REPORTS', {})
        content_cfg = env.get('CONTENT_CLASSIFICATION', {})
        format_cfg = env.get('FORMAT_ANALYSIS', {})
        processing_cfg = env.get('PROCESSING', {})

        # LLM Config - KEINE Defaults, muss aus env.yaml kommen
        llm_cfg = env.get('LLM', {})
        if not llm_cfg:
            raise ValueError("LLM configuration missing in env.yaml")
        
        gen_cfg = llm_cfg.get('generation', {})
        base_url = llm_cfg.get('base_url')
        if not base_url:
            raise ValueError("LLM base_url missing in env.yaml (LLM.base_url)")
        
        model = llm_cfg.get('classification_model') or llm_cfg.get('model')
        if not model:
            raise ValueError("LLM model missing in env.yaml (LLM.classification_model or LLM.model)")
        
        llm = LLMConfig(
            provider=llm_cfg.get('provider', 'LM-Studio'),
            base_url=base_url,
            model=model,
            api_key=llm_cfg.get('api_key', 'not-needed'),
            temperature=gen_cfg.get('temperature', 0.3),
            max_tokens=gen_cfg.get('max_tokens', 200),
            top_p=gen_cfg.get('top_p', 0.9)
        )

        # Query Generation Config
        sampling_cfg = query_cfg.get('sampling', {})
        output_cfg = query_cfg.get('output', {})
        query_generation = QueryGenerationConfig(
            enabled=query_cfg.get('enabled', True),
            llm=llm,
            pages_per_namespace=sampling_cfg.get('pages_per_namespace', 3),
            chunks_per_page=sampling_cfg.get('chunks_per_page', 2),
            min_chunk_length=sampling_cfg.get('min_chunk_length', 200),
            output_format=output_cfg.get('format', 'json'),
            include_source=output_cfg.get('include_source', True),
            include_context=output_cfg.get('include_context', True)
        )

        # Diploma Thesis Config
        diploma_thesis = DiplomaThesisConfig(
            enabled=diploma_cfg.get('enabled', True),
            separate_analysis=diploma_cfg.get('separate_analysis', True),
            files=diploma_cfg.get('files', [])
        )

        # Reports Config
        reports = ReportsConfig(
            author=reports_cfg.get('author', 'Jan Ritt'),
            institution=reports_cfg.get('institution', 'HTL Leonding'),
            generate_markdown=reports_cfg.get('formats', {}).get('markdown', True),
            generate_json=reports_cfg.get('formats', {}).get('json', True),
            generate_html=reports_cfg.get('formats', {}).get('html', False)
        )

        # Content Classification
        namespaces = content_cfg.get('namespaces', {})
        teacher_namespaces = namespaces.get('teacher_restricted', ['teacher'])
        public_namespaces = namespaces.get('public', [])

        # Quality Thresholds
        quality = format_cfg.get('quality_thresholds', {}).get('page_content', {})

        return cls(
            root_dir=paths.get('root_dir'),
            config_dir=paths.get('config_dir'),
            script_dir=paths.get('script_dir'),
            results_dir=paths.get('results_dir'),
            fetched_data_dir=paths.get('fetched_data_dir'),
            page_content_dir=paths.get('page_content_dir'),
            page_metadata_dir=paths.get('page_metadata_dir'),
            page_html_dir=paths.get('page_html_dir'),
            page_links_dir=paths.get('page_links_dir'),
            media_dir=paths.get('media_dir'),
            wiki_analysis_report=paths.get('wiki_analysis_report'),
            query_generation=query_generation,
            diploma_thesis=diploma_thesis,
            reports=reports,
            teacher_namespaces=teacher_namespaces,
            public_namespaces=public_namespaces,
            min_page_chars=quality.get('min_chars', 50),
            max_page_chars=quality.get('max_chars', 100000),
            min_page_words=quality.get('min_words', 10),
            batch_size=processing_cfg.get('batch_size', 50),
            max_workers=processing_cfg.get('max_workers', 4),
            continue_on_error=processing_cfg.get('continue_on_error', True),
            show_progress=processing_cfg.get('show_progress', True),
            log_level=processing_cfg.get('log_level', 'INFO'),
            raw_config=env
        )

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert Konfiguration zu Dictionary."""
        return {
            'root_dir': str(self.root_dir),
            'fetched_data_dir': str(self.fetched_data_dir),
            'results_dir': str(self.results_dir),
            'query_generation': {
                'enabled': self.query_generation.enabled,
                'llm_model': self.query_generation.llm.model
            },
            'diploma_thesis': {
                'enabled': self.diploma_thesis.enabled,
                'files_count': len(self.diploma_thesis.files)
            },
            'processing': {
                'batch_size': self.batch_size,
                'max_workers': self.max_workers
            }
        }


# =============================================================================
# Singleton Config Instance
# =============================================================================

_config_instance: Optional[EvaluationConfig] = None


def get_config(reload: bool = False) -> EvaluationConfig:
    """
    Gibt die globale Konfiguration zurück (Singleton).

    Args:
        reload: Wenn True, wird die Konfiguration neu geladen
    """
    global _config_instance
    if _config_instance is None or reload:
        _config_instance = EvaluationConfig.from_yaml()
    return _config_instance


def get_env() -> Dict[str, Any]:
    """Gibt das rohe env.yaml Dictionary zurück."""
    return load_env_yaml()


# =============================================================================
# Test
# =============================================================================

if __name__ == "__main__":
    # Test config loading
    config = get_config()
    print("=" * 60)
    print("  CONFIG LOADED SUCCESSFULLY")
    print("=" * 60)
    print(f"\n  Fetched Data: {config.fetched_data_dir}")
    print(f"  Results Dir:  {config.results_dir}")
    print(f"  Page Content: {config.page_content_dir}")
    print(f"  Media Dir:    {config.media_dir}")
    print(f"\n  Teacher Namespaces: {config.teacher_namespaces}")
    print(f"  Diploma Thesis Files: {len(config.diploma_thesis.files)}")
    print(f"  Query Generation: {config.query_generation.enabled}")
    print(f"  LLM Model: {config.query_generation.llm.model}")
    print("=" * 60)
