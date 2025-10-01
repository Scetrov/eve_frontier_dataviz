import traceback
from pathlib import Path

import bpy
from bpy.props import BoolProperty, FloatProperty, StringProperty
from bpy.types import AddonPreferences


def _default_db_path():
    """Best-effort default path to data/static.db relative to repository root.

    If resolution fails (unusual packaging), fall back to an empty string so the
    preference field is editable instead of crashing registration.
    """  # noqa: D401
    try:
        return str(Path(__file__).resolve().parents[3] / "data" / "static.db")
    except Exception as e:  # pragma: no cover - safety net
        print(f"[EVEVisualizer][warn] default db path resolution failed: {e}")
        traceback.print_exc()
        return ""


class EVEVisualizerPreferences(AddonPreferences):
    # Use actual folder name (works for dev 'addon' and distributed 'eve_frontier_visualizer').
    bl_idname = Path(__file__).parent.name

    # NOTE: Using classic assignment style for maximum compatibility (annotation-only
    # can be unreliable depending on Blender/Python bundling).
    db_path = StringProperty(  # type: ignore[valid-type]
        name="Database Path",
        subtype="FILE_PATH",
        default=_default_db_path(),
        description="Path to static.db SQLite file",
    )

    scale_factor = FloatProperty(  # type: ignore[valid-type]
        name="Coordinate Scale",
        default=0.001,
        min=0.0000001,
        description="Multiply raw coordinates by this factor",
    )

    enable_cache = BoolProperty(  # type: ignore[valid-type]
        name="Enable Data Cache",
        default=True,
        description="Cache parsed data in memory for faster rebuild",
    )

    def draw(self, context):  # noqa: D401
        layout = self.layout
        col = layout.column(align=True)
        col.prop(self, "db_path")
        col.prop(self, "scale_factor")
        col.prop(self, "enable_cache")
        # Helpful runtime hint (non-fatal) if path missing
        db = Path(self.db_path)
        if self.db_path and not db.exists():
            col.label(text="(File not found)", icon="ERROR")


def get_prefs(context):  # pragma: no cover - Blender runtime usage
    key = Path(__file__).parent.name
    if key in context.preferences.addons:
        return context.preferences.addons[key].preferences
    # Fallback: heuristic search.
    for v in context.preferences.addons.values():  # pragma: no cover - rare
        prefs = getattr(v, "preferences", None)
        if isinstance(prefs, EVEVisualizerPreferences):
            return prefs
    raise KeyError(f"EVEVisualizerPreferences not found (expected addon key '{key}')")


def register():  # noqa: D401
    try:
        bpy.utils.register_class(EVEVisualizerPreferences)
    except Exception as e:  # pragma: no cover - show why preferences might be blank
        print(f"[EVEVisualizer][error] register_class(EVEVisualizerPreferences) failed: {e}")
        traceback.print_exc()
        return
    try:  # pragma: no cover - Blender runtime only
        print(
            f"[EVEVisualizer] Preferences registered: bl_idname='{EVEVisualizerPreferences.bl_idname}', "
            f"folder='{Path(__file__).parent.name}'"
        )
        # If the folder name is literally 'addon', Blender may register the add-on under
        # a different key (e.g. archive name). Provide a runtime sanity check hint.
        prefs = getattr(bpy.context, "preferences", None)
        if prefs is not None:
            keys = list(getattr(prefs, "addons", {}).keys())
            if EVEVisualizerPreferences.bl_idname not in keys:
                print(
                    "[EVEVisualizer][warn] bl_idname not in addons keys; keys=",
                    keys,
                    "— preferences panel may be blank.",
                )
    except Exception:
        pass


def unregister():  # pragma: no cover - Blender runtime usage
    bpy.utils.unregister_class(EVEVisualizerPreferences)
