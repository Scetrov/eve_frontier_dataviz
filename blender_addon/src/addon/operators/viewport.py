"""Viewport / environment utility operators."""

from __future__ import annotations

try:  # pragma: no cover
    import bpy  # type: ignore
except Exception:  # noqa: BLE001
    bpy = None  # type: ignore


if bpy:

    class EVE_OT_viewport_set_space(bpy.types.Operator):  # type: ignore
        bl_idname = "eve.viewport_set_space"
        bl_label = "Set Space Black"
        bl_description = "Set world background color to pure black for space visualization"
        bl_options = {"REGISTER", "UNDO"}

        def execute(self, context):  # noqa: D401
            try:
                world = bpy.context.scene.world  # type: ignore[union-attr]
                if not world:
                    world = bpy.data.worlds.new("EVE_Space")  # type: ignore[union-attr]
                    bpy.context.scene.world = world  # type: ignore[union-attr]
                world.use_nodes = True
                bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
                bg.inputs[0].default_value = (0.0, 0.0, 0.0, 1.0)
            except Exception:  # noqa: BLE001
                pass
            self.report({"INFO"}, "World set to black")
            return {"FINISHED"}

    class EVE_OT_viewport_set_hdri(bpy.types.Operator):  # type: ignore
        bl_idname = "eve.viewport_set_hdri"
        bl_label = "Apply Space HDRI"
        bl_description = "Load space HDRI environment texture or use procedural space background if HDRI not found"
        bl_options = {"REGISTER", "UNDO"}

        strength: bpy.props.FloatProperty(  # type: ignore[valid-type]
            name="Strength", default=1.0, min=0.0, soft_max=10.0
        )

        def execute(self, context):  # noqa: D401
            from pathlib import Path

            # Resolve HDRI path relative to addon root (three parents from this file)
            hdri_path = None
            hdri_found = False
            try:
                hdri_path = (
                    Path(__file__).resolve().parents[3]
                    / "hdris"
                    / "space_hdri_deepblue_darker_v2_4k_float32.tiff"
                )
                if hdri_path.exists():
                    hdri_found = True
            except Exception:
                pass

            # If HDRI not found, use procedural space background instead
            if not hdri_found:
                self.report(
                    {"INFO"},
                    "HDRI file not found - using procedural space background instead",
                )
                # Create procedural space-like gradient
                world = bpy.context.scene.world  # type: ignore[union-attr]
                if not world:
                    world = bpy.data.worlds.new("EVE_World")  # type: ignore[union-attr]
                    bpy.context.scene.world = world  # type: ignore[union-attr]
                world.use_nodes = True
                nt = world.node_tree
                nodes = nt.nodes
                links = nt.links

                # Clear existing nodes
                nodes.clear()

                # Create output node
                out = nodes.new("ShaderNodeOutputWorld")
                out.location = (300, 0)

                # Create background shader
                bg = nodes.new("ShaderNodeBackground")
                bg.location = (100, 0)
                bg.inputs[1].default_value = self.strength

                # Create Sky Texture for procedural space
                sky = nodes.new("ShaderNodeTexSky")
                sky.location = (-100, 0)
                sky.sky_type = "NISHITA"
                sky.sun_elevation = 0.0  # Horizon
                sky.sun_rotation = 0.0
                sky.altitude = 0  # Sea level for deep space look
                sky.air_density = 0.0  # No atmosphere
                sky.dust_density = 0.0  # No dust
                sky.ozone_density = 0.0  # No ozone

                # Create ColorRamp to make it darker and more space-like
                color_ramp = nodes.new("ShaderNodeValToRGB")
                color_ramp.location = (-300, 0)
                # Make it very dark
                color_ramp.color_ramp.elements[0].position = 0.0
                color_ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
                color_ramp.color_ramp.elements[1].position = 1.0
                color_ramp.color_ramp.elements[1].color = (0.01, 0.01, 0.02, 1.0)

                # Connect nodes
                links.new(sky.outputs["Color"], color_ramp.inputs["Fac"])
                links.new(color_ramp.outputs["Color"], bg.inputs["Color"])
                links.new(bg.outputs["Background"], out.inputs["Surface"])

                self.report({"INFO"}, "Applied procedural space background")
                return {"FINISHED"}

            # HDRI found - use it
            world = bpy.context.scene.world  # type: ignore[union-attr]
            if not world:
                world = bpy.data.worlds.new("EVE_World")  # type: ignore[union-attr]
                bpy.context.scene.world = world  # type: ignore[union-attr]
            world.use_nodes = True
            nt = world.node_tree
            nodes = nt.nodes
            links = nt.links
            out = next((n for n in nodes if n.type == "OUTPUT_WORLD"), None)
            if not out:
                out = nodes.new("ShaderNodeOutputWorld")
            bg = next((n for n in nodes if n.type == "BACKGROUND"), None)
            if not bg:
                bg = nodes.new("ShaderNodeBackground")
            bg.inputs[1].default_value = self.strength
            env = next((n for n in nodes if n.type == "TEX_ENVIRONMENT"), None)
            if not env:
                env = nodes.new("ShaderNodeTexEnvironment")
                env.location = (-400, 0)
            # Load or reuse image
            img = bpy.data.images.get(hdri_path.name)
            if not img:
                try:
                    img = bpy.data.images.load(str(hdri_path))
                except Exception as e:
                    self.report({"ERROR"}, f"Load failed: {e}")
                    return {"CANCELLED"}
            env.image = img
            try:
                if hasattr(env.image, "colorspace_settings"):
                    env.image.colorspace_settings.name = "Linear"
            except Exception:
                pass
            # Rewire links
            try:
                for link in list(env.outputs[0].links):
                    nt.links.remove(link)
                for link in list(bg.outputs[0].links):
                    nt.links.remove(link)
                links.new(env.outputs[0], bg.inputs[0])
                links.new(bg.outputs[0], out.inputs[0])
            except Exception:
                pass
            self.report({"INFO"}, f"Applied HDRI: {hdri_path.name}")
            return {"FINISHED"}

    class EVE_OT_viewport_set_clip(bpy.types.Operator):  # type: ignore
        bl_idname = "eve.viewport_set_clip"
        bl_label = "Set Clip End 100km"
        bl_description = "Adjust 3D viewport clip end distance to render distant star systems (default 300 BU for ~190 BU galaxy diameter)"
        bl_options = {"REGISTER"}

        clip_end: bpy.props.FloatProperty(  # type: ignore[valid-type]
            name="Clip End", default=100000.0, min=1000.0, soft_max=1000000.0
        )

        def execute(self, context):  # noqa: D401
            for area in context.screen.areas:
                if area.type != "VIEW_3D":
                    continue
                for space in area.spaces:
                    if space.type == "VIEW_3D":
                        space.clip_end = self.clip_end
            self.report({"INFO"}, f"Clip end set to {self.clip_end}")
            return {"FINISHED"}

    class EVE_OT_viewport_hide_overlays(bpy.types.Operator):  # type: ignore
        bl_idname = "eve.viewport_hide_overlays"
        bl_label = "Hide Grid & Axis"
        bl_description = "Toggle floor grid and coordinate axes visibility in all 3D viewports for cleaner visualization"
        bl_options = {"REGISTER"}

        def execute(self, context):  # noqa: D401
            toggled = 0
            for area in context.screen.areas:
                if area.type != "VIEW_3D":
                    continue
                for space in area.spaces:
                    if space.type == "VIEW_3D":
                        space.overlay.show_floor = not space.overlay.show_floor
                        space.overlay.show_axis_x = not space.overlay.show_axis_x
                        space.overlay.show_axis_y = not space.overlay.show_axis_y
                        toggled += 1
            self.report({"INFO"}, f"Toggled overlays in {toggled} view(s)")
            return {"FINISHED"}

    class EVE_OT_viewport_frame_all(bpy.types.Operator):  # type: ignore
        bl_idname = "eve.viewport_frame_all"
        bl_label = "Frame All Stars"
        bl_description = "Zoom and center viewport camera to fit all star system objects in view"
        bl_options = {"REGISTER"}

        def execute(self, context):  # noqa: D401
            # Find all system objects in the Frontier collection
            systems = []
            frontier = bpy.data.collections.get("Frontier")  # type: ignore[union-attr]
            if frontier:

                def _collect_recursive(collection):
                    systems.extend(collection.objects)
                    for child in collection.children:
                        _collect_recursive(child)

                _collect_recursive(frontier)

            if not systems:
                self.report({"WARNING"}, "No systems found in Frontier collection")
                return {"CANCELLED"}

            # Deselect all, then select all systems
            try:
                bpy.ops.object.select_all(action="DESELECT")
                for obj in systems:
                    obj.select_set(True)

                # Frame selected objects in all 3D viewports
                for area in context.screen.areas:
                    if area.type != "VIEW_3D":
                        continue
                    for region in area.regions:
                        if region.type == "WINDOW":
                            with context.temp_override(area=area, region=region):
                                bpy.ops.view3d.view_selected()

                # Deselect all systems after framing
                bpy.ops.object.select_all(action="DESELECT")

                self.report({"INFO"}, f"Framed {len(systems)} systems in viewport")
            except Exception as e:  # noqa: BLE001
                self.report({"ERROR"}, f"Failed to frame view: {e}")
                return {"CANCELLED"}

            return {"FINISHED"}


def register():  # pragma: no cover
    if not bpy:
        return
    bpy.utils.register_class(EVE_OT_viewport_set_space)
    bpy.utils.register_class(EVE_OT_viewport_set_hdri)
    bpy.utils.register_class(EVE_OT_viewport_set_clip)
    bpy.utils.register_class(EVE_OT_viewport_hide_overlays)
    bpy.utils.register_class(EVE_OT_viewport_frame_all)


def unregister():  # pragma: no cover
    if not bpy:
        return
    bpy.utils.unregister_class(EVE_OT_viewport_frame_all)
    bpy.utils.unregister_class(EVE_OT_viewport_hide_overlays)
    bpy.utils.unregister_class(EVE_OT_viewport_set_clip)
    bpy.utils.unregister_class(EVE_OT_viewport_set_hdri)
    bpy.utils.unregister_class(EVE_OT_viewport_set_space)
