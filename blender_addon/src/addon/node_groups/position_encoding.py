"""Position-Based Encoding strategy node group.

Use first 3 character positions to create RGB color, with blackhole boost.
"""

from __future__ import annotations

try:  # pragma: no cover
    import bpy  # type: ignore
except Exception:  # noqa: BLE001
    bpy = None  # type: ignore


def ensure_node_group():
    """Create or update the Position-Based Encoding node group.

    Inputs: None (reads properties via Attribute nodes)
    Outputs:
        - Color: RGB from first 3 character positions
        - Strength: Boosted for blackhole systems

    Returns:
        str: Name of the node group
    """
    if not bpy:
        return ""

    group_name = "EVE_Strategy_PositionEncoding"

    # Remove existing if present
    if group_name in bpy.data.node_groups:  # type: ignore[attr-defined]
        bpy.data.node_groups.remove(bpy.data.node_groups[group_name])  # type: ignore[attr-defined]

    # Create new node group
    group = bpy.data.node_groups.new(group_name, "ShaderNodeTree")  # type: ignore[attr-defined]
    nodes = group.nodes
    links = group.links

    # Create group outputs
    output = nodes.new("NodeGroupOutput")
    output.location = (600, 0)
    group.interface.new_socket(name="Color", socket_type="NodeSocketColor", in_out="OUTPUT")
    group.interface.new_socket(name="Strength", socket_type="NodeSocketFloat", in_out="OUTPUT")

    # === COLOR PATH: First 3 characters → RGB ===

    # Read character 0 for R channel
    attr_char0 = nodes.new("ShaderNodeAttribute")
    attr_char0.attribute_name = "eve_name_char_index_0_ord"
    attr_char0.attribute_type = "OBJECT"
    attr_char0.location = (-800, 300)

    # Clamp char 0 (-1 to 0)
    max_r = nodes.new("ShaderNodeMath")
    max_r.operation = "MAXIMUM"
    max_r.inputs[1].default_value = 0.0
    max_r.location = (-600, 300)
    links.new(attr_char0.outputs["Fac"], max_r.inputs[0])

    # Read character 1 for G channel
    attr_char1 = nodes.new("ShaderNodeAttribute")
    attr_char1.attribute_name = "eve_name_char_index_1_ord"
    attr_char1.attribute_type = "OBJECT"
    attr_char1.location = (-800, 100)

    # Clamp char 1 (-1 to 0)
    max_g = nodes.new("ShaderNodeMath")
    max_g.operation = "MAXIMUM"
    max_g.inputs[1].default_value = 0.0
    max_g.location = (-600, 100)
    links.new(attr_char1.outputs["Fac"], max_g.inputs[0])

    # Read character 2 for B channel
    attr_char2 = nodes.new("ShaderNodeAttribute")
    attr_char2.attribute_name = "eve_name_char_index_2_ord"
    attr_char2.attribute_type = "OBJECT"
    attr_char2.location = (-800, -100)

    # Clamp char 2 (-1 to 0)
    max_b = nodes.new("ShaderNodeMath")
    max_b.operation = "MAXIMUM"
    max_b.inputs[1].default_value = 0.0
    max_b.location = (-600, -100)
    links.new(attr_char2.outputs["Fac"], max_b.inputs[0])

    # Combine RGB
    combine_rgb = nodes.new("ShaderNodeCombineRGB")
    combine_rgb.location = (-400, 100)
    links.new(max_r.outputs[0], combine_rgb.inputs["R"])
    links.new(max_g.outputs[0], combine_rgb.inputs["G"])
    links.new(max_b.outputs[0], combine_rgb.inputs["B"])

    # Connect color output
    links.new(combine_rgb.outputs["Image"], output.inputs["Color"])

    # === STRENGTH PATH: Blackhole boost ===

    # Read blackhole flag
    attr_blackhole = nodes.new("ShaderNodeAttribute")
    attr_blackhole.attribute_name = "eve_is_blackhole"
    attr_blackhole.attribute_type = "OBJECT"
    attr_blackhole.location = (-600, -300)

    # Multiply by 10 (0→0, 1→10 boost)
    math_mult = nodes.new("ShaderNodeMath")
    math_mult.operation = "MULTIPLY"
    math_mult.inputs[1].default_value = 10.0
    math_mult.location = (-400, -300)
    links.new(attr_blackhole.outputs["Fac"], math_mult.inputs[0])

    # Add base strength of 1.0
    math_add = nodes.new("ShaderNodeMath")
    math_add.operation = "ADD"
    math_add.inputs[1].default_value = 1.0
    math_add.location = (-200, -300)
    links.new(math_mult.outputs[0], math_add.inputs[0])

    # Connect strength output
    links.new(math_add.outputs[0], output.inputs["Strength"])

    return group_name
