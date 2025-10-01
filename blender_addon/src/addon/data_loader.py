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

MAX_SQL_VARS = 900  # safety margin below default SQLite limit (999) for IN clause batching


def _file_identity(path: Path) -> Tuple[str, int, int]:
    st = path.stat()
    return (str(path.resolve()), int(st.st_size), int(st.st_mtime_ns))


_TABLE_SYNONYMS: Dict[str, Tuple[str, ...]] = {
    # logical name -> acceptable variants (case-sensitive checks performed, but we match case-insensitive)
    "systems": (
        "systems",
        "system",
        "Systems",
        "System",
        "SolarSystems",
        "solarSystems",
        "solarsystems",
    ),
    "planets": ("planets", "Planets"),
    "moons": ("moons", "Moons"),
}


def _resolve_table_names(cur: sqlite3.Cursor) -> Dict[str, str]:
    """Resolve actual table names using synonym sets (case-insensitive).

    Raises a RuntimeError listing available tables if a required logical table cannot be found.
    """
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_names = [row[0] for row in cur.fetchall()]
    existing_lower = {n.lower(): n for n in existing_names}
    resolved: Dict[str, str] = {}
    for logical, variants in _TABLE_SYNONYMS.items():
        found = None
        for v in variants:
            key = v.lower()
            if key in existing_lower:
                found = existing_lower[key]
                break
        if not found:
            raise RuntimeError(
                f"Expected table '{logical}' (synonyms: {', '.join(variants)}) not found. Available: {', '.join(sorted(existing_names)) or '<<none>>'}"
            )
        resolved[logical] = found
    return resolved


# Column synonym lists (lowercased for matching)
_COL_SYSTEM_ID = ("id", "system_id", "solarsystemid", "solar_system_id")
_COL_SYSTEM_NAME = ("name", "system_name", "solarsystemname", "solar_system_name")
_COL_X = ("x", "posx", "positionx", "centerx")
_COL_Y = ("y", "posy", "positiony", "centery")
_COL_Z = ("z", "posz", "positionz", "centerz")
_COL_SECURITY = ("security", "securitystatus", "security_status")

_COL_PLANET_ID = ("id", "planetid")
_COL_PLANET_SYSTEM_ID = ("system_id", "solarsystemid", "solar_system_id")
_COL_PLANET_NAME = ("name", "planetname")
_COL_PLANET_ORBIT = ("orbit_index", "orbitindex")
_COL_PLANET_TYPE = ("planet_type", "planettype", "typeid")

_COL_MOON_ID = ("id", "moonid")
_COL_MOON_PLANET_ID = ("planet_id", "planetid")
_COL_MOON_NAME = ("name", "moonname")
_COL_MOON_ORBIT = ("orbit_index", "orbitindex")


def _column_lookup(columns: List[str]):
    """Return a helper that maps candidate synonym tuples to the concrete column name or None."""
    lower_map = {c.lower(): c for c in columns}

    def resolve(candidates: Tuple[str, ...]):  # type: ignore[override]
        for cand in candidates:
            real = lower_map.get(cand)
            if real:
                return real
        return None

    return resolve


