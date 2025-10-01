import colorsys

import bpy

from .shader_registry import BaseShaderStrategy, register_strategy


@register_strategy
class NameFirstCharHue(BaseShaderStrategy):
    id = "NameFirstCharHue"
    label = "Name First Char -> Hue"
    order = 10

    def build(self, context, objects_by_type: dict):
        mat_name = "EVE_NameFirstCharHue"
        mat = bpy.data.materials.get(mat_name)
        if not mat:
            mat = bpy.data.materials.new(mat_name)
            mat.use_nodes = True
        nt = mat.node_tree
        nodes = nt.nodes
        links = nt.links
        # Clear except output
        for n in list(nodes):
            if n.type != 'OUTPUT_MATERIAL':
                nodes.remove(n)
        out = next(n for n in nodes if n.type == 'OUTPUT_MATERIAL')
        emission = nodes.new("ShaderNodeEmission")
        emission.location = (-200, 0)
        links.new(emission.outputs[0], out.inputs[0])

        # Assign color per object name first char
        for obj in objects_by_type.get("systems", []):
            first = obj.name[:1].upper() if obj.name else 'A'
            idx = ord(first) - ord('A')
            hue = (idx / 26.0) % 1.0
            r, g, b = colorsys.hsv_to_rgb(hue, 0.8, 1.0)
            inst_name = f"{mat_name}_{first}"
            inst = bpy.data.materials.get(inst_name)
            if not inst:
                inst = mat.copy()
                inst.name = inst_name
                e_node = inst.node_tree.nodes.get(emission.name)
                if e_node:  # In copy, name preserved
                    e_node.inputs[0].default_value = (r, g, b, 1.0)
            if obj.data and hasattr(obj.data, 'materials'):
                if obj.data.materials:
                    obj.data.materials[0] = inst
                else:
                    obj.data.materials.append(inst)


@register_strategy
class ChildCountEmission(BaseShaderStrategy):
    id = "ChildCountEmission"
    label = "Child Count -> Emission Strength"
    order = 20

    def build(self, context, objects_by_type: dict):
        mat_name = "EVE_ChildCountEmission"
        base = bpy.data.materials.get(mat_name)
        if not base:
            base = bpy.data.materials.new(mat_name)
            base.use_nodes = True
            nt = base.node_tree
            nodes = nt.nodes
            links = nt.links
            for n in list(nodes):
                if n.type != 'OUTPUT_MATERIAL':
                    nodes.remove(n)
            out = next(n for n in nodes if n.type == 'OUTPUT_MATERIAL')
            emission = nodes.new("ShaderNodeEmission")
            emission.location = (-200, 0)
            links.new(emission.outputs[0], out.inputs[0])

        # For each system object set emission strength proportional to child count
        for obj in objects_by_type.get("systems", []):
            child_count = sum(1 for c in obj.children if c.type == 'MESH')
            strength = max(0.1, min(child_count / 10.0, 10.0))
            inst_name = f"{mat_name}_{child_count}"
            inst = bpy.data.materials.get(inst_name)
            if not inst:
                inst = base.copy()
                inst.name = inst_name
                for n in inst.node_tree.nodes:
                    if n.type == 'EMISSION':
                        n.inputs[1].default_value = strength
            if obj.data and hasattr(obj.data, 'materials'):
                if obj.data.materials:
                    obj.data.materials[0] = inst
                else:
                    obj.data.materials.append(inst)
