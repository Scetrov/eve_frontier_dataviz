import bpy
from bpy.types import Panel

from .shader_registry import get_strategies


class EVE_PT_main(Panel):
    bl_label = "EVE Frontier"
    bl_idname = "EVE_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'EVE Frontier'

    def draw(self, context):  # noqa: D401
        layout = self.layout
        col = layout.column(align=True)
        col.operator("eve.load_data", icon='FILE_REFRESH')
        col.operator("eve.build_scene", icon='OUTLINER_OB_EMPTY')

        col.separator()
        col.label(text="Visualization")
        row = col.row()
        strategies = get_strategies()
        if strategies:
            op = row.operator("eve.apply_shader", text="Apply", icon='MATERIAL')
            op.strategy_id = strategies[0].id
        else:
            row.label(text="No strategies registered")


def register():  # pragma: no cover - Blender runtime usage
    bpy.utils.register_class(EVE_PT_main)


def unregister():  # pragma: no cover - Blender runtime usage
    bpy.utils.unregister_class(EVE_PT_main)
