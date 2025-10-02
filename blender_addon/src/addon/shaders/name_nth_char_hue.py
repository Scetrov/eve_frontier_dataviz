import colorsys

import bpy

from ..shader_registry import BaseShaderStrategy, register_strategy
from ..shaders_builtin import _BLACKHOLE_NAMES, _get_blackhole_material


class _NthCharHueBase(BaseShaderStrategy):
    """Common implementation for character-at-index hue mapping.

    Subclasses set:
      _char_index (0-based index into name)
      id / label / order
    """

    _base_ready = False
    _cache = None
    _char_index = 0
    _material_prefix = "EVE_NameCharHue"

    def _ensure_base(self):
        mat_name = f"{self._material_prefix}_BASE_{self._char_index}"
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
        return mat

    def _char_for(self, name: str | None):
        if not name or len(name) <= self._char_index:
            return "A"
        return name[self._char_index].upper()

    def _color_for_char(self, ch: str):
        if not ch or not ch.isalpha():
            # Map digits / symbols into a stable sub-range
            if ch and ch.isdigit():
                idx = ord(ch) - ord("0")
                hue = (idx / 10.0) * 0.15  # small slice of wheel
            else:
                hue = 0.9  # punctuation bucket
            r, g, b = colorsys.hsv_to_rgb(hue, 0.5, 0.9)
            return r, g, b
        idx = ord(ch) - ord("A")
        hue = (idx / 26.0) % 1.0
        r, g, b = colorsys.hsv_to_rgb(hue, 0.8, 1.0)
        return r, g, b

    def build(self, context, objects_by_type: dict):  # noqa: D401
        base = self._ensure_base()
        cache = {}
        for obj in objects_by_type.get("systems", []):
            ch = self._char_for(obj.name)
            inst_name = f"{self._material_prefix}_{self._char_index}_{ch}"
            if obj.name in _BLACKHOLE_NAMES:
                inst = _get_blackhole_material()
            else:
                inst = bpy.data.materials.get(inst_name)
                if not inst:
                    r, g, b = self._color_for_char(ch)
                    inst = base.copy()
                    inst.name = inst_name
                    for n in inst.node_tree.nodes:
                        if n.type == "EMISSION":
                            n.inputs[0].default_value = (r, g, b, 1.0)
                cache[ch] = inst
            if obj.data and hasattr(obj.data, "materials"):
                if obj.data.materials:
                    obj.data.materials[0] = inst
                else:
                    obj.data.materials.append(inst)
        self._cache = cache

    def apply(self, context, obj):  # pragma: no cover
        if not obj or not hasattr(obj, "data"):
            return
        if not self._base_ready:
            self._ensure_base()
            self._cache = {}
            self._base_ready = True
        if obj.name in _BLACKHOLE_NAMES:
            inst = _get_blackhole_material()
        else:
            ch = self._char_for(obj.name)
            inst = self._cache.get(ch) if self._cache else None
            if not inst:
                base = self._ensure_base()
                r, g, b = self._color_for_char(ch)
                inst = base.copy()
                inst.name = f"{self._material_prefix}_{self._char_index}_{ch}"
                for n in inst.node_tree.nodes:
                    if n.type == "EMISSION":
                        n.inputs[0].default_value = (r, g, b, 1.0)
                if self._cache is not None:
                    self._cache[ch] = inst
        if obj.data and hasattr(obj.data, "materials"):
            if obj.data.materials:
                obj.data.materials[0] = inst
            else:
                obj.data.materials.append(inst)


def _make_strategy(index: int, order: int):
    cls_name = f"NameChar{index+1}GenericHue"
    strat_id = f"NameChar{index+1}HueUnified"
    label = f"Name {index+1}{_ordinal_suffix(index+1)} Char -> Hue (Unified)"

    return type(
        cls_name,
        (_NthCharHueBase,),
        {
            "id": strat_id,
            "label": label,
            "order": order,
            "_char_index": index,
        },
    )


def _ordinal_suffix(n: int) -> str:
    if 10 <= (n % 100) <= 20:
        return "th"
    last = n % 10
    return {1: "st", 2: "nd", 3: "rd"}.get(last, "th")


# Register unified forms for 1st-9th characters (indexes 0..8)
_indexes_orders = [
    (0, 10),
    (1, 11),
    (2, 12),
    (3, 13),
    (4, 14),
    (5, 15),
    (6, 16),
    (7, 17),
    (8, 18),
]
for i, order in _indexes_orders:
    Strat = _make_strategy(i, order)  # noqa: N806
    register_strategy(Strat)


def register():  # pragma: no cover
    pass


def unregister():  # pragma: no cover
    pass
