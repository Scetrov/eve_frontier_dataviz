"""Smoke test ensuring the addon package imports without Blender.

We only verify that top-level register/unregister are present and callable.
The operators package guards all bpy usage so an ImportError would signal a regression.
"""

import importlib


def test_import_root():
    mod = importlib.import_module("addon")
    assert hasattr(mod, "register")
    assert hasattr(mod, "unregister")
