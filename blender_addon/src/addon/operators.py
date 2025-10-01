import os

import bmesh
import bpy
from bpy.types import Operator

from . import data_state
from .data_loader import load_data
from .preferences import get_prefs
from .shader_registry import get_strategies, get_strategy

_generated_collection_names = ["EVE_Systems", "EVE_Planets", "EVE_Moons"]


def _get_or_create_collection(name: str):  # pragma: no cover - Blender runtime usage
    coll = bpy.data.collections.get(name)
    if not coll:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll


def _clear_generated():  # pragma: no cover - Blender runtime usage
    prev_undo = bpy.context.preferences.edit.use_global_undo
    bpy.context.preferences.edit.use_global_undo = False
    try:
        for cname in _generated_collection_names:
            coll = bpy.data.collections.get(cname)
            if not coll:
                continue
            coll.hide_viewport = True
            objs = list(coll.objects)
            if objs:
                # Try batch removal for speed (Blender 3.6+/4.x); fallback to loop if unavailable
                try:
                    bpy.data.batch_remove(objs)  # type: ignore[attr-defined]
                except Exception:
                    for o in objs:
                        bpy.data.objects.remove(o, do_unlink=True)
            # Unlink & remove collection
            for scene in list(bpy.data.scenes):
                if coll.name in scene.collection.children:
                    try:
                        scene.collection.children.unlink(coll)
                    except Exception:
                        pass
            try:
                bpy.data.collections.remove(coll)
            except Exception:
                pass
    finally:
        bpy.context.preferences.edit.use_global_undo = prev_undo


class EVE_OT_clear_scene(Operator):
    bl_idname = "eve.clear_scene"
    bl_label = "Clear Scene"
    bl_description = "Remove all generated EVE collections and their objects"

    def execute(self, context):  # noqa: D401
        removed_objs = 0
        removed_colls = 0
        prev_undo = bpy.context.preferences.edit.use_global_undo
        bpy.context.preferences.edit.use_global_undo = False
        try:
            for cname in _generated_collection_names:
                coll = bpy.data.collections.get(cname)
                if not coll:
                    continue
                coll.hide_viewport = True
                objs = list(coll.objects)
                removed_objs += len(objs)
                if objs:
                    try:
                        bpy.data.batch_remove(objs)  # type: ignore[attr-defined]
                    except Exception:
                        for o in objs:
                            bpy.data.objects.remove(o, do_unlink=True)
                for scene in list(bpy.data.scenes):
                    if coll.name in scene.collection.children:
                        try:
                            scene.collection.children.unlink(coll)
                        except Exception:
                            pass
                try:
                    bpy.data.collections.remove(coll)
                except Exception:
                    pass
                removed_colls += 1
        finally:
            bpy.context.preferences.edit.use_global_undo = prev_undo
        if removed_colls == 0:
            self.report({"INFO"}, "Nothing to clear")
            return {"CANCELLED"}
        self.report({"INFO"}, f"Cleared {removed_objs} objects ({removed_colls} collections)")
        return {"FINISHED"}


class EVE_OT_load_data(Operator):
    bl_idname = "eve.load_data"
    bl_label = "Load / Refresh Data"
    bl_description = "Load data from the configured SQLite database"

    limit_systems = bpy.props.IntProperty(
        name="Limit Systems",
        default=0,
        min=0,
        description="If > 0, only load this many systems (dev/testing)",
    )

    def execute(self, context):  # noqa: D401
        prefs = get_prefs(context)
        db_path = prefs.db_path
        if not os.path.exists(db_path):
            self.report({"ERROR"}, f"Database not found: {db_path}")
            return {"CANCELLED"}

        # Blender reload edge case: IntProperty may present as _PropertyDeferred until accessed.
        raw_limit = getattr(self, "limit_systems", 0)
        try:
            coerced_limit = int(raw_limit) if raw_limit else 0
        except Exception:  # pragma: no cover - fallback
            coerced_limit = 0
        limit_arg = coerced_limit or None

        try:
            systems = load_data(
                db_path,
                limit_systems=limit_arg,
                enable_cache=prefs.enable_cache,
            )
        except Exception as e:  # pragma: no cover - defensive
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


