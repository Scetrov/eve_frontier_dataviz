# Architecture Overview

## Layered Design (Current vs Planned)

1. Data Layer (implemented): `src/addon/data_loader.py` converts SQLite tables → dataclasses (Systems with nested Planets + Moons).
2. Scene Layer (partial): Implemented inline in `operators.build_scene` / `operators.build_scene_modal` (systems only). Planned extraction to `scene_builder.py`.
3. Visualization Layer: `shader_registry.py`, `shaders_builtin.py` apply / reuse materials per system.
4. UI / Orchestration: `operators/` package (modular operator modules), `panels.py`, `preferences.py` route user actions.

## Current Flow

```text
SQLite --> data_loader (pure Python) --> [System dataclasses (+ planets/moons in-memory)]
  --> build_scene (systems only, via operators/build_scene_modal.py) --> Blender objects (custom props: planet_count, moon_count) in `Frontier_Systems` (or hierarchical `Frontier_Regions/<Region>/<Constellation>` if preference enabled)
  --> shader operator (attribute-driven) assigns single material + per-object color/strength attributes
  --> strategies influence derived color/strength (no per-object material duplication)
```

## Planned Flow (Future Extraction)

```text
SQLite -> data_loader -> entities -> scene_builder.build() -> objects -> strategies -> materials/nodes
```

## Key Decisions

- Planets & moons are NOT instantiated yet: counts stored on system objects to keep scene light early.
- `bpy` imports isolated to UI/scene modules; pure loader stays testable.
- Deterministic material naming prevents duplication on repeated strategy application.
- `src/` layout clarifies import roots and avoids accidental extra packages.

## Performance Considerations

- Single bulk SELECT per table; filter by limited system IDs when slicing.
- In-memory cache keyed by `(path, size, mtime_ns, limit_systems)`.
- Avoid full scene rebuild for visualization-only changes (strategies operate in-place).
- Attribute-driven shading uses one shared material (`EVE_AttrDriven`), reducing material count and memory.
- Flat collection renamed to `Frontier_Systems` (legacy name `EVE_Systems` removed) to match project domain terminology.
- Global emission intensity scalable via preference `Emission Strength Scale`.
- Future: geometry nodes + instancing for large numbers of child bodies.

## Extensibility Points

| Area | How to Extend |
|------|---------------|
| Data Model | Add dataclass + bulk fetch + parent linking pattern |
| Scene (future) | New builder functions in `scene_builder.py` |
| Strategies | New subclass + `@register_strategy` decorator |
| Operators | Add new module under `operators/` (e.g. `my_feature.py`) exposing `EVE_OT_*` and let `operators.__init__` aggregate |

## Error Handling & Reporting

- Operators: use `self.report({'ERROR'}, msg)` and return `{'CANCELLED'}` on failure.
- Strategies: fail gracefully; skip objects lacking expected custom properties.
- Loader: raises `FileNotFoundError` early for missing DB; other exceptions bubble for explicit reporting.

## Roadmap Snapshot

- [ ] Extract scene building into dedicated module.
- [ ] Add planets/moons instancing toggle.
- [ ] Security metric visualization strategy.
- [ ] Node-group based shared material system (reduce per-variant copies).
- [ ] Optional Blender API stubs for deeper unit testing.

## Testing Boundary

Pure Python tests cover: loader hierarchy, cache behavior, data_state. No Blender API mocking yet; strategies and operators exercised manually in Blender.

## Future Enhancements

- Geometry Node driven attribute visualization.
- Asset Browser templates for materials.
- Export pipeline (batch procedural renders / data overlays).

If you have additional ideas for enhancements, feel free to create an issue.
