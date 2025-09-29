import sqlite3
import tempfile
from pathlib import Path

from addon.data_loader import clear_cache, load_data

SQL_FILE = Path(__file__).parent / 'fixtures' / 'mini.db.sql'


def build_temp_db() -> Path:
    with open(SQL_FILE, 'r', encoding='utf-8') as f:
        sql_script = f.read()
    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp.close()
    path = Path(tmp.name)
    with sqlite3.connect(path) as con:
        con.executescript(sql_script)
    return path


def test_load_data_basic():
    path = build_temp_db()
    systems = load_data(path)
    # Expect 2 systems
    assert len(systems) == 2
    alpha = systems[0]
    assert alpha.name == 'Alpha'
    # System 1 has 2 planets
    assert len(alpha.planets) == 2
    # Planet 10 has 2 moons
    p10 = next(p for p in alpha.planets if p.id == 10)
    assert len(p10.moons) == 2


def test_limit_systems():
    path = build_temp_db()
    systems = load_data(path, limit_systems=1)
    assert len(systems) == 1


def test_cache_behavior():
    path = build_temp_db()
    systems1 = load_data(path, enable_cache=True)
    systems2 = load_data(path, enable_cache=True)
    assert systems1 is systems2  # same cached object
    clear_cache()
    systems3 = load_data(path, enable_cache=True)
    assert systems3 is not systems2
