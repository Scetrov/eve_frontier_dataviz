## AI Contribution Guide (Project-Specific)

Authoritative rules for assisting on the EVE Frontier Blender data visualizer. Favor minimal, targeted edits; keep public behavior stable; provably accurate, incremental, testable changes, committed frequently. Each change should include updates to relevant documentation and tests where applicable. Commit and push each change before the next prompt.

> [!IMPORTANT]
> Under no circumstances should you suggest a command that disables or circumvents pre-commit hooks, GPG signing or other security controls put in place to maintain code integrity. If a GPG Signing request fails, notify the user and don't take any further action.

### Current Core Flow

```text
SQLite (data/static.db) -> data_loader (pure Python) -> in-memory systems + jumps
 -> operators.build_scene (systems only) -> system objects (custom props: planet_count, moon_count, npc_station_count)
 -> operators.build_jumps -> jump line objects (curves connecting systems)
 -> shader strategies apply / reuse materials
```

### Layer Boundaries (Do NOT cross)

1. Data layer (`src/addon/data_loader.py`): pure Python; no `bpy`; unit tested.
2. Scene layer (future): centralizes object creation (currently logic lives in `operators.build_scene`).
3. Visualization layer (`shader_registry.py`, `shaders_builtin.py`): assign/update materials only; no object creation.
4. UI / Ops (`operators.py`, `panels.py`, `preferences.py`): orchestration & user triggers; keep loops light.

### Key Conventions

- Source layout: `blender_addon/src/addon` is the Python package root.
- Collections created: `Frontier` (root, contains hierarchical Region/Constellation subcollections with system objects), `EVE_Jumps` (jump line curves).
- Future reserved names (do not misuse): `EVE_Planets`, `EVE_Moons`.
- Per-system custom properties:
    - `planet_count` (int)
    - `moon_count` (int)
    - `eve_system_id` (int) - system database ID for jump lookups
    - `eve_npc_station_count` (int) - count of NPC stations
    - `eve_name_pattern` (int) - pattern category
    - `eve_name_char_index_N_ord` (float) - character ordinal values
    - `eve_is_blackhole` (int) - 1 if system ID is 30000001-30000003 (A 2560, M 974, U 3183)
- Material naming: `EVE_` + StrategyID (+ deterministic suffix for variants, e.g. first char, child count).
- Jump lines: simple curves with emission shader, toggleable via collection visibility.
- `objects_by_type` dict currently only includes key `"systems"`.
- Data loader dataclasses use `slots=True`; extend by adding a single bulk SELECT, never per-row queries.

### Strategy Contract (Minimal)

```python
class BaseShaderStrategy:
    id: str; label: str; order: int = 1000
    def build(self, context, objects_by_type: dict): ...  # assign/update materials
```

Idempotent: re-running may reuse or lazily create a bounded set of materials; no unbounded growth. Derive variant names deterministically.

### Performance & Safety Guidelines

**Scale Context**: This addon manages 25,000+ objects (24,426 systems + jump lines + planets/moons future). O(n²) operations are **impossible** at this scale—they will hang Blender for minutes or crash.

**Critical Rules**:
- **O(n) maximum**: All operations must be linear or better. Batch operations wherever possible.
- **No nested object loops**: Never iterate objects inside another object loop (O(n²) death).
- **Use batch APIs**: `bpy.data.batch_remove()` for deletions, bulk property sets, etc.
- **Disable undo during bulk ops**: `bpy.context.preferences.edit.use_global_undo = False` before heavy operations.
- **Collect then process**: Build sets/lists first, then batch process (see `clear_generated()` pattern).

**Data Layer**:
- Bulk SELECT; never open a cursor per entity.
- Loader cache key: (resolved path, size, mtime_ns, limit_systems) → reuse when enabled.
- Single JOIN query better than N queries in a loop.

**Scene Layer**:
- Only touch objects inside `EVE_*` collections you create.
- Avoid scanning all materials each loop—cache lookups by name.
- Keep operator `execute` methods fast; heavy work belongs in pure Python helpers where possible.
- Ensure long-running operators (e.g. scene build) support cancellation and report progress.
- Modal operators for operations > 1 second (scene build, shader apply, etc.).

