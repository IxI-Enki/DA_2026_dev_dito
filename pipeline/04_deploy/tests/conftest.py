"""Shared fixtures for deploy tests."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the pipeline package root is importable
_repo = Path(__file__).resolve().parent.parent.parent.parent
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))
