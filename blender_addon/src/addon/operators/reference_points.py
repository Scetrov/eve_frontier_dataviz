"""Reference point system for spatial orientation.

Creates visual landmarks (text labels) to help identify locations in the star map.
This module is self-contained and can be easily disabled/removed.
"""

from __future__ import annotations

try:  # pragma: no cover
    import bpy  # type: ignore
except Exception:  # noqa: BLE001
    bpy = None  # type: ignore

from .. import data_state
from ..preferences import get_prefs

if bpy:  # Only define classes when Blender API is present

    class EVE_OT_add_reference_points(bpy.types.Operator):  # type: ignore[misc,name-defined]
        """Add text labels for navigation landmarks."""

        bl_idname = "eve.add_reference_points"
        bl_label = "Add Reference Points"
        bl_description = "Add text labels for black holes and constellation centers"
        bl_options = {"REGISTER", "UNDO"}

        show_blackholes: bpy.props.BoolProperty(  # type: ignore[valid-type]
            name="Black Hole Labels",
            default=True,
            description="Show labels for the three black hole systems",
        )

        show_constellations: bpy.props.BoolProperty(  # type: ignore[valid-type]
            name="Constellation Centers",
            default=True,
            description="Show labels for largest constellation centers",
        )

        constellation_count: bpy.props.IntProperty(  # type: ignore[valid-type]
            name="Constellation Count",
            default=10,
            min=0,
            max=50,
            description="Number of constellation labels to show (largest first)",
        )

        label_size: bpy.props.FloatProperty(  # type: ignore[valid-type]
            name="Label Size",
            default=1.0,
            min=0.1,
            max=10.0,
            description="Size of text labels (in Blender units, scaled for 1e-18 coordinate system)",
        )

        def execute(self, context):  # noqa: D401
            """Create reference point labels."""
            if not bpy or not hasattr(bpy, "data"):
                self.report({"ERROR"}, "Blender context not available")
                return {"CANCELLED"}

            # Check if Frontier collection exists
            frontier = bpy.data.collections.get("Frontier")  # type: ignore[union-attr]
            if not frontier:
                self.report({"ERROR"}, "Frontier collection not found. Build scene first.")
                return {"CANCELLED"}

            # Get or create reference points collection
            ref_coll_name = "EVE_ReferencePoints"
            ref_coll = bpy.data.collections.get(ref_coll_name)  # type: ignore[union-attr]

            if not ref_coll:
                ref_coll = bpy.data.collections.new(ref_coll_name)  # type: ignore[union-attr]
                frontier.children.link(ref_coll)
            else:
                # Clear existing labels
                for obj in list(ref_coll.objects):
                    bpy.data.objects.remove(obj, do_unlink=True)  # type: ignore[attr-defined]

            created_count = 0
            prefs = get_prefs(context)
            scale = float(getattr(prefs, "scale_factor", 1.0) or 1.0)
            apply_axis = bool(getattr(prefs, "apply_axis_transform", False))

            # Add black hole labels
            if self.show_blackholes:
                created_count += self._add_blackhole_labels(
                    context, ref_coll, scale, apply_axis, self.label_size
                )

            # Add constellation center labels
            if self.show_constellations and self.constellation_count > 0:
                created_count += self._add_constellation_labels(
                    context, ref_coll, scale, apply_axis, self.label_size, self.constellation_count
                )

            if created_count == 0:
                self.report({"WARNING"}, "No reference points created (check options)")
                return {"CANCELLED"}

            self.report({"INFO"}, f"Created {created_count} reference point labels")
            return {"FINISHED"}

        def _add_blackhole_labels(self, context, collection, scale, apply_axis, label_size):
            """Add text labels for the three black hole systems."""
            # Black hole IDs are universal constants
            blackhole_ids = [30000001, 30000002, 30000003]
            created = 0

            # Find black hole objects in the scene
            frontier = bpy.data.collections.get("Frontier")  # type: ignore[union-attr]
            if not frontier:
                return 0

            blackhole_objects = []

            def find_blackholes(coll):
                for obj in coll.objects:
                    if "eve_system_id" in obj and obj["eve_system_id"] in blackhole_ids:
                        blackhole_objects.append(obj)
                for child in coll.children:
                    find_blackholes(child)

            find_blackholes(frontier)

            # Create text labels at black hole positions
            for bh_obj in blackhole_objects:
                # Get system name from object
                label_text = bh_obj.name

                # Create text object
                curve_data = bpy.data.curves.new(name=f"Label_{label_text}", type="FONT")  # type: ignore[union-attr]
                curve_data.body = f"⚫ {label_text}"  # Black circle emoji + name
                curve_data.size = label_size
                curve_data.align_x = "CENTER"
                curve_data.align_y = "CENTER"

                text_obj = bpy.data.objects.new(f"REF_BH_{label_text}", curve_data)  # type: ignore[union-attr]
                collection.objects.link(text_obj)

                # Position at black hole location (with small offset up)
                loc = bh_obj.location
                text_obj.location = (loc[0], loc[1], loc[2] + label_size * 2)

                # Make text billboard (always face camera)
                constraint = text_obj.constraints.new(type="TRACK_TO")
                if context.scene.camera:
                    constraint.target = context.scene.camera
                    constraint.track_axis = "TRACK_NEGATIVE_Z"
                    constraint.up_axis = "UP_Y"

                # Set material to burnt orange emission (visible from far away)
                mat = bpy.data.materials.get("EVE_RefLabel_BlackHole")  # type: ignore[union-attr]
                if not mat:
                    mat = bpy.data.materials.new("EVE_RefLabel_BlackHole")  # type: ignore[union-attr]
                    mat.use_nodes = True
                    nodes = mat.node_tree.nodes
                    nodes.clear()
                    emission = nodes.new("ShaderNodeEmission")
                    emission.inputs[0].default_value = (1.0, 0.4, 0.1, 1.0)  # Burnt orange
                    emission.inputs[1].default_value = 5.0  # Strength
                    output = nodes.new("ShaderNodeOutputMaterial")
                    mat.node_tree.links.new(emission.outputs[0], output.inputs[0])

                if curve_data.materials:
                    curve_data.materials[0] = mat
                else:
                    curve_data.materials.append(mat)

                created += 1

            return created

        def _add_constellation_labels(
            self, context, collection, scale, apply_axis, label_size, count
        ):
            """Add text labels for largest constellation centers."""
            systems = data_state.get_loaded_systems()
            if not systems:
                return 0

            # Calculate constellation centers and sizes
            constellation_data = {}
            for sys in systems:
                const_id = getattr(sys, "constellation_id", None)
                const_name = getattr(sys, "constellation_name", None)
                if not const_id or not const_name:
                    continue

                if const_id not in constellation_data:
                    constellation_data[const_id] = {
                        "name": const_name,
                        "systems": [],
                        "region": getattr(sys, "region_name", "Unknown"),
                    }

                constellation_data[const_id]["systems"].append(sys)

            # Calculate centers and sort by size
            const_centers = []
            for _const_id, data in constellation_data.items():
                if len(data["systems"]) < 5:  # Skip very small constellations
                    continue

                # Calculate center point
                avg_x = sum(s.x for s in data["systems"]) / len(data["systems"])
                avg_y = sum(s.y for s in data["systems"]) / len(data["systems"])
                avg_z = sum(s.z for s in data["systems"]) / len(data["systems"])

                const_centers.append(
                    {
                        "name": data["name"],
                        "region": data["region"],
                        "count": len(data["systems"]),
                        "x": avg_x,
                        "y": avg_y,
                        "z": avg_z,
                    }
                )

            # Sort by system count and take top N
            const_centers.sort(key=lambda c: c["count"], reverse=True)
            const_centers = const_centers[:count]

            created = 0
            for const in const_centers:
                # Apply scaling and axis transform
                x, y, z = const["x"] * scale, const["y"] * scale, const["z"] * scale
                if apply_axis:
                    x, y, z = x, z, -y

                # Create text object
                label_text = f"{const['name']} ({const['count']})"
                curve_data = bpy.data.curves.new(  # type: ignore[union-attr]
                    name=f"Label_Const_{const['name']}", type="FONT"
                )
                curve_data.body = label_text
                curve_data.size = label_size * 0.6  # Smaller than black hole labels
                curve_data.align_x = "CENTER"
                curve_data.align_y = "CENTER"

                text_obj = bpy.data.objects.new(  # type: ignore[union-attr]
                    f"REF_CONST_{const['name']}", curve_data
                )
                collection.objects.link(text_obj)
                text_obj.location = (x, y, z)

                # Billboard constraint
                constraint = text_obj.constraints.new(type="TRACK_TO")
                if context.scene.camera:
                    constraint.target = context.scene.camera
                    constraint.track_axis = "TRACK_NEGATIVE_Z"
                    constraint.up_axis = "UP_Y"

                # Set material to burnt orange emission (matching black hole labels)
                mat = bpy.data.materials.get("EVE_RefLabel_Constellation")  # type: ignore[union-attr]
                if not mat:
                    mat = bpy.data.materials.new("EVE_RefLabel_Constellation")  # type: ignore[union-attr]
                    mat.use_nodes = True
                    nodes = mat.node_tree.nodes
                    nodes.clear()
                    emission = nodes.new("ShaderNodeEmission")
                    emission.inputs[0].default_value = (1.0, 0.4, 0.1, 1.0)  # Burnt orange
                    emission.inputs[1].default_value = 2.0  # Strength (dimmer than black holes)
                    output = nodes.new("ShaderNodeOutputMaterial")
                    mat.node_tree.links.new(emission.outputs[0], output.inputs[0])

                if curve_data.materials:
                    curve_data.materials[0] = mat
                else:
                    curve_data.materials.append(mat)

                created += 1

            return created

    class EVE_OT_remove_reference_points(bpy.types.Operator):  # type: ignore[misc,name-defined]
        """Remove all reference point labels."""

        bl_idname = "eve.remove_reference_points"
        bl_label = "Remove Reference Points"
        bl_description = "Remove all reference point labels from the scene"
        bl_options = {"REGISTER", "UNDO"}

        def execute(self, context):  # noqa: D401
            """Remove reference points collection."""
            if not bpy or not hasattr(bpy, "data"):
                self.report({"ERROR"}, "Blender context not available")
                return {"CANCELLED"}

            ref_coll = bpy.data.collections.get("EVE_ReferencePoints")  # type: ignore[union-attr]
            if ref_coll:
                # Remove all objects
                for obj in list(ref_coll.objects):
                    bpy.data.objects.remove(obj, do_unlink=True)  # type: ignore[attr-defined]

                # Remove collection
                bpy.data.collections.remove(ref_coll)  # type: ignore[union-attr]

                self.report({"INFO"}, "Reference points removed")
            else:
                self.report({"WARNING"}, "No reference points found")

            return {"FINISHED"}


def register():  # pragma: no cover - Blender runtime usage
    """Register reference point operators."""
    if bpy:
        bpy.utils.register_class(EVE_OT_add_reference_points)
        bpy.utils.register_class(EVE_OT_remove_reference_points)


def unregister():  # pragma: no cover - Blender runtime usage
    """Unregister reference point operators."""
    if bpy:
        bpy.utils.unregister_class(EVE_OT_remove_reference_points)
        bpy.utils.unregister_class(EVE_OT_add_reference_points)