**Example Patterns**:

```python
# ❌ BAD - O(n²) will hang on 25k objects
for obj in scene.objects:
    for other in scene.objects:
        compute_distance(obj, other)

# ✅ GOOD - O(n) batch collection then process
objects_to_remove = set()
for coll in collections:
    objects_to_remove.update(coll.objects)
bpy.data.batch_remove(ids=objects_to_remove)
```

Check the schema below if unsure about where to get data from.

### When Extending

1. New entity/table: add dataclass + one bulk fetch with IN (...) filtering (see planets/moons). Update `DATA_MODEL.md` once stable.
2. New strategy: add module OR extend `shaders_builtin.py`; ensure material reuse; document in `docs/SHADERS.md`.
3. Future scene builder: plan code so migration just moves object creation into `scene_builder.build()` later.
4. New operator: small, composable; register + expose in panel; user feedback via `self.report`.
5. Test additions: pure Python only—mocking `bpy` is out of scope for now.

### Testing & Tooling

- Tests: `pytest` with coverage (threshold 90%). Only modules without `bpy`, ensure passing before commit.
- Add fixtures under `tests/fixtures` as `.sql` scripts (see `mini.db.sql`).
- Lint: `ruff check .` (import ordering, errors, basic best practices).
- Markdown: `python blender_addon/scripts/markdown_lint.py` in CI.
- Pre-commit: ruff (fix + format), markdown lint, pytest.
- Commit messages: Conventional Commits style (chore:, feat:, fix:, docs:, test:, refactor:, etc).
- MCP servers: Pylance MCP for running python scripts, GitHub for accessing builds, PRs and issues.

### Common Pitfalls to Avoid

- Importing `bpy` in pure modules (`data_loader.py`, tests).
- Material explosion: missing deterministic naming or reuse lookup.
- Per-row DB queries inside loops.
- Relying on planets/moons objects (they do not exist yet; use counts via custom props).
- Hard-coded absolute paths—use preference `db_path`.

### Practical Examples

- Variant material naming: `EVE_ChildCountEmission_{child_count}`.
- Hue mapping: `NameFirstCharHue` derives hue from first letter ordinal.
- Parent linking: construct `system_map`, `planet_map` then attach children (see loader implementation pattern).
- Using custom properties: strategies can read `obj["planet_count"]` / `obj["moon_count"]`.

### Database Schema Reference

The SQLite database (`data/static.db`) contains the following tables:

#### SolarSystems

```sql
CREATE TABLE SolarSystems (
    solarSystemId INTEGER PRIMARY KEY,
    name TEXT,
    constellationId INTEGER,
    regionId INTEGER,
    centerX REAL,
    centerY REAL,
    centerZ REAL,
    frost_line REAL,
    habitable_zone_inner REAL,
    habitable_zone_outer REAL,
    star_age REAL,
    star_luminosity REAL,
    star_mass REAL,
    star_metallicity REAL,
    star_radius REAL,
    star_spectral_class TEXT,
    star_temperature REAL,
    FOREIGN KEY (constellationId) REFERENCES Constellations (constellationId),
    FOREIGN KEY (regionId) REFERENCES Regions (regionId)
)
```

#### Regions

```sql
CREATE TABLE Regions (
    regionId INTEGER PRIMARY KEY,
    name TEXT,
    centerX REAL,
    centerY REAL,
    centerZ REAL
)
```

#### Constellations

```sql
CREATE TABLE Constellations (
    constellationId INTEGER PRIMARY KEY,
    name TEXT,
    regionId INTEGER,
    centerX REAL,
    centerY REAL,
    centerZ REAL,
    FOREIGN KEY (regionId) REFERENCES Regions (regionId)
)
```

#### Planets

