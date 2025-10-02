"""Asynchronous scene build operator.

Only systems are instantiated (planets/moons counts kept as custom props).
"""

from __future__ import annotations

import random

try:  # pragma: no cover  # noqa: I001 (dynamic bpy import grouping)
    import bmesh  # type: ignore
    import bpy  # type: ignore
except Exception:  # noqa: BLE001
    bpy = None  # type: ignore
    bmesh = None  # type: ignore


from .. import data_state
from ..preferences import get_prefs
from ._shared import clear_generated, get_or_create_collection


def _ensure_mesh(kind: str, r: float):  # pragma: no cover
    if not bpy:
        return None
    key = f"EVE_SYS_{kind}_{int(r*1000)}"
    mesh = bpy.data.meshes.get(key)
    if mesh:
        return mesh
    mesh = bpy.data.meshes.new(key)
    if bmesh:
        bm = bmesh.new()
        if kind == "ICO":
            bmesh.ops.create_icosphere(bm, subdivisions=1, radius=r)
        else:
            bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=r)
        bm.to_mesh(mesh)
        bm.free()
    return mesh


if bpy:

    class EVE_OT_build_scene_modal(bpy.types.Operator):  # type: ignore
        bl_idname = "eve.build_scene_modal"
        bl_label = "Build Scene (Async)"
        bl_description = "Instantiate systems asynchronously"

        batch_size: bpy.props.IntProperty(  # type: ignore[valid-type]
            name="Batch Size", default=2500, min=100, max=100000
        )
        clear_previous: bpy.props.BoolProperty(  # type: ignore[valid-type]
            name="Clear Previous", default=True
        )

        _systems = None
        _index = 0
        _total = 0
        _timer = None
        _mesh = None
        _radius = 2.0
        _scale = 1.0
        _apply_axis = False

        def _init(self, context):
            systems = data_state.get_loaded_systems()
            if not systems:
                self.report({"ERROR"}, "No data loaded")
                return False
            prefs = get_prefs(context)
            pct = float(getattr(prefs, "build_percentage", 1.0) or 1.0)
            pct = max(0.01, min(1.0, pct))
            if pct < 0.9999:
                # reproducible slice using deterministic shuffle copy
                subset = systems[:]
                random.Random(42).shuffle(subset)
                take = max(1, int(len(subset) * pct))
                systems = subset[:take]
            self._systems = systems
            self._total = len(systems)
            self._radius = float(getattr(prefs, "system_point_radius", 2.0) or 2.0)
            self._scale = float(getattr(prefs, "scale_factor", 1.0) or 1.0)
            self._apply_axis = bool(getattr(prefs, "apply_axis_transform", False))
            if self.clear_previous:
                clear_generated()
            coll = get_or_create_collection("EVE_Systems")
            if coll:
                coll.hide_viewport = True
            self._mesh = _ensure_mesh("ICO", self._radius)
            wm = context.window_manager
            wm.eve_build_in_progress = True
            wm.eve_build_progress = 0.0
            wm.eve_build_total = self._total
            wm.eve_build_created = 0
            wm.eve_build_mode = "ICO_INST"
            return True

        def _finish(self, context, cancelled=False):
            wm = context.window_manager
            wm.eve_build_in_progress = False
            if cancelled:
                self.report({"WARNING"}, "Build cancelled")
            else:
                self.report({"INFO"}, f"Scene built with {wm.eve_build_created} systems")
            coll = bpy.data.collections.get("EVE_Systems")
            if coll:
                coll.hide_viewport = False

        def execute(self, context):  # noqa: D401
            if not self._init(context):
                return {"CANCELLED"}
            self._timer = context.window_manager.event_timer_add(0.01, window=context.window)
            context.window_manager.modal_handler_add(self)
            return {"RUNNING_MODAL"}

        def modal(self, context, event):  # noqa: D401
            if event.type == "TIMER":
                batch_end = min(self._index + self.batch_size, self._total)
                coll = bpy.data.collections.get("EVE_Systems")  # type: ignore[union-attr]
                created = 0
                for i in range(self._index, batch_end):
                    sys = self._systems[i]
                    x, y, z = sys.x * self._scale, sys.y * self._scale, sys.z * self._scale
                    if self._apply_axis:  # Rx-90 transformation (X,Y,Z) -> (X,Z,-Y)
                        x, y, z = x, z, -y
                    obj = bpy.data.objects.new(sys.name or f"System_{i}", self._mesh)  # type: ignore[union-attr]
                    obj.location = (x, y, z)
                    obj["planet_count"] = len(sys.planets)
                    obj["moon_count"] = sum(len(p.moons) for p in sys.planets)
                    if coll:
                        coll.objects.link(obj)
                    created += 1
                self._index = batch_end
                wm = context.window_manager
                wm.eve_build_created += created
                wm.eve_build_progress = self._index / self._total if self._total else 1.0
                if self._index >= self._total:
                    context.window_manager.event_timer_remove(self._timer)
                    self._finish(context)
                    return {"FINISHED"}
            return {"RUNNING_MODAL"}

    class EVE_OT_cancel_build(bpy.types.Operator):  # type: ignore
        bl_idname = "eve.cancel_build"
        bl_label = "Cancel Build"
        bl_description = "Cancel the asynchronous build"

        def execute(self, context):  # noqa: D401
            wm = context.window_manager
            if getattr(wm, "eve_build_in_progress", False):
                wm.eve_build_in_progress = False
                self.report({"INFO"}, "Cancellation requested (may finish current batch)")
            else:
                self.report({"INFO"}, "No build in progress")
            return {"FINISHED"}


def register():  # pragma: no cover
    if not bpy:
        return
    bpy.utils.register_class(EVE_OT_build_scene_modal)
    bpy.utils.register_class(EVE_OT_cancel_build)
    # Progress properties on WindowManager (created once)
    wm = bpy.types.WindowManager
    if not hasattr(wm, "eve_build_in_progress"):
        wm.eve_build_in_progress = bpy.props.BoolProperty(default=False)  # type: ignore
    if not hasattr(wm, "eve_build_progress"):
        wm.eve_build_progress = bpy.props.FloatProperty(default=0.0)  # type: ignore
    if not hasattr(wm, "eve_build_total"):
        wm.eve_build_total = bpy.props.IntProperty(default=0)  # type: ignore
    if not hasattr(wm, "eve_build_created"):
        wm.eve_build_created = bpy.props.IntProperty(default=0)  # type: ignore
    if not hasattr(wm, "eve_build_mode"):
        wm.eve_build_mode = bpy.props.StringProperty(default="")  # type: ignore


def unregister():  # pragma: no cover
    if not bpy:
        return
    bpy.utils.unregister_class(EVE_OT_cancel_build)
    bpy.utils.unregister_class(EVE_OT_build_scene_modal)
