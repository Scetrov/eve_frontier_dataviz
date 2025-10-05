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
        default=50.0,
        min=0.0,
        max=1000000.0,
    )

    density: bpy.props.FloatProperty(  # type: ignore[valid-type]
        name="Density",
        description="Volume density (lower = more subtle)",
        default=0.001,
        min=0.0,
        max=1.0,
    )

    anisotropy: bpy.props.FloatProperty(  # type: ignore[valid-type]
        name="Anisotropy",
        description="Scattering direction (-1=backward, 0=isotropic, 1=forward)",
        default=0.85,
        min=-1.0,
        max=1.0,
    )

    color: bpy.props.FloatVectorProperty(  # type: ignore[valid-type]
        name="Color",
        description="Volume scattering color",
        subtype="COLOR",
        default=(1.0, 0.065, 0.0),
        min=0.0,
        max=1.0,
        size=3,
    )

    noise_scale: bpy.props.FloatProperty(  # type: ignore[valid-type]
        name="Noise Scale",
        description="Scale of 3D noise texture (larger = bigger noise features)",
        default=5.0,
        min=0.1,
        max=100.0,
    )

    noise_detail: bpy.props.FloatProperty(  # type: ignore[valid-type]
        name="Noise Detail",
        description="Amount of fine detail in noise (0-16)",
        default=2.0,
        min=0.0,
        max=16.0,
    )

    noise_strength: bpy.props.FloatProperty(  # type: ignore[valid-type]
        name="Noise Strength",
        description="How much noise affects density (0=uniform, 1=fully broken up)",
        default=0.5,
        min=0.0,
        max=1.0,
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
            output.location = (600, 0)

            # Create principled volume node
            volume = nodes.new("ShaderNodeVolumePrincipled")
            volume.location = (300, 0)

            # Set basic properties
            volume.inputs["Anisotropy"].default_value = self.anisotropy
            volume.inputs["Color"].default_value = (
                self.color[0],
                self.color[1],
                self.color[2],
                1.0,
            )

            # Create 3D noise texture for density variation
            noise_tex = nodes.new("ShaderNodeTexNoise")
            noise_tex.location = (-300, 0)
            noise_tex.inputs["Scale"].default_value = self.noise_scale
            noise_tex.inputs["Detail"].default_value = self.noise_detail
            noise_tex.inputs["Roughness"].default_value = 0.5

            # Create ColorRamp to control noise contrast
            color_ramp = nodes.new("ShaderNodeValToRGB")
            color_ramp.location = (-100, 0)
            color_ramp.color_ramp.interpolation = "LINEAR"
            # Adjust stops for more broken-up appearance
            color_ramp.color_ramp.elements[0].position = 0.3
            color_ramp.color_ramp.elements[1].position = 0.7

            # Create Math node to multiply base density by noise
            math_multiply = nodes.new("ShaderNodeMath")
            math_multiply.operation = "MULTIPLY"
            math_multiply.location = (100, 0)
            math_multiply.inputs[0].default_value = self.density

            # Create Mix node to blend between uniform and noisy density
            mix_node = nodes.new("ShaderNodeMix")
            mix_node.data_type = "FLOAT"  # Mix float values
            mix_node.location = (100, -150)
            mix_node.inputs["Factor"].default_value = self.noise_strength
            mix_node.inputs["A"].default_value = self.density  # Uniform density
            # B will be connected to noisy density

            # Connect noise chain (use Alpha output from ColorRamp for float value)
            links.new(noise_tex.outputs["Fac"], color_ramp.inputs["Fac"])
            links.new(color_ramp.outputs["Alpha"], math_multiply.inputs[1])
            links.new(math_multiply.outputs["Value"], mix_node.inputs["B"])  # Noisy density
            links.new(mix_node.outputs["Result"], volume.inputs["Density"])

            # Connect to output
            links.new(volume.outputs["Volume"], output.inputs["Volume"])
        else:
            # Update existing material properties
            nodes = mat.node_tree.nodes
            links = mat.node_tree.links

            volume = next((n for n in nodes if n.type == "VOLUME_PRINCIPLED"), None)
            noise_tex = next((n for n in nodes if n.type == "TEX_NOISE"), None)
            color_ramp = next((n for n in nodes if n.type == "VALTORGB"), None)
            math_nodes = [n for n in nodes if n.type == "MATH"]
            mix_node = next((n for n in nodes if n.type == "MIX"), None)
            output = next((n for n in nodes if n.type == "OUTPUT_MATERIAL"), None)

            # Update properties
            if volume:
                volume.inputs["Anisotropy"].default_value = self.anisotropy
                volume.inputs["Color"].default_value = (
                    self.color[0],
                    self.color[1],
                    self.color[2],
                    1.0,
                )

            if noise_tex:
                noise_tex.inputs["Scale"].default_value = self.noise_scale
                noise_tex.inputs["Detail"].default_value = self.noise_detail

            # Find the multiply node
            math_multiply = None
            if len(math_nodes) >= 1:
                for node in math_nodes:
                    if node.operation == "MULTIPLY":
                        node.inputs[0].default_value = self.density
                        math_multiply = node
                        break

            # Update mix node
            if mix_node:
                mix_node.inputs["Factor"].default_value = self.noise_strength
                mix_node.inputs["A"].default_value = self.density

            # Recreate connections in case they were broken
            if all([noise_tex, color_ramp, math_multiply, mix_node, volume, output]):
                # Clear existing links
                links.clear()

                # Reconnect noise chain (use Alpha output from ColorRamp for float value)
                links.new(noise_tex.outputs["Fac"], color_ramp.inputs["Fac"])
                links.new(color_ramp.outputs["Alpha"], math_multiply.inputs[1])
                links.new(math_multiply.outputs["Value"], mix_node.inputs["B"])
                links.new(mix_node.outputs["Result"], volume.inputs["Density"])
                links.new(volume.outputs["Volume"], output.inputs["Volume"])

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
