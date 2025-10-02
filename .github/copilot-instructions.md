## AI Contribution Guide (Project-Specific)

Authoritative rules for assisting on the EVE Frontier Blender data visualizer. Favor minimal, targeted edits; keep public behavior stable; provably accurate, incremental, testable changes, committed frequently. Each change should include updates to relevant documentation and tests where applicable. Commit and push each change before the next prompt.

### Current Core Flow

```text
SQLite (data/static.db) -> data_loader (pure Python) -> in-memory systems list
 -> operators.build_scene (systems only) -> system objects (custom props: planet_count, moon_count)
 -> shader strategies apply / reuse materials
```

### Layer Boundaries (Do NOT cross)

1. Data layer (`src/addon/data_loader.py`): pure Python; no `bpy`; unit tested.
2. Scene layer (future): centralizes object creation (currently logic lives in `operators.build_scene`).
3. Visualization layer (`shader_registry.py`, `shaders_builtin.py`): assign/update materials only; no object creation.
4. UI / Ops (`operators.py`, `panels.py`, `preferences.py`): orchestration & user triggers; keep loops light.

### Key Conventions

- Source layout: `blender_addon/src/addon` is the Python package root.
- Collections currently created: `EVE_Systems` only (planets/moons represented as counts, not objects).
- Future reserved names (do not misuse): `EVE_Planets`, `EVE_Moons`.
- Per-system custom properties:
    - `planet_count` (int)
    - `moon_count` (int)
- Material naming: `EVE_` + StrategyID (+ deterministic suffix for variants, e.g. first char, child count).
- Strategy registry: use `@register_strategy` decorator; control ordering with `order` attribute.
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

- Bulk SELECT; never open a cursor per entity.
- Loader cache key: (resolved path, size, mtime_ns, limit_systems) → reuse when enabled.
- Only touch objects inside `EVE_*` collections you create.
- Avoid scanning all materials each loop—cache lookups by name.
- Keep operator `execute` methods fast; heavy work belongs in pure Python helpers where possible.

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

### Lightweight Roadmap Awareness

Near-term: scene builder module, planet/moon instancing, node-based attribute-driven shading, security metric visualizations.

### If Unsure

Add a tiny helper function near related code or start a focused module only when a pattern repeats 3+ times. Document new public surfaces in `docs/`.

---
Questions or ambiguous areas? Highlight them in PR or ask for clarification before broad refactors.
