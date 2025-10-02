"""Data related operators (load & clear)."""

from __future__ import annotations

import os

try:  # pragma: no cover  # noqa: I001 (dynamic bpy import grouping)
    import bpy  # type: ignore
except Exception:  # noqa: BLE001
    bpy = None  # type: ignore

from .. import data_state
from ..data_loader import load_data
from ..preferences import get_prefs
from ._shared import clear_generated

if bpy:  # Only define classes when Blender API is present

    class EVE_OT_clear_scene(bpy.types.Operator):  # type: ignore
        bl_idname = "eve.clear_scene"
        bl_label = "Clear Scene"
        bl_description = "Remove all generated collections and objects"

        def execute(self, context):  # noqa: D401
            removed_objs, removed_colls = clear_generated()
            if removed_colls == 0:
                self.report({"INFO"}, "Nothing to clear")
            else:
                self.report(
                    {"INFO"}, f"Cleared {removed_objs} objects ({removed_colls} collections)"
                )
            return {"FINISHED"}

    class EVE_OT_load_data(bpy.types.Operator):  # type: ignore
        bl_idname = "eve.load_data"
        bl_label = "Load / Refresh Data"
        bl_description = "Load data from configured SQLite DB"

        limit_systems: bpy.props.IntProperty(  # type: ignore[valid-type]
            name="Limit Systems",
            default=0,
            min=0,
            description="If > 0, only load this many systems (dev/testing)",
        )

        def execute(self, context):  # noqa: D401
            prefs = get_prefs(context)
            db_path = prefs.db_path
            if not os.path.exists(db_path):
                self.report({"ERROR"}, f"DB not found: {db_path}")
                return {"CANCELLED"}
            limit_val = int(getattr(self, "limit_systems", 0) or 0)
            limit_arg = limit_val if limit_val > 0 else None
            try:
                systems = load_data(db_path, limit_systems=limit_arg)
            except Exception as e:  # noqa: BLE001
                self.report({"ERROR"}, f"Load failed: {e}")
                return {"CANCELLED"}
            data_state.set_loaded_systems(systems)
            total_planets = sum(len(s.planets) for s in systems)
            total_moons = sum(len(p.moons) for s in systems for p in s.planets)
            self.report(
                {"INFO"},
                f"Loaded {len(systems)} systems / {total_planets} planets / {total_moons} moons",
            )
            return {"FINISHED"}


def register():  # pragma: no cover
    if not bpy:
        return
    bpy.utils.register_class(EVE_OT_clear_scene)
    bpy.utils.register_class(EVE_OT_load_data)


def unregister():  # pragma: no cover
    if not bpy:
        return
    bpy.utils.unregister_class(EVE_OT_load_data)
    bpy.utils.unregister_class(EVE_OT_clear_scene)