class EVE_OT_build_scene(Operator):
    bl_idname = "eve.build_scene"
    bl_label = "Build Scene"
    bl_description = "Build or rebuild the scene from loaded data"
    clear_previous = bpy.props.BoolProperty(name="Clear Previous", default=True)

    def execute(self, context):  # noqa: D401
        systems_data = data_state.get_loaded_systems()
        if not systems_data:
            prefs = get_prefs(context)
            if not os.path.exists(prefs.db_path):
                self.report({"ERROR"}, "No data loaded and database path invalid")
                return {"CANCELLED"}
            try:
                systems_data = load_data(prefs.db_path, enable_cache=prefs.enable_cache)
                data_state.set_loaded_systems(systems_data)
            except Exception as e:  # pragma: no cover
                self.report({"ERROR"}, f"Auto-load failed: {e}")
                return {"CANCELLED"}

        prefs = get_prefs(context)
        scale = prefs.scale_factor
        apply_axis = getattr(prefs, "apply_axis_transform", False)

        if self.clear_previous:
            _clear_generated()
        systems_coll = _get_or_create_collection("EVE_Systems")

        # Temporarily hide collection & disable undo for speed
        prev_undo = bpy.context.preferences.edit.use_global_undo
        bpy.context.preferences.edit.use_global_undo = False
        prev_hide_view = systems_coll.hide_viewport
        systems_coll.hide_viewport = True

        created = 0
        radius = getattr(prefs, "system_point_radius", 2.0)
        bh_scale_mult = getattr(prefs, "blackhole_scale_multiplier", 3.0)
        pct = getattr(prefs, "build_percentage", 1.0)
        representation = getattr(prefs, "system_representation", "SPHERE")
        try:
            pct = float(pct)
        except Exception:
            pct = 1.0
        if pct <= 0:
            pct = 0.01
        if pct > 1:
            pct = 1.0

        # Optional exclusions
        excl_ad = getattr(prefs, "exclude_ad_systems", False)
        excl_vdash = getattr(prefs, "exclude_vdash_systems", False)
        if excl_ad or excl_vdash:
            filtered = []
            for s in systems_data:
                nm = s.name or ""
                if excl_ad and len(nm) == 5 and nm.startswith("AD") and nm[2:].isdigit():
                    continue
                if excl_vdash and len(nm) == 5 and nm.startswith("V-") and nm[2:].isdigit():
                    continue
                filtered.append(s)
            systems_data = filtered

        systems_iter = systems_data
        if pct < 0.9999:
            # Uniform down-sampling by index stride
            target = max(1, int(len(systems_data) * pct))
            stride = max(1, len(systems_data) // target)
            systems_iter = [s for i, s in enumerate(systems_data) if i % stride == 0][:target]
        # Clamp radius defensively
        try:
            radius = max(0.01, float(radius))
        except Exception:
            radius = 2.0

        # --- Mesh template helpers ---
        def _ensure_mesh(kind: str, r: float, inst: bool) -> bpy.types.Mesh:
            suffix = "INST" if inst else "TPL"
            key = f"EVE_{kind}_{int(r*1000)}_{suffix}"
            m = bpy.data.meshes.get(key)
            if m:
                return m
            m = bpy.data.meshes.new(key)
            bm = bmesh.new()
            if kind == "ICO":
                bmesh.ops.create_icosphere(bm, subdivisions=1, radius=r)
            else:  # SPHERE
                bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=6, diameter=r * 2)
            bm.to_mesh(m)
            bm.free()
            return m

        instanced = representation in {"ICO_INST", "SPHERE_INST"}
        base_kind = None
        if representation.startswith("ICO"):
            base_kind = "ICO"
        elif representation.startswith("SPHERE"):
            base_kind = "SPHERE"

        shared_mesh = None
        if instanced and base_kind:
            shared_mesh = _ensure_mesh(base_kind, radius, True)

        for idx, sys in enumerate(systems_iter):
            name = sys.name or f"System_{sys.id}"
            is_blackhole = name in {"A 2560", "M 974", "U 3183"}
            if representation == "EMPTY":
                obj = bpy.data.objects.new(name, None)
                obj.empty_display_type = "PLAIN_AXES"
                obj.empty_display_size = radius * (bh_scale_mult if is_blackhole else 1.0)
                systems_coll.objects.link(obj)
            elif instanced and shared_mesh:
                obj = bpy.data.objects.new(name, shared_mesh)
                systems_coll.objects.link(obj)
            else:
                # Non-instanced mesh: copy from template mesh (faster than ops)
                tpl_mesh = _ensure_mesh(base_kind or "SPHERE", radius, False)
                obj = bpy.data.objects.new(name, tpl_mesh.copy())
                systems_coll.objects.link(obj)
                if is_blackhole:
                    # Uniform scale after creation (avoid duplicating mesh variants)
                    try:
                        obj.scale = (bh_scale_mult, bh_scale_mult, bh_scale_mult)
                    except Exception:
                        pass

            if idx and idx % 5000 == 0:
                self.report({"INFO"}, f"Placed {idx:,} systems...")
            if apply_axis:
                # (x,y,z)->(x,z,-y): rotate -90° about X to convert Z-up -> Y-up
                obj.location = (sys.x * scale, sys.z * scale, -sys.y * scale)
            else:
                obj.location = (sys.x * scale, sys.y * scale, sys.z * scale)
            planet_count = len(sys.planets)
            moon_count = sum(len(p.moons) for p in sys.planets)
            obj["planet_count"] = planet_count
            obj["moon_count"] = moon_count
            created += 1

        # Restore collection visibility & undo
        systems_coll.hide_viewport = prev_hide_view
        bpy.context.preferences.edit.use_global_undo = prev_undo

        self.report(
            {"INFO"},
            f"Scene built with {created} systems (sample={pct:.2%}, mode={representation}, inst={'yes' if instanced else 'no'})",
        )
        return {"FINISHED"}


