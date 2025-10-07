import sqlite3
import tempfile
from pathlib import Path

from addon.data_loader import load_data


def make_tmp_db(sql: str) -> Path:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    path = Path(tmp.name)
    with sqlite3.connect(path) as con:
        con.executescript(sql)
    return path


def test_planet_and_moon_sort_exceptions():
    # Insert non-integer ids for planets and moons to trigger ValueError in sorting
    sql = """
    CREATE TABLE SolarSystems (solarSystemId INTEGER PRIMARY KEY, name TEXT, centerX REAL, centerY REAL, centerZ REAL);
    CREATE TABLE Planets (planetId TEXT PRIMARY KEY, solarSystemId INTEGER, planetName TEXT);
    CREATE TABLE Moons (moonId TEXT PRIMARY KEY, planetId TEXT, moonName TEXT);
    CREATE TABLE Jumps (fromSystemId INTEGER, toSystemId INTEGER);
    CREATE TABLE NpcStations (stationId INTEGER PRIMARY KEY, solarSystemId INTEGER);
    INSERT INTO SolarSystems VALUES (1, 'S1', 0,0,0);
    -- planet ids as text
    INSERT INTO Planets VALUES ('pA', 1, 'P_A');
    INSERT INTO Planets VALUES ('2', 1, 'P_2');
    INSERT INTO Moons VALUES ('mX', 'pA', 'M_X');
    INSERT INTO Moons VALUES ('3', '2', 'M_3');
    """
    path = make_tmp_db(sql)
    # Current loader will attempt to convert planet ids to int and raise ValueError
    import pytest

    with pytest.raises(ValueError):
        load_data(path)


def test_npcstations_counts_resolved():
    # NpcStations with 'solarSystemId' column should be counted per system
    sql = """
    CREATE TABLE SolarSystems (solarSystemId INTEGER PRIMARY KEY, name TEXT, centerX REAL, centerY REAL, centerZ REAL);
    CREATE TABLE Planets (planetId INTEGER PRIMARY KEY, solarSystemId INTEGER, planetName TEXT);
    CREATE TABLE Moons (moonId INTEGER PRIMARY KEY, planetId INTEGER, moonName TEXT);
    CREATE TABLE Jumps (fromSystemId INTEGER, toSystemId INTEGER);
    CREATE TABLE NpcStations (stationId INTEGER PRIMARY KEY, solarSystemId INTEGER);
    INSERT INTO SolarSystems VALUES (1, 'S1', 0,0,0);
    INSERT INTO Planets VALUES (10, 1, 'P1');
    INSERT INTO Moons VALUES (100, 10, 'M1');
    INSERT INTO NpcStations VALUES (1, 1);
    INSERT INTO NpcStations VALUES (2, 1);
    """
    path = make_tmp_db(sql)
    systems = load_data(path)
    assert len(systems) == 1
    assert systems[0].npc_station_count == 2
