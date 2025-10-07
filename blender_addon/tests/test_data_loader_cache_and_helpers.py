import sqlite3
import tempfile
from pathlib import Path

import pytest

from addon.data_loader import (
    _column_lookup,
    _resolve_table_names,
    clear_cache,
    load_data,
    load_jumps,
)


def make_tmp_db(sql: str) -> Path:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    path = Path(tmp.name)
    with sqlite3.connect(path) as con:
        con.executescript(sql)
    return path


def test_column_lookup_basic():
    cols = ["id", "Name", "centerX", "securitystatus"]
    resolve = _column_lookup(cols)
    # Should resolve using case-insensitive matches
    assert resolve(("name", "system_name")) == "Name"
    # 'centerX' is present; resolving with 'centerx' should find it
    assert resolve(("centerx",)) == "centerX"
    # Candidates that aren't present should return None
    assert resolve(("x", "posx")) is None
    assert resolve(("nonexistent",)) is None


def test_resolve_table_names_raises_when_missing():
    # Create a DB with an unrelated table only
    sql = """
    CREATE TABLE foo (id INTEGER PRIMARY KEY);
    """
    path = make_tmp_db(sql)
    with sqlite3.connect(path) as con:
        cur = con.cursor()
        try:
            _resolve_table_names(cur)
        except RuntimeError as e:
            assert "Expected table" in str(e)
        else:
            raise AssertionError("_resolve_table_names should have raised RuntimeError")


def test_load_data_cache_and_clear():
    # Minimal DB with required tables and a single system
    sql = """
    CREATE TABLE SolarSystems (solarSystemId INTEGER PRIMARY KEY, name TEXT, centerX REAL, centerY REAL, centerZ REAL);
    CREATE TABLE Planets (planetId INTEGER PRIMARY KEY, solarSystemId INTEGER, planetName TEXT);
    CREATE TABLE Moons (moonId INTEGER PRIMARY KEY, planetId INTEGER, moonName TEXT);
    CREATE TABLE Jumps (fromSystemId INTEGER, toSystemId INTEGER);
    CREATE TABLE NpcStations (stationId INTEGER PRIMARY KEY, solarSystemId INTEGER);
    INSERT INTO SolarSystems VALUES (1, 'S1', 0,0,0);
    INSERT INTO Planets VALUES (10, 1, 'P1');
    INSERT INTO Moons VALUES (100, 10, 'M1');
    """
    path = make_tmp_db(sql)

    # Ensure cache is clear first
    clear_cache()

    systems1 = load_data(path)
    systems2 = load_data(path)
    # With caching enabled and file unchanged, second call should return same cached object
    assert systems1 is systems2

    # Clear cache then reload; should get a new object instance
    clear_cache()
    systems3 = load_data(path)
    assert systems3 is not systems2


def test_load_jumps_wrong_columns_returns_empty():
    # Create a Jumps table that lacks the required from/to column names
    sql = """
    CREATE TABLE SolarSystems (solarSystemId INTEGER PRIMARY KEY, name TEXT, centerX REAL, centerY REAL, centerZ REAL);
    CREATE TABLE Planets (planetId INTEGER PRIMARY KEY, solarSystemId INTEGER, planetName TEXT);
    CREATE TABLE Moons (moonId INTEGER PRIMARY KEY, planetId INTEGER, moonName TEXT);
    CREATE TABLE Jumps (foo INTEGER, bar INTEGER);
    CREATE TABLE NpcStations (stationId INTEGER PRIMARY KEY, solarSystemId INTEGER);
    INSERT INTO SolarSystems VALUES (1, 'S1', 0,0,0);
    """
    path = make_tmp_db(sql)
    jumps = load_jumps(path)
    assert isinstance(jumps, list)
    assert len(jumps) == 0


def test_load_data_limit_and_cache_flag():
    # Create a DB with three systems and ensure limit_systems works and cache key includes limit
    sql = """
    CREATE TABLE SolarSystems (solarSystemId INTEGER PRIMARY KEY, name TEXT, centerX REAL, centerY REAL, centerZ REAL);
    CREATE TABLE Planets (planetId INTEGER PRIMARY KEY, solarSystemId INTEGER, planetName TEXT);
    CREATE TABLE Moons (moonId INTEGER PRIMARY KEY, planetId INTEGER, moonName TEXT);
    CREATE TABLE Jumps (fromSystemId INTEGER, toSystemId INTEGER);
    CREATE TABLE NpcStations (stationId INTEGER PRIMARY KEY, solarSystemId INTEGER);
    INSERT INTO SolarSystems VALUES (1, 'S1', 0,0,0);
    INSERT INTO SolarSystems VALUES (2, 'S2', 0,0,0);
    INSERT INTO SolarSystems VALUES (3, 'S3', 0,0,0);
    """
    path = make_tmp_db(sql)

    # Clear cache and load with limit=1
    clear_cache()
    s1 = load_data(path, limit_systems=1)
    assert len(s1) == 1

    # Load again with the same limit should hit cache and return same object
    s1b = load_data(path, limit_systems=1)
    assert s1 is s1b

    # Load with enable_cache=False should return a new object
    s_nocache = load_data(path, limit_systems=1, enable_cache=False)
    assert s_nocache is not s1b


def test_security_parsing_valid_value():
    sql = """
    CREATE TABLE SolarSystems (solarSystemId INTEGER PRIMARY KEY, name TEXT, centerX REAL, centerY REAL, centerZ REAL, security TEXT);
    CREATE TABLE Planets (planetId INTEGER PRIMARY KEY, solarSystemId INTEGER, planetName TEXT);
    CREATE TABLE Moons (moonId INTEGER PRIMARY KEY, planetId INTEGER, moonName TEXT);
    CREATE TABLE Jumps (fromSystemId INTEGER, toSystemId INTEGER);
    CREATE TABLE NpcStations (stationId INTEGER PRIMARY KEY, solarSystemId INTEGER);
    INSERT INTO SolarSystems VALUES (1, 'GoodSec', 0,0,0, '0.123');
    INSERT INTO Planets VALUES (10, 1, 'P1');
    INSERT INTO Moons VALUES (100, 10, 'M1');
    """
    path = make_tmp_db(sql)
    systems = load_data(path)
    assert len(systems) == 1
    assert systems[0].security == pytest.approx(0.123)


def test_load_jumps_batching_with_system_ids():
    # Build a DB with 920 systems and jumps linking i -> i+1 to force batching (batch_size=450)
    n = 920
    parts = [
        "CREATE TABLE SolarSystems (solarSystemId INTEGER PRIMARY KEY, name TEXT, centerX REAL, centerY REAL, centerZ REAL);",
        "CREATE TABLE Planets (planetId INTEGER PRIMARY KEY, solarSystemId INTEGER, planetName TEXT);",
        "CREATE TABLE Moons (moonId INTEGER PRIMARY KEY, planetId INTEGER, moonName TEXT);",
        "CREATE TABLE Jumps (fromSystemId INTEGER, toSystemId INTEGER);",
        "CREATE TABLE NpcStations (stationId INTEGER PRIMARY KEY, solarSystemId INTEGER);",
    ]
    for i in range(1, n + 1):
        parts.append(f"INSERT INTO SolarSystems VALUES ({i}, 'S{i}', 0,0,0);")
    for i in range(1, n):
        parts.append(f"INSERT INTO Jumps VALUES ({i}, {i+1});")

    sql = "\n".join(parts)
    path = make_tmp_db(sql)
    system_ids = list(range(1, n + 1))
    jumps = load_jumps(path, system_ids=system_ids)
    assert isinstance(jumps, list)
    assert len(jumps) > 0
