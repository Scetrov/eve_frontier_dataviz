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
        bl_label = "Set Space HDRI"
        bl_description = "Assign a placeholder HDRI-like lighting (no bundled file)"

        strength: bpy.props.FloatProperty(  # type: ignore[valid-type]
            name="Strength", default=1.0, min=0.0, soft_max=10.0
        )

        def execute(self, context):  # noqa: D401
            world = bpy.context.scene.world  # type: ignore[union-attr]
            if not world:
                world = bpy.data.worlds.new("EVE_Space")  # type: ignore[union-attr]
                bpy.context.scene.world = world  # type: ignore[union-attr]
            world.use_nodes = True
            nt = world.node_tree
            nodes = nt.nodes
            env = next((n for n in nodes if n.type == "TEX_ENVIRONMENT"), None)
            if not env:
                env = nodes.new("ShaderNodeTexEnvironment")
                env.label = "(Placeholder)"
            bg = next(n for n in nodes if n.type == "BACKGROUND")
            bg.inputs[1].default_value = self.strength
            self.report({"INFO"}, "Applied placeholder HDRI setup")
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