def load_data(
    db_path: str | os.PathLike, *, limit_systems: int | None = None, enable_cache: bool = True
) -> List[System]:
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

        # Resolve table names and discover column mappings
        tables = _resolve_table_names(cur)

        # Introspect system columns
        cur.execute(f"PRAGMA table_info('{tables['systems']}')")
        sys_cols = [row[1] for row in cur.fetchall()]
        sys_col_resolve = _column_lookup(sys_cols)
        c_id = sys_col_resolve(_COL_SYSTEM_ID)
        c_name = sys_col_resolve(_COL_SYSTEM_NAME)
        c_x = sys_col_resolve(_COL_X)
        c_y = sys_col_resolve(_COL_Y)
        c_z = sys_col_resolve(_COL_Z)
        c_sec = sys_col_resolve(_COL_SECURITY)
        missing_core = [
            n
            for n, v in {"id": c_id, "name": c_name, "x": c_x, "y": c_y, "z": c_z}.items()
            if v is None
        ]
        if missing_core:
            raise RuntimeError(
                f"Missing required columns on '{tables['systems']}': {', '.join(missing_core)} (have: {', '.join(sys_cols)})"
            )
        sys_select_cols = [c for c in [c_id, c_name, c_x, c_y, c_z, c_sec] if c]
        sys_query = f"SELECT {', '.join(sys_select_cols)} FROM {tables['systems']} ORDER BY {c_id}"
        if limit_systems is not None:
            sys_query += f" LIMIT {int(limit_systems)}"
        cur.execute(sys_query)
        system_rows = cur.fetchall()

        # Build case-insensitive mapping for rows
        system_map: Dict[int, System] = {}
        for r in system_rows:
            # sqlite3.Row supports key lookup by original names
            rid = int(r[c_id])
            security_val = None
            if c_sec and r[c_sec] is not None:
                try:
                    security_val = float(r[c_sec])
                except Exception:
                    security_val = None
            system_map[rid] = System(
                id=rid,
                name=str(r[c_name]),
                x=float(r[c_x]),
                y=float(r[c_y]),
                z=float(r[c_z]),
                security=security_val,
            )

        if not system_map:
            systems: List[System] = []
            if enable_cache:
                _cache[cache_key] = systems
            return systems

        # Planets filtered by selected systems (if limited)
        sys_ids = tuple(system_map.keys())
        cur.execute(f"PRAGMA table_info('{tables['planets']}')")
        pl_cols = [row[1] for row in cur.fetchall()]
        pl_resolve = _column_lookup(pl_cols)
        pl_id = pl_resolve(_COL_PLANET_ID)
        pl_sys = pl_resolve(_COL_PLANET_SYSTEM_ID)
        pl_name = pl_resolve(_COL_PLANET_NAME)
        pl_orbit = pl_resolve(_COL_PLANET_ORBIT)
        pl_type = pl_resolve(_COL_PLANET_TYPE)
        missing_pl = [
            n for n, v in {"id": pl_id, "system": pl_sys, "name": pl_name}.items() if v is None
        ]
        if missing_pl:
            raise RuntimeError(
                f"Missing required columns on '{tables['planets']}': {', '.join(missing_pl)} (have: {', '.join(pl_cols)})"
            )
        pl_select = [c for c in (pl_id, pl_sys, pl_name, pl_orbit, pl_type) if c]
        planet_rows = []
        if sys_ids:
            # Batch to avoid "too many SQL variables" for large datasets
            for i in range(0, len(sys_ids), MAX_SQL_VARS):
                chunk = sys_ids[i : i + MAX_SQL_VARS]
                placeholder = ",".join(["?"] * len(chunk))
                cur.execute(
                    f"SELECT {', '.join(pl_select)} FROM {tables['planets']} WHERE {pl_sys} IN ({placeholder})",
                    chunk,
                )
                planet_rows.extend(cur.fetchall())
        # Sort to keep deterministic ordering by planet id
        try:
            planet_rows.sort(key=lambda r: int(r[pl_id]))  # type: ignore[arg-type]
        except Exception:
            pass
        planet_map: Dict[int, Planet] = {}
        for r in planet_rows:
            rid = int(r[pl_id])
            p = Planet(
                id=rid,
                system_id=int(r[pl_sys]),
                name=str(r[pl_name]),
                orbit_index=(r[pl_orbit] if (pl_orbit and r[pl_orbit] is not None) else None),
                planet_type=(str(r[pl_type]) if (pl_type and r[pl_type] is not None) else None),
            )
            planet_map[p.id] = p
            parent = system_map.get(p.system_id)
            if parent:
                parent.planets.append(p)

        # Moons filtered by selected planets
        if planet_map:
            planet_ids = tuple(planet_map.keys())
            cur.execute(f"PRAGMA table_info('{tables['moons']}')")
            moon_cols = [row[1] for row in cur.fetchall()]
            moon_resolve = _column_lookup(moon_cols)
            m_id = moon_resolve(_COL_MOON_ID)
            m_planet_id = moon_resolve(_COL_MOON_PLANET_ID)
            m_name = moon_resolve(_COL_MOON_NAME)
            m_orbit = moon_resolve(_COL_MOON_ORBIT)
            missing_m = [
                n
                for n, v in {"id": m_id, "planet_id": m_planet_id, "name": m_name}.items()
                if v is None
            ]
            if missing_m:
                raise RuntimeError(
                    f"Missing required columns on '{tables['moons']}': {', '.join(missing_m)} (have: {', '.join(moon_cols)})"
                )
            moon_select = [c for c in (m_id, m_planet_id, m_name, m_orbit) if c]
            moon_rows = []
            if planet_ids:
                for i in range(0, len(planet_ids), MAX_SQL_VARS):
                    chunk = planet_ids[i : i + MAX_SQL_VARS]
                    placeholder = ",".join(["?"] * len(chunk))
                    cur.execute(
                        f"SELECT {', '.join(moon_select)} FROM {tables['moons']} WHERE {m_planet_id} IN ({placeholder})",
                        chunk,
                    )
                    moon_rows.extend(cur.fetchall())
            try:
                moon_rows.sort(key=lambda r: int(r[m_id]))  # type: ignore[arg-type]
            except Exception:
                pass
            for r in moon_rows:
                mid = int(r[m_id])
                m = Moon(
                    id=mid,
                    planet_id=int(r[m_planet_id]),
                    name=str(r[m_name]),
                    orbit_index=(r[m_orbit] if (m_orbit and r[m_orbit] is not None) else None),
                )
                parent = planet_map.get(m.planet_id)
                if parent:
                    parent.moons.append(m)

    systems = list(system_map.values())
    # Optional debug mapping output
    if os.environ.get("EVE_LOADER_DEBUG"):
        print(
            "[EVEVisualizer][debug] Loaded systems count=",
            len(systems),
            " planets=",
            sum(len(s.planets) for s in systems),
            " moons=",
            sum(len(p.moons) for s in systems for p in s.planets),
        )
    if enable_cache:
        _cache[cache_key] = systems
    return systems


def clear_cache():  # pragma: no cover - utility
    _cache.clear()
