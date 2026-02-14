"""
Tests for config.py - Central Configuration Loader
====================================================
Constitution Article II-B: Centralized YAML Configuration
Constitution Article III: Critical-Path Unit Testing

Tests:
- YAML loading and parsing
- Placeholder resolution (${var} syntax)
- Secret file reference handling
- Missing config graceful fallback
- get_setting() nested path access
"""
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

# Import the functions under test (not the module-level side effects)
# We import specific functions to avoid triggering load_config() at import time
import importlib
import sys


# =============================================================================
# Helpers
# =============================================================================


def _import_config_functions():
    """
    Import config module functions without triggering module-level load_config().
    Returns the module after import.
    """
    # If already imported, just return it
    if "config" in sys.modules:
        return sys.modules["config"]

    # The module loads config at import time; that's fine for tests since
    # PLACEHOLDER_env.yaml exists as fallback
    import config

    return config


# =============================================================================
# Test: resolve_placeholders
# =============================================================================


class TestResolvePlaceholders:
    """Tests for the ${var} placeholder resolution logic."""

    def setup_method(self) -> None:
        self.config_mod = _import_config_functions()

    def test_simple_placeholder(self) -> None:
        data = {"PATHS": {"root_dir": "/test/root", "config_dir": "${root_dir}/config"}}
        result = self.config_mod.resolve_placeholders(data)
        assert result["PATHS"]["config_dir"] == "/test/root/config"

    def test_nested_placeholder(self) -> None:
        data = {
            "PATHS": {
                "root_dir": "/test/root",
                "config_dir": "${root_dir}/config",
                "secrets_dir": "${config_dir}/secrets",
            }
        }
        result = self.config_mod.resolve_placeholders(data)
        assert result["PATHS"]["secrets_dir"] == "/test/root/config/secrets"

    def test_no_placeholders(self) -> None:
        data = {"PATHS": {"root_dir": "/plain/path"}, "APP": {"name": "test"}}
        result = self.config_mod.resolve_placeholders(data)
        assert result["PATHS"]["root_dir"] == "/plain/path"
        assert result["APP"]["name"] == "test"

    def test_unresolvable_placeholder_preserved(self) -> None:
        data = {"PATHS": {"root_dir": "/test"}, "OTHER": {"ref": "${unknown_var}/path"}}
        result = self.config_mod.resolve_placeholders(data)
        assert result["OTHER"]["ref"] == "${unknown_var}/path"

    def test_non_string_values_unchanged(self) -> None:
        data = {"PATHS": {"root_dir": "/test"}, "NUMBERS": {"port": 18334, "enabled": True}}
        result = self.config_mod.resolve_placeholders(data)
        assert result["NUMBERS"]["port"] == 18334
        assert result["NUMBERS"]["enabled"] is True

    def test_list_values_resolved(self) -> None:
        data = {
            "PATHS": {"root_dir": "/test"},
            "LIST": {"items": ["${root_dir}/a", "${root_dir}/b"]},
        }
        result = self.config_mod.resolve_placeholders(data)
        assert result["LIST"]["items"] == ["/test/a", "/test/b"]


# =============================================================================
# Test: load_yaml_config
# =============================================================================


class TestLoadYamlConfig:
    """Tests for YAML file loading."""

    def setup_method(self) -> None:
        self.config_mod = _import_config_functions()

    def test_load_valid_yaml(self, tmp_path: Path) -> None:
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("APP:\n  name: test\n  version: '1.0'\n", encoding="utf-8")
        result = self.config_mod.load_yaml_config(yaml_file)
        assert result["APP"]["name"] == "test"
        assert result["APP"]["version"] == "1.0"

    def test_load_nonexistent_file_raises(self, tmp_path: Path) -> None:
        missing_file = tmp_path / "nonexistent.yaml"
        with pytest.raises(FileNotFoundError, match="Config Datei nicht gefunden"):
            self.config_mod.load_yaml_config(missing_file)

    def test_load_invalid_yaml_raises(self, tmp_path: Path) -> None:
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text("just a plain string", encoding="utf-8")
        with pytest.raises(ValueError, match="Ungueltiges Config-Format"):
            self.config_mod.load_yaml_config(yaml_file)


