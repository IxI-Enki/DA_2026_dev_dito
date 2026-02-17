"""
Tests for Docker Compose Configuration Validity
=================================================
Constitution Article III: Critical-Path Unit Testing
Constitution Article VI: Secret Containment

Tests:
- docker-compose.yml is valid YAML
- All referenced Dockerfiles exist
- No hardcoded secrets in compose files
- Required services are defined
- Network configuration is correct
"""
import re
from pathlib import Path

import pytest
import yaml

from tests.conftest import BACKEND_SERVICES_DIR, REPO_ROOT


# =============================================================================
# Test: docker-compose.yml Syntax
# =============================================================================


class TestDockerComposeSyntax:
    """Validate docker-compose.yml is parseable and well-structured."""

    @pytest.fixture
    def compose_path(self) -> Path:
        return BACKEND_SERVICES_DIR / "docker-compose.yml"

    @pytest.fixture
    def compose_data(self, compose_path: Path) -> dict:
        assert compose_path.exists(), f"docker-compose.yml not found at {compose_path}"
        with open(compose_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict), "docker-compose.yml must be a YAML mapping"
        return data

    def test_compose_file_exists(self, compose_path: Path) -> None:
        assert compose_path.exists()

    def test_compose_is_valid_yaml(self, compose_data: dict) -> None:
        assert "services" in compose_data, "docker-compose.yml must have 'services' key"

    def test_compose_has_project_name(self, compose_data: dict) -> None:
        assert compose_data.get("name") == "stack-g-devdito", (
            "docker-compose.yml must have 'name: stack-g-devdito'"
        )

    def test_compose_has_networks(self, compose_data: dict) -> None:
        assert "networks" in compose_data, "docker-compose.yml must define networks"
        networks = compose_data["networks"]
        # Must have the shared leonidas-network
        assert "leonidas-network" in networks, "Missing leonidas-network"
        net_config = networks["leonidas-network"]
        assert net_config.get("external") is True, "leonidas-network must be external"


# =============================================================================
# Test: Dockerfile References
# =============================================================================


class TestDockerfileReferences:
    """Verify all Dockerfiles referenced in compose exist on disk."""

    @pytest.fixture
    def compose_data(self) -> dict:
        compose_path = BACKEND_SERVICES_DIR / "docker-compose.yml"
        with open(compose_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_all_build_contexts_exist(self, compose_data: dict) -> None:
        services = compose_data.get("services", {})
        missing = []
        for svc_name, svc_config in services.items():
            if not isinstance(svc_config, dict):
                continue
            build = svc_config.get("build")
            if build is None:
                continue  # Image-based service, no build context

            if isinstance(build, str):
                context = build
                dockerfile = "Dockerfile"
            elif isinstance(build, dict):
                context = build.get("context", ".")
                dockerfile = build.get("dockerfile", "Dockerfile")
            else:
                continue

            # Resolve relative to backend_services/
            context_path = BACKEND_SERVICES_DIR / context
            dockerfile_path = context_path / dockerfile
            if not dockerfile_path.exists():
                missing.append(f"{svc_name}: {dockerfile_path}")

        assert not missing, (
            f"Missing Dockerfiles for services:\n" + "\n".join(f"  - {m}" for m in missing)
        )


# =============================================================================
# Test: No Hardcoded Secrets (Constitution Article VI)
# =============================================================================


class TestNoHardcodedSecrets:
    """Ensure no secrets are hardcoded in compose or Dockerfiles."""

    SECRET_PATTERNS = [
        r"sk-[a-zA-Z0-9]{20,}",  # OpenAI API key pattern
        r"ghp_[a-zA-Z0-9]{36}",  # GitHub personal access token
        r"password:\s*['\"]?[a-zA-Z0-9!@#$%^&*]{8,}",  # Hardcoded passwords
    ]

    def _scan_file_for_secrets(self, file_path: Path) -> list[str]:
        """Scan a single file for secret patterns. Returns list of findings."""
        findings = []
        content = file_path.read_text(encoding="utf-8", errors="replace")
        for pattern in self.SECRET_PATTERNS:
            matches = re.findall(pattern, content)
            for match in matches:
                findings.append(f"{file_path.name}: matched pattern '{pattern}' -> '{match[:20]}...'")
        return findings

    def test_no_secrets_in_compose(self) -> None:
        compose_path = BACKEND_SERVICES_DIR / "docker-compose.yml"
        findings = self._scan_file_for_secrets(compose_path)
        assert not findings, (
            f"Possible secrets found in docker-compose.yml:\n"
            + "\n".join(f"  - {f}" for f in findings)
        )

    def test_no_secrets_in_dockerfiles(self) -> None:
        findings = []
        for dockerfile in BACKEND_SERVICES_DIR.rglob("Dockerfile"):
            findings.extend(self._scan_file_for_secrets(dockerfile))
        assert not findings, (
            f"Possible secrets found in Dockerfiles:\n"
            + "\n".join(f"  - {f}" for f in findings)
        )


# =============================================================================
# Test: Required Services
# =============================================================================


class TestRequiredServices:
    """Verify core services are defined in docker-compose.yml."""

    @pytest.fixture
    def service_names(self) -> list[str]:
        compose_path = BACKEND_SERVICES_DIR / "docker-compose.yml"
        with open(compose_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return list(data.get("services", {}).keys())

    def test_orchestrator_service_exists(self, service_names: list[str]) -> None:
        assert "orchestrator" in service_names, "Missing orchestrator service"

    def test_qdrant_service_exists(self, service_names: list[str]) -> None:
        assert "qdrant" in service_names, "Missing qdrant service"

    def test_all_services_have_container_names(self) -> None:
        compose_path = BACKEND_SERVICES_DIR / "docker-compose.yml"
        with open(compose_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        services = data.get("services", {})
        missing_names = []
        for svc_name, svc_config in services.items():
            if not isinstance(svc_config, dict):
                continue
            if "container_name" not in svc_config:
                missing_names.append(svc_name)
        assert not missing_names, (
            f"Services without container_name:\n"
            + "\n".join(f"  - {s}" for s in missing_names)
        )
