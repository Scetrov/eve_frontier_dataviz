import colorsys
import re

import bpy

from .shader_registry import BaseShaderStrategy, register_strategy

_BLACKHOLE_NAMES = {"A 2560", "M 974", "U 3183"}


def _get_blackhole_material():  # pragma: no cover
    """Return (creating if needed) a shared bright orange emission material for black holes."""
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
    emission.inputs[0].default_value = (1.0, 0.45, 0.0, 1.0)  # bright orange
    emission.inputs[1].default_value = 5.0
    links.new(emission.outputs[0], out.inputs[0])
    return mat


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
            if n.type != "OUTPUT_MATERIAL":
                nodes.remove(n)
        out = next(n for n in nodes if n.type == "OUTPUT_MATERIAL")
        emission = nodes.new("ShaderNodeEmission")
        emission.location = (-200, 0)
        links.new(emission.outputs[0], out.inputs[0])

        # Assign color per object name first char
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
                if e_node:  # In copy, name preserved
                    e_node.inputs[0].default_value = (r, g, b, 1.0)
            if obj.name in _BLACKHOLE_NAMES:
                inst = _get_blackhole_material()
            if obj.data and hasattr(obj.data, "materials"):
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
                if n.type != "OUTPUT_MATERIAL":
                    nodes.remove(n)
            out = next(n for n in nodes if n.type == "OUTPUT_MATERIAL")
            emission = nodes.new("ShaderNodeEmission")
            emission.location = (-200, 0)
            links.new(emission.outputs[0], out.inputs[0])

        # For each system object set emission strength proportional to child count
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


@register_strategy
class NamePatternCategory(BaseShaderStrategy):
    """Highlight systems by detected name pattern category.

        Categories (evaluated in order):
            DASH:     XXX-XXX           (three alphanumeric, dash, three alphanumeric)
      COLON:    X:XXXX            (single letter, colon, four digits)
      DOTSEQ:   X.XXX.XXX         (single letter, dot, three chars, dot, three chars)
      OTHER:    Anything else

    Black hole names still override to orange emission.
    """

    id = "NamePatternCategory"
    label = "Name Pattern Category"
    order = 30

    # Relaxed: allow digits in both 3-char segments (captures names like O3H-1FN, E06-D68)
    _re_dash = re.compile(r"^[A-Z0-9]{3}-[A-Z0-9]{3}$")
    _re_colon = re.compile(r"^[A-Z]:[0-9]{4}$")
    # Allow dot-separated 1 + (3|4) + (3|4) alphanumeric to catch more variations
    _re_dotseq = re.compile(r"^[A-Z]\.[A-Z0-9]{3,4}\.[A-Z0-9]{3,4}$")
    # Extended variant: 3 alnum - 1 to 4 alnum + trailing alnum cluster (looser hybrid) e.g. O3H-1FN, E06-D68
    _re_dash_ext = re.compile(r"^[A-Z0-9]{3}-[A-Z0-9]{2,4}$")

    _CATEGORY_COLORS = {
        "DASH": (0.0, 0.8, 1.0),  # cyan
        "COLON": (1.0, 0.0, 1.0),  # magenta
        "DOTSEQ": (1.0, 1.0, 0.0),  # yellow
        "OTHER": (0.5, 0.5, 0.5),  # gray
    }

    def _category(self, name: str) -> str:
        nm = (name or "").strip().upper()
        if self._re_dash.match(nm):
            return "DASH"
        if self._re_dash_ext.match(nm):
            return "DASH"
        if self._re_colon.match(nm):
            return "COLON"
        if self._re_dotseq.match(nm):
            return "DOTSEQ"
        return "OTHER"

    def build(self, context, objects_by_type: dict):  # noqa: D401
        base_name = "EVE_NamePatternCategory"
        base = bpy.data.materials.get(base_name)
        if not base:
            base = bpy.data.materials.new(base_name)
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

        cache = {}
        for obj in objects_by_type.get("systems", []):
            if obj.name in _BLACKHOLE_NAMES:
                inst = _get_blackhole_material()
            else:
                cat = self._category(obj.name)
                inst_name = f"{base_name}_{cat}"
                inst = bpy.data.materials.get(inst_name)
                if not inst:
                    inst = base.copy()
                    inst.name = inst_name
                    color = self._CATEGORY_COLORS.get(cat, (0.5, 0.5, 0.5))
                    for n in inst.node_tree.nodes:
                        if n.type == "EMISSION":
                            n.inputs[0].default_value = (*color, 1.0)
                    cache[cat] = inst
            if obj.data and hasattr(obj.data, "materials"):
                if obj.data.materials:
                    obj.data.materials[0] = inst
                else:
                    obj.data.materials.append(inst)
