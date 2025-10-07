# EVE Frontier 3D Data Visualizer (Blender Add-on)

[![CI](https://github.com/Scetrov/eve_frontier_dataviz/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Scetrov/eve_frontier_dataviz/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/Scetrov/eve_frontier_dataviz/branch/main/graph/badge.svg)](https://codecov.io/gh/Scetrov/eve_frontier_dataviz)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Release](https://img.shields.io/github/v/release/Scetrov/eve_frontier_dataviz?include_prereleases)](https://github.com/Scetrov/eve_frontier_dataviz/releases)
[![License](https://img.shields.io/github/license/Scetrov/eve_frontier_dataviz)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Blender](https://img.shields.io/badge/Blender-4.0%2B-orange.svg?logo=blender)](https://www.blender.org/)

This repository contains a Blender add-on and supporting Python tooling to visualize astronomical / game world data stored in `data/static.db` inside a 3D scene. It uses **GPU-driven, node-based shader strategies** to encode metrics (counts, categorical codes, characters of names) into colors and emission strength with instant switching capability.

---

## 🔁 Quick Blender Access (TL;DR)

1. Download (or build) the add-on zip: `python blender_addon/scripts/build_addon.py` → creates `dist/eve_frontier_visualizer.zip`.
1. In Blender: `Edit > Preferences > Add-ons > Install…` and pick the zip.
1. Enable: search for `EVE Frontier: Data Visualizer` and tick the checkbox.
1. Still in Preferences, expand the add-on panel and set the path to your `static.db` (or use the Locate button; see Database File section below).
1. Close Preferences. In the 3D Viewport press `N` to open the Sidebar → find the `EVE Frontier` tab.
1. Click `Load / Refresh Data`, then `Build Scene`.
1. Select a visualization strategy from the dropdown (Character Rainbow, Pattern Categories, Position Encoding, or Proper Noun Highlight).
1. Click `Apply Visualization` to create the node-based material and see instant GPU-driven colors.

If the tab or operators don’t show up, see Troubleshooting below.

---

Notes about visibility and filtering

- The add-on now creates a top-level `SystemsByName` collection containing five name-pattern buckets
   (DASH, COLON, DOTSEQ, PIPE, OTHER) to help manage the visibility of large numbers of systems.
- By default the `Frontier` hierarchy (Region → Constellation → System) is hidden on import so the
   `SystemsByName` buckets control what's visible. Open the Filters panel (3D View → Sidebar → EVE Frontier → Filters)
   to toggle buckets. Use the Show All / Hide All buttons to persist defaults to the add-on preferences.

## ✨ Core Goals

- Parse a large SQLite database (`static.db`) without committing it to version control.
- Transform raw rows (systems, planets, moons, etc.) into a normalized in-memory scene graph.
- Instantiate Blender objects in collections with pre-calculated visualization properties.
- Provide **node-based visualization strategies** with instant GPU-driven switching (no Python iteration).
- Pre-calculate character indices and semantic properties once during scene build.
- Allow batch re-render/export (stills or animation) via headless `blender --background`.

## 🌟 Key Features

- **24,000+ Star Systems**: Full EVE Frontier galaxy visualization with accurate 3D coordinates
- **Five GPU-Driven Shader Strategies**: Uniform Orange, Character Rainbow, Pattern Categories, Position Encoding, Proper Noun Highlight
- **Instant Strategy Switching**: Change visualizations without rebuilding the scene
- **Navigation Landmarks**: Reference point labels at black holes and constellation centers
- **Jump Network Analysis**: Visualize stargate connections and find isolated triangle islands
- **Graph Algorithms**: Detect topological patterns in the jump network
- **Headless Rendering**: Batch export via command-line automation
- **90%+ Test Coverage**: Pure Python data layer comprehensively tested

See [`blender_addon/docs/FEATURES.md`](blender_addon/docs/FEATURES.md) for comprehensive feature documentation.

## 🗂 Project Structure

```text
blender_addon/
  copilot-instructions.md   # AI contribution guidance
  src/addon/
    __init__.py             # Add-on entry (lazy module loading)
    preferences.py          # Add-on preferences (DB path, scale, caching)
    operators/              # Modular operators (data, build, shader, viewport, property calculators)
    panels.py               # UI panel (N sidebar)
    data_loader.py          # Pure-Python SQLite → dataclasses (tested)
    data_state.py           # In-memory cache
    node_groups/            # Node-based visualization strategies
  scripts/
    export_batch.py         # Headless batch render script
    dev_reload.py           # Reload helper (during active Blender session)
  docs/
    FEATURES.md             # Comprehensive features guide (start here!)
    ARCHITECTURE.md         # Layered design overview
    NODE_BASED_STRATEGIES.md # Comprehensive node system guide
    SHADERS.md              # Strategy catalog
    SHADER_PROPERTIES.md    # Custom property reference
    DATA_MODEL.md           # Entity dataclasses & relationships
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

### Alternative: Direct Folder (Editable) Install

During active development you can skip zipping:

1. In Blender Add-ons preferences click `Install…` and select the folder `blender_addon/addon` (Blender will copy it). OR symlink/copy that folder into your Blender config `scripts/addons` directory.
1. When you change code, use the dev reload script inside Blender’s Text Editor:

- Open `blender_addon/scripts/dev_reload.py` in Blender.
- Run it to call `addon.reload_modules()` without restarting Blender.
- Re-apply a shader if materials need updating.

Note: structural changes (renaming modules or adding new files imported at register time) may still require a full Blender restart.

### Where Things Appear in Blender

| Component | Location |
|-----------|----------|
| Add-on enable toggle | Edit > Preferences > Add-ons (search "EVE Frontier") |
| Add-on preferences (DB path, cache) | Same panel, dropdown arrow under the add-on entry |
| Main UI panel | 3D Viewport → Sidebar (N) → `EVE Frontier` tab |
| Operators | Buttons: Load / Refresh Data, Build Scene, Apply (strategy) |
| Materials | Created under names prefixed `EVE_` in the Materials list |

### Typical First Run Flow

1. Launch Blender from the repository root (so relative DB path resolves), or set the absolute DB path in preferences.
1. Open the `EVE Frontier` sidebar tab.
1. Press `Load / Refresh Data` (loads systems into in-memory cache).
1. Press `Build Scene` (creates or refreshes system objects / custom props).
1. Press `Apply` to run the first registered shader strategy. Use the strategy dropdown to switch between Character Rainbow, Pattern Categories, Position Encoding, and Proper Noun Highlight. (More strategies listed in SHADERS.md.)
1. Select objects to inspect custom properties: `planet_count`, `moon_count`.

### Headless / Automation

You can run a headless build + shader application in future workflows. Example skeleton (scene build pending expansion):

   ```bash
   blender -b -P blender_addon/scripts/dev_reload.py -- --auto
   ```

   Or batch export with strategies:

   ```bash
   blender -b my_scene.blend -P blender_addon/scripts/export_batch.py -- --modes CharacterRainbow PatternCategories
   ```

### Uninstall / Clean

1. Disable the add-on in Preferences.
1. Click `Remove` in the same panel.
1. (Optional) Delete any `EVE_` collections from existing .blend files manually if you want a clean slate.

---

## Database File

You need a `static.db` SQLite file containing the source data.

Ways to point the add-on at it (precedence top → bottom):

1. Environment variable `EVE_STATIC_DB` (read-only in UI while set)
1. Locate button in the add-on preferences (opens file browser for `static.db`)
1. Manual edit of the path field in preferences


If none are provided, the field starts blank (no misleading placeholder). Set one before loading data. The environment variable is ideal for headless runs or when launching Blender from other directories.

Example (PowerShell on Windows):

   ```powershell
   $env:EVE_STATIC_DB = "C:\\data\\eve\\static.db"
   blender
   ```

   Or permanently via system environment settings.

## 🚀 Usage Workflow

1. Set DB path in Add-on Preferences if not default.
2. Click "Load / Refresh Data" (currently stub until `scene_builder` implemented).
3. Click "Build Scene" to generate placeholder / future real objects.
4. Pick and apply a visualization strategy (e.g. `CharacterRainbow`, `ProperNounHighlight`).
5. (Optional) Batch export renders:

   ```bash
   blender -b your_scene.blend -P blender_addon/scripts/export_batch.py -- --modes CharacterRainbow PatternCategories ProperNounHighlight
   ```

## 🧩 Adding a New Shader Strategy

1. Subclass `BaseShaderStrategy` in `shaders_builtin.py` or a new module.
2. Decorate with `@register_strategy`.
3. Implement `build(context, objects_by_type)`.
4. Re-open panel & apply strategy.
5. Document in `docs/SHADERS.md`.

## 🗃 Data Expectations (Example Tables)

- `systems(id, name, x, y, z, security)`
- `planets(id, system_id, name, orbit_index, planet_type)`
- `moons(id, planet_id, name, orbit_index)`

Details and dataclasses: see `docs/DATA_MODEL.md`.

## 🧪 Testing & Dev Loop

- Run tests: `pytest` or `make test`
- Lint: `ruff check .` or `make lint`
- Auto-fix trivial lint (imports/format): `make lint-fix`
- Focus pure-Python logic first (data loader) before large scene builds.
- Use `scripts/dev_reload.py` inside a Blender Text Editor to hot-reload the add-on.

## 📦 Roadmap (Excerpt)

- Scene builder (real object hierarchy) ✔ pending implementation
- Geometry Nodes instancing for large datasets
- Additional shader strategies (security gradient, hierarchy depth glow)
- CLI summarization / stats extraction
- CI: run tests + lint (GitHub Actions)

## 🛡 License

Licensed under the MIT License. See `LICENSE` for full text.

## 🧹 Pre-commit Hooks

This repo ships a `.pre-commit-config.yaml` that runs Ruff (lint & format), the custom markdown linter, and the test suite.

Install & enable:

   ```bash
   pip install pre-commit
   pre-commit install
   ```

   Run manually on all files:

   ```bash
   pre-commit run --all-files
   ```

## 🙌 Contributions

PRs welcome—please keep strategies deterministic & idempotent; avoid duplicating materials each run. See `CONTRIBUTING.md` for workflow details.

## ❓ Troubleshooting

| Issue | Fix |
|-------|-----|
| Add-on not visible | Confirm `__init__.py` has `bl_info` & correct folder structure. |
| DB not found | Set database path in Add-on Preferences. |
| Slow rebuild | Temporarily limit systems (add `limit_systems` param in loader call / future UI). |
| Materials uniform | Strategy may not assign per-object materials; check logs / console. |

---

Happy visualizing!