class EVE_OT_build_scene_modal(Operator):  # pragma: no cover - Blender runtime usage
    bl_idname = "eve.build_scene_modal"
    bl_label = "Build Scene (Async)"
    bl_description = "Asynchronously build the scene in batches to keep UI responsive"

    batch_size: bpy.props.IntProperty(  # type: ignore[valid-type]
        name="Batch Size",
        default=2500,
        min=100,
        max=100000,
        description="Systems instantiated per modal step",
    )
    clear_previous: bpy.props.BoolProperty(  # type: ignore[valid-type]
        name="Clear Previous",
        default=True,
    )

    _systems_iter = None
    _systems_total = 0
    _created = 0
    _shared_mesh = None
    _instanced = False
    _base_kind = None
    _coll = None
    _apply_axis = False
    _scale = 1.0
    _radius = 2.0
    _representation = "ICO_INST"
    _timer = None

    def _ensure_mesh(self, kind: str, r: float, inst: bool):  # local helper
        suffix = "INST" if inst else "TPL"
        key = f"EVE_{kind}_{int(r*1000)}_{suffix}"
        m = bpy.data.meshes.get(key)
        if m:
            return m
        m = bpy.data.meshes.new(key)
        bm = bmesh.new()
        if kind == "ICO":
            bmesh.ops.create_icosphere(bm, subdivisions=1, radius=r)
        else:
            bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=6, diameter=r * 2)
        bm.to_mesh(m)
        bm.free()
        return m

    def _init_build(self, context):
        # Acquire / load data
        systems_data = data_state.get_loaded_systems()
        if not systems_data:
            prefs = get_prefs(context)
            if not os.path.exists(prefs.db_path):
                self.report({"ERROR"}, "No data loaded and database path invalid")
                return False
            try:
                systems_data = load_data(prefs.db_path, enable_cache=prefs.enable_cache)
                data_state.set_loaded_systems(systems_data)
            except Exception as e:
                self.report({"ERROR"}, f"Auto-load failed: {e}")
                return False

        prefs = get_prefs(context)
        self._scale = getattr(prefs, "scale_factor", 1.0)
        self._apply_axis = getattr(prefs, "apply_axis_transform", False)
        self._radius = max(0.01, float(getattr(prefs, "system_point_radius", 2.0)))
        self._bh_scale_mult = float(getattr(prefs, "blackhole_scale_multiplier", 3.0))
        pct = getattr(prefs, "build_percentage", 1.0)
        try:
            pct = float(pct)
        except Exception:
            pct = 1.0
        pct = max(0.01, min(1.0, pct))
        representation = getattr(prefs, "system_representation", "ICO_INST")
        self._representation = representation
        # Apply exclusions if enabled
        excl_ad = getattr(prefs, "exclude_ad_systems", False)
        excl_vdash = getattr(prefs, "exclude_vdash_systems", False)
        if excl_ad or excl_vdash:
            filtered = []
            for s in systems_data:
                nm = s.name or ""
                if excl_ad and len(nm) == 5 and nm.startswith("AD") and nm[2:].isdigit():
                    continue
                if excl_vdash and len(nm) == 5 and nm.startswith("V-") and nm[2:].isdigit():
                    continue
                filtered.append(s)
            systems_data = filtered

        systems_iter = systems_data
        if pct < 0.9999:
            target = max(1, int(len(systems_data) * pct))
            stride = max(1, len(systems_data) // target)
            systems_iter = [s for i, s in enumerate(systems_data) if i % stride == 0][:target]
        self._systems_iter = systems_iter
        self._systems_total = len(systems_iter)

        # Clear previous if requested
        if self.clear_previous:
            _clear_generated()
        self._coll = _get_or_create_collection("EVE_Systems")
        self._coll.hide_viewport = True

        # Determine representation
        self._instanced = representation in {"ICO_INST", "SPHERE_INST"}
        if representation.startswith("ICO"):
            self._base_kind = "ICO"
        elif representation.startswith("SPHERE"):
            self._base_kind = "SPHERE"
        else:
            self._base_kind = None
        if self._instanced and self._base_kind:
            self._shared_mesh = self._ensure_mesh(self._base_kind, self._radius, True)

        # Disable undo for duration
        self._prev_undo = bpy.context.preferences.edit.use_global_undo
        bpy.context.preferences.edit.use_global_undo = False

        wm = context.window_manager
        wm.eve_build_in_progress = True
        wm.eve_build_progress = 0.0
        wm.eve_build_total = self._systems_total
        wm.eve_build_created = 0
        wm.eve_build_mode = representation
        return True

    def _finish(self, context, cancelled=False):
        if self._coll:
            self._coll.hide_viewport = False
        bpy.context.preferences.edit.use_global_undo = getattr(self, "_prev_undo", True)
        wm = context.window_manager
        wm.eve_build_progress = 1.0 if not cancelled else 0.0
        wm.eve_build_in_progress = False
        msg = f"Async build {'cancelled' if cancelled else 'complete'}: {self._created} systems (mode={self._representation}, inst={'yes' if self._instanced else 'no'})"
        self.report({"INFO"}, msg)
        # Remove timer if we added one
        try:
            if self._timer:
                context.window_manager.event_timer_remove(self._timer)
        except Exception:
            pass
        # Force redraw so panel updates and collection shows
        try:
            for area in context.screen.areas:
                area.tag_redraw()
        except Exception:
            pass

    def execute(self, context):  # start modal
        if not self._init_build(context):
            return {"CANCELLED"}
        # Add a timer to guarantee periodic modal callbacks (keeps progress moving without user input)
        try:
            self._timer = context.window_manager.event_timer_add(0.01, window=context.window)
        except Exception:
            self._timer = None
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        wm = context.window_manager
        if event.type == "ESC":  # user pressed escape
            self._finish(context, cancelled=True)
            return {"CANCELLED"}
        if not wm.eve_build_in_progress:
            # External cancel (e.g. cancel operator) – perform cleanup
            self._finish(context, cancelled=True)
            return {"CANCELLED"}
        # If init somehow failed earlier, abort safely
        if self._systems_iter is None or self._coll is None:
            self.report({"ERROR"}, "Build state invalid; aborting")
            wm.eve_build_in_progress = False
            self._finish(context, cancelled=True)
            return {"CANCELLED"}
        # Build a batch each TIMER or redraw event
        if event.type == "TIMER":
            remaining = self._systems_total - self._created
            if remaining <= 0:
                self._finish(context)
                return {"FINISHED"}
            count = min(self.batch_size, remaining)
            start_index = self._created
            systems_slice = (
                self._systems_iter[start_index : start_index + count] if self._systems_iter else []
            )
            for sys in systems_slice:
                name = sys.name or f"System_{sys.id}"
                if self._representation == "EMPTY":
                    obj = bpy.data.objects.new(name, None)
                    obj.empty_display_type = "PLAIN_AXES"
                    obj.empty_display_size = self._radius * (
                        self._bh_scale_mult if name in {"A 2560", "M 974", "U 3183"} else 1.0
                    )
                    if self._coll:
                        self._coll.objects.link(obj)
                elif self._instanced and self._shared_mesh:
                    obj = bpy.data.objects.new(name, self._shared_mesh)
                    if self._coll:
                        self._coll.objects.link(obj)
                else:
                    tpl_mesh = self._ensure_mesh(self._base_kind or "SPHERE", self._radius, False)
                    obj = bpy.data.objects.new(name, tpl_mesh.copy())
                    if self._coll:
                        self._coll.objects.link(obj)
                    if name in {"A 2560", "M 974", "U 3183"}:
                        try:
                            obj.scale = (
                                self._bh_scale_mult,
                                self._bh_scale_mult,
                                self._bh_scale_mult,
                            )
                        except Exception:
                            pass
                if self._apply_axis:
                    obj.location = (sys.x * self._scale, sys.z * self._scale, -sys.y * self._scale)
                else:
                    obj.location = (sys.x * self._scale, sys.y * self._scale, sys.z * self._scale)
                planet_count = len(sys.planets)
                moon_count = sum(len(p.moons) for p in sys.planets)
                obj["planet_count"] = planet_count
                obj["moon_count"] = moon_count
                self._created += 1
            # Update progress
            wm.eve_build_created = self._created
            if self._systems_total > 0:
                wm.eve_build_progress = self._created / self._systems_total
            # Tag redraw so UI progress updates promptly
            try:
                for area in context.screen.areas:
                    if area.type == "VIEW_3D":
                        area.tag_redraw()
            except Exception:
                pass
            return {"RUNNING_MODAL"}
        return {"PASS_THROUGH"}


class EVE_OT_cancel_build(Operator):  # pragma: no cover - Blender runtime usage
    bl_idname = "eve.cancel_build"
    bl_label = "Cancel Build"
    bl_description = "Cancel the asynchronous build in progress"

    def execute(self, context):  # noqa: D401
        wm = context.window_manager
        if getattr(wm, "eve_build_in_progress", False):
            wm.eve_build_in_progress = False
            self.report({"INFO"}, "Cancellation requested")
            try:
                for area in context.screen.areas:
                    area.tag_redraw()
            except Exception:
                pass
            return {"FINISHED"}
        self.report({"WARNING"}, "No build in progress")
        return {"CANCELLED"}


class EVE_OT_cancel_shader(Operator):  # pragma: no cover - Blender runtime usage
    bl_idname = "eve.cancel_shader"
    bl_label = "Cancel Visualization"
    bl_description = "Cancel the asynchronous visualization (shader) application in progress"

    def execute(self, context):  # noqa: D401
        wm = context.window_manager
        if getattr(wm, "eve_shader_in_progress", False):
            wm.eve_shader_in_progress = False
            self.report({"INFO"}, "Shader apply cancellation requested")
            try:
                for area in context.screen.areas:
                    area.tag_redraw()
            except Exception:
                pass
            return {"FINISHED"}
        self.report({"WARNING"}, "No shader application in progress")
        return {"CANCELLED"}


def _strategy_items(self, context):  # pragma: no cover - Blender runtime usage
    try:
        return [(s.id, s.label, "") for s in get_strategies()] or [("__none__", "None", "")]
    except Exception:
        return [("__error__", "(error)", "Failed to enumerate strategies")]


class EVE_OT_apply_shader(Operator):
    bl_idname = "eve.apply_shader"
    bl_label = "Apply Visualization"
    bl_description = "Apply selected shader strategy to generated objects"

    # Proper EnumProperty declaration (annotation only) to avoid _PropertyDeferred leakage on reload.
    strategy_id: bpy.props.EnumProperty(  # type: ignore[valid-type]
        name="Strategy",
        description="Shader / visualization strategy to apply",
        items=_strategy_items,
    )

    def execute(self, context):  # noqa: D401
        objs_by_type = {"systems": []}
        for cname in _generated_collection_names:
            coll = bpy.data.collections.get(cname)
            if not coll:
                continue
            if cname == "EVE_Systems":
                objs_by_type["systems"].extend(coll.objects)
        # Resolve selected strategy id; handle reload edge cases where EnumProperty is still deferred.
        # Prefer global dropdown selection if present
        wm = context.window_manager
        sid = None
        sid_wm = getattr(wm, "eve_strategy_id", None)
        if isinstance(sid_wm, str) and sid_wm not in {"__none__", "__error__"}:
            sid = sid_wm
        else:
            sid = getattr(self, "strategy_id", None)
        if not isinstance(sid, str) or sid in {"__none__", "__error__"}:
            # Pick first available strategy as fallback
            strats = get_strategies()
            if strats:
                sid = strats[0].id
            else:
                self.report({"ERROR"}, "No strategies registered")
                return {"CANCELLED"}
        strat = get_strategy(sid)
        if not strat:
            self.report({"ERROR"}, f"Strategy {sid} not found")
            return {"CANCELLED"}
        self.strategy_id = sid  # persist chosen id
        strat.build(context, objs_by_type)
        self.report({"INFO"}, f"Applied {sid}")
        return {"FINISHED"}


class EVE_OT_apply_shader_modal(Operator):  # pragma: no cover - Blender runtime usage
    bl_idname = "eve.apply_shader_modal"
    bl_label = "Apply Visualization (Async)"
    bl_description = "Apply selected shader strategy asynchronously in batches"

    batch_size: bpy.props.IntProperty(  # type: ignore[valid-type]
        name="Batch Size",
        default=5000,
        min=100,
        max=100000,
        description="Objects shaded per modal tick",
    )
    strategy_id: bpy.props.StringProperty(  # type: ignore[valid-type]
        name="Strategy Id",
        default="",
        description="Strategy to apply (leave blank to use panel selection)",
    )

    _objects = None
    _index = 0
    _total = 0
    _timer = None
    _strategy = None

    def _gather(self, context):
        objs = []
        coll = bpy.data.collections.get("EVE_Systems")
        if coll:
            objs.extend(coll.objects)
        return objs

    def _resolve_strategy(self, context):
        sid = self.strategy_id.strip() or getattr(context.window_manager, "eve_strategy_id", "")
        if not sid:
            strats = get_strategies()
            if strats:
                sid = strats[0].id
        strat = get_strategy(sid)
        return strat

    def execute(self, context):  # start async
        strat = self._resolve_strategy(context)
        if not strat:
            self.report({"ERROR"}, "Strategy not found")
            return {"CANCELLED"}
        self._strategy = strat
        objs = self._gather(context)
        if not objs:
            self.report({"WARNING"}, "No system objects to shade")
            return {"CANCELLED"}
        self._objects = objs
        self._index = 0
        self._total = len(objs)
        wm = context.window_manager
        wm.eve_shader_in_progress = True
        wm.eve_shader_progress = 0.0
        wm.eve_shader_total = self._total
        wm.eve_shader_processed = 0
        wm.eve_shader_strategy = strat.id
        try:
            self._timer = context.window_manager.event_timer_add(0.01, window=context.window)
        except Exception:
            self._timer = None
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        wm = context.window_manager
        if event.type == "ESC":
            self._finish(context, cancelled=True)
            return {"CANCELLED"}
        if event.type != "TIMER":
            return {"PASS_THROUGH"}
        if not getattr(wm, "eve_shader_in_progress", False):
            self._finish(context, cancelled=True)
            return {"CANCELLED"}
        if self._objects is None or self._strategy is None:
            self._finish(context, cancelled=True)
            return {"CANCELLED"}
        end = min(self._index + self.batch_size, self._total)
        # Apply strategy incrementally if it supports 'apply'; else fallback to full build once
        if hasattr(self._strategy, "apply"):
            for i in range(self._index, end):
                obj = self._objects[i]
                try:
                    self._strategy.apply(context, obj)
                except Exception:
                    pass
        else:
            # Fallback: call build once then finish
            try:
                self._strategy.build(context, {"systems": self._objects})
            except Exception as e:
                self.report({"ERROR"}, f"Apply failed: {e}")
                self._finish(context, cancelled=True)
                return {"CANCELLED"}
            self._index = self._total
            self._finish(context, cancelled=False)
            return {"FINISHED"}
        self._index = end
        wm.eve_shader_processed = self._index
        if self._total:
            wm.eve_shader_progress = self._index / self._total
        if self._index >= self._total:
            self._finish(context, cancelled=False)
            return {"FINISHED"}
        # Tag redraw for UI
        try:
            for area in context.screen.areas:
                area.tag_redraw()
        except Exception:
            pass
        return {"RUNNING_MODAL"}

    def _finish(self, context, cancelled=False):
        wm = context.window_manager
        wm.eve_shader_in_progress = False
        wm.eve_shader_progress = 0.0 if cancelled else 1.0
        msg = f"Shader async {'cancelled' if cancelled else 'complete'}: strategy={getattr(self._strategy, 'id', '?')} objects={self._total}"
        self.report({"INFO"}, msg)
        try:
            if self._timer:
                context.window_manager.event_timer_remove(self._timer)
        except Exception:
            pass
        try:
            for area in context.screen.areas:
                area.tag_redraw()
        except Exception:
            pass


class EVE_OT_viewport_fit_systems(Operator):
    bl_idname = "eve.viewport_fit_systems"
    bl_label = "Frame All Systems"
    bl_description = "Adjust 3D View to frame all generated system objects"

    def execute(self, context):  # noqa: D401
        systems_coll = bpy.data.collections.get("EVE_Systems")
        if not systems_coll or not systems_coll.objects:
            self.report({"WARNING"}, "No systems to frame")
            return {"CANCELLED"}
        objs = list(systems_coll.objects)
        # Safety: avoid attempting to frame if too many objects for selection-based method
        count = len(objs)
        if count == 0:
            self.report({"WARNING"}, "No systems to frame")
            return {"CANCELLED"}

        # Preserve current selection / active
        view_layer = context.view_layer
        prev_selected = set(bpy.context.selected_objects)
        prev_active = view_layer.objects.active
        restore_mode = None
        try:
            if bpy.context.mode != "OBJECT":  # leave edit/sculpt modes cleanly
                restore_mode = bpy.context.mode
                bpy.ops.object.mode_set(mode="OBJECT")
        except Exception:
            restore_mode = None

        # Deselect all then select system objects
        try:
            bpy.ops.object.select_all(action="DESELECT")
        except Exception:
            for o in bpy.context.selected_objects:
                try:
                    o.select_set(False)
                except Exception:
                    pass
        for o in objs:
            try:
                o.select_set(True)
            except Exception:
                pass
        # Set an active object (helps view_selected stability)
        try:
            view_layer.objects.active = objs[0]
        except Exception:
            pass

        framed_any = False
        for area in context.screen.areas:
            if area.type != "VIEW_3D":
                continue
            region = next((r for r in area.regions if r.type == "WINDOW"), None)
            space = next((s for s in area.spaces if s.type == "VIEW_3D"), None)
            if not (region and space):
                continue
            override = {
                "window": context.window,
                "screen": context.screen,
                "area": area,
                "region": region,
                "space_data": space,
                "scene": context.scene,
                "view_layer": view_layer,
            }
            # Force top view
            try:
                bpy.ops.view3d.view_axis(override, type="TOP")
            except Exception:
                pass
            # Ensure orthographic
            try:
                space.region_3d.view_perspective = "ORTHO"
            except Exception:
                pass
            # Frame selection using Blender's internal logic (robust for all sizes)
            try:
                bpy.ops.view3d.view_selected(override, use_all_regions=False)
            except TypeError:
                # Older / different Blender signature fallback
                try:
                    bpy.ops.view3d.view_selected(override)
                except Exception:
                    pass
            except Exception:
                pass
            # Add a tiny padding (zoom out slightly) so nothing hugs edge
            try:
                r3d = space.region_3d
                if hasattr(r3d, "view_distance"):
                    r3d.view_distance *= 1.02
            except Exception:
                pass
            framed_any = True

        # Restore previous selection
        try:
            bpy.ops.object.select_all(action="DESELECT")
        except Exception:
            for o in bpy.context.selected_objects:
                try:
                    o.select_set(False)
                except Exception:
                    pass
        for o in prev_selected:
            try:
                o.select_set(True)
            except Exception:
                pass
        try:
            view_layer.objects.active = prev_active
        except Exception:
            pass
        if restore_mode:
            try:
                bpy.ops.object.mode_set(mode=restore_mode)
            except Exception:
                pass

        if not framed_any:
            self.report({"WARNING"}, "No VIEW_3D area found")
            return {"CANCELLED"}
        self.report({"INFO"}, f"Viewport framed (Top Ortho, {count} systems)")
        return {"FINISHED"}


class EVE_OT_viewport_fit_systems_preserve(Operator):
    bl_idname = "eve.viewport_fit_preserve"
    bl_label = "Frame Systems (Keep Angle)"
    bl_description = "Frame all systems without changing current view angle (uses view_selected)"

    def execute(self, context):  # noqa: D401
        systems_coll = bpy.data.collections.get("EVE_Systems")
        if not systems_coll or not systems_coll.objects:
            self.report({"WARNING"}, "No systems to frame")
            return {"CANCELLED"}
        objs = list(systems_coll.objects)
        if not objs:
            self.report({"WARNING"}, "No systems to frame")
            return {"CANCELLED"}
        view_layer = context.view_layer
        prev_selected = set(bpy.context.selected_objects)
        prev_active = view_layer.objects.active
        restore_mode = None
        try:
            if bpy.context.mode != "OBJECT":
                restore_mode = bpy.context.mode
                bpy.ops.object.mode_set(mode="OBJECT")
        except Exception:
            restore_mode = None
        # Deselect then select systems
        try:
            bpy.ops.object.select_all(action="DESELECT")
        except Exception:
            for o in bpy.context.selected_objects:
                try:
                    o.select_set(False)
                except Exception:
                    pass
        for o in objs:
            try:
                o.select_set(True)
            except Exception:
                pass
        try:
            view_layer.objects.active = objs[0]
        except Exception:
            pass
        framed_any = False
        for area in context.screen.areas:
            if area.type != "VIEW_3D":
                continue
            region = next((r for r in area.regions if r.type == "WINDOW"), None)
            space = next((s for s in area.spaces if s.type == "VIEW_3D"), None)
            if not (region and space):
                continue
            override = {
                "window": context.window,
                "screen": context.screen,
                "area": area,
                "region": region,
                "space_data": space,
                "scene": context.scene,
                "view_layer": view_layer,
            }
            try:
                bpy.ops.view3d.view_selected(override, use_all_regions=False)
            except TypeError:
                try:
                    bpy.ops.view3d.view_selected(override)
                except Exception:
                    pass
            except Exception:
                pass
            # Slight outward padding
            try:
                r3d = space.region_3d
                if hasattr(r3d, "view_distance"):
                    r3d.view_distance *= 1.02
            except Exception:
                pass
            framed_any = True
        # Restore selection
        try:
            bpy.ops.object.select_all(action="DESELECT")
        except Exception:
            for o in bpy.context.selected_objects:
                try:
                    o.select_set(False)
                except Exception:
                    pass
        for o in prev_selected:
            try:
                o.select_set(True)
            except Exception:
                pass
        try:
            view_layer.objects.active = prev_active
        except Exception:
            pass
        if restore_mode:
            try:
                bpy.ops.object.mode_set(mode=restore_mode)
            except Exception:
                pass
        if not framed_any:
            self.report({"WARNING"}, "No VIEW_3D area found")
            return {"CANCELLED"}
        self.report({"INFO"}, f"Viewport framed (preserve angle, {len(objs)} systems)")
        return {"FINISHED"}


class EVE_OT_viewport_fit_selection(Operator):
    bl_idname = "eve.viewport_fit_selection"
    bl_label = "Frame Selection"
    bl_description = "Frame only the currently selected system objects (keeps angle)"

    def execute(self, context):  # noqa: D401
        selected = list(bpy.context.selected_objects)
        if not selected:
            self.report({"WARNING"}, "No objects selected")
            return {"CANCELLED"}
        view_layer = context.view_layer
        prev_selected = set(selected)
        prev_active = view_layer.objects.active
        # Ensure in object mode
        restore_mode = None
        try:
            if bpy.context.mode != "OBJECT":
                restore_mode = bpy.context.mode
                bpy.ops.object.mode_set(mode="OBJECT")
        except Exception:
            restore_mode = None
        # (Selection already as desired) set active if missing
        try:
            if prev_active not in prev_selected and selected:
                view_layer.objects.active = selected[0]
        except Exception:
            pass
        framed_any = False
        for area in context.screen.areas:
            if area.type != "VIEW_3D":
                continue
            region = next((r for r in area.regions if r.type == "WINDOW"), None)
            space = next((s for s in area.spaces if s.type == "VIEW_3D"), None)
            if not (region and space):
                continue
            override = {
                "window": context.window,
                "screen": context.screen,
                "area": area,
                "region": region,
                "space_data": space,
                "scene": context.scene,
                "view_layer": view_layer,
            }
            try:
                bpy.ops.view3d.view_selected(override, use_all_regions=False)
            except TypeError:
                try:
                    bpy.ops.view3d.view_selected(override)
                except Exception:
                    pass
            except Exception:
                pass
            try:
                r3d = space.region_3d
                if hasattr(r3d, "view_distance"):
                    r3d.view_distance *= 1.015
            except Exception:
                pass
            framed_any = True
        if restore_mode:
            try:
                bpy.ops.object.mode_set(mode=restore_mode)
            except Exception:
                pass
        if not framed_any:
            self.report({"WARNING"}, "No VIEW_3D area found")
            return {"CANCELLED"}
        self.report({"INFO"}, f"Framed current selection ({len(selected)} objects)")
        return {"FINISHED"}


class EVE_OT_viewport_set_space(Operator):
    bl_idname = "eve.viewport_set_space"
    bl_label = "Set Space Black"
    bl_description = (
        "Set world background to black and enable simple lighting for space visualization"
    )

    def execute(self, context):  # noqa: D401
        world = bpy.context.scene.world
        if not world:
            world = bpy.data.worlds.new("EVE_World")
            bpy.context.scene.world = world
        world.use_nodes = True
        nt = world.node_tree
        # Ensure background node exists
        bg = None
        for n in nt.nodes:
            if n.type == "BACKGROUND":
                bg = n
                break
        if not bg:
            bg = nt.nodes.new("ShaderNodeBackground")
        bg.inputs[0].default_value = (0.0030, 0.0040, 0.0060, 1.0)  # space blue
        # Optionally reduce strength for neutral backdrop
        bg.inputs[1].default_value = 1.0
        # Ensure output
        out = None
        for n in nt.nodes:
            if n.type == "OUTPUT_WORLD":
                out = n
                break
        if not out:
            out = nt.nodes.new("ShaderNodeOutputWorld")
        # Link if not linked
        linked = any(lnk.from_node == bg and lnk.to_node == out for lnk in nt.links)
        if not linked:
            nt.links.new(bg.outputs[0], out.inputs[0])
        # Simple shading: switch viewport to use scene world & flat lighting
        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                for space in area.spaces:
                    if space.type == "VIEW_3D":
                        space.shading.use_scene_world = True
                        space.shading.background_type = "WORLD"
        self.report({"INFO"}, "Background set to black")
        return {"FINISHED"}


class EVE_OT_viewport_set_hdri(Operator):  # pragma: no cover - Blender runtime usage
    bl_idname = "eve.viewport_set_hdri"
    bl_label = "Set Space HDRI"
    bl_description = "Use bundled space HDRI environment texture"

    strength: bpy.props.FloatProperty(  # type: ignore[valid-type]
        name="Strength",
        default=1.0,
        min=0.0,
        soft_max=10.0,
        description="Background emission strength",
    )

    def execute(self, context):  # noqa: D401
        from pathlib import Path

        # Resolve HDRI path relative to repo root (two parents from addon module)
        try:
            hdri_path = (
                Path(__file__).resolve().parents[2]
                / "hdris"
                / "space_hdri_deepblue_darker_v2_4k_float32.tiff"
            )
        except Exception:
            self.report({"ERROR"}, "Failed to resolve HDRI path")
            return {"CANCELLED"}
        if not hdri_path.exists():
            self.report({"ERROR"}, f"HDRI not found: {hdri_path.name}")
            return {"CANCELLED"}

        world = bpy.context.scene.world
        if not world:
            world = bpy.data.worlds.new("EVE_World")
            bpy.context.scene.world = world
        world.use_nodes = True
        nt = world.node_tree
        nodes = nt.nodes
        links = nt.links
        out = next((n for n in nodes if n.type == "OUTPUT_WORLD"), None)
        if not out:
            out = nodes.new("ShaderNodeOutputWorld")
        bg = next((n for n in nodes if n.type == "BACKGROUND"), None)
        if not bg:
            bg = nodes.new("ShaderNodeBackground")
        bg.inputs[1].default_value = self.strength
        env = next((n for n in nodes if n.type == "TEX_ENVIRONMENT"), None)
        if not env:
            env = nodes.new("ShaderNodeTexEnvironment")
            env.location = (-400, 0)
        # Load or reuse image
        img = bpy.data.images.get(hdri_path.name)
        if not img:
            try:
                img = bpy.data.images.load(str(hdri_path))
            except Exception as e:
                self.report({"ERROR"}, f"Load failed: {e}")
                return {"CANCELLED"}
        env.image = img
        try:
            if hasattr(env.image, "colorspace_settings"):
                env.image.colorspace_settings.name = "Linear"
        except Exception:
            pass
        # Rewire links
        try:
            for link in list(env.outputs[0].links):
                nt.links.remove(link)
        except Exception:
            pass
        if not any(link.from_node == env and link.to_node == bg for link in nt.links):
            links.new(env.outputs[0], bg.inputs[0])
        if not any(link.from_node == bg and link.to_node == out for link in nt.links):
            links.new(bg.outputs[0], out.inputs[0])
        # Enable scene world
        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                for space in area.spaces:
                    if space.type == "VIEW_3D":
                        space.shading.use_scene_world = True
                        space.shading.background_type = "WORLD"
        self.report({"INFO"}, "HDRI applied")
        return {"FINISHED"}


class EVE_OT_viewport_set_clip(Operator):
    bl_idname = "eve.viewport_set_clip"
    bl_label = "Set Clip End 100km"
    bl_description = "Set 3D View clip end distance to 100,000 (for large-scale starmap)"

    clip_end: bpy.props.FloatProperty(  # type: ignore[valid-type]
        name="Clip End",
        default=100000.0,
        min=1000.0,
        soft_max=1000000.0,
        description="Clip end distance to apply to all 3D viewports",
    )

    def execute(self, context):  # noqa: D401
        applied = 0
        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                for space in area.spaces:
                    if space.type == "VIEW_3D":
                        space.clip_end = float(self.clip_end)
                        applied += 1
        if applied:
            self.report({"INFO"}, f"Set clip end to {self.clip_end:g} on {applied} view(s)")
            return {"FINISHED"}
        self.report({"WARNING"}, "No VIEW_3D areas found")
        return {"CANCELLED"}


class EVE_OT_viewport_hide_overlays(Operator):
    bl_idname = "eve.viewport_hide_overlays"
    bl_label = "Hide Grid & Axis"
    bl_description = "Hide floor grid and XYZ axis in all 3D Viewports (toggle)"

    def execute(self, context):  # noqa: D401
        toggled = 0
        last_show_floor = None
        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                for space in area.spaces:
                    if space.type == "VIEW_3D":
                        overlay = space.overlay
                        # Toggle both grid and axis visibility
                        new_state = not overlay.show_floor
                        overlay.show_floor = new_state
                        overlay.show_axis_x = new_state  # axis follows floor
                        overlay.show_axis_y = new_state
                        overlay.show_axis_z = new_state
                        last_show_floor = new_state
                        toggled += 1
        if toggled:
            state = "shown" if last_show_floor else "hidden"
            self.report({"INFO"}, f"Grid/Axis now {state} ({toggled} view(s))")
            return {"FINISHED"}
        self.report({"WARNING"}, "No VIEW_3D areas found")
        return {"CANCELLED"}


def register():  # pragma: no cover - Blender runtime usage
    bpy.utils.register_class(EVE_OT_clear_scene)
    bpy.utils.register_class(EVE_OT_load_data)
    bpy.utils.register_class(EVE_OT_build_scene)
    bpy.utils.register_class(EVE_OT_build_scene_modal)
    bpy.utils.register_class(EVE_OT_cancel_build)
    bpy.utils.register_class(EVE_OT_cancel_shader)
    bpy.utils.register_class(EVE_OT_apply_shader)
    bpy.utils.register_class(EVE_OT_apply_shader_modal)
    bpy.utils.register_class(EVE_OT_viewport_fit_systems)
    bpy.utils.register_class(EVE_OT_viewport_fit_systems_preserve)
    bpy.utils.register_class(EVE_OT_viewport_fit_selection)
    bpy.utils.register_class(EVE_OT_viewport_set_space)
    bpy.utils.register_class(EVE_OT_viewport_set_hdri)
    bpy.utils.register_class(EVE_OT_viewport_set_clip)
    bpy.utils.register_class(EVE_OT_viewport_hide_overlays)
    # WindowManager properties for progress
    wm = bpy.types.WindowManager
    if not hasattr(wm, "eve_build_in_progress"):
        wm.eve_build_in_progress = bpy.props.BoolProperty(
            name="EVE Build In Progress", default=False
        )  # type: ignore[attr-defined]
    if not hasattr(wm, "eve_build_progress"):
        wm.eve_build_progress = bpy.props.FloatProperty(
            name="EVE Build Progress", default=0.0, min=0.0, max=1.0, subtype="FACTOR"
        )  # type: ignore[attr-defined]
    if not hasattr(wm, "eve_build_total"):
        wm.eve_build_total = bpy.props.IntProperty(name="EVE Build Total", default=0, min=0)  # type: ignore[attr-defined]
    if not hasattr(wm, "eve_build_created"):
        wm.eve_build_created = bpy.props.IntProperty(name="EVE Build Created", default=0, min=0)  # type: ignore[attr-defined]
    if not hasattr(wm, "eve_build_mode"):
        wm.eve_build_mode = bpy.props.StringProperty(name="EVE Build Mode", default="")  # type: ignore[attr-defined]
    # Shader async progress properties
    if not hasattr(wm, "eve_shader_in_progress"):
        wm.eve_shader_in_progress = bpy.props.BoolProperty(  # type: ignore[attr-defined]
            name="EVE Shader In Progress", default=False
        )
    if not hasattr(wm, "eve_shader_progress"):
        wm.eve_shader_progress = bpy.props.FloatProperty(  # type: ignore[attr-defined]
            name="EVE Shader Progress", default=0.0, min=0.0, max=1.0, subtype="FACTOR"
        )
    if not hasattr(wm, "eve_shader_total"):
        wm.eve_shader_total = bpy.props.IntProperty(  # type: ignore[attr-defined]
            name="EVE Shader Total", default=0, min=0
        )
    if not hasattr(wm, "eve_shader_processed"):
        wm.eve_shader_processed = bpy.props.IntProperty(  # type: ignore[attr-defined]
            name="EVE Shader Processed", default=0, min=0
        )
    if not hasattr(wm, "eve_shader_strategy"):
        wm.eve_shader_strategy = bpy.props.StringProperty(  # type: ignore[attr-defined]
            name="EVE Shader Strategy", default=""
        )

    # Strategy dropdown property
    def _strategy_enum_items(self, context):  # pragma: no cover - dynamic items
        try:
            return [(s.id, s.label, "") for s in get_strategies()] or [("__none__", "None", "")]
        except Exception:
            return [("__error__", "(error)", "Failed to enumerate strategies")]

    if not hasattr(wm, "eve_strategy_id"):
        wm.eve_strategy_id = bpy.props.EnumProperty(  # type: ignore[attr-defined]
            name="Strategy",
            description="Visualization strategy to apply",
            items=_strategy_enum_items,
        )
    # Fallback: ensure strategy_id materialized (rare on some reload sequences)
    if not hasattr(EVE_OT_apply_shader, "strategy_id"):
        print(
            "[EVEVisualizer][warn] strategy_id EnumProperty missing; injecting StringProperty fallback"
        )
        EVE_OT_apply_shader.strategy_id = bpy.props.StringProperty(name="Strategy")  # type: ignore[attr-defined]


def unregister():  # pragma: no cover - Blender runtime usage
    bpy.utils.unregister_class(EVE_OT_viewport_set_clip)
    bpy.utils.unregister_class(EVE_OT_viewport_hide_overlays)
    bpy.utils.unregister_class(EVE_OT_clear_scene)
    bpy.utils.unregister_class(EVE_OT_viewport_set_space)
    bpy.utils.unregister_class(EVE_OT_viewport_set_hdri)
    bpy.utils.unregister_class(EVE_OT_viewport_fit_systems)
    bpy.utils.unregister_class(EVE_OT_apply_shader)
    bpy.utils.unregister_class(EVE_OT_apply_shader_modal)
    bpy.utils.unregister_class(EVE_OT_cancel_build)
    bpy.utils.unregister_class(EVE_OT_cancel_shader)
    bpy.utils.unregister_class(EVE_OT_build_scene_modal)
    bpy.utils.unregister_class(EVE_OT_build_scene)
    bpy.utils.unregister_class(EVE_OT_load_data)
