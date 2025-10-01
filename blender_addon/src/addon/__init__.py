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

_loaded_modules = []  # populated at register time to support unregister & reload


def _load_modules():  # lazy import to avoid bpy dependency in pure-Python tests
    global _loaded_modules
    if _loaded_modules:
        return _loaded_modules
    from . import operators, panels, preferences, shader_registry, shaders_builtin  # noqa: F401

    _loaded_modules = [preferences, operators, panels, shader_registry, shaders_builtin]
    return _loaded_modules


def reload_modules():  # for dev reload (inside Blender only)
    mods = _load_modules()
    for m in mods:
        importlib.reload(m)


def register():
    mods = _load_modules()
    for m in mods:
        if hasattr(m, "register"):
            m.register()


def unregister():
    mods = list(reversed(_load_modules()))
    for m in mods:
        if hasattr(m, "unregister"):
            m.unregister()
