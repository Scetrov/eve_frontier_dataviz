from pathlib import Path

import bpy
from bpy.props import BoolProperty, FloatProperty, StringProperty
from bpy.types import AddonPreferences


class EVEVisualizerPreferences(AddonPreferences):
    bl_idname = __package__ or "addon"

    # Resolve default DB path relative to repo root (three parents up from src/addon)
    _default_db = Path(__file__).resolve().parents[3] / 'data' / 'static.db'
    db_path = StringProperty(
        name="Database Path",
        subtype='FILE_PATH',
        default=str(_default_db),
        description="Path to static.db SQLite file",
    )

    scale_factor = FloatProperty(
        name="Coordinate Scale",
        default=0.001,
        min=0.0000001,
        description="Multiply raw coordinates by this factor",
    )

    enable_cache = BoolProperty(
        name="Enable Data Cache",
        default=True,
        description="Cache parsed data in memory for faster rebuild",
    )

    def draw(self, context):  # noqa: D401
        layout = self.layout
        layout.prop(self, "db_path")
        layout.prop(self, "scale_factor")
        layout.prop(self, "enable_cache")


def get_prefs(context):  # pragma: no cover - Blender runtime usage
    return context.preferences.addons[__package__].preferences


def register():  # noqa: D401
    bpy.utils.register_class(EVEVisualizerPreferences)


def unregister():  # pragma: no cover - Blender runtime usage
    bpy.utils.unregister_class(EVEVisualizerPreferences)
