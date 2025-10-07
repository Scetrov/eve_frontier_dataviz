"""Camera setup operators for star map visualization."""

from __future__ import annotations

try:  # pragma: no cover
    import bpy  # type: ignore
    from mathutils import Vector  # type: ignore
except (ImportError, ModuleNotFoundError):  # noqa: BLE001
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

            # If no systems exist, position camera at a good default viewing position
            if not frontier or not any(frontier.all_objects):
                # Default position: looking at origin from distance
                # With scale 1e-18, galaxy diameter ~190 units centered at origin
                # Position camera 150 units back on Z, looking at origin
                cam_obj.location = Vector((0.0, -150.0, 50.0))
                cam_obj.rotation_euler = (1.2, 0.0, 0.0)  # Tilt down slightly to look at origin
                self.report(
                    {"INFO"},
                    "Camera added at default position. Build scene to frame all stars.",
                )
            else:
                # Calculate bounding box of all system objects
                min_coord = Vector((float("inf"), float("inf"), float("inf")))
                max_coord = Vector((float("-inf"), float("-inf"), float("-inf")))

                def get_bounds(coll):
                    nonlocal min_coord, max_coord
                    for obj in coll.objects:
                        if obj.type == "MESH" or obj.type == "EMPTY":
                            loc = obj.location
                            min_coord.x = min(min_coord.x, loc.x)
                            min_coord.y = min(min_coord.y, loc.y)
                            min_coord.z = min(min_coord.z, loc.z)
                            max_coord.x = max(max_coord.x, loc.x)
                            max_coord.y = max(max_coord.y, loc.y)
                            max_coord.z = max(max_coord.z, loc.z)
                    for child in coll.children:
                        get_bounds(child)

                get_bounds(frontier)

                # Calculate center and size
                center = (min_coord + max_coord) / 2
                size = max_coord - min_coord
                max_dim = max(size.x, size.y, size.z)

                # Position camera to view entire scene
                # Distance based on max dimension and FOV (50mm lens ~40° FOV)
                if cam_data.type == "PERSP":
                    distance = max_dim * 1.5  # 1.5x for comfortable margin
                else:
                    distance = max_dim * 1.2
                    cam_data.ortho_scale = max_dim * 1.2

                # Position camera behind and above center
                cam_obj.location = center + Vector((0.0, -distance, distance * 0.3))
                # Point camera at center
                direction = center - cam_obj.location
                cam_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

                self.report(
                    {"INFO"},
                    f"Camera added and framed to {len(list(frontier.all_objects))} systems",
                )

            # Make this the active camera
            context.scene.camera = cam_obj

            # Set viewport to camera view
            space.region_3d.view_perspective = "CAMERA"
            return {"FINISHED"}


def register():  # pragma: no cover
    if not bpy:
        return
    bpy.utils.register_class(EVE_OT_add_camera)


def unregister():  # pragma: no cover
    if not bpy:
        return
    bpy.utils.unregister_class(EVE_OT_add_camera)
