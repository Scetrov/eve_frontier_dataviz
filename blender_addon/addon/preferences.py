import os

import bpy
from bpy.props import BoolProperty, FloatProperty, StringProperty
from bpy.types import AddonPreferences


class EVEVisualizerPreferences(AddonPreferences):
    bl_idname = __package__ or "addon"

    db_path = StringProperty(
        name="Database Path",
        subtype='FILE_PATH',
        default=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'static.db')),
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

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "db_path")
        layout.prop(self, "scale_factor")
        layout.prop(self, "enable_cache")


def get_prefs(context):
    return context.preferences.addons[__package__].preferences


def register():  # noqa: D401
    bpy.utils.register_class(EVEVisualizerPreferences)


def unregister():
    bpy.utils.unregister_class(EVEVisualizerPreferences)
