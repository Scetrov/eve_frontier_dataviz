"""Pattern Categories strategy node group.

Distinct colors per naming pattern (DASH/COLON/DOTSEQ/PIPE/OTHER).
"""

from __future__ import annotations

try:  # pragma: no cover
    import bpy  # type: ignore
except Exception:  # noqa: BLE001
    bpy = None  # type: ignore


def ensure_node_group():
    """Create or update the Pattern Categories node group.

    Inputs: None (reads properties via Attribute nodes)
    Outputs:
        - Color: Category-based color from ColorRamp
        - Strength: Constant emission strength

    Returns:
        str: Name of the node group
    """
    if not bpy:
        return ""

    group_name = "EVE_Strategy_PatternCategories"

    # Remove existing if present
    if group_name in bpy.data.node_groups:  # type: ignore[attr-defined]
        bpy.data.node_groups.remove(bpy.data.node_groups[group_name])  # type: ignore[attr-defined]

    # Create new node group
    group = bpy.data.node_groups.new(group_name, "ShaderNodeTree")  # type: ignore[attr-defined]
    nodes = group.nodes
    links = group.links

    # Create group outputs
    output = nodes.new("NodeGroupOutput")
    output.location = (400, 0)
    group.interface.new_socket(name="Color", socket_type="NodeSocketColor", in_out="OUTPUT")
    group.interface.new_socket(name="Strength", socket_type="NodeSocketFloat", in_out="OUTPUT")

    # === COLOR PATH: Pattern category → ColorRamp ===

    # Read pattern category (0-4: DASH/COLON/DOTSEQ/PIPE/OTHER)
    attr_pattern = nodes.new("ShaderNodeAttribute")
    attr_pattern.attribute_name = "eve_name_pattern"
    attr_pattern.attribute_type = "OBJECT"
    attr_pattern.location = (-600, 200)

    # Map 0-4 integer to 0-1 range for ColorRamp
    map_range = nodes.new("ShaderNodeMapRange")
    map_range.location = (-400, 200)
    map_range.inputs["From Min"].default_value = 0.0
    map_range.inputs["From Max"].default_value = 4.0
    map_range.inputs["To Min"].default_value = 0.0
    map_range.inputs["To Max"].default_value = 1.0
    map_range.clamp = True
    links.new(attr_pattern.outputs["Fac"], map_range.inputs["Value"])

    # ColorRamp with 5 distinct colors for each pattern
    color_ramp = nodes.new("ShaderNodeValToRGB")
    color_ramp.location = (-200, 200)
    color_ramp.color_ramp.interpolation = "CONSTANT"  # Sharp transitions

    # Clear default elements
    while len(color_ramp.color_ramp.elements) > 2:
        color_ramp.color_ramp.elements.remove(color_ramp.color_ramp.elements[0])

    # Set up 5 color stops (one per category)
    color_ramp.color_ramp.elements[0].position = 0.0
    color_ramp.color_ramp.elements[0].color = (0.2, 0.4, 0.8, 1.0)  # Blue - DASH

    color_ramp.color_ramp.elements[1].position = 1.0
    color_ramp.color_ramp.elements[1].color = (0.5, 0.5, 0.5, 1.0)  # Gray - OTHER

    elem1 = color_ramp.color_ramp.elements.new(0.25)
    elem1.color = (1.0, 0.5, 0.2, 1.0)  # Orange - COLON

    elem2 = color_ramp.color_ramp.elements.new(0.5)
    elem2.color = (0.6, 0.2, 0.8, 1.0)  # Purple - DOTSEQ

    elem3 = color_ramp.color_ramp.elements.new(0.75)
    elem3.color = (0.2, 0.8, 0.3, 1.0)  # Green - PIPE

    links.new(map_range.outputs["Result"], color_ramp.inputs["Fac"])

    # Connect color output
    links.new(color_ramp.outputs["Color"], output.inputs["Color"])

    # === STRENGTH PATH: Constant value ===

    # Constant strength value
    value = nodes.new("ShaderNodeValue")
    value.location = (-200, -100)
    value.outputs[0].default_value = 1.5

    # Connect strength output
    links.new(value.outputs[0], output.inputs["Strength"])

    return group_name
