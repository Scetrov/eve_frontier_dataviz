"""Shared helper utilities for operator modules."""

from __future__ import annotations

try:  # pragma: no cover
    import bpy  # type: ignore
except Exception:  # noqa: BLE001
    bpy = None  # type: ignore

GENERATED_COLLECTIONS = ["EVE_Systems", "EVE_Planets", "EVE_Moons"]


def get_or_create_collection(name: str):  # pragma: no cover - needs Blender
    if bpy is None:
        return None
    coll = bpy.data.collections.get(name)
    if not coll:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
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
