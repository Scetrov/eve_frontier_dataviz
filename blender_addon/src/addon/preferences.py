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
    """Add-on preferences.

    Uses annotation-style definitions (Blender 4.x recommended) with a runtime
    fallback to classic assignments for older or edge cases. We avoid heavy
    default path resolution; user will set DB path explicitly if blank.
    """

    bl_idname = Path(__file__).parent.name  # matches installed folder name

    # Properties (annotation style)
    db_path: StringProperty(  # type: ignore[valid-type]
        name="Database Path",
        subtype="FILE_PATH",
        default="",  # leave blank; attempting repo-relative path in an installed add-on is brittle
        description="Path to static.db SQLite file (set this before loading data)",
    )
    scale_factor: FloatProperty(  # type: ignore[valid-type]
        name="Coordinate Scale",
        default=0.001,
        min=0.0000001,
        description="Multiply raw coordinates by this factor",
    )
    enable_cache: BoolProperty(  # type: ignore[valid-type]
        name="Enable Data Cache",
        default=True,
        description="Cache parsed data in memory for faster rebuild",
    )

    def draw(self, context):  # noqa: D401
        layout = self.layout
        col = layout.column(align=True)
        # Only draw props if they are resolved (avoid _PropertyDeferred edge cases)
        for prop_name in ("db_path", "scale_factor", "enable_cache"):
            if prop_name in self.__class__.__dict__:
                try:
                    col.prop(self, prop_name)
                except Exception as e:  # pragma: no cover - Blender UI safety
                    col.label(text=f"(Failed prop {prop_name}: {e})", icon="ERROR")
        # Show path existence hint
        try:
            if isinstance(self.db_path, str) and self.db_path:
                if not Path(self.db_path).exists():
                    col.label(text="(File not found)", icon="ERROR")
        except Exception:
            pass


# ---- Fallback injection (in case Blender did not materialize annotation properties) ----
try:  # pragma: no cover - runtime safety
    _missing = []
    if not hasattr(EVEVisualizerPreferences, "db_path"):
        EVEVisualizerPreferences.db_path = StringProperty(  # type: ignore[attr-defined]
            name="Database Path",
            subtype="FILE_PATH",
            default="",
            description="Path to static.db SQLite file",
        )
        _missing.append("db_path")
    if not hasattr(EVEVisualizerPreferences, "scale_factor"):
        EVEVisualizerPreferences.scale_factor = FloatProperty(  # type: ignore[attr-defined]
            name="Coordinate Scale",
            default=0.001,
            min=0.0000001,
            description="Multiply raw coordinates by this factor",
        )
        _missing.append("scale_factor")
    if not hasattr(EVEVisualizerPreferences, "enable_cache"):
        EVEVisualizerPreferences.enable_cache = BoolProperty(  # type: ignore[attr-defined]
            name="Enable Data Cache",
            default=True,
            description="Cache parsed data in memory for faster rebuild",
        )
        _missing.append("enable_cache")
    if _missing:
        print(f"[EVEVisualizer][info] Injected fallback properties: {_missing}")
    else:
        print("[EVEVisualizer][info] Annotation properties present (no fallback needed)")
except Exception as _e:  # pragma: no cover
    print(f"[EVEVisualizer][warn] Fallback property injection failed: {_e}")


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
