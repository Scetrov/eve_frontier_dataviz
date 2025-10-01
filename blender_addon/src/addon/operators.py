import os

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
            for parent in list(coll.users_scene):
                parent.collection.children.unlink(coll)
            for obj in list(coll.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.collections.remove(coll)


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

        if self.clear_previous:
            _clear_generated()
        systems_coll = _get_or_create_collection("EVE_Systems")

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
        for sys in systems_iter:
            name = sys.name or f"System_{sys.id}"
            if representation == "EMPTY":
                # Lightweight display: Empty (plain axes)
                obj = bpy.data.objects.new(name, None)
                obj.empty_display_type = "PLAIN_AXES"
                obj.empty_display_size = radius
                systems_coll.objects.link(obj)
            elif representation == "ICO":
                # Low poly icosphere (subdiv=1 gives 12 verts -> 42 verts). Fewer than UV sphere segments.
                bpy.ops.mesh.primitive_ico_sphere_add(
                    radius=radius, enter_editmode=False, location=(0, 0, 0), subdivisions=1
                )
                obj = bpy.context.active_object
                obj.name = name
                systems_coll.objects.link(obj)
            elif representation == "ICO_INST":
                # Reuse single icosphere mesh datablock
                base_name = "EVE_System_Ico_Base"
                mesh = bpy.data.meshes.get(base_name)
                if not mesh:
                    bpy.ops.mesh.primitive_ico_sphere_add(
                        radius=radius, enter_editmode=False, location=(0, 0, 0), subdivisions=1
                    )
                    base_obj = bpy.context.active_object
                    base_obj.name = base_name
                    mesh = base_obj.data
                    # Keep base object hidden in viewport & render to avoid duplicate
                    base_obj.hide_set(True)
                    base_obj.hide_render = True
                    systems_coll.objects.link(base_obj)
                obj = bpy.data.objects.new(name, mesh)
                systems_coll.objects.link(obj)
            elif representation == "SPHERE_INST":
                base_name = "EVE_System_Sphere_Base"
                mesh = bpy.data.meshes.get(base_name)
                if not mesh:
                    bpy.ops.mesh.primitive_uv_sphere_add(
                        radius=radius,
                        enter_editmode=False,
                        location=(0, 0, 0),
                        segments=8,
                        ring_count=6,
                    )
                    base_obj = bpy.context.active_object
                    base_obj.name = base_name
                    mesh = base_obj.data
                    base_obj.hide_set(True)
                    base_obj.hide_render = True
                    systems_coll.objects.link(base_obj)
                obj = bpy.data.objects.new(name, mesh)
                systems_coll.objects.link(obj)
            else:
                # Default UV sphere geometry (still low segments)
                bpy.ops.mesh.primitive_uv_sphere_add(
                    radius=radius,
                    enter_editmode=False,
                    location=(0, 0, 0),
                    segments=8,
                    ring_count=6,
                )
                obj = bpy.context.active_object
                obj.name = name
                systems_coll.objects.link(obj)
            obj.location = (sys.x * scale, sys.y * scale, sys.z * scale)
            planet_count = len(sys.planets)
            moon_count = sum(len(p.moons) for p in sys.planets)
            obj["planet_count"] = planet_count
            obj["moon_count"] = moon_count
            created += 1

        self.report(
            {"INFO"},
            f"Scene built with {created} systems (sample={pct:.2%}, mode={representation}) planets/moons as counts only",
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


def register():  # pragma: no cover - Blender runtime usage
    bpy.utils.register_class(EVE_OT_load_data)
    bpy.utils.register_class(EVE_OT_build_scene)
    bpy.utils.register_class(EVE_OT_apply_shader)
    # Fallback: ensure strategy_id materialized (rare on some reload sequences)
    if not hasattr(EVE_OT_apply_shader, "strategy_id"):
        print(
            "[EVEVisualizer][warn] strategy_id EnumProperty missing; injecting StringProperty fallback"
        )
        EVE_OT_apply_shader.strategy_id = bpy.props.StringProperty(name="Strategy")  # type: ignore[attr-defined]


def unregister():  # pragma: no cover - Blender runtime usage
    bpy.utils.unregister_class(EVE_OT_apply_shader)
    bpy.utils.unregister_class(EVE_OT_build_scene)
    bpy.utils.unregister_class(EVE_OT_load_data)
