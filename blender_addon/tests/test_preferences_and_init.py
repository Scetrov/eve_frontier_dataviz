import importlib
import importlib.util
from pathlib import Path

import pytest


def test_scale_factor_property():
    from addon.preferences import EVEVisualizerPreferences

    prefs = EVEVisualizerPreferences()
    prefs.scale_exponent = -3
    assert pytest.approx(prefs.scale_factor, rel=1e-9) == 10.0**-3


def test_default_db_path_fallback(monkeypatch, tmp_path):
    # Force Path.resolve to raise to exercise the fallback branch
    from addon import preferences

    original_resolve = Path.resolve

    def _bad_resolve(self):
        raise OSError("boom")

    monkeypatch.setattr(Path, "resolve", _bad_resolve, raising=False)
    try:
        val = preferences._default_db_path()
        assert val == ""  # fallback to empty string
    finally:
        monkeypatch.setattr(Path, "resolve", original_resolve, raising=False)


def test_get_prefs_heuristic_finds_preferences():
    # Create a fake context where one addon entry exposes a preferences object
    from addon.preferences import EVEVisualizerPreferences, get_prefs

    class FakeAddon:
        def __init__(self):
            self.preferences = EVEVisualizerPreferences()

    class FakeContext:
        def __init__(self):
            self.preferences = type("_P", (), {"addons": {"something": FakeAddon()}})()

    ctx = FakeContext()
    prefs = get_prefs(ctx)
    assert isinstance(prefs, EVEVisualizerPreferences)


def test__load_modules_handles_import_errors(monkeypatch):
    # Ensure __init__._load_modules handles import failures gracefully
    import addon.__init__ as ai

    called = []

    def fake_import(name, *args, **kwargs):
        # Simulate import failure when importing the first requested module
        called.append(name)
        if name.endswith(".preferences"):
            raise ImportError("nope")
        return importlib.import_module(name)

    monkeypatch.setattr(importlib, "import_module", fake_import)
    try:
        mods = ai._load_modules()
        # Should return a list (possibly empty) and not raise
        assert isinstance(mods, list)
    finally:
        importlib.reload(ai)
