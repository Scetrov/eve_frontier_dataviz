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
        # Inline build percentage slider (from add-on prefs) if available
        try:
            # Determine addon key from this module's path: addon.<name>.panels → folder name after 'addon'.
            mod_name = __name__.split(
                "."
            )  # e.g., ['addon', 'panels'] or ['addon'] depending on load
            addon_key = mod_name[0] if mod_name else "addon"
            prefs_container = context.preferences.addons.get(addon_key)
            if prefs_container:
                prefs = getattr(prefs_container, "preferences", None)
                if hasattr(prefs, "build_percentage"):
                    slider = col.row(align=True)
                    slider.prop(prefs, "build_percentage", text="Build %")
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
