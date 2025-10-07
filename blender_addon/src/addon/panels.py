import importlib

import bpy
from bpy.types import Panel


def _resolve_get_prefs():
    """Resolve and return a suitable get_prefs(context) callable.

    We try a small set of import strategies because the add-on package may be
    loaded under different top-level names when installed into Blender. If
    none of the strategies succeed we return a no-op function so the panels
    can still draw in test or limited contexts.

    Returns
    -------
    callable
        A function accepting a single argument 'context' and returning the
        add-on preferences object. If preferences cannot be resolved the
        returned callable will accept 'context' and return None (no-op).
    """
    # Strategy 1: Normal relative import when running as the package `addon`
    try:
        from .preferences import get_prefs  # type: ignore

        return get_prefs
    except (ImportError, ModuleNotFoundError):
        pass

    # Strategy 2: Import from root package if loaded as a submodule
    try:
        root_pkg = __package__.split(".")[0] if __package__ else None
        if root_pkg:
            mod = importlib.import_module(f"{root_pkg}.preferences")
            return mod.get_prefs
    except (ImportError, ModuleNotFoundError, AttributeError):
        pass

    # Strategy 3: Import from addon.preferences (src layout during pytest/dev)
    try:
        from addon.preferences import get_prefs  # type: ignore

        return get_prefs
    except (ImportError, ModuleNotFoundError):
        pass

    # Fallback: no-op
    def _noop_get_prefs(context):
        return None

    return _noop_get_prefs


get_prefs = _resolve_get_prefs()


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
        # Guard access to addon preferences - use explicit checks instead of broad
        # exception swallowing so we don't hide programming errors.
        # Use clearer variable names: name_parts -> top-level package name
        name_parts = __name__.split(".")
        addon_key = name_parts[0] if name_parts else "addon"
        prefs_context = getattr(context, "preferences", None)
        try:
            addon_prefs_container = (
                context.preferences.addons.get(addon_key) if prefs_context else None
            )
        except (AttributeError, TypeError):
            addon_prefs_container = None
        if addon_prefs_container:
            prefs = getattr(addon_prefs_container, "preferences", None)
            if prefs:
                if hasattr(prefs, "build_percentage"):
                    box_build.prop(prefs, "build_percentage", text="Sample Proportion (0.0 to 1.0)")
                # Coordinate scale now panel-only (removed from preferences UI)
                if hasattr(prefs, "scale_exponent"):
                    box_build.prop(prefs, "scale_exponent", text="Scale (10^x)")
                if hasattr(prefs, "system_point_radius"):
                    box_build.prop(prefs, "system_point_radius", text="Star Radius")
                if hasattr(prefs, "system_representation"):
                    box_build.prop(prefs, "system_representation", text="Display")
                # Black hole scale remains accessible where user tweaks visualization
                if hasattr(prefs, "blackhole_scale_multiplier"):
                    box_build.prop(prefs, "blackhole_scale_multiplier", text="Black Hole Scale")

        # --- Visualization Section ---
        box_vis = layout.box()
        box_vis.label(text="Visualization", icon="MATERIAL")

        # Node-based strategy selector - auto-applies on change
        if hasattr(context.scene, "eve_active_strategy"):
            box_vis.prop(context.scene, "eve_active_strategy", text="Strategy")

            # Strategy-specific parameters
            active_strategy = context.scene.eve_active_strategy

            if active_strategy == "CharacterRainbow":
                # Character index selector for Character Rainbow
                if hasattr(context.scene, "eve_char_rainbow_index"):
                    box_vis.prop(context.scene, "eve_char_rainbow_index", text="Character Index")
            elif active_strategy == "PositionEncoding":
                # Info label explaining Position Encoding
                box_vis.label(text="RGB from chars 0-2, blackhole boost", icon="INFO")
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
            "eve.viewport_set_hdri", text="Apply Space Background", icon="IMAGE_DATA"
        )
        op_hdri.strength = 1.0
        row_view3 = box_view.row(align=True)
        op_clip = row_view3.operator(
            "eve.viewport_set_clip", text="Set Clipping for Stars", icon="VIEW_PERSPECTIVE"
        )
        op_clip.clip_end = 300.0
        row_view4 = box_view.row(align=True)
        row_view4.operator("eve.viewport_hide_overlays", text="Toggle Grid/Axis", icon="GRID")


# Note: panel registration for both main and filters is handled below where
# both classes and operators are registered together. The single-class
# register/unregister definitions above were duplicate and caused ruff
# redefinition errors; they have been removed.


