# Data Model

Defines the conceptual mapping from the SQLite database (`static.db`) into Python dataclasses used for scene generation.

## Entities

```python
@dataclass
class System:
    id: int
    name: str
    x: float
    y: float
    z: float
    security: float | None
    region_name: str | None
    constellation_name: str | None
    npc_station_count: int  # Count of NPC stations in this system
    planets: list[Planet]

@dataclass
class Planet:
    id: int
    system_id: int
    name: str
    orbit_index: int | None
    planet_type: str | None
    moons: list[Moon]

@dataclass
class Moon:
    id: int
    planet_id: int
    name: str
    orbit_index: int | None

@dataclass
class Jump:
    from_system_id: int
    to_system_id: int
```

## Table Assumptions

| Table | Columns (core) | Notes |
|-------|----------------|-------|
| systems (or SolarSystems) | id, name, x, y, z, security, regionId, constellationId | coordinates likely large: apply scale factor |
| planets (or Planets) | id, system_id, name, orbit_index, planet_type | orbit_index may be null |
| moons (or Moons) | id, planet_id, name, orbit_index | similar hierarchy principle |
| jumps (or Jumps) | fromSolarSystemId, toSolarSystemId | system connectivity graph |
| npcstations (or NpcStations) | solarSystemId | grouped by system for counts |

## Relationships

- One `System` -> many `Planet`.
- One `Planet` -> many `Moon`.
- One `System` -> zero or more NPC stations (stored as count).
- Systems connected via `Jump` entities (bidirectional graph).

## Coordinate Scaling

Raw coordinates may be large (e.g. astronomical). Use preference `scale_factor` to multiply each axis when instantiating objects.

## Loader Responsibilities

1. Open SQLite once (context manager).
2. Bulk fetch each table into memory.
3. Construct dicts by id for O(1) parent linking.
4. Attach children lists.
5. Return list of systems (root entities).
6. Provide optional slice / filter for dev (limit N systems).

## Caching Strategy

- Hash of (file size, mtime) + loader parameters -> in-memory singleton.
- Invalidate if file changed or `enable_cache` disabled.

## Extending Model

Add new dataclasses & tables (e.g. Stations, Belts):

1. Introduce new dataclass.
2. Fetch table with minimal SELECT.
3. Link into parent entity attribute.
4. Update `objects_by_type` keys and strategies that can leverage new data.

### Table Name Case

The loader now resolves table names case-insensitively and accepts either snake/lower (`systems`) or PascalCase (`Systems`). If a required table (systems / planets / moons) is missing in any case form, a clear error is raised listing available tables.

Following these guides helps to keep the project organized.
