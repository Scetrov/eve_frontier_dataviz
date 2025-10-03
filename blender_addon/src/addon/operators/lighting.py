"""Lighting operators for highlighting special systems."""

from __future__ import annotations

try:  # pragma: no cover
    import bpy  # type: ignore
except Exception:  # noqa: BLE001
    bpy = None  # type: ignore

if bpy:  # Only define classes when Blender API is present

    class EVE_OT_add_blackhole_lights(bpy.types.Operator):  # type: ignore[misc,name-defined]
        """Add bright point lights at black hole positions."""

        bl_idname = "eve.add_blackhole_lights"
        bl_label = "Add Black Hole Lights"
        bl_description = "Add bright point lights at black hole system positions"
        bl_options = {"REGISTER", "UNDO"}

        light_power: bpy.props.FloatProperty(  # type: ignore[valid-type]
            name="Light Power",
            default=1000000.0,
            min=1000.0,
            soft_max=10000000.0,
            description="Power of the point lights (in Watts)",
        )

        light_radius: bpy.props.FloatProperty(  # type: ignore[valid-type]
            name="Light Radius",
            default=50000.0,
            min=100.0,
            soft_max=500000.0,
            description="Radius of influence for the lights",
        )

        def execute(self, context):  # noqa: D401
            """Create point lights at black hole system positions."""
            if not bpy or not hasattr(bpy, "data"):
                self.report({"ERROR"}, "Blender context not available")
                return {"CANCELLED"}

            # Check if Frontier collection exists
            frontier = bpy.data.collections.get("Frontier")  # type: ignore[union-attr]
            if not frontier:
                self.report({"ERROR"}, "Frontier collection not found. Build scene first.")
                return {"CANCELLED"}

            # Find all black hole system objects
            blackhole_objects = []

            def find_blackholes(collection):
                for obj in collection.objects:
                    # Check if object has eve_is_blackhole property set to 1
                    if "eve_is_blackhole" in obj and obj["eve_is_blackhole"] == 1:
                        blackhole_objects.append(obj)
                for child in collection.children:
                    find_blackholes(child)

            find_blackholes(frontier)

            if not blackhole_objects:
                self.report({"WARNING"}, "No black hole systems found in scene")
                return {"CANCELLED"}

            # Get or create EVE_Lights collection
            lights_coll_name = "EVE_BlackHole_Lights"
            lights_coll = bpy.data.collections.get(lights_coll_name)  # type: ignore[union-attr]

            if not lights_coll:
                lights_coll = bpy.data.collections.new(lights_coll_name)  # type: ignore[union-attr]
                frontier.children.link(lights_coll)
            else:
                # Clear existing lights
                for obj in list(lights_coll.objects):
                    bpy.data.objects.remove(obj, do_unlink=True)  # type: ignore[attr-defined]

            # Create a bright point light at each black hole position
            created_count = 0
            for bh_obj in blackhole_objects:
                # Create light data
                light_data = bpy.data.lights.new(  # type: ignore[attr-defined]
                    name=f"BlackHole_Light_{bh_obj.name}", type="POINT"
                )

                # Set light properties for very bright visibility
                light_data.energy = self.light_power
                light_data.shadow_soft_size = self.light_radius

                # Set color to bright white with slight blue tint (like accretion disk)
                light_data.color = (0.9, 0.95, 1.0)

                # Create light object
                light_obj = bpy.data.objects.new(  # type: ignore[attr-defined]
                    f"BlackHole_Light_{bh_obj.name}", light_data
                )

                # Position at black hole system location
                light_obj.location = bh_obj.matrix_world.translation

                # Link to lights collection
                lights_coll.objects.link(light_obj)

                created_count += 1

            self.report(
                {"INFO"},
                f"Created {created_count} black hole lights (Power: {self.light_power:,.0f}W)",
            )
            return {"FINISHED"}

    class EVE_OT_remove_blackhole_lights(bpy.types.Operator):  # type: ignore[misc,name-defined]
        """Remove black hole lights."""

        bl_idname = "eve.remove_blackhole_lights"
        bl_label = "Remove Black Hole Lights"
        bl_description = "Remove all black hole point lights"

        def execute(self, context):  # noqa: D401
            """Remove EVE_BlackHole_Lights collection and all its lights."""
            if not bpy or not hasattr(bpy, "data"):
                self.report({"ERROR"}, "Blender context not available")
                return {"CANCELLED"}

            lights_coll = bpy.data.collections.get("EVE_BlackHole_Lights")  # type: ignore[union-attr]

            if not lights_coll:
                self.report({"INFO"}, "No black hole lights to remove")
                return {"CANCELLED"}

            # Remove all objects in the collection
            for obj in list(lights_coll.objects):
                bpy.data.objects.remove(obj, do_unlink=True)  # type: ignore[attr-defined]

            # Remove the collection itself
            bpy.data.collections.remove(lights_coll)  # type: ignore[attr-defined]

            self.report({"INFO"}, "Removed black hole lights")
            return {"FINISHED"}


def register():  # pragma: no cover
    if not bpy:
        return
    bpy.utils.register_class(EVE_OT_add_blackhole_lights)
    bpy.utils.register_class(EVE_OT_remove_blackhole_lights)


def unregister():  # pragma: no cover
    if not bpy:
        return
    bpy.utils.unregister_class(EVE_OT_remove_blackhole_lights)
    bpy.utils.unregister_class(EVE_OT_add_blackhole_lights)
