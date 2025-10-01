import os
import traceback
from pathlib import Path

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, StringProperty
from bpy.types import AddonPreferences, Operator


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


ENV_DB_VAR = "EVE_STATIC_DB"
_ENV_DB_PATH = os.environ.get(ENV_DB_VAR)
_DEFAULT_USER_DB = str(
    (Path.home() / "Documents" / "static.db").resolve()
)  # kept for documentation only


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
        default=_ENV_DB_PATH or "",  # empty if no ENV override
        description="Path to static.db (set here, use Locate, or define env EVE_STATIC_DB)",
    )
    scale_factor: FloatProperty(  # type: ignore[valid-type]
        name="Coordinate Scale",
        default=1e-13,
        min=1e-16,
        soft_min=1e-16,
        soft_max=1e-1,
        description=(
            "Multiply raw coordinates by this factor. 1e-13 maps ~1e16m spans to ~1000 BU."
        ),
        precision=6,
    )
    enable_cache: BoolProperty(  # type: ignore[valid-type]
        name="Enable Data Cache",
        default=True,
        description="Cache parsed data in memory for faster rebuild",
    )
    system_point_radius: FloatProperty(  # type: ignore[valid-type]
        name="System Point Radius",
        default=2.0,
        min=0.01,
        soft_max=25.0,
        description="Visual radius (in Blender Units after scaling) for system spheres",
        precision=3,
    )
    system_representation: EnumProperty(  # type: ignore[valid-type]
        name="System Display",
        description="Geometry used for system markers (Point=Empty, Sphere=UV Sphere geometry)",
        items=[
            ("EMPTY", "Point", "Use lightweight empties (fast, not renderable geometry)"),
            ("SPHERE", "Sphere", "Use sphere mesh per system (slower, fully renderable)"),
        ],
        default="EMPTY",
    )
    build_percentage: FloatProperty(  # type: ignore[valid-type]
        name="Build %",
        default=1.0,
        min=0.01,
        max=1.0,
        subtype="FACTOR",
        description="Fraction of loaded systems to instantiate (sampled uniformly). Increase for more detail.",
        precision=3,
    )

    def draw(self, context):  # noqa: D401
        layout = self.layout
        col = layout.column(align=True)
        # Only draw props if they are resolved (avoid _PropertyDeferred edge cases)
        for prop_name in (
            "db_path",
            "scale_factor",
            "enable_cache",
            "system_representation",
            "system_point_radius",
            "build_percentage",
        ):
            if prop_name in self.__class__.__dict__:
                try:
                    # If env var override is active, show db_path disabled to communicate source.
                    if prop_name == "db_path" and _ENV_DB_PATH:
                        row = col.row()
                        row.enabled = False
                        row.prop(self, prop_name)
                    else:
                        col.prop(self, prop_name)
                except Exception as e:  # pragma: no cover - Blender UI safety
                    col.label(text=f"(Failed prop {prop_name}: {e})", icon="ERROR")
        # Locate / override info
        row = col.row(align=True)
        row.operator("eve.locate_static_db", text="Locate", icon="FILE_FOLDER")
        if _ENV_DB_PATH:
            col.label(text=f"Env {ENV_DB_VAR} in use (read-only)", icon="INFO")
        elif not self.db_path:
            col.label(
                text="Set a database path, click Locate, or define EVE_STATIC_DB", icon="INFO"
            )
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
            default=_ENV_DB_PATH or "",
            description="Path to static.db (set here, use Locate, or define env EVE_STATIC_DB)",
        )
        _missing.append("db_path")
    if not hasattr(EVEVisualizerPreferences, "scale_factor"):
        EVEVisualizerPreferences.scale_factor = FloatProperty(  # type: ignore[attr-defined]
            name="Coordinate Scale",
            default=1e-13,
            min=1e-16,
            soft_min=1e-16,
            soft_max=1e-1,
            description="Multiply raw coordinates by this factor. 1e-13 maps ~1e16m spans to ~1000 BU.",
            precision=6,
        )
        _missing.append("scale_factor")
    if not hasattr(EVEVisualizerPreferences, "enable_cache"):
        EVEVisualizerPreferences.enable_cache = BoolProperty(  # type: ignore[attr-defined]
            name="Enable Data Cache",
            default=True,
            description="Cache parsed data in memory for faster rebuild",
        )
        _missing.append("enable_cache")
    if not hasattr(EVEVisualizerPreferences, "system_point_radius"):
        EVEVisualizerPreferences.system_point_radius = FloatProperty(  # type: ignore[attr-defined]
            name="System Point Radius",
            default=2.0,
            min=0.01,
            soft_max=25.0,
            description="Visual radius (in Blender Units after scaling) for system spheres",
            precision=3,
        )
        _missing.append("system_point_radius")
    if not hasattr(EVEVisualizerPreferences, "system_representation"):
        EVEVisualizerPreferences.system_representation = EnumProperty(  # type: ignore[attr-defined]
            name="System Display",
            description="Geometry used for system markers (Point=Empty, Sphere=UV Sphere geometry)",
            items=[
                ("EMPTY", "Point", "Use lightweight empties (fast, not renderable geometry)"),
                ("SPHERE", "Sphere", "Use sphere mesh per system (slower, fully renderable)"),
            ],
            default="EMPTY",
        )
        _missing.append("system_representation")
    if not hasattr(EVEVisualizerPreferences, "build_percentage"):
        EVEVisualizerPreferences.build_percentage = FloatProperty(  # type: ignore[attr-defined]
            name="Build %",
            default=1.0,
            min=0.01,
            max=1.0,
            subtype="FACTOR",
            description="Fraction of loaded systems to instantiate (sampled uniformly). Increase for more detail.",
            precision=3,
        )
        _missing.append("build_percentage")
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


