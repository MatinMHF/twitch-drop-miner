"""Pytest configuration and environment bootstrap for backend tests."""

import sys
from pathlib import Path

# Ensure backend/app/engine/devilxd is in sys.path so bare internal imports inside devilxd resolve cleanly
_devilxd_dir = Path(__file__).resolve().parent.parent / "app" / "engine" / "devilxd"
if _devilxd_dir.is_dir() and str(_devilxd_dir) not in sys.path:
    sys.path.insert(0, str(_devilxd_dir))

# Ensure backend root is in sys.path
_backend_dir = Path(__file__).resolve().parent.parent
if _backend_dir.is_dir() and str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))
