# EVE Frontier 3D Data Visualizer (Blender Add-on)

This repository contains a Blender add-on and supporting scripts to visualize astronomical / game world data extracted from [the EVE Frontier Client](https://github.com/frontier-reapers/Phobos/tree/fsdbinary-t1) inside a 3D scene. It focuses on representing systems, planets, moons, stations, and other entities with **GPU-driven, node-based shader strategies** that encode metrics (counts, categorical codes, characters of names) into colors and emission strength.

## ✨ Core Goals

- Read data from a large SQLite database, while remaining separate from it so as not to commit a 30MB file to Git.
- Transform raw rows (systems, planets, moons, etc.) into a normalized in-memory scene graph.
- Instantiate Solar Systems as Blender objects in collections.
- Provide multiple **node-based visualization strategies** with instant GPU-driven switching.
- Pre-calculate properties once during scene build for zero-cost strategy changes.
- Allow batch re-render/export (stills or animation) via command line (headless `blender --background`).

## 🗂 Project Structure

Current layout uses a `src/` style package for clearer discovery & editable installs.

```text
blender_addon/
  README.md               – This overview
  README_TESTING.md       – Notes on testing approach
  pyproject.toml          – Build / tooling config (setuptools + ruff + pytest)
  .gitignore              – Ignore rules (excludes large DB, coverage artifacts)
  src/
    addon/                – Python package (Blender add-on code)
      __init__.py         – Blender entry (bl_info, register/unregister)
      data_loader.py      – Pure Python SQLite loader (systems→planets→moons)
      data_state.py       – In‑memory cache of loaded systems
      preferences.py      – Add-on preferences (db path, scale, cache toggle)
      operators/          – Modular operators (data, build, shader, viewport, property calculators)
      panels.py           – UI panel (N‑panel) integrating operators
      node_groups/        – Node-based visualization strategies (CharacterRainbow, PatternCategories, PositionEncoding)
  docs/
    ARCHITECTURE.md       – Layer boundaries & design notes
    DATA_MODEL.md         – Database tables / dataclass mapping
    NODE_BASED_STRATEGIES.md – Comprehensive node system guide
    SHADERS.md            – Strategy catalog and usage
    SHADER_PROPERTIES.md  – Custom property reference
  scripts/
    dev_reload.py         – Helper to reload add-on inside Blender session
    export_batch.py       – Example headless export / batch script
    markdown_lint.py      – Minimal Markdown formatting linter
  tests/
    conftest.py           – Adds src path for imports
    fixtures/mini.db.sql  – Tiny SQLite schema + seed data for tests
    test_data_loader.py   – Loader hierarchy & cache tests
    test_data_state.py    – In‑memory state tests
    test_property_calculators.py – Property calculation tests
```

Not (yet) present: `scene_builder.py`, geometry node assets, or planet/moon object instancing (the scene currently creates only system objects with planet/moon counts stored as custom properties).

## Key Features

### Node-Based Visualization System

- **GPU-Driven**: All color/strength calculations happen on GPU via shader nodes
- **Instant Switching**: Change strategies via dropdown with zero Python iteration
- **Pre-Calculated Properties**: Character indices and semantic data computed once during scene build
- **Three Built-In Strategies**:
  - **Character Rainbow**: Color by first character, brightness by child count
  - **Pattern Categories**: Distinct colors for naming patterns (DASH/COLON/DOTSEQ/PIPE/OTHER)
  - **Position Encoding**: Multi-character RGB encoding with black hole boost
- **Single Shared Material**: All systems use `EVE_NodeGroupStrategies` material with Mix node switcher
- **Extensible**: Add new strategies by creating shader node groups

## 🔧 Installation (Development Mode)

1. Ensure the SQLite database exists at `../data/static.db` relative to this folder (or configure via Add-on Preferences).
2. In Blender: `Edit > Preferences > Add-ons > Install...` and select a zip of the `addon` directory OR symlink/copy the folder into your Blender scripts/addons path.
3. Enable the add-on: look for `EVE Frontier: Data Visualizer`.
4. Open the `N` panel in the 3D Viewport → locate the "EVE Frontier" tab to load / rebuild the scene.

### Optional: Zip Packaging

From the `blender_addon` directory:

```sh
python -m zipfile -c eve_frontier_visualizer.zip addon
```

Then install the produced zip in Blender.

## 🚀 Usage Workflow

1. Set DB path in Add-on Preferences if not default.
2. Click **Load / Refresh Data** to parse and cache entities.
3. Click **Build Scene** to instantiate objects with pre-calculated properties.
  - The build now creates a top-level `SystemsByName` grouping with child collections for naming-pattern buckets (DASH, COLON, DOTSEQ, PIPE, OTHER). The `Frontier` hierarchy (Region/Constellation) is created but hidden by default so visibility is controlled via `SystemsByName`.
4. Select a visualization strategy from the **Strategy** dropdown:
   - Character Rainbow
   - Pattern Categories
   - Position Encoding
5. Click **Apply Visualization** to create/update the shared material.
6. Change strategies instantly via dropdown (no rebuild needed).
7. Filter systems by naming-pattern using the new Filters panel (EVE Frontier → Filters).
  - Toggle individual buckets via checkboxes (session-only).
  - Use "Show All" / "Hide All" to persist a default across Blender sessions (these buttons update add-on preferences).
8. (Optional) Run batch export:

```sh
blender -b your_scene.blend -P scripts/export_batch.py
```

## 🧩 Adding a New Visualization Strategy

The system uses **node-based strategies** implemented as Blender shader node groups:

1. Create a new shader node group in Blender:
   - Name: `EVE_Strategy_YourStrategyName`
   - Inputs: None (read from Attribute nodes)
   - Outputs: `Color` (RGBA) and `Strength` (Value)

2. Implement your visualization logic using:
   - **Attribute nodes** to read `eve_name_char_index_*`, `eve_planet_count`, etc.
   - **Math/ColorRamp/Mix nodes** for processing
   - **Combine HSV/RGB nodes** for color generation

3. Integrate into the add-on:
   - Add creation function to `node_groups/__init__.py`
   - Update `_ensure_node_group_material()` to include your strategy in the Mix node switcher
   - Add enum item to `_node_strategy_enum_items()` for UI dropdown

4. Document in `docs/SHADERS.md`.

See `docs/NODE_BASED_STRATEGIES.md` for detailed examples and templates.

## 🗃 Data Expectations

The database is assumed to be SQLite with tables resembling:

- `systems(id, name, x, y, z, security)`
- `planets(id, system_id, name, orbit_index, planet_type)`
- `moons(id, planet_id, name, orbit_index)`
(Extend as needed; define canonical mapping in `DATA_MODEL.md`.)

## 🏗 Scene Construction Conventions

- Units: 1 Blender unit == 1 arbitrary spatial unit (scaled from original coordinates if needed).
- Systems placed at `(x, y, z)` scaled (configurable factor, default 10^-18 = 1e-18).
- Collections: `Frontier` with nested hierarchy `Frontier/<Region>/<Constellation>/<Systems>` enabled by default (toggle in preferences: "Hierarchy (Region/Constellation)"). Disable the toggle for a flat list.

## 🎨 Visualization Concepts

| Concept | Example Mapping |
|---------|-----------------|
| First char of name | Hue via HSV index (A→0°, Z→~360°) |
| Count of children (planets, moons) | (Future) attribute-driven emission scaling |
| Hierarchy depth | Gradient emission or outline |
| Orbital index | Saturation or value shift |

## 🧪 Testing & Dev Loop

- Use `scripts/dev_reload.py` inside Blender's text editor to quickly reload the add-on after changes.
- Add pytest-style offline tests for data parsing (pure Python, no Blender) in a `/tests` folder.

## 📦 Roadmap (Initial)

- [ ] Implement base add-on registration
- [ ] Add preferences for DB path & scale
- [ ] Implement data loader with caching
- [ ] Scene builder with collections & parenting
- [ ] Basic shader strategies (NamePatternCategory, unified nth-char hue)
- [ ] Batch export script
- [ ] Documentation: DATA_MODEL, SHADERS, ARCHITECTURE
- [ ] Add minimal CI to lint Python (flake8 or ruff)

## 🛡 License

MIT

## 🙌 Contributions

PRs welcome—focus on: new shader strategies, performance improvements (bulk bmesh, instancing), better color ramps.

## ⚙ Preference Highlights (Shading)

| Preference | Effect |
|------------|--------|
| Emission Strength Scale | Global multiplier for per-object emission values used by the attribute-driven material |

## ❓ Troubleshooting

| Issue | Fix |
|-------|-----|
| Add-on not visible | Check folder structure: the `__init__.py` must define `bl_info`. |
| DB not found | Set correct path in preferences or ensure relative placement. |
| Scene rebuild slow | Enable caching in loader or reduce dataset slice while prototyping. |
| Materials all gray | Ensure chosen visualization mode implements `build()` correctly and registers. |

## 🙏 Acknowledgements

## 📦 Releases & Packaging

Two quick ways to build the add-on zip locally:

### Make (Linux/macOS / Git Bash)

```sh
make build
```

Outputs: `dist/eve_frontier_visualizer-<version>.zip`

### PowerShell (Windows)

```powershell
./build_addon.ps1
```

Or override the file name:

```powershell
./build_addon.ps1 -Name custom.zip
```

### Python Direct

```sh
python blender_addon/scripts/build_addon.py
```

### Publishing a Release

1. Update version in `blender_addon/pyproject.toml`.
2. Commit the change.
3. Tag it: `git tag v<version>` (or `make release`).
4. Push tag: `git push origin v<version>`.
5. GitHub Actions builds zip & attaches it to a GitHub Release automatically.

Artifacts live under `dist/` and contain the top-level `addon/` folder suitable for Blender installation.

These visualizations would not have been possible without the work of the following individuals and organizations:

- **CCP Games**: for taking the time and brain space to build something meaningful.
- **Amber Goose**: for their original conceptual that the letters meant something.
- **Reapers Tribe**: for putting up with my rambling and being a sounding board for ideas.
- **ProtoDroidBot**: for doing the leg work in extracting the data from the client.
- **Lacal**: for identifying the Rx-90 transformation required to normalize the coordinate system.
- **Space Spheremaps**: for their awesome [space spheremaps](https://www.spacespheremaps.com)

---
Happy visualizing!
