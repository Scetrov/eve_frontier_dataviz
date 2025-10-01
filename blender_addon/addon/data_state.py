"""In-memory state for loaded EVE data.

Separated from operators so it stays pure-Python and testable / reloadable.
"""
from __future__ import annotations

from typing import List, Optional

from .data_loader import System

_loaded_systems: Optional[List[System]] = None


def set_loaded_systems(systems: List[System]):
    global _loaded_systems
    _loaded_systems = systems


def get_loaded_systems() -> Optional[List[System]]:
    return _loaded_systems


def clear_loaded_systems():  # pragma: no cover - utility for manual reloads
    global _loaded_systems
    _loaded_systems = None
