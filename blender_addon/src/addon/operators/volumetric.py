"""Volumetric atmosphere operator for star field."""

from __future__ import annotations

try:  # pragma: no cover
    import bpy  # type: ignore
except Exception:  # noqa: BLE001
    bpy = None  # type: ignore


class EVE_OT_add_volumetric(bpy.types.Operator):  # type: ignore[misc,name-defined]
    """Add volumetric scattering cube around star field."""

    bl_idname = "eve.add_volumetric"
    bl_label = "Add Volumetric Atmosphere"
    bl_options = {"REGISTER", "UNDO"}

    padding: bpy.props.FloatProperty(  # type: ignore[valid-type]
        name="Padding",
        description="Extra space around bounding box (in meters)",
        default=50000.0,
        min=0.0,
        max=1000000.0,
    )

    density: bpy.props.FloatProperty(  # type: ignore[valid-type]
        name="Density",
        description="Volume density (lower = more subtle)",
        default=0.00001,
        min=0.0,
        max=1.0,
    )

    anisotropy: bpy.props.FloatProperty(  # type: ignore[valid-type]
        name="Anisotropy",
        description="Scattering direction (-1=backward, 0=isotropic, 1=forward)",
        default=0.0,
        min=-1.0,
        max=1.0,
    )

    color: bpy.props.FloatVectorProperty(  # type: ignore[valid-type]
        name="Color",
        description="Volume scattering color",
        subtype="COLOR",
        default=(0.5, 0.7, 1.0),
        min=0.0,
        max=1.0,
        size=3,
    )

    def execute(self, context):  # noqa: D401
        """Create volumetric cube."""
        if not bpy or not hasattr(bpy, "data"):
            self.report({"ERROR"}, "Blender context not available")
            return {"CANCELLED"}

        # Find Frontier collection to get bounding box
        frontier = bpy.data.collections.get("Frontier")  # type: ignore[union-attr]
        if not frontier:
            self.report({"ERROR"}, "Frontier collection not found. Build scene first.")
            return {"CANCELLED"}

        # Collect all objects
        objects = []

        def _collect_recursive(collection):
            objects.extend(collection.objects)
            for child in collection.children:
                _collect_recursive(child)

        _collect_recursive(frontier)

        if not objects:
            self.report({"ERROR"}, "No objects found in Frontier collection")
            return {"CANCELLED"}

        # Calculate bounding box
        min_x = min_y = min_z = float("inf")
        max_x = max_y = max_z = float("-inf")

        for obj in objects:
            # Get object world location
            loc = obj.matrix_world.translation
            min_x = min(min_x, loc.x)
            min_y = min(min_y, loc.y)
            min_z = min(min_z, loc.z)
            max_x = max(max_x, loc.x)
            max_y = max(max_y, loc.y)
            max_z = max(max_z, loc.z)

        # Add padding
        min_x -= self.padding
        min_y -= self.padding
        min_z -= self.padding
        max_x += self.padding
        max_y += self.padding
        max_z += self.padding

        # Calculate center and dimensions
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        center_z = (min_z + max_z) / 2

        size_x = max_x - min_x
        size_y = max_y - min_y
        size_z = max_z - min_z

        # Create or get volumetric cube
        cube_name = "EVE_VolumetricAtmosphere"
        cube = bpy.data.objects.get(cube_name)  # type: ignore[union-attr]

        if cube:
            # Update existing cube
            cube.location = (center_x, center_y, center_z)
            cube.scale = (size_x / 2, size_y / 2, size_z / 2)
        else:
            # Create new cube
            bpy.ops.mesh.primitive_cube_add(size=1.0, location=(center_x, center_y, center_z))
            cube = context.active_object
            cube.name = cube_name
            cube.scale = (size_x / 2, size_y / 2, size_z / 2)

            # Move to Frontier collection
            for coll in cube.users_collection:
                coll.objects.unlink(cube)
            frontier.objects.link(cube)

        # Create or update material
        mat_name = "EVE_VolumetricMaterial"
        mat = bpy.data.materials.get(mat_name)  # type: ignore[attr-defined]

        if not mat:
            mat = bpy.data.materials.new(mat_name)  # type: ignore[attr-defined]
            mat.use_nodes = True

            # Setup volumetric shader
            nodes = mat.node_tree.nodes
            links = mat.node_tree.links

            # Clear default nodes
            nodes.clear()

            # Create output node
            output = nodes.new("ShaderNodeOutputMaterial")
            output.location = (400, 0)

            # Create principled volume node
            volume = nodes.new("ShaderNodeVolumePrincipled")
            volume.location = (0, 0)

            # Set properties
            volume.inputs["Density"].default_value = self.density
            volume.inputs["Anisotropy"].default_value = self.anisotropy
            volume.inputs["Color"].default_value = (
                self.color[0],
                self.color[1],
                self.color[2],
                1.0,
            )

            # Connect to output
            links.new(volume.outputs["Volume"], output.inputs["Volume"])
        else:
            # Update existing material properties
            nodes = mat.node_tree.nodes
            volume = next((n for n in nodes if n.type == "VOLUME_PRINCIPLED"), None)
            if volume:
                volume.inputs["Density"].default_value = self.density
                volume.inputs["Anisotropy"].default_value = self.anisotropy
                volume.inputs["Color"].default_value = (
                    self.color[0],
                    self.color[1],
                    self.color[2],
                    1.0,
                )

        # Assign material to cube
        if cube.data.materials:
            cube.data.materials[0] = mat
        else:
            cube.data.materials.append(mat)

        # Set cube to not cast shadows and render as volume
        cube.display_type = "WIRE"  # Show as wireframe in viewport
        cube.hide_render = False

        self.report(
            {"INFO"},
            f"Volumetric atmosphere created: {size_x:.0f}×{size_y:.0f}×{size_z:.0f}m",
        )
        return {"FINISHED"}


class EVE_OT_remove_volumetric(bpy.types.Operator):  # type: ignore[misc,name-defined]
    """Remove volumetric atmosphere cube."""

    bl_idname = "eve.remove_volumetric"
    bl_label = "Remove Volumetric Atmosphere"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):  # noqa: D401
        """Remove volumetric cube and material."""
        if not bpy or not hasattr(bpy, "data"):
            self.report({"ERROR"}, "Blender context not available")
            return {"CANCELLED"}

        cube_name = "EVE_VolumetricAtmosphere"
        cube = bpy.data.objects.get(cube_name)  # type: ignore[union-attr]

        if cube:
            bpy.data.objects.remove(cube, do_unlink=True)  # type: ignore[attr-defined]
            self.report({"INFO"}, "Removed volumetric atmosphere cube")
        else:
            self.report({"WARNING"}, "No volumetric atmosphere cube found")

        return {"FINISHED"}


def register():  # pragma: no cover
    if not bpy:
        return
    bpy.utils.register_class(EVE_OT_add_volumetric)
    bpy.utils.register_class(EVE_OT_remove_volumetric)


def unregister():  # pragma: no cover
    if not bpy:
        return
    bpy.utils.unregister_class(EVE_OT_remove_volumetric)
    bpy.utils.unregister_class(EVE_OT_add_volumetric)
