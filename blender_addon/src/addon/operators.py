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
    for cname in _generated_collection_names:
        coll = bpy.data.collections.get(cname)
        if coll:
            # Unlink from all scenes that reference it (iterate over all scenes)
            for scene in list(bpy.data.scenes):
                if coll.name in scene.collection.children:
                    try:
                        scene.collection.children.unlink(coll)
                    except Exception:
                        pass
            for obj in list(coll.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.collections.remove(coll)


class EVE_OT_clear_scene(Operator):
    bl_idname = "eve.clear_scene"
    bl_label = "Clear Scene"
    bl_description = "Remove all generated EVE collections and their objects"

    def execute(self, context):  # noqa: D401
        removed_objs = 0
        removed_colls = 0
        for cname in _generated_collection_names:
            coll = bpy.data.collections.get(cname)
            if not coll:
                continue
            for scene in list(bpy.data.scenes):
                if coll.name in scene.collection.children:
                    try:
                        scene.collection.children.unlink(coll)
                    except Exception:
                        pass
            for obj in list(coll.objects):
                removed_objs += 1
                bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.collections.remove(coll)
            removed_colls += 1
        if removed_colls == 0:
            self.report({"INFO"}, "No generated collections present")
            return {"CANCELLED"}
        self.report({"INFO"}, f"Cleared {removed_objs} objects across {removed_colls} collections")
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
            if representation == "EMPTY":
                obj = bpy.data.objects.new(name, None)
                obj.empty_display_type = "PLAIN_AXES"
                obj.empty_display_size = radius
                systems_coll.objects.link(obj)
            elif instanced and shared_mesh:
                obj = bpy.data.objects.new(name, shared_mesh)
                systems_coll.objects.link(obj)
            else:
                # Non-instanced mesh: copy from template mesh (faster than ops)
                tpl_mesh = _ensure_mesh(base_kind or "SPHERE", radius, False)
                obj = bpy.data.objects.new(name, tpl_mesh.copy())
                systems_coll.objects.link(obj)

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


class EVE_OT_viewport_fit_systems(Operator):
    bl_idname = "eve.viewport_fit_systems"
    bl_label = "Frame All Systems"
    bl_description = "Adjust 3D View to frame all generated system objects"

    def execute(self, context):  # noqa: D401
        # Collect system objects
        systems_coll = bpy.data.collections.get("EVE_Systems")
        if not systems_coll or not systems_coll.objects:
            self.report({"WARNING"}, "No systems to frame")
            return {"CANCELLED"}
        objs = list(systems_coll.objects)
        # Compute bounding box (object-space origins only; spheres small so okay)
        xs = [o.location.x for o in objs]
        ys = [o.location.y for o in objs]
        zs = [o.location.z for o in objs]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        min_z, max_z = min(zs), max(zs)
        center = ((min_x + max_x) * 0.5, (min_y + max_y) * 0.5, (min_z + max_z) * 0.5)
        span = max(max_x - min_x, max_y - min_y, max_z - min_z)
        if span <= 0:
            span = 1.0

        # Find an active 3D view region
        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                for space in area.spaces:
                    if space.type == "VIEW_3D":
                        region3d = space.region_3d
                        region3d.view_location = center
                        # Position view distance so all systems fit; add some padding
                        region3d.view_distance = span * 0.75
                        self.report({"INFO"}, "Viewport framed")
                        return {"FINISHED"}
        self.report({"WARNING"}, "No VIEW_3D area found")
        return {"CANCELLED"}


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
        bg.inputs[0].default_value = (0.0, 0.0, 0.0, 1.0)  # black
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
    bpy.utils.register_class(EVE_OT_apply_shader)
    bpy.utils.register_class(EVE_OT_viewport_fit_systems)
    bpy.utils.register_class(EVE_OT_viewport_set_space)
    bpy.utils.register_class(EVE_OT_viewport_set_clip)
    bpy.utils.register_class(EVE_OT_viewport_hide_overlays)
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
    bpy.utils.unregister_class(EVE_OT_viewport_fit_systems)
    bpy.utils.unregister_class(EVE_OT_apply_shader)
    bpy.utils.unregister_class(EVE_OT_build_scene)
    bpy.utils.unregister_class(EVE_OT_load_data)
