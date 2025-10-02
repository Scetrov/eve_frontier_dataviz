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

        # Node-based strategy selector (new)
        if hasattr(context.scene, "eve_active_strategy"):
            box_vis.prop(context.scene, "eve_active_strategy", text="Strategy")

        # Legacy strategy dropdown (for old Python-based strategies)
        strategies = get_strategies()
        if strategies:
            # Dropdown from WindowManager (legacy)
            wm = context.window_manager
            if hasattr(wm, "eve_strategy_id"):
                box_vis.prop(wm, "eve_strategy_id", text="Legacy Strategy")
            shader_in_progress = getattr(wm, "eve_shader_in_progress", False)
            if not shader_in_progress:
                row_vis = box_vis.row(align=True)
                # Only async apply retained (sync removed for reliability)
                row_vis.operator(
                    "eve.apply_shader_modal", text="Apply (Async)", icon="PLAY_REVERSE"
                )
            else:
                prog = getattr(wm, "eve_shader_progress", 0.0)
                processed = getattr(wm, "eve_shader_processed", 0)
                total = getattr(wm, "eve_shader_total", 0)
                sid = getattr(wm, "eve_shader_strategy", "?")
                box_vis.label(text=f"Applying {sid}: {processed}/{total} ({prog*100:.1f}%)")
                row_bar = box_vis.row(align=True)
                if hasattr(wm, "eve_shader_progress"):
                    row_bar.enabled = False
                    row_bar.prop(wm, "eve_shader_progress", text="Progress")
                row_cancel = box_vis.row(align=True)
                row_cancel.operator("eve.cancel_shader", text="Cancel", icon="CANCEL")
        else:
            row_vis = box_vis.row(align=True)
            row_vis.label(text="No strategies registered")

        # --- View Section ---
        box_view = layout.box()
        box_view.label(text="View / Camera", icon="VIEW_CAMERA")
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
            "eve.viewport_set_clip", text="Set Clipping to 100km", icon="VIEW_PERSPECTIVE"
        )
        op_clip.clip_end = 100000.0
        row_view4 = box_view.row(align=True)
        row_view4.operator("eve.viewport_hide_overlays", text="Toggle Grid/Axis", icon="GRID")


def register():  # pragma: no cover - Blender runtime usage
    bpy.utils.register_class(EVE_PT_main)


def unregister():  # pragma: no cover - Blender runtime usage
    bpy.utils.unregister_class(EVE_PT_main)
