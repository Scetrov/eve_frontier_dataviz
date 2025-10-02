import re

import bpy

from ..shader_registry import BaseShaderStrategy, register_strategy
from ..shaders_builtin import _BLACKHOLE_NAMES, _get_blackhole_material


@register_strategy
class NamePatternCategory(BaseShaderStrategy):
    """Highlight systems by detected name pattern category (relaxed).

    Categories:
        DASH:   3 alnum - 3 alnum
        COLON:  A:DDDD
        DOTSEQ: A.XXX.XXX (3-4 length segments allowed)
        PIPE:   3 alnum | digit + 2 alnum (e.g. MVT|1IT)
        OTHER:  fallback
    """

    id = "NamePatternCategory"
    label = "Name Pattern Category"
    order = 30

    _re_dash = re.compile(r"^[A-Z0-9]{3}-[A-Z0-9]{3}$")
    _re_colon = re.compile(r"^[A-Z]:[0-9]{4}$")
    _re_dotseq = re.compile(r"^[A-Z]\.[A-Z0-9]{3,4}\.[A-Z0-9]{3,4}$")
    _re_pipe = re.compile(r"^[A-Z0-9]{3}\|[0-9][A-Z0-9]{2}$")

    # High-contrast, color-blind friendlier-ish palette (distinct hue + luminance):
    # DASH  -> Blue, COLON -> Orange, DOTSEQ -> Purple, PIPE -> Green, OTHER -> Gray
    _CATEGORY_COLORS = {
        "DASH": (0.20, 0.50, 1.00),  # blue
        "COLON": (1.00, 0.55, 0.00),  # orange
        "DOTSEQ": (0.60, 0.20, 0.85),  # purple
        "PIPE": (0.00, 0.90, 0.30),  # green
        "OTHER": (0.50, 0.50, 0.50),  # neutral gray
    }

    def _category(self, name: str) -> str:
        nm = (name or "").strip().upper()
        if self._re_dash.match(nm):
            return "DASH"
        if self._re_colon.match(nm):
            return "COLON"
        if self._re_dotseq.match(nm):
            return "DOTSEQ"
        if self._re_pipe.match(nm):
            return "PIPE"
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

    _base_created = False
    _pattern_cache = {}

    def apply(self, context, obj):  # pragma: no cover
        if not obj or not hasattr(obj, "data"):
            return
        base_name = "EVE_NamePatternCategory"
        if not self._base_created:
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
            self._base_created = True
        if obj.name in _BLACKHOLE_NAMES:
            inst = _get_blackhole_material()
        else:
            cat = self._category(obj.name)
            key = f"{base_name}_{cat}"
            inst = self._pattern_cache.get(key)
            if not inst:
                base = bpy.data.materials.get(base_name)
                if not base:
                    return
                inst = base.copy()
                inst.name = key
                color = self._CATEGORY_COLORS.get(cat, (0.5, 0.5, 0.5))
                for n in inst.node_tree.nodes:
                    if n.type == "EMISSION":
                        n.inputs[0].default_value = (*color, 1.0)
                self._pattern_cache[key] = inst
        if obj.data and hasattr(obj.data, "materials"):
            if obj.data.materials:
                obj.data.materials[0] = inst
            else:
                obj.data.materials.append(inst)
