# Architecture Overview

## Layered Design

1. **Data Layer** (implemented): `src/addon/data_loader.py` converts SQLite tables → dataclasses (Systems with nested Planets + Moons).
2. **Scene Layer** (partial): Implemented inline in `operators.build_scene_modal` (systems only). Planned extraction to `scene_builder.py`.
3. **Visualization Layer**: Node-based shader system (`node_groups/`) with GPU-driven attribute reading.
4. **UI / Orchestration**: `operators/` package (modular operator modules), `panels.py`, `preferences.py` route user actions.

## Current Flow

```text
SQLite --> data_loader (pure Python) --> [System dataclasses (+ planets/moons in-memory)]
  --> build_scene_modal (systems only) --> Blender objects (custom props: planet_count, moon_count, eve_name_char_index_*) in `Frontier` collection
  --> node-based shader strategies read pre-calculated properties via Attribute nodes
  --> instant GPU-driven visualization with material switching
```

## Planned Flow (Future Extraction)

```text
SQLite -> data_loader -> entities -> scene_builder.build() -> objects -> strategies -> materials/nodes
```

## Key Decisions

- Planets & moons are NOT instantiated yet: counts stored on system objects to keep scene light early.
- `bpy` imports isolated to UI/scene modules; pure loader stays testable.
- **Node-based visualization**: All strategies implemented as GPU shader node groups for instant switching.
- **Pre-calculated properties**: Character indices and semantic properties stored on objects during scene build.
- **Single shared material**: All systems share one material (`EVE_NodeGroupStrategies`) with Mix node switcher.
- `src/` layout clarifies import roots and avoids accidental extra packages.

## Performance Considerations

**Scale**: 25,000+ objects (24,426 systems minimum, plus jump lines, future planets/moons)

**Critical Constraint**: O(n²) operations are **impossible** at this scale. They will hang Blender for minutes or cause crashes. All algorithms must be O(n) or better.

**Optimization Strategies**:
- **Single bulk SELECT per table**: Filter by limited system IDs when slicing; never per-row queries.
- **In-memory cache**: Keyed by `(path, size, mtime_ns, limit_systems)` for instant reloads.
- **Batch operations**: Use `bpy.data.batch_remove()` for deletions, collect-then-process pattern everywhere.
- **Undo disabled during bulk ops**: `bpy.context.preferences.edit.use_global_undo = False` before heavy operations.
- **Node-based shading**: Single shared material drastically reduces memory overhead vs per-object materials.
- **GPU-driven**: All property-to-color mapping happens on GPU via shader nodes (no Python iteration).
- **Modal operators**: Long operations (scene build, shader apply) run asynchronously with progress reporting.
- **Avoid full scene rebuild for visualization-only changes**: Strategies operate via GPU nodes, instant switching.

**Performance Examples**:

```python
# ❌ NEVER DO THIS - O(n²) hangs on 25k objects
for obj in collection.objects:
    for other in collection.objects:
        compute_distance(obj, other)

# ✅ CORRECT - O(n) collect then batch process
objects_to_remove = set()
collections_to_process = [root_coll]
while collections_to_process:
    current = collections_to_process.pop()
    collections_to_process.extend(current.children)
    objects_to_remove.update(current.objects)
bpy.data.batch_remove(ids=objects_to_remove)
```

**Measured Performance** (24,426 systems on typical hardware):
- Scene build: 30-60 seconds (modal, cancellable)
- Clear scene: <1 second (batch removal)
- Strategy switch: Instant (GPU shader swap)
- Jump network build: 15-30 seconds (modal)

Flat collection renamed to `Frontier` (legacy name `EVE_Systems` removed) to match project domain terminology.
Future: geometry nodes + instancing for large numbers of child bodies.

## Extensibility Points

| Area | How to Extend |
|------|---------------|
| Data Model | Add dataclass + bulk fetch + parent linking pattern |
| Scene (future) | New builder functions in `scene_builder.py` |
| Strategies | Add new node group to `node_groups/` module |
| Operators | Add new module under `operators/` (e.g. `my_feature.py`) exposing `EVE_OT_*` |

## Error Handling & Reporting

- Operators: use `self.report({'ERROR'}, msg)` and return `{'CANCELLED'}` on failure.
- Node groups: fail gracefully; Attribute nodes return default values for missing properties.
- Loader: raises `FileNotFoundError` early for missing DB; other exceptions bubble for explicit reporting.

## Roadmap Snapshot

- [x] Node-based shader system with GPU-driven property reading
- [x] Pre-calculated character index properties (0-9)
- [x] UI-based strategy switching via dropdown
- [ ] Extract scene building into dedicated module
- [ ] Add planets/moons instancing toggle
- [ ] Security metric visualization strategy
- [ ] Geometry Node-driven attribute visualization

## Testing Boundary

Pure Python tests cover: loader hierarchy, cache behavior, data_state, property calculators. No Blender API mocking yet; node groups and operators exercised manually in Blender.

## Future Enhancements

- Additional node-based strategies (security zones, hierarchy depth, temporal data)
- Asset Browser templates for materials
- Export pipeline (batch procedural renders / data overlays)
- Animated strategy transitions

If you have additional ideas for enhancements, feel free to create an issue.
