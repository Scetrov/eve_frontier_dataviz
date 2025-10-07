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


def test_table_and_column_synonyms_resolve():
    # Use alternate table names and column synonyms (lowercase, different column names)
    sql = """
    CREATE TABLE systems (id INTEGER PRIMARY KEY, system_name TEXT, posx REAL, posy REAL, posz REAL, securitystatus TEXT);
    CREATE TABLE planets (planetid INTEGER PRIMARY KEY, solarsystemid INTEGER, planetname TEXT, orbitindex INTEGER, planettype TEXT);
    CREATE TABLE moons (moonid INTEGER PRIMARY KEY, planetid INTEGER, moonname TEXT, orbitindex INTEGER);
    CREATE TABLE jumps (fromSystemId INTEGER, toSystemId INTEGER);
    CREATE TABLE npcstations (stationId INTEGER PRIMARY KEY, solarSystemId INTEGER);

    INSERT INTO systems VALUES (1, 'SynSys', 1.0, 2.0, 3.0, '0.5');
    INSERT INTO planets VALUES (10, 1, 'P_syn', 0, 'rock');
    INSERT INTO moons VALUES (100, 10, 'M_syn', 0);
    INSERT INTO jumps VALUES (1, 2);
    INSERT INTO npcstations VALUES (1, 1);
    """
    path = make_tmp_db(sql)
    systems = load_data(path)
    assert len(systems) == 1
    s = systems[0]
    assert s.name == "SynSys"
    assert abs(s.x - 1.0) < 1e-9
    assert s.security == 0.5
    assert len(s.planets) == 1
    assert len(s.planets[0].moons) == 1
    assert s.npc_station_count == 1
