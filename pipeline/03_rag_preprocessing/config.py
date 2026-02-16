"""
Configuration Loader for RAG Preprocessing Pipeline
====================================================
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass


class ConfigError(Exception):
    """Configuration related errors."""
    pass


def load_yaml(path: Path) -> Dict[str, Any]:
    """Load YAML configuration file."""
    if not path.exists():
        raise ConfigError(f"Configuration file not found: {path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def resolve_variables(config: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve ${variable} placeholders in configuration."""
    
    def collect_values(d: Dict, prefix: str = '') -> Dict[str, str]:
        """Collect all string values for variable resolution."""
        values = {}
        for key, value in d.items():
            full_key = f"{prefix}{key}" if prefix else key
            if isinstance(value, str) and '${' not in value:
                values[full_key] = value
            elif isinstance(value, dict):
                values.update(collect_values(value, f"{full_key}."))
        return values
    
    def resolve_value(value: Any, context: Dict[str, str]) -> Any:
        """Resolve variables in a value."""
        if isinstance(value, str):
            import re
            pattern = r'\$\{([^}]+)\}'
            matches = re.findall(pattern, value)
            for match in matches:
                # Try exact match first
                if match in context:
                    value = value.replace(f'${{{match}}}', context[match])
                else:
                    # Try partial match (e.g., 'root_dir' matches 'PATHS.root_dir')
                    for ctx_key, ctx_val in context.items():
                        if ctx_key.endswith(f'.{match}') or ctx_key == match:
                            value = value.replace(f'${{{match}}}', ctx_val)
                            break
            return value
        elif isinstance(value, dict):
            return {k: resolve_value(v, context) for k, v in value.items()}
        elif isinstance(value, list):
            return [resolve_value(item, context) for item in value]
        return value
    
    # Collect context and resolve
    context = collect_values(config)
    return resolve_value(config, context)


@dataclass
class PreprocessingConfig:
    """Configuration for RAG Preprocessing Pipeline."""
    
    # Paths
    root_dir: Path
    fetched_dir: Path
    evaluated_dir: Path
    output_dir: Path
    log_dir: Path
    
    # Wiki settings
    wiki_base_url: str
    
    # Conversion settings
    conversion: Dict[str, Any]
    
    # Frontmatter settings
    frontmatter_fields: list
    
    # Media settings
    media: Dict[str, Any]
    
    # Output settings
    output: Dict[str, Any]
    
    # Processing settings
    processing: Dict[str, Any]
    
    @classmethod
    def from_yaml(cls, config_path: Optional[Path] = None) -> 'PreprocessingConfig':
        """Load configuration from YAML file.

        Prefers config/env.yaml (Article II-B), then env.yaml in module root.
        """
        if config_path is None:
            base = Path(__file__).parent
            config_path = base / 'config' / 'env.yaml'
            if not config_path.exists():
                config_path = base / 'env.yaml'
        
        raw_config = load_yaml(config_path)
        config = resolve_variables(raw_config)
        
        paths = config.get('PATHS', {})
        
        return cls(
            root_dir=Path(paths.get('root_dir', '.')),
            fetched_dir=Path(paths.get('fetched_dir', 'data/fetched')),
            evaluated_dir=Path(paths.get('evaluated_dir', 'data/evaluated')),
            output_dir=Path(paths.get('output_dir', 'data/preprocessed')),
            log_dir=Path(paths.get('log_dir', 'data/logs')),
            wiki_base_url=config.get('CONVERSION', {}).get('wiki_base_url', ''),
            conversion=config.get('CONVERSION', {}),
            frontmatter_fields=config.get('FRONTMATTER', {}).get('fields', []),
            media=config.get('MEDIA', {}),
            output=config.get('OUTPUT', {}),
            processing=config.get('PROCESSING', {}),
        )


def get_config(config_path: Optional[Path] = None) -> PreprocessingConfig:
    """Get configuration instance."""
    return PreprocessingConfig.from_yaml(config_path)


def get_latest_fetch_dir(fetched_base: Path) -> Optional[Path]:
    """Find the latest fetched_at_* directory."""
    if not fetched_base.exists():
        return None
    
    fetch_dirs = sorted(
        [d for d in fetched_base.iterdir() if d.is_dir() and d.name.startswith('fetched_at_')],
        key=lambda x: x.name,
        reverse=True
    )
    
    return fetch_dirs[0] if fetch_dirs else None


def get_latest_evaluation(evaluated_base: Path) -> Optional[Path]:
    """Find the latest evaluation directory or file.

    Looks for (in order of preference):
    1. ``deep_eval_*`` directories (from Stage 2 strategy_generator)
    2. ``evaluation_*.json`` files (legacy)

    Returns:
        Path to the directory or file, or None if nothing found.
    """
    if not evaluated_base.exists():
        return None

    # Prefer deep_eval_* directories (Stage 2 output)
    eval_dirs = sorted(
        [d for d in evaluated_base.iterdir() if d.is_dir() and d.name.startswith('deep_eval_')],
        key=lambda x: x.name,
        reverse=True,
    )
    if eval_dirs:
        return eval_dirs[0]

    # Fallback: evaluation_*.json files (legacy)
    eval_files = sorted(
        [f for f in evaluated_base.iterdir() if f.is_file() and f.name.startswith('evaluation_') and f.suffix == '.json'],
        key=lambda x: x.name,
        reverse=True,
    )
    return eval_files[0] if eval_files else None
