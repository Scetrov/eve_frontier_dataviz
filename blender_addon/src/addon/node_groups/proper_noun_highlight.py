"""Proper Noun Highlight strategy node group.

Highlights systems that are proper nouns (scene attribute `eve_is_proper_noun`).
Outputs a Color (bright highlight for proper nouns, neutral otherwise) and Strength.
"""

from __future__ import annotations

try:  # pragma: no cover
    import bpy  # type: ignore
except (ImportError, ModuleNotFoundError):  # noqa: BLE001
    bpy = None  # type: ignore


def ensure_node_group():
    if not bpy:
        return ""

    group_name = "EVE_Strategy_ProperNounHighlight"

    if group_name in bpy.data.node_groups:  # type: ignore[attr-defined]
        bpy.data.node_groups.remove(bpy.data.node_groups[group_name])  # type: ignore[attr-defined]

    group = bpy.data.node_groups.new(group_name, "ShaderNodeTree")  # type: ignore[attr-defined]
    nodes = group.nodes
    links = group.links

    # Outputs
    output = nodes.new("NodeGroupOutput")
    output.location = (600, 0)
    group.interface.new_socket(name="Color", socket_type="NodeSocketColor", in_out="OUTPUT")
    group.interface.new_socket(name="Strength", socket_type="NodeSocketFloat", in_out="OUTPUT")

    # Read proper noun flag
    attr_flag = nodes.new("ShaderNodeAttribute")
    attr_flag.attribute_name = "eve_is_proper_noun"
    attr_flag.attribute_type = "OBJECT"
    attr_flag.location = (-400, 100)

    # Create highlight color (orange) and dark grey
    highlight = nodes.new("ShaderNodeRGB")
    highlight.outputs[0].default_value = (1.0, 0.6, 0.0, 1.0)
    highlight.location = (-200, 200)

    neutral = nodes.new("ShaderNodeRGB")
    neutral.outputs[0].default_value = (0.1, 0.1, 0.1, 1.0)
    neutral.location = (-200, 0)

    # Mix color based on flag
    mix = nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.location = (0, 100)
    links.new(attr_flag.outputs[0], mix.inputs[0])
    links.new(neutral.outputs[0], mix.inputs[6])
    links.new(highlight.outputs[0], mix.inputs[7])

    # Strength: subtle boost for proper nouns
    mult = nodes.new("ShaderNodeMath")
    mult.operation = "MULTIPLY"
    mult.inputs[1].default_value = 2.0
    mult.location = (-200, -150)
    links.new(attr_flag.outputs[0], mult.inputs[0])

    add = nodes.new("ShaderNodeMath")
    add.operation = "ADD"
    add.inputs[1].default_value = 0.5
    add.location = (100, -150)
    links.new(mult.outputs[0], add.inputs[0])

    links.new(mix.outputs[2], output.inputs["Color"])
    links.new(add.outputs[0], output.inputs["Strength"])

    return group_name
