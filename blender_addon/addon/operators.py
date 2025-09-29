import bpy
from bpy.types import Operator

from .shader_registry import get_strategies, get_strategy

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

    def execute(self, context):
        # TODO: implement real loader
        self.report({'INFO'}, "(Stub) Data loaded")
        return {'FINISHED'}


class EVE_OT_build_scene(Operator):
    bl_idname = "eve.build_scene"
    bl_label = "Build Scene"
    bl_description = "Build or rebuild the scene from loaded data"
    clear_previous = bpy.props.BoolProperty(name="Clear Previous", default=True)

    def execute(self, context):
        if self.clear_previous:
            _clear_generated()
        systems = _get_or_create_collection("EVE_Systems")
        # stub: create placeholder objects
        import math
        for i in range(5):
            mesh = bpy.data.meshes.new(f"System_{i}_Mesh")
            obj = bpy.data.objects.new(f"System_{i}", mesh)
            systems.objects.link(obj)
            obj.location = (math.sin(i) * 10, math.cos(i) * 10, i * 2)
        self.report({'INFO'}, "(Stub) Scene built with placeholder systems")
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
