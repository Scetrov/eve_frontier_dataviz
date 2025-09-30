# EVE Frontier 3D Data Visualizer (Blender Add-on)

This repository contains a Blender add-on and supporting scripts to visualize astronomical / game world data stored in `data/static.db` inside a 3D scene. It focuses on representing systems, planets, moons, stations, and other entities with procedural shaders that encode metrics (counts, categorical codes, characters of names) into colors, emission, shape modifiers, or geometry node inputs.

## ✨ Core Goals

- Parse a large SQLite database (`static.db`) without committing it to version control.
- Transform raw rows (systems, planets, moons, etc.) into a normalized in-memory scene graph.
- Instantiate Blender objects in collections (e.g. `Systems`, `Planets`, `Moons`).
- Provide multiple **visualization modes** ("shaders") to map attributes (e.g. first letter of system name, population, hierarchy depth, orbital count) to material properties.
- Offer an extensible plug-in style registry for adding new shader strategies.
- Allow batch re-render/export (stills or animation) via command line (headless `blender --background`).

## 🗂 Project Structure

```tree
blender_addon/
  README.md                -> Project overview & usage
  copilot-instructions.md  -> Guidance for AI pair-programming
  .gitignore               -> Excludes large / generated artifacts
  addon/
    __init__.py            -> Blender add-on entry (register classes/menus)
    preferences.py         -> Add-on preferences (e.g. path to static.db)
    operators.py           -> Custom operators (load data, build scene, apply shader)
    panels.py              -> UI panels in the 3D Viewport / N panel
    data_loader.py         -> SQLite access & transformation to Python objects
    scene_builder.py       -> Creates collections & objects
    shader_registry.py     -> Registry & base class for visualization strategies
    shaders_builtin.py     -> Example shader strategies
    materials.py           -> Material creation helpers
    utils.py               -> Shared helpers (logging, caching, color ramps)
  shaders/
    examples/              -> Optional external node groups / .blend assets
  scripts/
    export_batch.py        -> Example headless rendering script
    dev_reload.py          -> Utility to reload add-on during dev
  docs/
    ARCHITECTURE.md        -> Deeper technical design
    SHADERS.md             -> Document visualization modes
    DATA_MODEL.md          -> Describe DB tables & mapped entities
```

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
- Planets parented to their system empty; moons parented to planet empty.
- Collections: `EVE_Systems`, `EVE_Planets`, `EVE_Moons`.

## 🎨 Visualization Concepts

| Concept | Example Mapping |
|---------|-----------------|
| First char of name | Hue via HSV index (A→0°, Z→~360°) |
| Count of children (planets, moons) | Emission strength / size |
| Security / type | Color ramp or discrete material |
| Hierarchy depth | Gradient emission or outline |
| Orbital index | Saturation or value shift |

## 🧪 Testing & Dev Loop

- Use `scripts/dev_reload.py` inside Blender's text editor to quickly reload the add-on after changes.
- (Future) Add pytest-style offline tests for data parsing (pure Python, no Blender) in a `/tests` folder.

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

---
Happy visualizing!
