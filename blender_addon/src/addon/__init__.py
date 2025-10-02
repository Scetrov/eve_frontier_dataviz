bl_info = {
    "name": "EVE Frontier: Data Visualizer",
    "author": "Scetrov",
    "version": (0, 1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > EVE Frontier",
    "description": "Visualize EVE Frontier static.db data with procedural shader strategies.",
    "category": "Import-Export",
}

import importlib  # noqa: E402
import traceback  # noqa: E402

_loaded_modules = []  # populated at register time to support unregister & reload


def _load_modules():  # lazy import to avoid bpy dependency in pure-Python tests
    global _loaded_modules
    if _loaded_modules:
        return _loaded_modules
    module_names = [
        "preferences",
        "operators",  # now a package with submodules
        "panels",
        "shader_registry",
        "shaders_builtin",
        # shader strategy modules
        "shaders.name_pattern_category",
        "shaders.name_nth_char_hue",  # unified nth-char + alias for NameFirstCharHue
    ]
    mods = []
    for name in module_names:
        try:
            mods.append(importlib.import_module(f"{__package__}.{name}"))
        except Exception as e:  # pragma: no cover - Blender runtime diagnostics
            print(f"[EVEVisualizer][error] Failed importing '{name}': {e}")
            traceback.print_exc()
    _loaded_modules = mods
    return _loaded_modules


def reload_modules():  # for dev reload (inside Blender only)
    mods = _load_modules()
    for m in mods:
        importlib.reload(m)


def register():
    try:
        mods = _load_modules()
        for m in mods:
            if hasattr(m, "register"):
                try:
                    m.register()
                except Exception as e:  # pragma: no cover - runtime diagnostics
                    print(f"[EVEVisualizer][error] register() failed in {m.__name__}: {e}")
                    traceback.print_exc()
        if not mods:
            print("[EVEVisualizer][warn] No modules loaded; preferences panel will be blank.")
    except Exception as e:  # pragma: no cover
        print(f"[EVEVisualizer][fatal] Top-level register failed: {e}")
        traceback.print_exc()


def unregister():
    try:
        mods = list(reversed(_load_modules()))
        for m in mods:
            if hasattr(m, "unregister"):
                try:
                    m.unregister()
                except Exception as e:  # pragma: no cover - runtime diagnostics
                    print(f"[EVEVisualizer][error] unregister() failed in {m.__name__}: {e}")
    except Exception as e:  # pragma: no cover
        print(f"[EVEVisualizer][fatal] Top-level unregister failed: {e}")
