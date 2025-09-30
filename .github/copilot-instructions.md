## AI Contribution Guide (Project-Specific)

Focused, repo-tailored rules for assisting on the EVE Frontier Blender data visualizer. Keep edits minimal, deterministic, and aligned with current scaffold (some modules still stubs).

### Core Purpose

SQLite (`data/static.db`, ignored) -> pure-Python entity graph (`data_loader.py`) -> Blender scene objects (future `scene_builder.py`) -> switchable visualization strategies (materials) via registry (`shader_registry.py`).

### Layer Boundaries (Do NOT cross)

1. Data layer (`data_loader.py`): no `bpy` imports; fast, unit tested (`tests/test_data_loader.py`).
2. Scene layer (`scene_builder.py` – pending): creates `EVE_*` collections & object hierarchy.
3. Visualization layer (`shader_registry.py`, `shaders_builtin.py`): strategy objects mutate / assign materials only.
4. UI / Ops (`operators.py`, `panels.py`, `preferences.py`): orchestrate user actions; keep heavy work out of draw callbacks.



### Key Conventions
- Collections: `EVE_Systems`, `EVE_Planets`, `EVE_Moons` (list lives in `operators._generated_collection_names`).
- Material prefix: `EVE_` + StrategyID (e.g. `EVE_NameFirstCharHue`). Reuse or copy intelligently; never explode counts each run.
- Strategy registry: decorate subclass with `@register_strategy` (see `shaders_builtin.py`). UI order via `order` attr.
- Object grouping passed to strategies as `objects_by_type` dict (currently only `systems` filled; plan for `planets`, `moons`).
- Dataclasses use `slots=True`; extend by adding fields + new table fetch in loader in bulk, not row-by-row.

### Strategy Contract (Minimal)

```python
class BaseShaderStrategy:
    id: str; label: str; order: int = 1000
    def build(self, context, objects_by_type: dict): ...  # assign/update materials
```

Idempotent: running twice must not create duplicate materials. Derive variant material names deterministically (e.g. base + key like first letter / child count).

### Performance & Safety Guidelines
- Batch SELECTs (see planet/moon fetching pattern with IN (...) batching in `data_loader.py`).
- Cache: loader keyed by (file path, size, mtime, limit). Respect `enable_cache` param when adding features.
- Do not traverse or mutate global Blender data outside targeted `EVE_*` objects/collections.
- Wrap potentially large loops with cheap lookups (e.g. precompute maps) rather than repeated searches.

### When Extending

1. New entity/table: add dataclass + single bulk fetch + parent linking (mirror existing planets/moons pattern). Update docs if finalized.
2. New strategy: implement in new module or `shaders_builtin.py`, register, ensure material reuse, document in `docs/SHADERS.md`.
3. Scene builder (future work): centralize object creation there; avoid putting creation logic into operators or strategies.
4. New operator: register in `operators.register()`, surface in `panels.py`. Use `report({...}, msg)` for user feedback.



### Testing & Tooling
- Run tests: `pytest` (only pure Python modules). Add new loader tests w/ fixtures under `tests/fixtures` (add SQL -> load -> assert hierarchy lengths).
- Lint: `ruff check .` (config in `pyproject.toml`). Keep imports minimal; avoid adding heavy deps.

### Common Pitfalls to Avoid
- Adding `bpy` import to `data_loader.py` (breaks headless tests).
- Creating a new material for every object without a reuse key.
- Querying DB per row instead of one bulk query with IN clause.
- Forgetting to sort strategies (set `order` to control UI listing).
- Hard-coding absolute file paths; rely on user preference for DB path.

### Practical Examples
- Variant material naming (see `ChildCountEmission`: `EVE_ChildCountEmission_{child_count}`).
- Hue mapping (see `NameFirstCharHue`: first letter -> HSV hue -> emission color node).
- Bulk linking pattern: build parent maps then attach children (`planet_map`, `system_map`). Reproduce this pattern for new hierarchies.

### Lightweight Roadmap Awareness
Scene builder + geometry nodes instancing not implemented yet—keep contributions forward-compatible (avoid baking hierarchy logic into strategies/operators).

### If Unsure
Prefer adding a small, isolated helper (e.g. in future `utils.py`) over inlining repeated logic. Keep public API additions documented briefly in corresponding `docs/*.md` file.

---
Questions or ambiguous areas? Highlight them in PR or ask for clarification before broad refactors.
