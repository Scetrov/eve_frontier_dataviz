"""Shared helper utilities for operator modules."""

from __future__ import annotations

try:  # pragma: no cover
    import bpy  # type: ignore
except Exception:  # noqa: BLE001
    bpy = None  # type: ignore

GENERATED_COLLECTIONS = ["Frontier_Systems", "EVE_Planets", "EVE_Moons"]


def get_or_create_collection(name: str):  # pragma: no cover - needs Blender
    """Get or create a *top-level* collection under the scene root.

    Used for the canonical flat collections (Frontier_Systems, etc.). When
    hierarchy mode is enabled, region and constellation subcollections are
    nested under Frontier_Systems (Region -> Constellation -> Systems).
    """
    if bpy is None:
        return None
    coll = bpy.data.collections.get(name)
    if not coll:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll


def get_or_create_subcollection(parent, name: str):  # pragma: no cover - needs Blender
    """Get or create a collection *under* a parent collection.

    Unlike get_or_create_collection this will not implicitly link the new
    collection to the scene root; it links only beneath the supplied parent.
    If the collection already exists but is not parented, it will be linked
    to the parent (allowing reuse without duplicate trees).
    """
    if bpy is None or parent is None:
        return None
    coll = bpy.data.collections.get(name)
    if not coll:
        coll = bpy.data.collections.new(name)
        parent.children.link(coll)
        return coll
    # Ensure parent link present (a collection can have multiple parents, but
    # we only add if not already linked).
    try:
        if parent not in coll.parents:  # type: ignore[attr-defined]
            parent.children.link(coll)
    except Exception:  # noqa: BLE001
        pass
    return coll


def clear_generated():  # pragma: no cover - needs Blender
    if bpy is None:
        return 0, 0
    removed_objs = 0
    removed_colls = 0
    prev_undo = bpy.context.preferences.edit.use_global_undo
    bpy.context.preferences.edit.use_global_undo = False
    try:
        for cname in GENERATED_COLLECTIONS:
            coll = bpy.data.collections.get(cname)
            if not coll:
                continue
            for obj in list(coll.objects):
                try:
                    bpy.data.objects.remove(obj, do_unlink=True)
                    removed_objs += 1
                except Exception:  # noqa: BLE001
                    pass
            try:
                bpy.data.collections.remove(coll)
                removed_colls += 1
            except Exception:  # noqa: BLE001
                pass
    finally:
        bpy.context.preferences.edit.use_global_undo = prev_undo
    return removed_objs, removed_colls
