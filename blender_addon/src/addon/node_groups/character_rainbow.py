"""Character Rainbow strategy node group.

Color based on first character, brightness based on child count.
"""

from __future__ import annotations

try:  # pragma: no cover
    import bpy  # type: ignore
except Exception:  # noqa: BLE001
    bpy = None  # type: ignore


def ensure_node_group(context=None):
    """Create or update the Character Rainbow node group.

    Inputs: None (reads properties via Attribute nodes)
    Outputs:
        - Color: HSV-based color from selected character index
        - Strength: Emission strength from planet+moon count

    Args:
        context: Optional Blender context to read character index parameter

    Returns:
        str: Name of the node group
    """
    if not bpy:
        return ""

    # Get character index from scene property (default to 0)
    char_index = 0
    if context and hasattr(context, "scene"):
        char_index = getattr(context.scene, "eve_char_rainbow_index", 0)

    group_name = "EVE_Strategy_CharacterRainbow"

    # Remove existing if present (for updates)
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

    # === COLOR PATH: Selected character → HSV or Grey ===

    # Read selected character index
    attr_char = nodes.new("ShaderNodeAttribute")
    attr_char.attribute_name = f"eve_name_char_index_{char_index}_ord"
    attr_char.attribute_type = "OBJECT"
    attr_char.location = (-800, 200)

    # Check if character is valid (>= 0)
    math_is_valid = nodes.new("ShaderNodeMath")
    math_is_valid.operation = "GREATER_THAN"
    math_is_valid.inputs[1].default_value = -0.5  # Threshold between -1 and 0
    math_is_valid.location = (-600, 300)
    links.new(attr_char.outputs["Fac"], math_is_valid.inputs[0])

    # Clamp -1 to 0 (non-alphanumeric becomes 0)
    math_max = nodes.new("ShaderNodeMath")
    math_max.operation = "MAXIMUM"
    math_max.inputs[1].default_value = 0.0
    math_max.location = (-600, 200)
    links.new(attr_char.outputs["Fac"], math_max.inputs[0])

    # Multiply by 0.9 to get hue range 0.0-0.9 (avoids wrapping red)
    math_mult = nodes.new("ShaderNodeMath")
    math_mult.operation = "MULTIPLY"
    math_mult.inputs[1].default_value = 0.9
    math_mult.location = (-400, 200)
    links.new(math_max.outputs[0], math_mult.inputs[0])

    # Combine HSV (full saturation and brightness)
    hsv = nodes.new("ShaderNodeCombineHSV")
    hsv.location = (-200, 200)
    hsv.inputs["S"].default_value = 1.0  # Full saturation
    hsv.inputs["V"].default_value = 1.0  # Full brightness
    links.new(math_mult.outputs[0], hsv.inputs["H"])

    # Create neutral grey for invalid characters
    grey = nodes.new("ShaderNodeRGB")
    grey.outputs[0].default_value = (0.5, 0.5, 0.5, 1.0)  # Neutral grey
    grey.location = (-200, 50)

    # Mix between grey (invalid) and HSV color (valid)
    mix_color = nodes.new("ShaderNodeMix")
    mix_color.data_type = "RGBA"
    mix_color.location = (0, 200)
    links.new(math_is_valid.outputs[0], mix_color.inputs[0])  # Factor (0=grey, 1=HSV)
    links.new(grey.outputs[0], mix_color.inputs[6])  # A (grey)
    links.new(hsv.outputs["Color"], mix_color.inputs[7])  # B (HSV color)

    # Connect color output
    links.new(mix_color.outputs[2], output.inputs["Color"])

    # === STRENGTH PATH: Planet + Moon count → Map Range ===

    # Read planet count
    attr_planets = nodes.new("ShaderNodeAttribute")
    attr_planets.attribute_name = "eve_planet_count"
    attr_planets.attribute_type = "OBJECT"
    attr_planets.location = (-800, -100)

    # Read moon count
    attr_moons = nodes.new("ShaderNodeAttribute")
    attr_moons.attribute_name = "eve_moon_count"
    attr_moons.attribute_type = "OBJECT"
    attr_moons.location = (-800, -250)

    # Add planet + moon counts
    math_add = nodes.new("ShaderNodeMath")
    math_add.operation = "ADD"
    math_add.location = (-600, -150)
    links.new(attr_planets.outputs["Fac"], math_add.inputs[0])
    links.new(attr_moons.outputs["Fac"], math_add.inputs[1])

    # Map 0-20 children → 0.5-3.0 emission strength
    map_range = nodes.new("ShaderNodeMapRange")
    map_range.location = (-400, -150)
    map_range.inputs["From Min"].default_value = 0.0
    map_range.inputs["From Max"].default_value = 20.0
    map_range.inputs["To Min"].default_value = 0.5
    map_range.inputs["To Max"].default_value = 3.0
    map_range.clamp = True
    links.new(math_add.outputs[0], map_range.inputs["Value"])

    # Connect strength output
    links.new(map_range.outputs["Result"], output.inputs["Strength"])

    return group_name
