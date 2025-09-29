# Architecture Overview

## Layers

1. Data Layer (pure Python) – future `data_loader.py` parses SQLite into dataclasses.
2. Scene Layer – builds Blender objects/collections from structured entities.
3. Visualization Layer – shader strategies produce / assign materials.
4. UI Layer – panels + operators orchestrate workflows.

## Flow

```text
SQLite -> Data Loader -> Entities -> Scene Builder -> Objects -> Strategy -> Materials/Nodes
```

## Performance Considerations

- Bulk fetch DB tables instead of per-row queries.
- Reuse materials & node groups.
- Avoid rebuilding entire scene if only visualization changes.
- Potential future: Use Geometry Nodes for large instances (systems as points -> instanced sphere).

## Caching

- In-memory cache keyed by DB mtime + size. Invalidate if file changed or preference toggled.

## Extensibility Points

- Strategy Registry: plug new classes without modifying core.
- Data Model: additional tables mapped by extending dataclasses.
- Operators: add export / analysis steps.

## Error Handling

- Operators should `report({'ERROR'}, msg)` on failure and early return.
- Strategies must fail gracefully (wrap heavy ops try/except, log not crash).

## Future Enhancements

- Headless test harness with mocked Blender API (e.g. via `bpy.types` stubs for CI).
- Geometry Node based visual encodings.
- Asset Browser integration for reusable material templates.
