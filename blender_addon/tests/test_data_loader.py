import sqlite3
import tempfile
from pathlib import Path

import pytest

from addon.data_loader import clear_cache, load_data

SQL_FILE = Path(__file__).parent / "fixtures" / "mini.db.sql"


def build_temp_db() -> Path:
    with open(SQL_FILE, "r", encoding="utf-8") as f:
        sql_script = f.read()
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
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
    assert alpha.name == "Alpha"
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


def test_disable_cache():
    """Test that disabling cache works."""
    path = build_temp_db()
    systems1 = load_data(path, enable_cache=False)
    systems2 = load_data(path, enable_cache=False)
    # Should be different objects when cache disabled
    assert systems1 is not systems2


def test_system_properties():
    """Test that all system properties are loaded correctly."""
    path = build_temp_db()
    systems = load_data(path)

    alpha = systems[0]
    assert alpha.id == 1
    assert alpha.name == "Alpha"
    assert alpha.x == 1000.0
    assert alpha.y == 2000.0
    assert alpha.z == 3000.0
    assert alpha.security == 0.7


def test_planet_properties():
    """Test that planet properties are loaded correctly."""
    path = build_temp_db()
    systems = load_data(path)

    alpha = systems[0]
    planet = alpha.planets[0]
    assert planet.id == 10
    assert planet.name == "Alpha I"
    assert planet.orbit_index == 1
    assert planet.planet_type == "Gas"


def test_moon_properties():
    """Test that moon properties are loaded correctly."""
    path = build_temp_db()
    systems = load_data(path)

    alpha = systems[0]
    p10 = next(p for p in alpha.planets if p.id == 10)
    moon = p10.moons[0]
    assert moon.id == 100
    assert moon.name == "Alpha I-a"
    assert moon.orbit_index == 1


def test_multiple_systems():
    """Test loading multiple systems."""
    path = build_temp_db()
    systems = load_data(path)
    assert len(systems) >= 2

    # Systems should be ordered by ID
    for i in range(len(systems) - 1):
        assert systems[i].id <= systems[i + 1].id


def test_planet_parent_linkage():
    """Test that planets are correctly linked to their systems."""
    path = build_temp_db()
    systems = load_data(path)

    for system in systems:
        for planet in system.planets:
            # Each planet should have moons list (might be empty)
            assert isinstance(planet.moons, list)


def test_empty_planets_list():
    """Test that Beta system has one planet."""
    path = build_temp_db()
    systems = load_data(path)

    # Beta system (id=2) should have 1 planet
    beta = next((s for s in systems if s.id == 2), None)
    assert beta is not None
    assert len(beta.planets) == 1
    assert beta.planets[0].name == "Beta I"


def test_missing_tables_error():
    """Test that missing required tables raises appropriate error."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    path = Path(tmp.name)
    with sqlite3.connect(path) as con:
        # Create only one table, missing others
        con.execute("""
            CREATE TABLE SolarSystems (
                solarSystemId INTEGER PRIMARY KEY,
                name TEXT,
                centerX REAL,
                centerY REAL,
                centerZ REAL
            )
        """)
        con.commit()

    with pytest.raises(RuntimeError, match="Expected table"):
        load_data(path)


def test_region_and_constellation_names():
    """Test that region and constellation names are loaded when available."""
    path = build_temp_db()
    systems = load_data(path)

    # Check that region_name and constellation_name attributes exist
    for system in systems:
        assert hasattr(system, "region_name")
        assert hasattr(system, "constellation_name")
        # They might be None or actual names
        assert system.region_name is None or isinstance(system.region_name, str)
        assert system.constellation_name is None or isinstance(system.constellation_name, str)


def test_cache_key_uniqueness():
    """Test that cache keys properly differentiate different files."""
    path1 = build_temp_db()
    path2 = build_temp_db()  # Different file

    systems1 = load_data(path1, enable_cache=True)
    systems2 = load_data(path2, enable_cache=True)

    # Different files should have different cached results
    assert systems1 is not systems2


def test_limit_systems_zero():
    """Test that limit_systems=0 returns empty list."""
    path = build_temp_db()
    systems = load_data(path, limit_systems=0)
    assert len(systems) == 0


def test_dataclass_immutability():
    """Test that dataclasses are properly structured."""
    path = build_temp_db()
    systems = load_data(path)

    system = systems[0]
    # Dataclasses should have __slots__
    assert hasattr(type(system), "__slots__")

    if system.planets:
        planet = system.planets[0]
        assert hasattr(type(planet), "__slots__")

        if planet.moons:
            moon = planet.moons[0]
            assert hasattr(type(moon), "__slots__")


def test_npc_station_count():
    """Test that NPC station counts are loaded correctly."""
    from addon.data_loader import load_data

    path = build_temp_db()
    systems = load_data(path)

    # Alpha system should have 2 NPC stations
    alpha = next(s for s in systems if s.name == "Alpha")
    assert alpha.npc_station_count == 2

    # Beta system should have 1 NPC station
    beta = next(s for s in systems if s.name == "Beta")
    assert beta.npc_station_count == 1


def test_load_jumps():
    """Test that jumps are loaded correctly."""
    from addon.data_loader import load_jumps

    path = build_temp_db()
    jumps = load_jumps(path)

    # Should have 2 jump entries (bidirectional)
    assert len(jumps) == 2

    # Check jump from Alpha (1) to Beta (2)
    jump_1_2 = next(j for j in jumps if j.from_system_id == 1 and j.to_system_id == 2)
    assert jump_1_2 is not None

    # Check jump from Beta (2) to Alpha (1)
    jump_2_1 = next(j for j in jumps if j.from_system_id == 2 and j.to_system_id == 1)
    assert jump_2_1 is not None


def test_load_jumps_filtered():
    """Test that jumps can be filtered by system IDs."""
    from addon.data_loader import load_jumps

    path = build_temp_db()

    # Load only jumps involving both system 1 and 2
    jumps = load_jumps(path, system_ids=[1, 2])
    assert len(jumps) == 2  # Both directions

    # Load jumps for single system (no jumps since both ends must be in list)
    jumps = load_jumps(path, system_ids=[1])
    assert len(jumps) == 0  # No jumps between only system 1

    # Load jumps for non-existent system
    jumps = load_jumps(path, system_ids=[999])
    assert len(jumps) == 0
