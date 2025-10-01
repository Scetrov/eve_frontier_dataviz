import bpy

# Shared constants & util functions for shader strategies.

_BLACKHOLE_NAMES = {"A 2560", "M 974", "U 3183"}


def _get_blackhole_material():  # pragma: no cover
    """Return (creating if needed) a shared bright orange emission material for black holes.

    Strategies import this from shaders_builtin to keep a single material definition & reuse.
    """
    mat_name = "EVE_BlackHole_Orange"
    mat = bpy.data.materials.get(mat_name)
    if mat:
        return mat
    mat = bpy.data.materials.new(mat_name)
    mat.use_nodes = True
    nt = mat.node_tree
    nodes = nt.nodes
    links = nt.links
    for n in list(nodes):
        if n.type != "OUTPUT_MATERIAL":
            nodes.remove(n)
    out = next(n for n in nodes if n.type == "OUTPUT_MATERIAL")
    emission = nodes.new("ShaderNodeEmission")
    emission.location = (-200, 0)
    emission.inputs[0].default_value = (1.0, 0.45, 0.0, 1.0)
    emission.inputs[1].default_value = 5.0
    links.new(emission.outputs[0], out.inputs[0])
    return mat


# NOTE: Legacy strategies previously lived here; they were moved into separate modules under
# addon/shaders/. This file intentionally kept small to avoid circular imports and provide
# a single source for special-system coloring.
