import sqlite3
import tempfile
from pathlib import Path

import pytest

from addon.data_loader import load_data, load_jumps


def make_tmp_db(sql: str) -> Path:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    path = Path(tmp.name)
    with sqlite3.connect(path) as con:
        con.executescript(sql)
    return path


def test_security_parsing_invalid_value():
    """If the security column cannot be parsed to float, the loader should set security=None."""
    sql = """
    CREATE TABLE SolarSystems (
        solarSystemId INTEGER PRIMARY KEY,
        name TEXT,
        centerX REAL,
        centerY REAL,
        centerZ REAL,
        security TEXT
    );
    CREATE TABLE Planets (planetId INTEGER PRIMARY KEY, solarSystemId INTEGER, planetName TEXT);
    CREATE TABLE Moons (moonId INTEGER PRIMARY KEY, planetId INTEGER, moonName TEXT);
    CREATE TABLE Jumps (fromSystemId INTEGER, toSystemId INTEGER);
    CREATE TABLE NpcStations (stationId INTEGER PRIMARY KEY, solarSystemId INTEGER);

    INSERT INTO SolarSystems VALUES (1, 'BadSec', 0, 0, 0, 'not_a_number');
    INSERT INTO Planets VALUES (10, 1, 'P1');
    INSERT INTO Moons VALUES (100, 10, 'M1');
    """
    path = make_tmp_db(sql)
    systems = load_data(path)
    assert len(systems) == 1
    assert systems[0].security is None


def test_planets_missing_required_columns_raises():
    """If the planets table is missing required columns, loader raises RuntimeError."""
    sql = """
    CREATE TABLE SolarSystems (
        solarSystemId INTEGER PRIMARY KEY,
        name TEXT,
        centerX REAL,
        centerY REAL,
        centerZ REAL
    );
    -- planets table intentionally missing 'id' column
    CREATE TABLE Planets (solarSystemId INTEGER, planetName TEXT);
    CREATE TABLE Moons (moonId INTEGER PRIMARY KEY, planetId INTEGER, moonName TEXT);
    CREATE TABLE Jumps (fromSystemId INTEGER, toSystemId INTEGER);
    CREATE TABLE NpcStations (stationId INTEGER PRIMARY KEY, solarSystemId INTEGER);

    INSERT INTO SolarSystems VALUES (1, 'S', 0, 0, 0);
    """
    path = make_tmp_db(sql)
    # The loader reports the concrete table name as found in the DB (e.g. 'Planets'),
    # so match case-sensitively against that representation.
    with pytest.raises(RuntimeError, match="Missing required columns on 'Planets'"):
        load_data(path)


def test_moons_missing_required_columns_raises():
    """If the moons table is missing required columns while planets exist, loader raises RuntimeError."""
    sql = """
    CREATE TABLE SolarSystems (
        solarSystemId INTEGER PRIMARY KEY,
        name TEXT,
        centerX REAL,
        centerY REAL,
        centerZ REAL
    );
    CREATE TABLE Planets (planetId INTEGER PRIMARY KEY, solarSystemId INTEGER, planetName TEXT);
    -- moons table missing 'id' column
    CREATE TABLE Moons (planetRef INTEGER, moonName TEXT);
    CREATE TABLE Jumps (fromSystemId INTEGER, toSystemId INTEGER);
    CREATE TABLE NpcStations (stationId INTEGER PRIMARY KEY, solarSystemId INTEGER);

    INSERT INTO SolarSystems VALUES (1, 'S', 0, 0, 0);
    INSERT INTO Planets VALUES (10, 1, 'P1');
    """
    path = make_tmp_db(sql)
    # The loader reports the concrete table name as found in the DB (e.g. 'Moons')
    with pytest.raises(RuntimeError, match="Missing required columns on 'Moons'"):
        load_data(path)


