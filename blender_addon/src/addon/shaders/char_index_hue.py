import colorsys

import bpy

from ..shader_registry import BaseShaderStrategy, register_strategy
from ..shaders_builtin import _BLACKHOLE_NAMES, _get_blackhole_material


@register_strategy
class CharIndexHue(BaseShaderStrategy):
    """Color each system by aggregating per-character hue contributions.

    Algorithm:
      For each character at position i (0-based), map its ordinal into a hue offset.
      Accumulate RGB (clamped) for a final color. Digits use a separate base offset.
    """

    id = "CharIndexHue"
    label = "Character Index Aggregate Hue"
    order = 40

    def _char_color(self, ch: str, idx: int):
        if not ch:
            return (0.2, 0.2, 0.2)
        ch_u = ch.upper()
        if "A" <= ch_u <= "Z":
            base = (ord(ch_u) - ord("A")) / 26.0
        elif ch_u.isdigit():
            base = (ord(ch_u) - ord("0")) / 10.0 * 0.75  # digits compressed
        else:
            base = 0.9  # punctuation cluster
        hue = (base + (idx * 0.07)) % 1.0
        r, g, b = colorsys.hsv_to_rgb(hue, 0.65, 1.0)
        return (r, g, b)

    def build(self, context, objects_by_type: dict):  # noqa: D401
        mat_name = "EVE_CharIndexHue"
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
        cache = {}
        for obj in objects_by_type.get("systems", []):
            if obj.name in _BLACKHOLE_NAMES:
                inst = _get_blackhole_material()
            else:
                key = obj.name
                inst = cache.get(key)
                if not inst:
                    # Derive aggregated color
                    chars = (obj.name or "")[:12]  # limit length influence
                    acc = [0.0, 0.0, 0.0]
                    for i, ch in enumerate(chars):
                        r, g, b = self._char_color(ch, i)
                        acc[0] += r
                        acc[1] += g
                        acc[2] += b
                    # Normalize accumulation
                    n = max(1, len(chars))
                    r = min(1.0, acc[0] / n)
                    g = min(1.0, acc[1] / n)
                    b = min(1.0, acc[2] / n)
                    inst = base.copy()
                    inst.name = f"{mat_name}_{hash(key) & 0xFFFF:X}"
                    for n in inst.node_tree.nodes:
                        if n.type == "EMISSION":
                            n.inputs[0].default_value = (r, g, b, 1.0)
                    cache[key] = inst
            if obj.data and hasattr(obj.data, "materials"):
                if obj.data.materials:
                    obj.data.materials[0] = inst
                else:
                    obj.data.materials.append(inst)

    _base_ready = False
    _cache = {}

    def apply(self, context, obj):  # pragma: no cover
        if not obj or not hasattr(obj, "data"):
            return
        mat_name = "EVE_CharIndexHue"
        if not self._base_ready:
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
            self._base_ready = True
        if obj.name in _BLACKHOLE_NAMES:
            inst = _get_blackhole_material()
        else:
            key = obj.name
            inst = self._cache.get(key)
            if not inst:
                chars = (obj.name or "")[:12]
                acc = [0.0, 0.0, 0.0]
                for i, ch in enumerate(chars):
                    r, g, b = self._char_color(ch, i)
                    acc[0] += r
                    acc[1] += g
                    acc[2] += b
                n = max(1, len(chars))
                r = min(1.0, acc[0] / n)
                g = min(1.0, acc[1] / n)
                b = min(1.0, acc[2] / n)
                base = bpy.data.materials.get(mat_name)
                if not base:
                    return
                inst = base.copy()
                inst.name = f"{mat_name}_{hash(key) & 0xFFFF:X}"
                for n in inst.node_tree.nodes:
                    if n.type == "EMISSION":
                        n.inputs[0].default_value = (r, g, b, 1.0)
                self._cache[key] = inst
        if obj.data and hasattr(obj.data, "materials"):
            if obj.data.materials:
                obj.data.materials[0] = inst
            else:
                obj.data.materials.append(inst)
