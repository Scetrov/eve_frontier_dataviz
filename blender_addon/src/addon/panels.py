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

        # --- Load Section ---
        box_load = layout.box()
        box_load.label(text="Load", icon="FILE_FOLDER")
        row_load = box_load.row(align=True)
        row_load.operator("eve.load_data", icon="FILE_REFRESH")

        # --- Build Section ---
        box_build = layout.box()
        box_build.label(text="Build", icon="OUTLINER_OB_EMPTY")
        row_build = box_build.row(align=True)
        row_build.operator("eve.build_scene", icon="OUTLINER_OB_EMPTY")
        row_build.operator("eve.clear_scene", text="Clear", icon="TRASH")
        # Inline controls (sampling, scale, radius, display)
        try:
            mod_name = __name__.split(".")
            addon_key = mod_name[0] if mod_name else "addon"
            prefs_container = context.preferences.addons.get(addon_key)
            if prefs_container:
                prefs = getattr(prefs_container, "preferences", None)
                if prefs:
                    if hasattr(prefs, "build_percentage"):
                        box_build.prop(prefs, "build_percentage", text="Build %")
                    if hasattr(prefs, "scale_factor"):
                        box_build.prop(prefs, "scale_factor", text="Scale")
                    if hasattr(prefs, "system_point_radius"):
                        box_build.prop(prefs, "system_point_radius", text="Radius")
                    if hasattr(prefs, "system_representation"):
                        box_build.prop(prefs, "system_representation", text="Display")
                    if hasattr(prefs, "apply_axis_transform"):
                        box_build.prop(prefs, "apply_axis_transform", text="Axis Rx-90")
        except Exception:
            pass

        # --- Visualization Section ---
        box_vis = layout.box()
        box_vis.label(text="Visualization", icon="MATERIAL")
        row_vis = box_vis.row(align=True)
        strategies = get_strategies()
        if strategies:
            op = row_vis.operator("eve.apply_shader", text="Apply Strategy", icon="MATERIAL")
            if hasattr(op, "strategy_id") and strategies:
                try:
                    op.strategy_id = strategies[0].id
                except Exception:
                    pass
        else:
            row_vis.label(text="No strategies registered")

        # --- View Section ---
        box_view = layout.box()
        box_view.label(text="View / Camera", icon="VIEW_CAMERA")
        row_view = box_view.row(align=True)
        row_view.operator("eve.viewport_fit_systems", text="Frame Systems", icon="VIEWZOOM")
        row_view2 = box_view.row(align=True)
        row_view2.operator("eve.viewport_set_space", text="Black BG", icon="WORLD_DATA")
        row_view3 = box_view.row(align=True)
        op_clip = row_view3.operator(
            "eve.viewport_set_clip", text="Clip 100km", icon="VIEW_PERSPECTIVE"
        )
        op_clip.clip_end = 100000.0
        row_view4 = box_view.row(align=True)
        row_view4.operator("eve.viewport_hide_overlays", text="Toggle Grid/Axis", icon="GRID")


def register():  # pragma: no cover - Blender runtime usage
    bpy.utils.register_class(EVE_PT_main)


def unregister():  # pragma: no cover - Blender runtime usage
    bpy.utils.unregister_class(EVE_PT_main)
