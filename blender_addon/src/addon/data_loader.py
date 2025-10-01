"""Pure-Python data loader for the static SQLite database.

No Blender API calls here so it can be unit tested headlessly.
"""
from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

__all__ = [
    "System",
    "Planet",
    "Moon",
    "load_data",
]


@dataclass(slots=True)
class Moon:
    id: int
    planet_id: int
    name: str
    orbit_index: Optional[int] | None


@dataclass(slots=True)
class Planet:
    id: int
    system_id: int
    name: str
    orbit_index: Optional[int] | None
    planet_type: Optional[str] | None
    moons: List[Moon] = field(default_factory=list)


@dataclass(slots=True)
class System:
    id: int
    name: str
    x: float
    y: float
    z: float
    security: Optional[float] | None
    planets: List[Planet] = field(default_factory=list)


# Simple in-process cache keyed by file identity + limit parameter
_cache: Dict[Tuple[str, int, int, Optional[int]], List[System]] = {}


def _file_identity(path: Path) -> Tuple[str, int, int]:
    st = path.stat()
    return (str(path.resolve()), int(st.st_size), int(st.st_mtime_ns))


def load_data(db_path: str | os.PathLike, *, limit_systems: int | None = None, enable_cache: bool = True) -> List[System]:
    """Load systems, planets, moons from the SQLite database.

    Parameters
    ----------
    db_path: str | Path
        Path to the SQLite file.
    limit_systems: int | None
        If provided, truncates the number of systems returned (useful for dev/testing).
    enable_cache: bool
        Return cached result if file unchanged and parameters match.
    """
    path = Path(db_path)
    if not path.exists():  # pragma: no cover - defensive
        raise FileNotFoundError(f"Database not found: {db_path}")

    fid = _file_identity(path)
    cache_key = (*fid, limit_systems)
    if enable_cache and cache_key in _cache:
        return _cache[cache_key]

    with sqlite3.connect(path) as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()

        # Fetch systems (optionally limited)
        sys_query = "SELECT id, name, x, y, z, security FROM systems ORDER BY id"
        if limit_systems is not None:
            sys_query += f" LIMIT {int(limit_systems)}"
        cur.execute(sys_query)
        system_rows = cur.fetchall()

        system_map: Dict[int, System] = {}
        for r in system_rows:
            system_map[r["id"]] = System(
                id=r["id"],
                name=r["name"],
                x=float(r["x"]),
                y=float(r["y"]),
                z=float(r["z"]),
                security=(float(r["security"]) if r["security"] is not None else None),
            )

        if not system_map:
            systems: List[System] = []
            if enable_cache:
                _cache[cache_key] = systems
            return systems

        # Planets filtered by selected systems (if limited)
        sys_ids = tuple(system_map.keys())
        placeholder = ",".join(["?"] * len(sys_ids))
        cur.execute(
            f"SELECT id, system_id, name, orbit_index, planet_type FROM planets WHERE system_id IN ({placeholder})",
            sys_ids,
        )
        planet_rows = cur.fetchall()
        planet_map: Dict[int, Planet] = {}
        for r in planet_rows:
            p = Planet(
                id=r["id"],
                system_id=r["system_id"],
                name=r["name"],
                orbit_index=r["orbit_index"],
                planet_type=r["planet_type"],
            )
            planet_map[p.id] = p
            parent = system_map.get(p.system_id)
            if parent:
                parent.planets.append(p)

        # Moons filtered by selected planets
        if planet_map:
            planet_ids = tuple(planet_map.keys())
            placeholder = ",".join(["?"] * len(planet_ids))
            cur.execute(
                f"SELECT id, planet_id, name, orbit_index FROM moons WHERE planet_id IN ({placeholder})",
                planet_ids,
            )
            moon_rows = cur.fetchall()
            for r in moon_rows:
                m = Moon(
                    id=r["id"],
                    planet_id=r["planet_id"],
                    name=r["name"],
                    orbit_index=r["orbit_index"],
                )
                parent = planet_map.get(m.planet_id)
                if parent:
                    parent.moons.append(m)

    systems = list(system_map.values())
    if enable_cache:
        _cache[cache_key] = systems
    return systems


def clear_cache():  # pragma: no cover - utility
    _cache.clear()
