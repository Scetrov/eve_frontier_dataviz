import os
import math
import bpy
from bpy.types import Operator

from .shader_registry import get_strategies, get_strategy
from .preferences import get_prefs
from .data_loader import load_data
from . import data_state

_generated_collection_names = ["EVE_Systems", "EVE_Planets", "EVE_Moons"]


def _get_or_create_collection(name: str):
    coll = bpy.data.collections.get(name)
    if not coll:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll


def _clear_generated():
    for cname in _generated_collection_names:
        coll = bpy.data.collections.get(cname)
        if coll:
            # unlink from scene
            for parent in list(coll.users_scene):
                parent.collection.children.unlink(coll)
            # delete objects first
            for obj in list(coll.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.collections.remove(coll)


class EVE_OT_load_data(Operator):
    bl_idname = "eve.load_data"
    bl_label = "Load / Refresh Data"
    bl_description = "Load data from the configured SQLite database"

    # Optional developer helper to restrict systems loaded
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
            self.report({'ERROR'}, f"Database not found: {db_path}")
            return {'CANCELLED'}
        try:
            systems = load_data(
                db_path,
                limit_systems=self.limit_systems or None,
                enable_cache=prefs.enable_cache,
            )
        except Exception as e:  # pragma: no cover - defensive around IO/SQLite errors
            self.report({'ERROR'}, f"Load failed: {e}")
            return {'CANCELLED'}
        data_state.set_loaded_systems(systems)
        total_planets = sum(len(s.planets) for s in systems)
        total_moons = sum(len(p.moons) for s in systems for p in s.planets)
        self.report(
            {'INFO'},
            f"Loaded {len(systems)} systems / {total_planets} planets / {total_moons} moons",
        )
        return {'FINISHED'}


class EVE_OT_build_scene(Operator):
    bl_idname = "eve.build_scene"
    bl_label = "Build Scene"
    bl_description = "Build or rebuild the scene from loaded data"
    clear_previous = bpy.props.BoolProperty(name="Clear Previous", default=True)

    def execute(self, context):  # noqa: D401
        systems_data = data_state.get_loaded_systems()
        if not systems_data:
            # Attempt implicit load if possible
            prefs = get_prefs(context)
            if not os.path.exists(prefs.db_path):
                self.report({'ERROR'}, "No data loaded and database path invalid")
                return {'CANCELLED'}
            try:
                systems_data = load_data(prefs.db_path, enable_cache=prefs.enable_cache)
                data_state.set_loaded_systems(systems_data)
            except Exception as e:  # pragma: no cover
                self.report({'ERROR'}, f"Auto-load failed: {e}")
                return {'CANCELLED'}

        prefs = get_prefs(context)
        scale = prefs.scale_factor

        if self.clear_previous:
            _clear_generated()
        systems_coll = _get_or_create_collection("EVE_Systems")

        # Create one object per system only; encode counts as custom properties
        created = 0
        for sys in systems_data:
            name = sys.name or f"System_{sys.id}"
            mesh = bpy.data.meshes.new(f"{name}_Mesh")
            obj = bpy.data.objects.new(name, mesh)
            systems_coll.objects.link(obj)
            obj.location = (sys.x * scale, sys.y * scale, sys.z * scale)
            planet_count = len(sys.planets)
            moon_count = sum(len(p.moons) for p in sys.planets)
            # Store counts as custom properties (simple ints) for strategies
            obj["planet_count"] = planet_count
            obj["moon_count"] = moon_count
            created += 1

        self.report({'INFO'}, f"Scene built with {created} systems (planets/moons as counts only)")
        return {'FINISHED'}


class EVE_OT_apply_shader(Operator):
    bl_idname = "eve.apply_shader"
    bl_label = "Apply Visualization"
    bl_description = "Apply selected shader strategy to generated objects"

    strategy_id = bpy.props.EnumProperty(
        name="Strategy",
        items=lambda self, context: [(s.id, s.label, "") for s in get_strategies()],
    )

    def execute(self, context):
        # gather objects by type (stub only systems)
        objs_by_type = {"systems": []}
        for cname in _generated_collection_names:
            coll = bpy.data.collections.get(cname)
            if not coll:
                continue
            if cname == "EVE_Systems":
                objs_by_type["systems"].extend(coll.objects)
        strat = get_strategy(self.strategy_id)
        if not strat:
            self.report({'ERROR'}, f"Strategy {self.strategy_id} not found")
            return {'CANCELLED'}
        strat.build(context, objs_by_type)
        self.report({'INFO'}, f"Applied {self.strategy_id}")
        return {'FINISHED'}


def register():
    bpy.utils.register_class(EVE_OT_load_data)
    bpy.utils.register_class(EVE_OT_build_scene)
    bpy.utils.register_class(EVE_OT_apply_shader)


def unregister():
    bpy.utils.unregister_class(EVE_OT_apply_shader)
    bpy.utils.unregister_class(EVE_OT_build_scene)
    bpy.utils.unregister_class(EVE_OT_load_data)
