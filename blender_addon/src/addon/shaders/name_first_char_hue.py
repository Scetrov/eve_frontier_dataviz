import colorsys

import bpy

from ..shader_registry import BaseShaderStrategy, register_strategy
from ..shaders_builtin import _BLACKHOLE_NAMES, _get_blackhole_material


@register_strategy
class NameFirstCharHue(BaseShaderStrategy):
    id = "NameFirstCharHue"
    label = "Name First Char -> Hue"
    order = 10

    def build(self, context, objects_by_type: dict):  # noqa: D401
        mat_name = "EVE_NameFirstCharHue"
        mat = bpy.data.materials.get(mat_name)
        if not mat:
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
        links.new(emission.outputs[0], out.inputs[0])

        for obj in objects_by_type.get("systems", []):
            first = obj.name[:1].upper() if obj.name else "A"
            idx = ord(first) - ord("A")
            hue = (idx / 26.0) % 1.0
            r, g, b = colorsys.hsv_to_rgb(hue, 0.8, 1.0)
            inst_name = f"{mat_name}_{first}"
            inst = bpy.data.materials.get(inst_name)
            if not inst:
                inst = mat.copy()
                inst.name = inst_name
                e_node = inst.node_tree.nodes.get(emission.name)
                if e_node:
                    e_node.inputs[0].default_value = (r, g, b, 1.0)
            if obj.name in _BLACKHOLE_NAMES:
                inst = _get_blackhole_material()
            if obj.data and hasattr(obj.data, "materials"):
                if obj.data.materials:
                    obj.data.materials[0] = inst
                else:
                    obj.data.materials.append(inst)

    _fc_cache = {}
    _base_ready = False

    def apply(self, context, obj):  # pragma: no cover
        if not obj or not hasattr(obj, "data"):
            return
        if not self._base_ready:
            mat_name = "EVE_NameFirstCharHue"
            mat = bpy.data.materials.get(mat_name)
            if not mat:
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
                links.new(emission.outputs[0], out.inputs[0])
            self._base_ready = True
        if obj.name in _BLACKHOLE_NAMES:
            inst = _get_blackhole_material()
        else:
            first = obj.name[:1].upper() if obj.name else "A"
            inst = self._fc_cache.get(first)
            if not inst:
                base = bpy.data.materials.get("EVE_NameFirstCharHue")
                if not base:
                    return
                idx = ord(first) - ord("A")
                hue = (idx / 26.0) % 1.0
                r, g, b = colorsys.hsv_to_rgb(hue, 0.8, 1.0)
                inst = base.copy()
                inst.name = f"EVE_NameFirstCharHue_{first}"
                for n in inst.node_tree.nodes:
                    if n.type == "EMISSION":
                        n.inputs[0].default_value = (r, g, b, 1.0)
                self._fc_cache[first] = inst
        if obj.data and hasattr(obj.data, "materials"):
            if obj.data.materials:
                obj.data.materials[0] = inst
            else:
                obj.data.materials.append(inst)
