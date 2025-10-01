import bpy

from ..shader_registry import BaseShaderStrategy, register_strategy
from ..shaders_builtin import _BLACKHOLE_NAMES, _get_blackhole_material


@register_strategy
class ChildCountEmission(BaseShaderStrategy):
    id = "ChildCountEmission"
    label = "Child Count -> Emission Strength"
    order = 20

    def build(self, context, objects_by_type: dict):  # noqa: D401
        mat_name = "EVE_ChildCountEmission"
        base = bpy.data.materials.get(mat_name)
        if not base:
            base = bpy.data.materials.new(mat_name)
            base.use_nodes = True
            nt = base.node_tree
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
            child_count = sum(1 for c in obj.children if c.type == "MESH")
            strength = max(0.1, min(child_count / 10.0, 10.0))
            inst_name = f"{mat_name}_{child_count}"
            inst = bpy.data.materials.get(inst_name)
            if not inst:
                inst = base.copy()
                inst.name = inst_name
                for n in inst.node_tree.nodes:
                    if n.type == "EMISSION":
                        n.inputs[1].default_value = strength
            if obj.name in _BLACKHOLE_NAMES:
                inst = _get_blackhole_material()
            if obj.data and hasattr(obj.data, "materials"):
                if obj.data.materials:
                    obj.data.materials[0] = inst
                else:
                    obj.data.materials.append(inst)

    _base_initialized = False
    _variant_cache = {}

    def apply(self, context, obj):  # pragma: no cover
        if not obj or not hasattr(obj, "data"):
            return
        mat_name = "EVE_ChildCountEmission"
        if not self._base_initialized:
            base = bpy.data.materials.get(mat_name)
            if not base:
                base = bpy.data.materials.new(mat_name)
                base.use_nodes = True
                nt = base.node_tree
                nodes = nt.nodes
                links = nt.links
                for n in list(nodes):
                    if n.type != "OUTPUT_MATERIAL":
                        nodes.remove(n)
                out = next(n for n in nodes if n.type == "OUTPUT_MATERIAL")
                emission = nodes.new("ShaderNodeEmission")
                emission.location = (-200, 0)
                links.new(emission.outputs[0], out.inputs[0])
            self._base_initialized = True
        if obj.name in _BLACKHOLE_NAMES:
            inst = _get_blackhole_material()
        else:
            child_count = sum(1 for c in obj.children if c.type == "MESH")
            strength = max(0.1, min(child_count / 10.0, 10.0))
            key = f"{mat_name}_{child_count}"
            inst = self._variant_cache.get(key)
            if not inst:
                base = bpy.data.materials.get(mat_name)
                if not base:
                    return
                inst = base.copy()
                inst.name = key
                for n in inst.node_tree.nodes:
                    if n.type == "EMISSION":
                        n.inputs[1].default_value = strength
                self._variant_cache[key] = inst
        if obj.data and hasattr(obj.data, "materials"):
            if obj.data.materials:
                obj.data.materials[0] = inst
            else:
                obj.data.materials.append(inst)
