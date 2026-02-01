"""
Configuration Loader for Qdrant Embeddings Creator
===================================================
Loads and resolves configuration from env.yaml with variable substitution.
Pattern follows the RAG Preprocessing Pipeline implementation.
"""

import os
import re
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field


class ConfigError(Exception):
    """Configuration related errors."""
    pass


def resolve_variables(config: Dict[str, Any], context: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Recursively resolve ${variable} placeholders in configuration.
    
    Args:
        config: Configuration dictionary
        context: Variable context for resolution (built during traversal)
        
    Returns:
        Configuration with resolved variables
    """
    if context is None:
        context = {}
    
    def resolve_value(value: Any) -> Any:
        if isinstance(value, str):
            pattern = r'\$\{([^}]+)\}'
            matches = re.findall(pattern, value)
            
            for match in matches:
                if match in context:
                    value = value.replace(f'${{{match}}}', context[match])
                else:
                    for ctx_key, ctx_val in context.items():
                        if ctx_key.endswith(f'.{match}') or ctx_key == match:
                            value = value.replace(f'${{{match}}}', ctx_val)
                            break
            return value
        elif isinstance(value, dict):
            return {k: resolve_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [resolve_value(item) for item in value]
        return value
    
    def collect_context(d: Dict[str, Any], prefix: str = '') -> None:
        for key, value in d.items():
            full_key = f"{prefix}{key}" if prefix else key
            if isinstance(value, str):
                if '${' not in value:
                    context[full_key] = value
                    context[key] = value
            elif isinstance(value, dict):
                collect_context(value, f"{full_key}.")
    
    result = config.copy()
    for _ in range(10):
        old_result = str(result)
        collect_context(result)
        result = resolve_value(result)
        if str(result) == old_result:
            break
    
    return result


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to env.yaml (default: auto-detect)
        
    Returns:
        Resolved configuration dictionary
    """
    if config_path is None:
        # Look for env.yaml in the same directory as this script (embeddings_creator/)
        script_dir = Path(__file__).parent
        resolved_path = script_dir / "env.yaml"
        
        # Fallback: check pipeline/config/env.yaml
        if not resolved_path.exists():
            resolved_path = script_dir.parent / "config" / "env.yaml"
    else:
        resolved_path = Path(config_path)
    
    if not resolved_path.exists():
        raise ConfigError(f"Configuration file not found: {resolved_path}")
    
    with open(resolved_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    if config is None:
        raise ConfigError(f"Empty configuration file: {resolved_path}")
    
    config = resolve_variables(config)
    return config


@dataclass
class PathsConfig:
    """Paths configuration."""
    root_dir: str
    config_dir: str
    script_dir: str
    output_dir: str
    log_dir: str
    preprocessing_base: str
    input_dir: str
    input_fallback: str


@dataclass
class OpenAIConfig:
    """OpenAI API configuration."""
    api_key_env: str
    base_url: str
    timeout: int
    max_retries: int
    retry_delay: int
    embedding_model: str
    embedding_dimensions: int
    encoding_format: str
    batch_size: int
    max_tokens_per_batch: int
    delay_between_batches: float


@dataclass
class ChunkingConfig:
    """Chunking configuration."""
    default: Dict[str, Any]
    content_types: Dict[str, Dict[str, Any]]


@dataclass
class OutputConfig:
    """Output configuration."""
    format: str
    encoding: str
    combined: bool
    filename: str
    schema: Dict[str, str]
    include_metadata: Dict[str, bool]


@dataclass
class Config:
    """Main configuration container."""
    app: Dict[str, Any]
    paths: PathsConfig
    openai: OpenAIConfig
    chunking: ChunkingConfig
    text_prep: Dict[str, Any]
    output: OutputConfig
    statistics: Dict[str, Any]
    logging: Dict[str, Any]
    processing: Dict[str, Any]
    validation: Dict[str, Any]
    
    _raw: Dict[str, Any] = field(default_factory=dict, repr=False)
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> 'Config':
        """Load and parse configuration."""
        raw = load_config(config_path)
        
        # Check for container environment variables (Docker overrides)
        data_path = os.environ.get('DATA_PATH')
        pipeline_path = os.environ.get('PIPELINE_PATH')
        
        if data_path and pipeline_path:
            # Running in Docker container - use container paths
            paths = PathsConfig(
                root_dir=pipeline_path,
                config_dir=pipeline_path,
                script_dir=pipeline_path,
                output_dir=f"{data_path}/embeddings",
                log_dir=f"{data_path}/logs",
                preprocessing_base=f"{data_path}/preprocessed",
                input_dir=f"{data_path}/preprocessed",
                input_fallback=f"{data_path}/evaluated/for_qdrant",
            )
        else:
            # Running locally - use paths from env.yaml
            paths = PathsConfig(
                root_dir=raw['PATHS']['root_dir'],
                config_dir=raw['PATHS']['config_dir'],
                script_dir=raw['PATHS']['script_dir'],
                output_dir=raw['PATHS']['output_dir'],
                log_dir=raw['PATHS']['log_dir'],
                preprocessing_base=raw['PATHS'].get('preprocessing_base', raw['PATHS']['input_dir']),
                input_dir=raw['PATHS']['input_dir'],
                input_fallback=raw['PATHS']['input_fallback'],
            )
        
        openai = OpenAIConfig(
            api_key_env=raw['OPENAI']['api_key_env'],
            base_url=raw['OPENAI']['base_url'],
            timeout=raw['OPENAI']['timeout'],
            max_retries=raw['OPENAI']['max_retries'],
            retry_delay=raw['OPENAI']['retry_delay'],
            embedding_model=raw['OPENAI']['embedding']['model'],
            embedding_dimensions=raw['OPENAI']['embedding']['dimensions'],
            encoding_format=raw['OPENAI']['embedding']['encoding_format'],
            batch_size=raw['OPENAI']['batch']['size'],
            max_tokens_per_batch=raw['OPENAI']['batch']['max_tokens_per_batch'],
            delay_between_batches=raw['OPENAI']['rate_limit']['delay_between_batches'],
        )
        
        chunking = ChunkingConfig(
            default=raw['CHUNKING']['default'],
            content_types=raw['CHUNKING']['content_types'],
        )
        
        output = OutputConfig(
            format=raw['OUTPUT']['format'],
            encoding=raw['OUTPUT']['encoding'],
            combined=raw['OUTPUT']['combined'],
            filename=raw['OUTPUT']['filename'],
            schema=raw['OUTPUT']['schema'],
            include_metadata=raw['OUTPUT']['include_metadata'],
        )
        
        # Get logging and statistics configs
        logging_config = raw['LOGGING'].copy()
        statistics_config = raw['STATISTICS'].copy()
        
        # Override paths in logging/statistics if running in container
        if data_path and pipeline_path:
            logging_config['file'] = f"{data_path}/logs/embedding_process.log"
            statistics_config['output_file'] = f"{data_path}/embeddings/embedding_statistics.json"
        
        return cls(
            app=raw['APP'],
            paths=paths,
            openai=openai,
            chunking=chunking,
            text_prep=raw['TEXT_PREP'],
            output=output,
            statistics=statistics_config,
            logging=logging_config,
            processing=raw['PROCESSING'],
            validation=raw['VALIDATION'],
            _raw=raw,
        )
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from raw config by dot notation."""
        keys = key.split('.')
        value = self._raw
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def get_api_key(self) -> str:
        """Get OpenAI API key from environment."""
        key = os.environ.get(self.openai.api_key_env)
        if not key:
            raise ConfigError(f"Environment variable {self.openai.api_key_env} not set")
        return key


# Global config instance (lazy loaded)
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or load the global configuration."""
    global _config
    if _config is None:
        _config = Config.load()
    return _config


def reload_config(config_path: Optional[str] = None) -> Config:
    """Force reload configuration."""
    global _config
    _config = Config.load(config_path)
    return _config


def get_latest_timestamped_path(base_dir: str, prefix: str) -> Optional[Path]:
    """
    Get the most recent timestamped subdirectory.
    
    Args:
        base_dir: Base directory path
        prefix: Prefix to filter by
        
    Returns:
        Path to latest matching directory, or None if none found
    """
    base = Path(base_dir)
    if not base.exists():
        return None
    
    matching = sorted(
        [d for d in base.iterdir() if d.is_dir() and d.name.startswith(prefix)],
        key=lambda x: x.name,
        reverse=True
    )
    
    return matching[0] if matching else None


# Test config loading
if __name__ == "__main__":
    config = get_config()
    print(f"App: {config.app['name']} v{config.app['version']}")
    print(f"Root: {config.paths.root_dir}")
    print(f"Input: {config.paths.input_dir}")
    print(f"Output: {config.paths.output_dir}")
    print(f"\nOpenAI:")
    print(f"  Model: {config.openai.embedding_model}")
    print(f"  Dimensions: {config.openai.embedding_dimensions}")
    print(f"  Batch size: {config.openai.batch_size}")
    print(f"\nChunking:")
    print(f"  Default method: {config.chunking.default['method']}")
    print(f"  Default chunk size: {config.chunking.default['max_chunk_size']}")
    print(f"  Content types: {list(config.chunking.content_types.keys())}")
