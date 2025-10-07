import importlib
import sys
import types


def _make_minimal_bpy_with_collections():
    """Create a minimal bpy module with data/collections and context stubs."""
    bpy_mod = types.ModuleType("bpy")
    types_mod = types.ModuleType("bpy.types")

    class Panel:  # minimal stand-in
        pass

    class Operator:
        def report(self, *_a, **_k):
            return None

    types_mod.Panel = Panel
    types_mod.Operator = Operator
    bpy_mod.types = types_mod

    # Minimal data.collections implementation
    class Collection:
        def __init__(self, name):
            self.name = name
            self.children = []
            # default properties that real collections have
            self.hide_viewport = True
            self.hide_render = True

    class Collections:
        def __init__(self):
            self._map = {}

        def get(self, name):
            return self._map.get(name)

        def add(self, coll):
            self._map[coll.name] = coll

    data = types.SimpleNamespace()
    data.collections = Collections()
    bpy_mod.data = data

    # Minimal context with preferences/addons and global context attr
    prefs = types.SimpleNamespace()
    prefs.addons = {}
    ctx = types.SimpleNamespace()
    ctx.preferences = prefs
    bpy_mod.context = ctx

    return bpy_mod, Collection


def test_filters_show_and_hide_persist(monkeypatch):
    # Prepare a minimal bpy stub and inject into sys.modules
    bpy_mod, Collection = _make_minimal_bpy_with_collections()
    sys.modules["bpy"] = bpy_mod
    sys.modules["bpy.types"] = bpy_mod.types

    # Create SystemsByName root with two child buckets
    root = Collection("SystemsByName")
    child_a = Collection("A-Dash")
    child_b = Collection("B-Colon")
    root.children.extend([child_a, child_b])
    bpy_mod.data.collections.add(root)

    # Import panels and ensure a fresh module import
    import addon.panels as panels

    importlib.reload(panels)

    # Replace panels.get_prefs with a fake prefs provider that exposes
    # the per-pattern boolean attributes so persistence code runs.
    class FakePrefs:
        def __init__(self):
            self.filter_dash = False
            self.filter_colon = False
            self.filter_dotseq = False
            self.filter_pipe = False
            self.filter_other = False
            self.filter_blackhole = False

    fake_prefs = FakePrefs()

    def _fake_get_prefs(_ctx):
        return fake_prefs

    panels.get_prefs = _fake_get_prefs

    # Run show all operator - should set children visible and prefs True
    op_show = panels.EVE_OT_filters_show_all()
    res = op_show.execute(None)
    assert res == {"FINISHED"}
    assert child_a.hide_viewport is False
    assert child_b.hide_viewport is False
    assert child_a.hide_render is False
    assert fake_prefs.filter_dash is True or fake_prefs.filter_colon is True

    # Now run hide all operator - should set children hidden and prefs False
    op_hide = panels.EVE_OT_filters_hide_all()
    res2 = op_hide.execute(None)
    assert res2 == {"FINISHED"}
    assert child_a.hide_viewport is True
    assert child_b.hide_viewport is True
    assert child_a.hide_render is True
    assert fake_prefs.filter_dash is False or fake_prefs.filter_colon is False


def test_filters_show_all_no_root_returns_cancelled(monkeypatch):
    # Ensure behavior when SystemsByName missing returns CANCELLED
    bpy_mod, _ = _make_minimal_bpy_with_collections()
    sys.modules["bpy"] = bpy_mod
    sys.modules["bpy.types"] = bpy_mod.types
    import addon.panels as panels

    importlib.reload(panels)

    op_show = panels.EVE_OT_filters_show_all()
    res = op_show.execute(None)
    assert res == {"CANCELLED"}