def _register_prefs():  # internal helper
    try:
        bpy.utils.register_class(EVEVisualizerPreferences)
    except Exception as e:  # pragma: no cover - show why preferences might be blank
        print(f"[EVEVisualizer][error] register_class(EVEVisualizerPreferences) failed: {e}")
        traceback.print_exc()
        return
    try:  # pragma: no cover - Blender runtime only
        print(
            f"[EVEVisualizer] Preferences registered: bl_idname='{EVEVisualizerPreferences.bl_idname}', "
            f"folder='{Path(__file__).parent.name}', env_override={'yes' if _ENV_DB_PATH else 'no'}"
        )
    except Exception:
        pass


def _unregister_prefs():  # pragma: no cover - Blender runtime usage
    try:
        bpy.utils.unregister_class(EVEVisualizerPreferences)
    except Exception:
        pass


class EVE_OT_locate_static_db(Operator):  # pragma: no cover - Blender runtime usage
    bl_idname = "eve.locate_static_db"
    bl_label = "Locate static.db"
    bl_description = "Browse for a static.db file and set it as database path"

    filepath: StringProperty(subtype="FILE_PATH")  # type: ignore[valid-type]

    def execute(self, context):
        prefs = get_prefs(context)
        if self.filepath and self.filepath.lower().endswith("static.db"):
            prefs.db_path = self.filepath
            self.report({"INFO"}, f"Database path set: {self.filepath}")
            return {"FINISHED"}
        self.report({"ERROR"}, "Please select a static.db file")
        return {"CANCELLED"}

    def invoke(self, context, event):  # noqa: D401
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


# Public register/unregister
def register():  # noqa: D401
    _register_prefs()
    try:  # operator
        bpy.utils.register_class(EVE_OT_locate_static_db)
    except Exception as e:  # pragma: no cover
        print(f"[EVEVisualizer][warn] Failed to register locate operator: {e}")


def unregister():  # pragma: no cover - Blender runtime usage
    try:
        bpy.utils.unregister_class(EVE_OT_locate_static_db)
    except Exception:
        pass
    _unregister_prefs()
