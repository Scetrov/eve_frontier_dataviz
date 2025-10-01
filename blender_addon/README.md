# EVE Frontier 3D Data Visualizer (Blender Add-on)

This repository contains a Blender add-on and supporting scripts to visualize astronomical / game world data stored extracted from [the EVE Frontier Client](https://github.com/frontier-reapers/Phobos/tree/fsdbinary-t1) inside a 3D scene. It focuses on representing systems, planets, moons, stations, and other entities with procedural shaders that encode metrics (counts, categorical codes, characters of names) into colors, emission, shape modifiers, or geometry node inputs.

## ✨ Core Goals

- Read data from a large SQLite database, while remaining separate from it so as not to commit a 30MB file to Git.
- Transform raw rows (systems, planets, moons, etc.) into a normalized in-memory scene graph.
- Instantiate Solar Systems as Blender objects in collections.
- Provide multiple **visualization modes** ("shaders") to map attributes (e.g. first letter of system name, orbital count) to material properties.
- Offer an extensible plug-in style registry for adding new shader strategies.
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
      operators.py        – Operators: load data, build scene, apply shader
      panels.py           – UI panel (N‑panel) integrating operators
      shader_registry.py  – Strategy registry + base class
      shaders_builtin.py  – Built-in visualization strategies
  docs/
    ARCHITECTURE.md       – Layer boundaries & design notes
    DATA_MODEL.md         – Database tables / dataclass mapping
    SHADERS.md            – Strategy contract & examples
  scripts/
    dev_reload.py         – Helper to reload add-on inside Blender session
    export_batch.py       – Example headless export / batch script
    markdown_lint.py      – Minimal Markdown formatting linter
  shaders/                – (Placeholder for external .blend / node assets)
  tests/
    conftest.py           – Adds src path for imports
    fixtures/mini.db.sql  – Tiny SQLite schema + seed data for tests
    test_data_loader.py   – Loader hierarchy & cache tests
    test_data_state.py    – In‑memory state tests
```

Not (yet) present: `scene_builder.py`, geometry node assets, or planet/moon object instancing (the scene currently creates only system objects with planet/moon counts stored as custom properties).

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
2. Click "Load / Refresh Data" to parse and cache entities.
3. Click "Build Scene" to instantiate objects.
4. Choose a Visualization Mode (e.g. `NameFirstCharHue`, `HierarchyDepthGlow`).
5. Press "Apply Shader" to update materials.
6. (Optional) Run batch export:

```sh
blender -b your_scene.blend -P scripts/export_batch.py -- --modes NameFirstCharHue HierarchyDepthGlow
```

## 🧩 Adding a New Shader Strategy

1. Create a subclass of `BaseShaderStrategy` in `shader_registry.py` or a new module.
2. Implement:

   ```python
   id = "MyStrategy"
   label = "My Custom Strategy"
   attributes = ["uses_name", "uses_counts"]

   def build(self, context, objects):
       # assign or update materials on provided objects
   ```

3. Register it via the `register_strategy()` call or decorator.
4. Document it in `docs/SHADERS.md`.

## 🗃 Data Expectations

The database is assumed to be SQLite with tables resembling:

- `systems(id, name, x, y, z, security)`
- `planets(id, system_id, name, orbit_index, planet_type)`
- `moons(id, planet_id, name, orbit_index)`
(Extend as needed; define canonical mapping in `DATA_MODEL.md`.)

## 🏗 Scene Construction Conventions

- Units: 1 Blender unit == 1 arbitrary spatial unit (scaled from original coordinates if needed).
- Systems placed at `(x, y, z)` possibly scaled (configurable factor, default 0.001).
- Collections: `EVE_Systems`

## 🎨 Visualization Concepts

| Concept | Example Mapping |
|---------|-----------------|
| First char of name | Hue via HSV index (A→0°, Z→~360°) |
| Count of children (planets, moons) | Emission strength / size |
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
- [ ] Basic shader strategies (NameFirstCharHue, ChildCountEmission)
- [ ] Batch export script
- [ ] Documentation: DATA_MODEL, SHADERS, ARCHITECTURE
- [ ] Add minimal CI to lint Python (flake8 or ruff)

## 🛡 License

MIT

## 🙌 Contributions

PRs welcome—focus on: new shader strategies, performance improvements (bulk bmesh, instancing), better color ramps.

## ❓ Troubleshooting

| Issue | Fix |
|-------|-----|
| Add-on not visible | Check folder structure: the `__init__.py` must define `bl_info`. |
| DB not found | Set correct path in preferences or ensure relative placement. |
| Scene rebuild slow | Enable caching in loader or reduce dataset slice while prototyping. |
| Materials all gray | Ensure chosen visualization mode implements `build()` correctly and registers. |

## 🙏 Acknowledgements

These visualizations would not have been possible without the work of the following individuals and organizations:

- **CCP Games**: for taking the time and brain space to build something meaningful.
- **Amber Goose**: for their original conceptual that the letters meant something.
- **Reapers Tribe**: for putting up with my rambling and being a sounding board for ideas.
- **ProtoDroidBot**: for doing the leg work in extracting the data from the client.

---
Happy visualizing!
