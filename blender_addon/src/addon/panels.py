import bpy
from bpy.types import Panel

from .shader_registry import get_strategies


class EVE_PT_main(Panel):
    bl_label = "EVE Frontier"
    bl_idname = "EVE_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "EVE Frontier"

    def draw(self, context):  # noqa: D401
        layout = self.layout
        col = layout.column(align=True)
        col.operator("eve.load_data", icon="FILE_REFRESH")
        build_row = col.row(align=True)
        build_row.operator("eve.build_scene", icon="OUTLINER_OB_EMPTY")
        # Inline controls (sampling, scale, radius) from preferences if available
        try:
            mod_name = __name__.split(".")
            addon_key = mod_name[0] if mod_name else "addon"
            prefs_container = context.preferences.addons.get(addon_key)
            if prefs_container:
                prefs = getattr(prefs_container, "preferences", None)
                if prefs:
                    ctrl_col = col.column(align=True)
                    if hasattr(prefs, "build_percentage"):
                        row_pct = ctrl_col.row(align=True)
                        row_pct.prop(prefs, "build_percentage", text="Build %")
                    if hasattr(prefs, "scale_factor"):
                        row_scale = ctrl_col.row(align=True)
                        row_scale.prop(prefs, "scale_factor", text="Scale")
                    if hasattr(prefs, "system_point_radius"):
                        row_rad = ctrl_col.row(align=True)
                        row_rad.prop(prefs, "system_point_radius", text="Radius")
        except Exception:
            pass

        col.separator()
        col.label(text="Visualization")
        row = col.row()
        strategies = get_strategies()
        if strategies:
            op = row.operator("eve.apply_shader", text="Apply", icon="MATERIAL")
            # Guard against missing property if registration hiccup occurred.
            if hasattr(op, "strategy_id") and strategies:
                try:
                    op.strategy_id = strategies[0].id
                except Exception:
                    pass
        else:
            row.label(text="No strategies registered")


def register():  # pragma: no cover - Blender runtime usage
    bpy.utils.register_class(EVE_PT_main)


def unregister():  # pragma: no cover - Blender runtime usage
    bpy.utils.unregister_class(EVE_PT_main)
