"""Shared fixtures for preprocessing tests."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the preprocessing package is importable
_pkg = Path(__file__).resolve().parent.parent
if str(_pkg) not in sys.path:
    sys.path.insert(0, str(_pkg))
