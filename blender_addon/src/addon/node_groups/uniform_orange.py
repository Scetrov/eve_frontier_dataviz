"""Uniform Orange strategy node group.

Simple uniform orange-red color for all stars.
"""

from __future__ import annotations

try:  # pragma: no cover
    import bpy  # type: ignore
except Exception:  # noqa: BLE001
    bpy = None  # type: ignore


def ensure_node_group():
    """Create or update the Uniform Orange node group.

    Inputs: None
    Outputs:
        - Color: Constant orange-red (1.0, 0.065, 0.0)
        - Strength: Constant emission strength

    Returns:
        str: Name of the node group
    """
    if not bpy:
        return ""

    group_name = "EVE_Strategy_UniformOrange"

    # Remove existing if present
    if group_name in bpy.data.node_groups:  # type: ignore[attr-defined]
        bpy.data.node_groups.remove(bpy.data.node_groups[group_name])  # type: ignore[attr-defined]

    # Create new node group
    group = bpy.data.node_groups.new(group_name, "ShaderNodeTree")  # type: ignore[attr-defined]
    nodes = group.nodes
    links = group.links

    # Create group outputs
    output = nodes.new("NodeGroupOutput")
    output.location = (200, 0)
    group.interface.new_socket(name="Color", socket_type="NodeSocketColor", in_out="OUTPUT")
    group.interface.new_socket(name="Strength", socket_type="NodeSocketFloat", in_out="OUTPUT")

    # === COLOR: Constant orange-red ===
    color_value = nodes.new("ShaderNodeRGB")
    color_value.location = (-200, 100)
    color_value.outputs[0].default_value = (1.0, 0.065, 0.0, 1.0)  # RGB + Alpha

    # === STRENGTH: Constant emission ===
    strength_value = nodes.new("ShaderNodeValue")
    strength_value.location = (-200, -100)
    strength_value.outputs[0].default_value = 10.0  # Strong emission

    # Connect to outputs
    links.new(color_value.outputs["Color"], output.inputs["Color"])
    links.new(strength_value.outputs["Value"], output.inputs["Strength"])

    return group_name
