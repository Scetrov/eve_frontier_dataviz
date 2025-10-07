"""Shared helper utilities for operator modules."""

from __future__ import annotations

try:  # pragma: no cover
    import bpy  # type: ignore
except Exception:  # noqa: BLE001
    bpy = None  # type: ignore

GENERATED_COLLECTIONS = ["Frontier", "EVE_Planets", "EVE_Moons", "SystemsByName"]


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
        # First pass: collect all objects and collections to remove
        objects_to_remove = set()
        collections_to_remove = []

        for cname in GENERATED_COLLECTIONS:
            coll = bpy.data.collections.get(cname)
            if not coll:
                continue

            # Recursively collect all objects and subcollections
            collections_to_process = [coll]
            while collections_to_process:
                current = collections_to_process.pop()
                collections_to_remove.append(current)
                # Add child collections to process queue
                collections_to_process.extend(list(current.children))
                # Collect all objects in current collection
                objects_to_remove.update(current.objects)

        # Second pass: batch remove all objects (much faster than one-by-one)
        # Use batch_remove if available (Blender 3.2+), otherwise fall back to loop
        if objects_to_remove:
            try:
                # batch_remove is significantly faster for large numbers of objects
                bpy.data.batch_remove(ids=objects_to_remove)
                removed_objs = len(objects_to_remove)
            except (AttributeError, TypeError):  # noqa: BLE001
                # Fallback for older Blender versions or if batch_remove fails
                for obj in objects_to_remove:
                    try:
                        bpy.data.objects.remove(obj, do_unlink=True)
                        removed_objs += 1
                    except Exception:  # noqa: BLE001
                        pass

        # Third pass: remove collections in reverse order (children before parents)
        # This ensures we don't try to remove a parent before its children
        for coll in reversed(collections_to_remove):
            try:
                bpy.data.collections.remove(coll)
                removed_colls += 1
            except Exception:  # noqa: BLE001
                pass

    finally:
        bpy.context.preferences.edit.use_global_undo = prev_undo
    return removed_objs, removed_colls


def collapse_collections_to_depth(
    root_name: str, depth: int = 1
):  # pragma: no cover - needs Blender
    """Hide (viewport + render) all subcollections deeper than `depth` under root_name.

    This is a pragmatic approximation of "collapsing" groups in the Outliner by
    hiding their contents. Blender does not expose Outliner expansion state via
    the stable Python API, so hiding child collections gives a similar, useful
    default: only the root and its immediate children remain visible.

    Args:
        root_name: Top-level collection name to operate on (e.g., 'Frontier').
        depth: Maximum depth to keep visible (0 = only root, 1 = root + immediate children).
    """
    if bpy is None:
        return
    root = bpy.data.collections.get(root_name)
    if not root:
        return

    # Iterative DFS/BFS with depth tracking (avoid recursion limits)
    stack = [(root, 0)]
    while stack:
        coll, d = stack.pop()
        for child in coll.children:
            child_depth = d + 1
            # If the child is deeper than allowed, hide it; otherwise keep and traverse
            if child_depth > depth:
                try:
                    child.hide_viewport = True
                except Exception:
                    pass
                try:
                    child.hide_render = True
                except Exception:
                    pass
            else:
                # Still within allowed depth, traverse children
                stack.append((child, child_depth))
