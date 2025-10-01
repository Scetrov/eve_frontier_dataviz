from pathlib import Path

import bpy
from bpy.props import BoolProperty, FloatProperty, StringProperty
from bpy.types import AddonPreferences


def _top_level_addon_name():
    """Return the top-level addon module name.

    Handles cases where the user installed either the inner folder ("addon")
    or a renamed/distribution folder (e.g. eve_frontier_visualizer).
    """
    return __name__.split(".")[0]


def _default_db_path():
    """Best-effort default path to data/static.db relative to repository root.

    If resolution fails (unusual packaging), fall back to an empty string so the
    preference field is editable instead of crashing registration.
    """  # noqa: D401
    try:
        # repo_root / blender_addon / src / addon / preferences.py -> parents[3] == repo_root
        return str(Path(__file__).resolve().parents[3] / "data" / "static.db")
    except Exception:  # pragma: no cover - safety net
        return ""


class EVEVisualizerPreferences(AddonPreferences):
    # Blender matches this to the add-on package name key in context.preferences.addons
    bl_idname = _top_level_addon_name()

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
    addon_key = _top_level_addon_name()
    # Defensive: ensure key exists; if not, attempt a fallback search.
    if addon_key in context.preferences.addons:
        return context.preferences.addons[addon_key].preferences
    # Fallback: find first addon module containing our preferences class
    for _k, v in context.preferences.addons.items():  # pragma: no cover - rare
        if hasattr(v, "preferences") and isinstance(v.preferences, EVEVisualizerPreferences):
            return v.preferences
    raise KeyError(f"EVEVisualizerPreferences not found under addon key '{addon_key}'")


def register():  # noqa: D401
    bpy.utils.register_class(EVEVisualizerPreferences)
    try:  # pragma: no cover - Blender runtime only
        print(
            f"[EVEVisualizer] Preferences registered: bl_idname='{EVEVisualizerPreferences.bl_idname}', "
            f"folder='{Path(__file__).parent.name}'"
        )
    except Exception:
        pass


def unregister():  # pragma: no cover - Blender runtime usage
    bpy.utils.unregister_class(EVEVisualizerPreferences)
