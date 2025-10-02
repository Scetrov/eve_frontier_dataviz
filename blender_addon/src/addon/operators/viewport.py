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
        bl_description = "Set world background to black"

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
        bl_description = "Load space HDRI for environment lighting"

        strength: bpy.props.FloatProperty(  # type: ignore[valid-type]
            name="Strength", default=1.0, min=0.0, soft_max=10.0
        )

        def execute(self, context):  # noqa: D401
            from pathlib import Path

            # Resolve HDRI path relative to addon root (three parents from this file)
            try:
                hdri_path = (
                    Path(__file__).resolve().parents[3]
                    / "hdris"
                    / "space_hdri_deepblue_darker_v2_4k_float32.tiff"
                )
            except Exception:
                self.report({"ERROR"}, "Failed to resolve HDRI path")
                return {"CANCELLED"}
            if not hdri_path.exists():
                self.report({"ERROR"}, f"HDRI not found: {hdri_path.name}")
                return {"CANCELLED"}

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
        bl_description = "Set 3D view clip end distance"

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
        bl_description = "Toggle floor grid and axis in all 3D viewports"

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


def register():  # pragma: no cover
    if not bpy:
        return
    bpy.utils.register_class(EVE_OT_viewport_set_space)
    bpy.utils.register_class(EVE_OT_viewport_set_hdri)
    bpy.utils.register_class(EVE_OT_viewport_set_clip)
    bpy.utils.register_class(EVE_OT_viewport_hide_overlays)


def unregister():  # pragma: no cover
    if not bpy:
        return
    bpy.utils.unregister_class(EVE_OT_viewport_hide_overlays)
    bpy.utils.unregister_class(EVE_OT_viewport_set_clip)
    bpy.utils.unregister_class(EVE_OT_viewport_set_hdri)
    bpy.utils.unregister_class(EVE_OT_viewport_set_space)