class EVE_PT_filters(Panel):
    """Filters panel exposing SystemsByName child collections as check boxes."""

    bl_label = "Filters"
    bl_idname = "EVE_PT_filters"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "EVE Frontier"

    def draw(self, context):  # noqa: D401
        layout = self.layout
        systems_by_name = None
        try:
            systems_by_name = bpy.data.collections.get("SystemsByName")
        except (AttributeError, RuntimeError):
            systems_by_name = None

        if not systems_by_name:
            layout.label(text="No SystemsByName collection (build scene first)")
            return

        box = layout.box()
        box.label(text="SystemsByName Filters", icon="FILTER")

        # Sort children for stable display
        children = sorted(list(systems_by_name.children), key=lambda c: c.name)
        if not children:
            box.label(text="No pattern buckets found")
            return

        for child in children:
            row = box.row(align=True)
            # Use the collection's hide_viewport as the checkbox; keep hide_render synced
            # Show an Outliner-like camera icon to indicate render/collection visibility
            try:
                row.prop(child, "hide_viewport", text=child.name, icon="OUTLINER_OB_CAMERA")
            except (AttributeError, TypeError):
                # Fall back to a simple label if property access fails
                row.label(text=child.name)
                continue
            # Keep render visibility in sync with viewport visibility for consistent behavior
            try:
                child.hide_render = child.hide_viewport
            except AttributeError:
                # Older or test contexts may not expose hide_render
                pass

        # Show/Hide All quick actions
        row_ops = box.row(align=True)
        row_ops.operator("eve.filters_show_all", text="Show All", icon="HIDE_OFF")
        row_ops.operator("eve.filters_hide_all", text="Hide All", icon="HIDE_ON")
        # Status and sync with preferences if available
        try:
            # Ensure preferences are available (we don't need the object value)
            get_prefs(context)
            vis_count = sum(0 if c.hide_viewport else 1 for c in children)
            box.label(text=f"Visible buckets: {vis_count}/{len(children)}")
        except (AttributeError, ImportError, ModuleNotFoundError):
            # best-effort: if preferences are not reachable, skip
            pass


def register():  # pragma: no cover - Blender runtime usage
    if not bpy:
        return
    bpy.utils.register_class(EVE_PT_main)
    bpy.utils.register_class(EVE_PT_filters)
    # Register filter toggle operators - be noisy if registration fails so
    # that CI / development logs show an actionable message.
    try:
        bpy.utils.register_class(EVE_OT_filters_show_all)
    except (RuntimeError, ValueError) as e:
        print(f"[EVEVisualizer][panels] ERROR registering show_all operator: {e}")
    try:
        bpy.utils.register_class(EVE_OT_filters_hide_all)
    except (RuntimeError, ValueError) as e:
        print(f"[EVEVisualizer][panels] ERROR registering hide_all operator: {e}")


def unregister():  # pragma: no cover - Blender runtime usage
    if not bpy:
        return
    try:
        bpy.utils.unregister_class(EVE_OT_filters_hide_all)
    except (RuntimeError, ValueError) as e:
        print(f"[EVEVisualizer][panels] WARNING unregister hide_all: {e}")
    try:
        bpy.utils.unregister_class(EVE_OT_filters_show_all)
    except (RuntimeError, ValueError) as e:
        print(f"[EVEVisualizer][panels] WARNING unregister show_all: {e}")
    bpy.utils.unregister_class(EVE_PT_filters)
    bpy.utils.unregister_class(EVE_PT_main)


class EVE_OT_filters_show_all(bpy.types.Operator):
    """Show all SystemsByName child collections"""

    bl_idname = "eve.filters_show_all"
    bl_label = "Show All SystemsByName"

    def execute(self, context):
        try:
            root = bpy.data.collections.get("SystemsByName")
            if not root:
                self.report({"WARNING"}, "SystemsByName not found")
                return {"CANCELLED"}
            for child in root.children:
                try:
                    child.hide_viewport = False
                except AttributeError:
                    # Some test contexts may not expose these attributes
                    pass
                try:
                    child.hide_render = False
                except AttributeError:
                    pass
            # Persist preference if available
            try:
                prefs = get_prefs(bpy.context)
                # Set each preference only if it exists to avoid nested try/except
                for attr in (
                    "filter_dash",
                    "filter_colon",
                    "filter_dotseq",
                    "filter_pipe",
                    "filter_other",
                    "filter_blackhole",
                ):
                    if hasattr(prefs, attr):
                        setattr(prefs, attr, True)
            except (AttributeError, ImportError, ModuleNotFoundError):
                # best-effort persistence; ignore if prefs not reachable
                pass
            return {"FINISHED"}
        except (AttributeError, RuntimeError, TypeError, ImportError) as e:
            # Non-fatal: report actionable error instead of silencing all exceptions
            self.report({"ERROR"}, f"Show all failed: {e}")
            return {"CANCELLED"}


class EVE_OT_filters_hide_all(bpy.types.Operator):
    """Hide all SystemsByName child collections"""

    bl_idname = "eve.filters_hide_all"
    bl_label = "Hide All SystemsByName"

    def execute(self, context):
        try:
            root = bpy.data.collections.get("SystemsByName")
            if not root:
                self.report({"WARNING"}, "SystemsByName not found")
                return {"CANCELLED"}
            for child in root.children:
                try:
                    child.hide_viewport = True
                except AttributeError:
                    pass
                try:
                    child.hide_render = True
                except AttributeError:
                    pass
            # Persist preference if available
            try:
                prefs = get_prefs(bpy.context)
                for attr in (
                    "filter_dash",
                    "filter_colon",
                    "filter_dotseq",
                    "filter_pipe",
                    "filter_other",
                    "filter_blackhole",
                ):
                    if hasattr(prefs, attr):
                        setattr(prefs, attr, False)
            except (AttributeError, ImportError, ModuleNotFoundError):
                pass
            return {"FINISHED"}
        except (AttributeError, RuntimeError, TypeError, ImportError) as e:
            # Non-fatal: report actionable error instead of silencing all exceptions
            self.report({"ERROR"}, f"Hide all failed: {e}")
            return {"CANCELLED"}
