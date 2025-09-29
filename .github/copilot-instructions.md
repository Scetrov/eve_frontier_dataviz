# Copilot Instructions for This Repository

These guidelines tell AI assistants how to operate within this Blender data visualization project.

## Core Intent

Transform structured data from a large SQLite database (`data/static.db`, excluded from VCS) into a 3D hierarchical scene in Blender with multiple switchable visualization (shader/material) strategies.

## Architectural Pillars

1. Separation of Concerns:
   - Data access (`data_loader.py`) contains NO Blender API imports—pure Python for testability.
   - Scene construction (`scene_builder.py`) isolates object & collection creation.
   - Visualization strategies live behind a registry (`shader_registry.py`).
2. Extensibility:
   - Add new shader strategies by subclassing `BaseShaderStrategy`.
   - Keep each strategy deterministic & idempotent (re-applying should not duplicate materials).
3. Performance:
   - Prefer instancing or shared materials where possible.
   - Batch DB reads; avoid per-row transactions.
4. Non-destructive Updates:
   - Scene rebuild should optionally clear previous generated collections.
   - Shader application updates materials only on managed objects.

## File Responsibilities

| File                       | Purpose                                                          |
| -------------------------- | ---------------------------------------------------------------- |
| `addon/__init__.py`        | Add-on metadata, register/unregister, menu/panel bootstrap.      |
| `addon/preferences.py`     | Add-on preferences (DB path, scale factor, caching toggle).      |
| `addon/operators.py`       | Blender operators: load data, build scene, apply shader, export. |
| `addon/panels.py`          | UI Panels for user interaction.                                  |
| `addon/data_loader.py`     | Pure Python DB -> in-memory dataclasses.                         |
| `addon/scene_builder.py`   | Create collections & objects from loaded data.                   |
| `addon/materials.py`       | Material / node creation helpers.                                |
| `addon/shader_registry.py` | Base class + registry mechanisms.                                |
| `addon/shaders_builtin.py` | Built-in example strategies.                                     |
| `addon/utils.py`           | Logging, color ramps, hashing, shared helpers.                   |
| `scripts/export_batch.py`  | Headless batch rendering entry point.                            |
| `scripts/dev_reload.py`    | Developer convenience reload script.                             |

## Data Model (Conceptual)

Represent entities via lightweight dataclasses:

```python
@dataclass
class System: id: int; name: str; x: float; y: float; z: float; security: float; planets: list
@dataclass
class Planet: id: int; system_id: int; name: str; orbit_index: int; planet_type: str; moons: list
@dataclass
class Moon: id: int; planet_id: int; name: str; orbit_index: int
```

## Shader Strategy Contract

```python
class BaseShaderStrategy:
    id: str  # unique key
    label: str
    def build(self, context, objects_by_type: dict):
        """Create or update materials and assign to objects.
        objects_by_type: {"systems": [...], "planets": [...], "moons": [...]} (Blender objects)
        """
```

Return value optional; should log actions. Strategies may create node groups & reuse them.

## Naming Conventions

- Generated collections prefixed with `EVE_`.
- Generated materials prefixed with `EVE_` + strategy id.
- Custom properties: store lightweight metadata under `obj["eve_meta"]` dict.

## Avoid

- Hard-coding file system absolute paths.
- Creating duplicate materials each run.
- Running heavy DB queries in the main thread during UI draws.

## Testing Guidance

- Add pure-Python tests for `data_loader.py` once a `/tests` directory exists.
- Mock minimal rows to validate hierarchy assembly & attribute mapping.

## Roadmap Hooks for AI

When implementing tasks:

1. Search for existing strategy patterns before adding new ones.
2. If adding new operators, ensure they are registered & appear in panel.
3. Maintain backward compatibility for preference property names.
4. Use feature flags in preferences for experimental behavior.

## Style

- Prefer `ruff` / `black` formatting (to be added).
- Type annotate public functions.

## Incremental Additions

When expanding:

- Implement base scaffold first (`__init__`, registry, loader stub) before advanced optimizations.
- Document any new shader in `docs/SHADERS.md`.

## Example Extension Idea

Add a strategy mapping the second letter of the system name to metallic + roughness values for subtle classification.

---

These instructions should help AI contributors make coherent, minimal-diff, well-structured changes.
