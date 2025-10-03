"""Camera setup operators for star map visualization."""

from __future__ import annotations

try:  # pragma: no cover
    import bpy  # type: ignore
    from mathutils import Vector  # type: ignore
except Exception:  # noqa: BLE001
    bpy = None  # type: ignore
    Vector = None  # type: ignore

if bpy:  # Only define classes when Blender API is present

    class EVE_OT_add_camera(bpy.types.Operator):  # type: ignore[misc,name-defined]
        """Add and configure camera for star map visualization."""

        bl_idname = "eve.add_camera"
        bl_label = "Add Camera"
        bl_description = "Add camera positioned at current view with proper clipping for star map"
        bl_options = {"REGISTER", "UNDO"}

        def execute(self, context):  # noqa: D401
            """Create camera matching current viewport with star map clipping."""
            if not bpy or not hasattr(bpy, "data"):
                self.report({"ERROR"}, "Blender context not available")
                return {"CANCELLED"}

            # Check if Frontier collection exists
            frontier = bpy.data.collections.get("Frontier")  # type: ignore[union-attr]
            if not frontier:
                self.report(
                    {"WARNING"},
                    "Frontier collection not found. Build scene first for better framing.",
                )

            # Get current 3D view
            area = None
            for a in context.screen.areas:
                if a.type == "VIEW_3D":
                    area = a
                    break

            if not area:
                self.report({"ERROR"}, "No 3D viewport found")
                return {"CANCELLED"}

            space = area.spaces.active
            region = None
            for r in area.regions:
                if r.type == "WINDOW":
                    region = r
                    break

            if not region:
                self.report({"ERROR"}, "No viewport region found")
                return {"CANCELLED"}

            # Get current view matrix
            view_matrix = space.region_3d.view_matrix.copy()

            # Create camera data
            cam_data = bpy.data.cameras.new(name="EVE_StarMap_Camera")  # type: ignore[attr-defined]

            # Set clipping distances
            # With 1e-18 scale: map diagonal ~190 units, max radius from center ~77 units
            # Start: 0.01 units (very close, can see nearby stars)
            # End: 300 units (covers full diagonal with margin, ensures all stars visible)
            cam_data.clip_start = 0.01
            cam_data.clip_end = 300.0

            # Set to orthographic or perspective based on current view
            if space.region_3d.is_perspective:
                cam_data.type = "PERSP"
                cam_data.lens = 50  # Standard 50mm lens
            else:
                cam_data.type = "ORTHO"
                cam_data.ortho_scale = space.region_3d.view_distance * 2

            # Create camera object
            cam_obj = bpy.data.objects.new(  # type: ignore[attr-defined]
                "EVE_StarMap_Camera", cam_data
            )

            # Link to scene
            context.scene.collection.objects.link(cam_obj)

            # Position camera to match current view
            # Get the view matrix inverse to position camera
            cam_obj.matrix_world = view_matrix.inverted()

            # Make this the active camera
            context.scene.camera = cam_obj

            # Set viewport to camera view
            space.region_3d.view_perspective = "CAMERA"

            # Frame all objects if Frontier collection exists
            if frontier:
                # Store current selection
                original_selection = context.selected_objects.copy()
                original_active = context.view_layer.objects.active

                # Deselect all
                bpy.ops.object.select_all(action="DESELECT")  # type: ignore[attr-defined]

                # Select all objects in Frontier collection (recursively)
                def select_collection_objects(coll):
                    for obj in coll.objects:
                        obj.select_set(True)
                    for child in coll.children:
                        select_collection_objects(child)

                select_collection_objects(frontier)

                # Set camera as active
                context.view_layer.objects.active = cam_obj

                # Frame selected (all stars)
                # We need to do this through the viewport
                for window in context.window_manager.windows:
                    for a in window.screen.areas:
                        if a.type == "VIEW_3D":
                            with context.temp_override(window=window, area=a):
                                # First ensure camera is selected
                                bpy.ops.view3d.camera_to_view_selected()  # type: ignore[attr-defined]
                                break
                    break

                # Restore selection
                bpy.ops.object.select_all(action="DESELECT")  # type: ignore[attr-defined]
                for obj in original_selection:
                    obj.select_set(True)
                context.view_layer.objects.active = original_active

            self.report({"INFO"}, "Camera added with clip range 1km - 100,000km")
            return {"FINISHED"}


def register():  # pragma: no cover
    if not bpy:
        return
    bpy.utils.register_class(EVE_OT_add_camera)


def unregister():  # pragma: no cover
    if not bpy:
        return
    bpy.utils.unregister_class(EVE_OT_add_camera)
