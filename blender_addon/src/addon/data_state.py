"""In-memory state for loaded EVE data."""

from __future__ import annotations

from typing import List, Optional

from .data_loader import Jump, System

_loaded_systems: Optional[List[System]] = None
_loaded_jumps: Optional[List[Jump]] = None


def set_loaded_systems(systems: List[System]):
    global _loaded_systems
    _loaded_systems = systems


def get_loaded_systems() -> Optional[List[System]]:
    return _loaded_systems


def set_loaded_jumps(jumps: List[Jump]):
    global _loaded_jumps
    _loaded_jumps = jumps


def get_loaded_jumps() -> Optional[List[Jump]]:
    return _loaded_jumps


def clear_loaded_systems():  # pragma: no cover - utility
    global _loaded_systems
    _loaded_systems = None


def clear_loaded_jumps():  # pragma: no cover - utility
    global _loaded_jumps
    _loaded_jumps = None