```sql
CREATE TABLE Planets (
    planetId INTEGER PRIMARY KEY,
    solarSystemId INTEGER,
    name TEXT,
    orbit_index INTEGER,
    planet_type TEXT,
    FOREIGN KEY (solarSystemId) REFERENCES SolarSystems (solarSystemId)
)
```

#### Moons

```sql
CREATE TABLE Moons (
    moonId INTEGER PRIMARY KEY,
    planetId INTEGER,
    name TEXT,
    orbit_index INTEGER,
    FOREIGN KEY (planetId) REFERENCES Planets (planetId)
)
```

**Notes:**
- Table names use PascalCase (e.g., `SolarSystems`, not `systems` or `solar_systems`)
- Foreign key columns use camelCase (e.g., `constellationId`, `regionId`)
- Constellation names in the database are currently numeric IDs (e.g., "20000001")
- Region names are descriptive strings (e.g., "000-0Y-0", "DG8-Y-D3")
- Black hole systems: IDs 30000001-30000003 (A 2560, M 974, U 3183) are universal constants
  - Identified by: spectral class 'O0', infinite mass (`star_mass = inf`), zero luminosity
  - Detection uses system ID, not name, for reliability
- Data loader performs LEFT JOINs to populate `region_name` and `constellation_name` on System dataclass
- Additional tables: `Jumps`, `NpcStations` (not currently loaded by visualizer)

### Lightweight Roadmap Awareness

Near-term: scene builder module, planet/moon instancing, node-based attribute-driven shading, security metric visualizations.

### If Unsure

Add a tiny helper function near related code or start a focused module only when a pattern repeats 3+ times. Document new public surfaces in `docs/`.

### Release workflow (how releases are created)

This repo uses an automated release workflow (`.github/workflows/release.yml`) that runs when a semantic tag matching `v*.*.*` is pushed. A few important rules to follow so releases are reproducible and secure:

- Tag format: strictly `vMAJOR.MINOR.PATCH` (for example `v0.6.0`). The release workflow only triggers on tags that match this pattern.
- Tags must be annotated or, preferably, GPG-signed. Lightweight (simple) tags are rejected by the workflow. Use `git tag -s v0.6.0 -m "Release v0.6.0"` to create a signed tag.
- The workflow verifies the tag object is annotated and looks for a PGP signature. For full verification, ensure your signing key is uploaded to GitHub (Settings → SSH and GPG keys → New GPG key).
- What `release.yml` does (high level):
    - Re-fetches tag objects and verifies the tag is annotated/signed
    - Generates a changelog (grouped by conventional commit types) between the previous semver tag and the new tag
    - Collects contributors from the commit range
    - Builds the add-on ZIP and renames it to include the tag
    - Generates an attestation for the ZIP (supply-chain provenance) and creates a GitHub Release with the ZIP attached

- Permissions: the release workflow requires `contents: write` (to create releases and upload artifacts) and additional attestation scopes (`id-token: write`, `attestations: write`) — these are already set in `release.yml`.

- Quick local workflow (how to create a compliant release tag):

    1. Make sure your work is on `main` and up-to-date.
    2. Create a signed annotated tag (GPG key must be available locally):

         git tag -s v0.6.0 -m "Release v0.6.0"

    3. Push the tag to trigger the release workflow:

         git push origin v0.6.0

    4. The release job will run and (if successful) create the Release on GitHub and upload the ZIP. The release body is generated from the tag message, changelog, and contributors.

- If you cannot sign locally, do not create lightweight tags. Instead, create an annotated tag (`git tag -a v0.6.0 -m "Release v0.6.0"`) — the workflow will accept annotated tags but will emit a warning if not PGP-signed.

- Post-release: the workflow uploads JUnit/coverage artifacts for CI (see `ci.yml`) and generates attestations for the built ZIP. If you need to update the Release body after it's created, use the GitHub UI or the GitHub API; automation may also update it via the MCP if authorized.

Keeping releases signed and annotated ensures authenticity and makes supply-chain verification straightforward for downstream users.

---
Questions or ambiguous areas? Highlight them in PR or ask for clarification before broad refactors.
