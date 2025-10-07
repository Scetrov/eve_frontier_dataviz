import sqlite3
import tempfile
from pathlib import Path

from addon.data_loader import clear_cache, load_data


def make_tmp_db(sql: str) -> Path:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    path = Path(tmp.name)
    with sqlite3.connect(path) as con:
        con.executescript(sql)
    return path


def test_region_fk_but_no_region_table():
    # Systems declare regionId/constellationId but the actual region/constellation tables are absent
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

    INSERT INTO SolarSystems VALUES (1, 'Rless', 0,0,0, 10, 20);
    INSERT INTO Regions VALUES (10, 'R-Alpha');
    INSERT INTO Constellations VALUES (20, 'C-Alpha');
    INSERT INTO Planets VALUES (10, 1, 'P1');
    INSERT INTO Moons VALUES (100, 10, 'M1');
    """
    path = make_tmp_db(sql)
    # Should not raise and should return the system with populated region/constellation names
    systems = load_data(path)
    assert len(systems) == 1
    s = systems[0]
    assert s.region_name == "R-Alpha"
    assert s.constellation_name == "C-Alpha"


def test_empty_systems_cached_empty():
    sql = """
    CREATE TABLE SolarSystems (solarSystemId INTEGER PRIMARY KEY, name TEXT, centerX REAL, centerY REAL, centerZ REAL);
    CREATE TABLE Planets (planetId INTEGER PRIMARY KEY, solarSystemId INTEGER, planetName TEXT);
    CREATE TABLE Moons (moonId INTEGER PRIMARY KEY, planetId INTEGER, moonName TEXT);
    CREATE TABLE Jumps (fromSystemId INTEGER, toSystemId INTEGER);
    CREATE TABLE NpcStations (stationId INTEGER PRIMARY KEY, solarSystemId INTEGER);
    """
    path = make_tmp_db(sql)
    clear_cache()
    s1 = load_data(path)
    assert s1 == []
    s2 = load_data(path)
    assert s1 is s2
