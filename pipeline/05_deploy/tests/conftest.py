"""Shared fixtures for deploy tests."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure pipeline/05_deploy is importable so deploy_qdrant can be imported
_deploy_dir = Path(__file__).resolve().parent.parent
if str(_deploy_dir) not in sys.path:
    sys.path.insert(0, str(_deploy_dir))
