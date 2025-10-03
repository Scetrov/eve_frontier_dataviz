"""Build jump connection lines operator."""

from __future__ import annotations

try:  # pragma: no cover
    import bpy  # type: ignore
except Exception:  # noqa: BLE001
    bpy = None  # type: ignore

from .. import data_state


class EVE_OT_build_jumps(bpy.types.Operator):  # type: ignore[misc,name-defined]
    """Build jump connection lines between systems."""

    bl_idname = "eve.build_jumps"
    bl_label = "Build Jump Lines"
    bl_description = "Create visual lines connecting systems via jumps"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):  # noqa: D401
        """Build jump lines as curve objects."""
        if not bpy or not hasattr(bpy, "data"):
            self.report({"ERROR"}, "Blender context not available")
            return {"CANCELLED"}

        jumps = data_state.get_loaded_jumps()
        if not jumps:
            self.report({"ERROR"}, "No jump data loaded. Load data first.")
            return {"CANCELLED"}

        systems = data_state.get_loaded_systems()
        if not systems:
            self.report({"ERROR"}, "No system data loaded. Build scene first.")
            return {"CANCELLED"}

        # Build system ID to object lookup
        frontier = bpy.data.collections.get("Frontier")  # type: ignore[union-attr]
        if not frontier:
            self.report({"ERROR"}, "Frontier collection not found. Build scene first.")
            return {"CANCELLED"}

        system_objects = {}

        def _collect_systems(collection):
            for obj in collection.objects:
                # Check if object has eve_system_id custom property
                if "eve_system_id" in obj:
                    system_objects[obj["eve_system_id"]] = obj
            for child in collection.children:
                _collect_systems(child)

        _collect_systems(frontier)

        if not system_objects:
            self.report({"ERROR"}, "No system objects found in scene")
            return {"CANCELLED"}

        # Get or create EVE_Jumps collection
        jumps_coll_name = "EVE_Jumps"
        jumps_coll = bpy.data.collections.get(jumps_coll_name)  # type: ignore[union-attr]

        if not jumps_coll:
            jumps_coll = bpy.data.collections.new(jumps_coll_name)  # type: ignore[union-attr]
            frontier.children.link(jumps_coll)
        else:
            # Clear existing jump objects
            for obj in list(jumps_coll.objects):
                bpy.data.objects.remove(obj, do_unlink=True)  # type: ignore[attr-defined]

        # Create jump material
        mat_name = "EVE_JumpMaterial"
        mat = bpy.data.materials.get(mat_name)  # type: ignore[attr-defined]

        if not mat:
            mat = bpy.data.materials.new(mat_name)  # type: ignore[attr-defined]
            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            links = mat.node_tree.links

            # Clear default nodes
            nodes.clear()

            # Create output node
            output = nodes.new("ShaderNodeOutputMaterial")
            output.location = (200, 0)

            # Create emission shader for the lines
            emission = nodes.new("ShaderNodeEmission")
            emission.location = (0, 0)
            emission.inputs["Color"].default_value = (0.2, 0.5, 0.8, 1.0)  # Cyan color
            emission.inputs["Strength"].default_value = 1.0

            # Connect
            links.new(emission.outputs["Emission"], output.inputs["Surface"])

        # Create jump lines
        created_count = 0
        skipped_count = 0

        for jump in jumps:
            from_obj = system_objects.get(jump.from_system_id)
            to_obj = system_objects.get(jump.to_system_id)

            if not from_obj or not to_obj:
                skipped_count += 1
                continue

            # Create a curve for this jump
            curve_data = bpy.data.curves.new(  # type: ignore[attr-defined]
                name=f"Jump_{jump.from_system_id}_{jump.to_system_id}", type="CURVE"
            )
            curve_data.dimensions = "3D"
            curve_data.bevel_depth = 0.5  # Make lines visible
            curve_data.resolution_u = 1  # Low resolution for performance

            # Create a spline (line segment)
            spline = curve_data.splines.new("POLY")
            spline.points.add(1)  # Add one more point (total 2 points)

            # Set point positions
            from_loc = from_obj.matrix_world.translation
            to_loc = to_obj.matrix_world.translation

            spline.points[0].co = (from_loc.x, from_loc.y, from_loc.z, 1.0)
            spline.points[1].co = (to_loc.x, to_loc.y, to_loc.z, 1.0)

            # Create object from curve
            curve_obj = bpy.data.objects.new(  # type: ignore[attr-defined]
                f"Jump_{jump.from_system_id}_{jump.to_system_id}", curve_data
            )

            # Assign material
            curve_obj.data.materials.append(mat)

            # Link to jumps collection
            jumps_coll.objects.link(curve_obj)

            created_count += 1

        self.report({"INFO"}, f"Created {created_count} jump lines ({skipped_count} skipped)")
        return {"FINISHED"}


class EVE_OT_toggle_jumps(bpy.types.Operator):  # type: ignore[misc,name-defined]
    """Toggle visibility of jump lines."""

    bl_idname = "eve.toggle_jumps"
    bl_label = "Toggle Jump Visibility"
    bl_description = "Show/hide jump connection lines"

    def execute(self, context):  # noqa: D401
        """Toggle EVE_Jumps collection visibility."""
        if not bpy or not hasattr(bpy, "data"):
            self.report({"ERROR"}, "Blender context not available")
            return {"CANCELLED"}

        jumps_coll = bpy.data.collections.get("EVE_Jumps")  # type: ignore[union-attr]

        if not jumps_coll:
            self.report({"WARNING"}, "No jump lines found. Build jumps first.")
            return {"CANCELLED"}

        # Toggle hide_viewport
        jumps_coll.hide_viewport = not jumps_coll.hide_viewport

        status = "hidden" if jumps_coll.hide_viewport else "visible"
        self.report({"INFO"}, f"Jump lines {status}")

        return {"FINISHED"}


def register():  # pragma: no cover
    if not bpy:
        return
    bpy.utils.register_class(EVE_OT_build_jumps)
    bpy.utils.register_class(EVE_OT_toggle_jumps)


def unregister():  # pragma: no cover
    if not bpy:
        return
    bpy.utils.unregister_class(EVE_OT_toggle_jumps)
    bpy.utils.unregister_class(EVE_OT_build_jumps)
