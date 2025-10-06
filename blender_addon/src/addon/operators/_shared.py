"""Shared helper utilities for operator modules."""

from __future__ import annotations

try:  # pragma: no cover
    import bpy  # type: ignore
except Exception:  # noqa: BLE001
    bpy = None  # type: ignore

GENERATED_COLLECTIONS = ["Frontier", "EVE_Planets", "EVE_Moons"]


def get_or_create_collection(name: str):  # pragma: no cover - needs Blender
    """Get or create a *top-level* collection under the scene root.

    Used for the canonical flat collections (Frontier, etc.). When
    hierarchy mode is enabled, region and constellation subcollections are
    nested under Frontier (Region -> Constellation -> Systems).
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
    Checks if collection is already a child of parent before reusing.
    """
    if bpy is None or parent is None:
        return None
    # First check if this collection already exists as a child of parent
    for child in parent.children:
        if child.name == name:
            return child
    # Not found as child - create new or reuse orphaned collection
    coll = bpy.data.collections.get(name)
    if not coll:
        coll = bpy.data.collections.new(name)
    # Link to parent (handles both new and orphaned collections)
    try:
        parent.children.link(coll)
    except Exception:  # noqa: BLE001 - already linked or error
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
            # Recursively remove all objects from this collection and subcollections
            collections_to_process = [coll]
            while collections_to_process:
                current = collections_to_process.pop()
                # Add child collections to process queue
                collections_to_process.extend(list(current.children))
                # Remove all objects in current collection
                for obj in list(current.objects):
                    try:
                        bpy.data.objects.remove(obj, do_unlink=True)
                        removed_objs += 1
                    except Exception:  # noqa: BLE001
                        pass

            # Now recursively remove all subcollections, then the parent
            def _remove_collection_recursive(c):
                nonlocal removed_colls
                # Remove children first (depth-first)
                for child in list(c.children):
                    _remove_collection_recursive(child)
                # Remove this collection
                try:
                    bpy.data.collections.remove(c)
                    removed_colls += 1
                except Exception:  # noqa: BLE001
                    pass

            _remove_collection_recursive(coll)
    finally:
        bpy.context.preferences.edit.use_global_undo = prev_undo
    return removed_objs, removed_colls