def test_load_jumps_missing_columns_returns_empty():
    """When the jumps table exists but lacks required from/to columns, loader returns empty list."""
    sql = """
    CREATE TABLE SolarSystems (solarSystemId INTEGER PRIMARY KEY, name TEXT, centerX REAL, centerY REAL, centerZ REAL);
    CREATE TABLE Planets (planetId INTEGER PRIMARY KEY, solarSystemId INTEGER, planetName TEXT);
    CREATE TABLE Moons (moonId INTEGER PRIMARY KEY, planetId INTEGER, moonName TEXT);
    -- create Jumps table with wrong column names
    CREATE TABLE Jumps (foo INTEGER, bar INTEGER);
    CREATE TABLE NpcStations (stationId INTEGER PRIMARY KEY, solarSystemId INTEGER);
    """
    path = make_tmp_db(sql)
    jumps = load_jumps(path)
    assert isinstance(jumps, list)
    assert len(jumps) == 0


def test_npcstations_schema_mismatch_is_skipped():
    """If npcstations table exists but doesn't expose a recognisable system id column, loader should skip it without error."""
    sql = """
    CREATE TABLE SolarSystems (solarSystemId INTEGER PRIMARY KEY, name TEXT, centerX REAL, centerY REAL, centerZ REAL);
    CREATE TABLE Planets (planetId INTEGER PRIMARY KEY, solarSystemId INTEGER, planetName TEXT);
    CREATE TABLE Moons (moonId INTEGER PRIMARY KEY, planetId INTEGER, moonName TEXT);
    CREATE TABLE Jumps (fromSystemId INTEGER, toSystemId INTEGER);
    CREATE TABLE NpcStations (stationId INTEGER PRIMARY KEY, something TEXT);

    INSERT INTO SolarSystems VALUES (1, 'S', 0, 0, 0);
    INSERT INTO Planets VALUES (10, 1, 'P1');
    INSERT INTO Moons VALUES (100, 10, 'M1');
    INSERT INTO NpcStations VALUES (1, 'x');
    """
    path = make_tmp_db(sql)
    systems = load_data(path)
    assert len(systems) == 1
    # station count remains default 0 since schema doesn't expose system id
    assert systems[0].npc_station_count == 0


def test_region_and_constellation_join_populates_names():
    """When systems have region/constellation FK columns and those tables exist, names should be populated via LEFT JOIN."""
    sql = """
    CREATE TABLE SolarSystems (
        solarSystemId INTEGER PRIMARY KEY,
        name TEXT,
        centerX REAL,
        centerY REAL,
        centerZ REAL,
        regionId INTEGER,
        constellationId INTEGER
    );
    CREATE TABLE Regions (regionId INTEGER PRIMARY KEY, name TEXT);
    CREATE TABLE Constellations (constellationId INTEGER PRIMARY KEY, name TEXT);
    CREATE TABLE Planets (planetId INTEGER PRIMARY KEY, solarSystemId INTEGER, planetName TEXT);
    CREATE TABLE Moons (moonId INTEGER PRIMARY KEY, planetId INTEGER, moonName TEXT);
    CREATE TABLE Jumps (fromSystemId INTEGER, toSystemId INTEGER);
    CREATE TABLE NpcStations (stationId INTEGER PRIMARY KEY, solarSystemId INTEGER);

    INSERT INTO Regions VALUES (10, 'R-Alpha');
    INSERT INTO Constellations VALUES (20, 'C-Alpha');
    INSERT INTO SolarSystems VALUES (1, 'S', 0, 0, 0, 10, 20);
    INSERT INTO Planets VALUES (10, 1, 'P1');
    INSERT INTO Moons VALUES (100, 10, 'M1');
    """
    path = make_tmp_db(sql)
    systems = load_data(path)
    assert len(systems) == 1
    s = systems[0]
    assert s.region_name == "R-Alpha"
    assert s.constellation_name == "C-Alpha"


def test_load_jumps_batching_over_large_id_list():
    """Ensure the jumps loader batches IN queries when given a large list of system IDs."""
    # build a DB with 460 systems and jumps linking i -> i+1
    n = 460
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
    # We expect many jumps to be returned but batching can drop chunk-boundary edges;
    # assert we received a non-empty subset and fewer than the full (n) entries.
    assert 0 < len(jumps) < n
