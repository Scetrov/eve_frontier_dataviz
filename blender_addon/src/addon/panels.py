import bpy
from bpy.types import Panel


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
        wm = context.window_manager
        in_progress = getattr(wm, "eve_build_in_progress", False)
        if not in_progress:
            row_build = box_build.row(align=True)
            op = row_build.operator("eve.build_scene_modal", icon="OUTLINER_OB_EMPTY")
            op.batch_size = 2500
            row_build.operator("eve.clear_scene", text="Clear", icon="TRASH")
        else:
            # Progress & cancel UI
            prog = getattr(wm, "eve_build_progress", 0.0)
            created = getattr(wm, "eve_build_created", 0)
            total = getattr(wm, "eve_build_total", 0)
            mode = getattr(wm, "eve_build_mode", "")
            box_build.label(text=f"Building {created}/{total} ({prog*100:.1f}%) mode={mode}")
            row_p = box_build.row(align=True)
            # Simulated progress bar: factor property if registered
            if hasattr(wm, "eve_build_progress"):
                row_p.enabled = False
                row_p.prop(wm, "eve_build_progress", text="Progress")
            row_cancel = box_build.row(align=True)
            row_cancel.operator("eve.cancel_build", text="Cancel", icon="CANCEL")
            row_cancel.operator("eve.clear_scene", text="Clear", icon="TRASH")
        # Inline controls (sampling, scale, radius, display)
        try:
            mod_name = __name__.split(".")
            addon_key = mod_name[0] if mod_name else "addon"
            prefs_container = context.preferences.addons.get(addon_key)
            if prefs_container:
                prefs = getattr(prefs_container, "preferences", None)
                if prefs:
                    if hasattr(prefs, "build_percentage"):
                        box_build.prop(
                            prefs, "build_percentage", text="Sample Proportion (0.0 to 1.0)"
                        )
                    # Coordinate scale now panel-only (removed from preferences UI)
                    if hasattr(prefs, "scale_factor"):
                        box_build.prop(prefs, "scale_factor", text="Scale")
                    if hasattr(prefs, "system_point_radius"):
                        box_build.prop(prefs, "system_point_radius", text="Star Radius")
                    if hasattr(prefs, "system_representation"):
                        box_build.prop(prefs, "system_representation", text="Display")
                    # Black hole scale remains accessible where user tweaks visualization
                    if hasattr(prefs, "blackhole_scale_multiplier"):
                        box_build.prop(prefs, "blackhole_scale_multiplier", text="Black Hole Scale")
        except Exception:
            pass

        # --- Visualization Section ---
        box_vis = layout.box()
        box_vis.label(text="Visualization", icon="MATERIAL")

        # Node-based strategy selector - auto-applies on change
        if hasattr(context.scene, "eve_active_strategy"):
            box_vis.prop(context.scene, "eve_active_strategy", text="Strategy")
        else:
            box_vis.label(text="Reload add-on to enable strategies", icon="INFO")

        # Volumetric atmosphere controls
        row_vol = box_vis.row(align=True)
        row_vol.operator("eve.add_volumetric", text="Add Atmosphere", icon="VOLUME_DATA")
        row_vol.operator("eve.remove_volumetric", text="", icon="X")

        # Jump lines controls
        row_jumps = box_vis.row(align=True)
        row_jumps.operator("eve.build_jumps", text="Build Jumps", icon="MESH_MONKEY")
        row_jumps.operator("eve.toggle_jumps", text="", icon="HIDE_OFF")

        # Jump analysis controls
        row_jump_analysis = box_vis.row(align=True)
        row_jump_analysis.operator(
            "eve.highlight_triangle_islands", text="Triangle Islands", icon="MESH_DATA"
        )
        row_jump_analysis.operator("eve.show_all_jumps", text="", icon="RESTRICT_VIEW_OFF")

        # Black hole lights
        row_lights = box_vis.row(align=True)
        row_lights.operator(
            "eve.add_blackhole_lights", text="Add Black Hole Lights", icon="LIGHT_POINT"
        )
        row_lights.operator("eve.remove_blackhole_lights", text="", icon="X")

        # Reference points (navigation landmarks)
        row_refs = box_vis.row(align=True)
        row_refs.operator("eve.add_reference_points", text="Add Reference Points", icon="FONT_DATA")
        row_refs.operator("eve.remove_reference_points", text="", icon="X")

        # --- View Section ---
        box_view = layout.box()
        box_view.label(text="View / Camera", icon="VIEW_CAMERA")
        row_view_cam = box_view.row(align=True)
        row_view_cam.operator("eve.add_camera", text="Add Camera", icon="OUTLINER_OB_CAMERA")
        row_view1 = box_view.row(align=True)
        row_view1.operator("eve.viewport_frame_all", text="Frame All Stars", icon="VIEWZOOM")
        row_view2 = box_view.row(align=True)
        row_view2.operator(
            "eve.viewport_set_space", text="Set Background to Black", icon="WORLD_DATA"
        )
        row_view_hdri = box_view.row(align=True)
        op_hdri = row_view_hdri.operator(
            "eve.viewport_set_hdri", text="Apply Space HDRI", icon="IMAGE_DATA"
        )
        op_hdri.strength = 1.0
        row_view3 = box_view.row(align=True)
        op_clip = row_view3.operator(
            "eve.viewport_set_clip", text="Set Clipping for Stars", icon="VIEW_PERSPECTIVE"
        )
        op_clip.clip_end = 300.0
        row_view4 = box_view.row(align=True)
        row_view4.operator("eve.viewport_hide_overlays", text="Toggle Grid/Axis", icon="GRID")


def register():  # pragma: no cover - Blender runtime usage
    bpy.utils.register_class(EVE_PT_main)


def unregister():  # pragma: no cover - Blender runtime usage
    bpy.utils.unregister_class(EVE_PT_main)
