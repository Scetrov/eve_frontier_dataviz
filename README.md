# EVE Frontier 3D Data Visualizer (Blender Add-on)

This repository contains a Blender add-on and supporting Python tooling to visualize astronomical / game world data stored in `data/static.db` inside a 3D scene. It focuses on representing systems, planets, moons, stations, and other entities with procedural shaders that encode metrics (counts, categorical codes, characters of names) into colors, emission, shape modifiers, or geometry node inputs.

## ✨ Core Goals

- Parse a large SQLite database (`static.db`) without committing it to version control.
- Transform raw rows (systems, planets, moons, etc.) into a normalized in-memory scene graph.
- Instantiate Blender objects in collections (e.g. `Systems`, `Planets`, `Moons`).
- Provide multiple visualization modes ("shaders") mapping attributes (first letter, hierarchy depth, child counts) to material properties.
- Offer an extensible plug-in style registry for adding new shader strategies.
- Allow batch re-render/export (stills or animation) via headless `blender --background`.

## 🗂 Project Structure

```text
blender_addon/
  copilot-instructions.md   # AI contribution guidance
  addon/
    __init__.py             # Add-on entry (lazy module loading)
    preferences.py          # Add-on preferences (DB path, scale, caching)
    operators.py            # Operators: load data, build scene, apply shader
    panels.py               # UI panel (N sidebar)
    data_loader.py          # Pure-Python SQLite → dataclasses (tested)
    shader_registry.py      # Strategy registry
    shaders_builtin.py      # Example strategies
    (future) scene_builder.py, materials.py, utils.py
  scripts/
    export_batch.py         # Headless batch render script
    dev_reload.py           # Reload helper (during active Blender session)
  docs/
    ARCHITECTURE.md         # Layered design overview
    DATA_MODEL.md           # Entity dataclasses & relationships
    SHADERS.md              # Strategy catalogue & guidelines
  tests/
    fixtures/mini.db.sql    # Schema + tiny dataset
    test_data_loader.py     # Unit tests for loader
pyproject.toml              # Packaging, ruff, pytest config
README.md                   # (this file)
README_TESTING.md           # Testing & lint instructions
.gitignore                  # Root ignore (excludes large DB)
data/static.db (ignored)    # Large real dataset (not in repo)
```

## 🔧 Installation (Development Mode)

1. Ensure the SQLite database exists at `data/static.db` (or set a custom path in Add-on Preferences inside Blender).
1. (Optional) Create a virtual environment & install dev deps:

```bash
pip install -e .[dev]
```

1. Zip the add-on directory or point Blender at it directly:

```bash
python -m zipfile -c eve_frontier_visualizer.zip blender_addon/addon
```

1. In Blender: Edit > Preferences > Add-ons > Install… → choose the zip (or copy folder into scripts/addons) and enable it (`EVE Frontier: Data Visualizer`).
1. Open the 3D Viewport > N panel > "EVE Frontier" tab.

## 🚀 Usage Workflow

1. Set DB path in Add-on Preferences if not default.
1. Click "Load / Refresh Data" (currently stub until `scene_builder` implemented).
1. Click "Build Scene" to generate placeholder / future real objects.
1. Pick and apply a visualization strategy (e.g. `NameFirstCharHue`).
1. (Optional) Batch export renders:

```bash
blender -b your_scene.blend -P blender_addon/scripts/export_batch.py -- --modes NameFirstCharHue ChildCountEmission
```

## 🧩 Adding a New Shader Strategy

1. Subclass `BaseShaderStrategy` in `shaders_builtin.py` or a new module.
1. Decorate with `@register_strategy`.
1. Implement `build(context, objects_by_type)`.
1. Re-open panel & apply strategy.
1. Document in `docs/SHADERS.md`.

## 🗃 Data Expectations (Example Tables)

- `systems(id, name, x, y, z, security)`
- `planets(id, system_id, name, orbit_index, planet_type)`
- `moons(id, planet_id, name, orbit_index)`

Details and dataclasses: see `docs/DATA_MODEL.md`.

## 🧪 Testing & Dev Loop

- Run tests: `pytest`
- Lint: `ruff check .`
- Focus pure-Python logic first (data loader) before large scene builds.
- Use `scripts/dev_reload.py` inside a Blender Text Editor to hot-reload the add-on.

## 📦 Roadmap (Excerpt)

- Scene builder (real object hierarchy) ✔ pending implementation
- Geometry Nodes instancing for large datasets
- Additional shader strategies (security gradient, hierarchy depth glow)
- CLI summarization / stats extraction
- CI: run tests + lint (GitHub Actions)

## 🛡 License

Choose a license (MIT / Apache-2.0 / etc.) and update `pyproject.toml` and this section.

## 🙌 Contributions

PRs welcome—please keep strategies deterministic & idempotent; avoid duplicating materials each run.

## ❓ Troubleshooting

| Issue | Fix |
|-------|-----|
| Add-on not visible | Confirm `__init__.py` has `bl_info` & correct folder structure. |
| DB not found | Set database path in Add-on Preferences. |
| Slow rebuild | Temporarily limit systems (add `limit_systems` param in loader call / future UI). |
| Materials uniform | Strategy may not assign per-object materials; check logs / console. |

---

Happy visualizing!
