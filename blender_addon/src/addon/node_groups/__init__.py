"""Node group creation and management for shader strategies."""

from __future__ import annotations

__all__ = [
    "ensure_strategy_node_groups",
    "get_strategy_node_group",
]

try:  # pragma: no cover
    import bpy  # type: ignore
except (ImportError, ModuleNotFoundError):  # noqa: BLE001
    bpy = None  # type: ignore


def ensure_strategy_node_groups(context=None):
    """Ensure all strategy node groups exist in the blend file.

    Creates or updates the following node groups:
    - EVE_Strategy_UniformOrange
    - EVE_Strategy_CharacterRainbow
    - EVE_Strategy_PatternCategories
    - EVE_Strategy_PositionEncoding

    Args:
        context: Optional Blender context for accessing scene properties

    Returns:
        list[str]: Names of created/updated node groups
    """
    if not bpy:
        return []

    from . import (
        character_rainbow,
        pattern_categories,
        position_encoding,
        proper_noun_highlight,
        uniform_orange,
    )

    groups = []
    groups.append(uniform_orange.ensure_node_group())
    groups.append(character_rainbow.ensure_node_group(context))
    groups.append(pattern_categories.ensure_node_group())
    groups.append(position_encoding.ensure_node_group())
    groups.append(proper_noun_highlight.ensure_node_group())

    return groups


def get_strategy_node_group(strategy_name: str):
    """Get a strategy node group by name.

    Args:
        strategy_name: Name of the strategy (e.g. "CharacterRainbow")

    Returns:
        bpy.types.ShaderNodeTree or None: The node group if found
    """
    if not bpy:
        return None

    group_name = f"EVE_Strategy_{strategy_name}"
    return bpy.data.node_groups.get(group_name)  # type: ignore[attr-defined]
