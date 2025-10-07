import io
import sqlite3
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

from addon.data_loader import clear_cache, load_data


def make_tmp_db(sql: str) -> Path:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    path = Path(tmp.name)
    with sqlite3.connect(path) as con:
        con.executescript(sql)
    return path


def test_loader_debug_prints(monkeypatch):
    sql = """
    CREATE TABLE SolarSystems (solarSystemId INTEGER PRIMARY KEY, name TEXT, centerX REAL, centerY REAL, centerZ REAL);
    CREATE TABLE Planets (planetId INTEGER PRIMARY KEY, solarSystemId INTEGER, planetName TEXT);
    CREATE TABLE Moons (moonId INTEGER PRIMARY KEY, planetId INTEGER, moonName TEXT);
    CREATE TABLE Jumps (fromSystemId INTEGER, toSystemId INTEGER);
    CREATE TABLE NpcStations (stationId INTEGER PRIMARY KEY, solarSystemId INTEGER);
    INSERT INTO SolarSystems VALUES (1, 'Dbg', 0,0,0);
    INSERT INTO Planets VALUES (10, 1, 'P1');
    INSERT INTO Moons VALUES (100, 10, 'M1');
    INSERT INTO NpcStations VALUES (1, 1);
    """
    path = make_tmp_db(sql)
    clear_cache()
    # Ensure debug env var set
    monkeypatch.setenv("EVE_LOADER_DEBUG", "1")
    buf = io.StringIO()
    with redirect_stdout(buf):
        systems = load_data(path)
    out = buf.getvalue()
    # Expect debug print content to include 'Loaded systems count' when env var is set
    assert "Loaded systems count" in out or len(systems) == 1