# =============================================================================
# Test: load_secret_file
# =============================================================================


class TestLoadSecretFile:
    """Tests for secret file loading."""

    def setup_method(self) -> None:
        self.config_mod = _import_config_functions()

    def test_load_plain_token(self, tmp_path: Path) -> None:
        token_file = tmp_path / "api.token"
        token_file.write_text("sk-test-token-12345\n", encoding="utf-8")
        result = self.config_mod.load_secret_file(token_file)
        assert result == "sk-test-token-12345"

    def test_load_key_value_format(self, tmp_path: Path) -> None:
        token_file = tmp_path / "api.token"
        token_file.write_text("TOKEN=my-secret-value\n", encoding="utf-8")
        result = self.config_mod.load_secret_file(token_file)
        assert result == "my-secret-value"

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        missing = tmp_path / "missing.token"
        result = self.config_mod.load_secret_file(missing)
        assert result == ""

    def test_jwt_token_not_split(self, tmp_path: Path) -> None:
        token_file = tmp_path / "jwt.token"
        jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.abc123="
        token_file.write_text(jwt, encoding="utf-8")
        result = self.config_mod.load_secret_file(token_file)
        assert result == jwt


# =============================================================================
# Test: get_setting
# =============================================================================


class TestGetSetting:
    """Tests for nested path-based config access."""

    def setup_method(self) -> None:
        self.config_mod = _import_config_functions()

    def test_get_existing_path(self) -> None:
        # APP.name should always exist (even from PLACEHOLDER fallback)
        result = self.config_mod.get_setting("APP.name")
        assert result is not None
        assert isinstance(result, str)

    def test_get_missing_path_returns_default(self) -> None:
        result = self.config_mod.get_setting("NONEXISTENT.deep.path", "fallback_value")
        assert result == "fallback_value"

    def test_get_none_default(self) -> None:
        result = self.config_mod.get_setting("NONEXISTENT.path")
        assert result is None


# =============================================================================
# Test: compute_config_hash
# =============================================================================


class TestComputeConfigHash:
    """Tests for config hash computation."""

    def setup_method(self) -> None:
        self.config_mod = _import_config_functions()

    def test_same_config_same_hash(self) -> None:
        config = {"APP": {"name": "test"}, "PATHS": {"root_dir": "/test"}}
        hash1 = self.config_mod.compute_config_hash(config)
        hash2 = self.config_mod.compute_config_hash(config)
        assert hash1 == hash2

    def test_different_config_different_hash(self) -> None:
        config1 = {"APP": {"name": "test1"}}
        config2 = {"APP": {"name": "test2"}}
        hash1 = self.config_mod.compute_config_hash(config1)
        hash2 = self.config_mod.compute_config_hash(config2)
        assert hash1 != hash2

    def test_meta_excluded_from_hash(self) -> None:
        config_with_meta = {"APP": {"name": "test"}, "_meta": {"generated": "now"}}
        config_without_meta = {"APP": {"name": "test"}}
        h1 = self.config_mod.compute_config_hash(config_with_meta)
        h2 = self.config_mod.compute_config_hash(config_without_meta)
        assert h1 == h2


# =============================================================================
# Test: PLACEHOLDER_env.yaml Validity
# =============================================================================


class TestPlaceholderEnvYaml:
    """Validate that the committed PLACEHOLDER_env.yaml is parseable."""

    def test_placeholder_yaml_is_valid(self, config_dir: Path) -> None:
        placeholder = config_dir / "PLACEHOLDER_env.yaml"
        assert placeholder.exists(), "PLACEHOLDER_env.yaml must exist in config/"
        with open(placeholder, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)
        assert "APP" in data
        assert "PATHS" in data
        assert "SERVICES" in data

    def test_placeholder_has_required_sections(self, config_dir: Path) -> None:
        placeholder = config_dir / "PLACEHOLDER_env.yaml"
        with open(placeholder, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        required_sections = ["APP", "PATHS", "SOURCE_WIKI", "SERVICES", "PIPELINE", "PLUGIN"]
        for section in required_sections:
            assert section in data, f"PLACEHOLDER_env.yaml missing required section: {section}"
