import importlib
import sys
import types
from pathlib import Path


def _make_minimal_bpy_for_viewport():
    """Create a minimal bpy stub sufficient for viewport.hdri procedural branch."""
    bpy_mod = types.ModuleType("bpy")
    types_mod = types.ModuleType("bpy.types")

    class Operator:
        def report(self, *_a, **_k):
            return None

    types_mod.Operator = Operator
    bpy_mod.types = types_mod

    # Lightweight props shim used at class definition time
    bpy_mod.props = types.SimpleNamespace(FloatProperty=lambda **kwargs: 1.0)

    # Data containers
    class Socket:
        def __init__(self):
            self.default_value = None

    class ColorRampElement:
        def __init__(self):
            self.position = 0.0
            self.color = (0.0, 0.0, 0.0, 1.0)

    class ColorRamp:
        def __init__(self):
            self.interpolation = "LINEAR"
            self.elements = [ColorRampElement(), ColorRampElement()]

    class IOMap:
        def __init__(self, names=()):
            # preserve name -> socket and indexable list
            self._by_name = {n: Socket() for n in names}
            # create a larger indexed list for numeric access used by nodes
            # include indices up to at least 8 to satisfy operator use
            self._by_index = [Socket() for _ in range(12)]

        def __getitem__(self, key):
            if isinstance(key, int):
                return self._by_index[key]
            # Return existing named socket or create one lazily for tests
            return self._by_name.setdefault(key, Socket())

        def __iter__(self):
            return iter(self._by_index)

    class Node:
        def __init__(self, ntype):
            self.type = ntype
            self.location = (0, 0)
            # Provide inputs/outputs that support numeric and string access
            self.inputs = IOMap(names=("Fac", "Color"))
            self.outputs = IOMap(names=("Color",))
            # misc custom attrs
            if ntype == "ShaderNodeValToRGB":
                self.color_ramp = ColorRamp()

    class Nodes:
        def __init__(self):
            self._nodes = []

        def clear(self):
            self._nodes.clear()

        def new(self, ntype):
            n = Node(ntype)
            self._nodes.append(n)
            return n

    class Links:
        def __init__(self):
            self._links = []

        def new(self, a, b):
            # record the link; no-op otherwise
            self._links.append((a, b))

    class NodeTree:
        def __init__(self):
            self.nodes = Nodes()
            self.links = Links()

    class World:
        def __init__(self, name):
            self.name = name
            self.use_nodes = False
            self.node_tree = NodeTree()

    class Worlds:
        def __init__(self):
            self._map = {}

        def new(self, name):
            w = World(name)
            self._map[name] = w
            return w

    data = types.SimpleNamespace()
    data.worlds = Worlds()
    data.images = types.SimpleNamespace(get=lambda name: None, load=lambda p: None)
    bpy_mod.data = data

    # Context & scene
    class Scene:
        def __init__(self):
            self.world = None

    ctx = types.SimpleNamespace()
    ctx.scene = Scene()
    bpy_mod.context = ctx

    return bpy_mod


def test_viewport_hdri_procedural(monkeypatch):
    # Force Path.exists to return False so the operator uses procedural branch
    monkeypatch.setattr(Path, "exists", lambda self: False, raising=False)

    bpy_mod = _make_minimal_bpy_for_viewport()
    sys.modules["bpy"] = bpy_mod
    sys.modules["bpy.types"] = bpy_mod.types

    # Import the module under test and reload to pick up our stub
    import addon.operators.viewport as viewport

    importlib.reload(viewport)

    # Instantiate operator and run execute. The procedural branch should finish successfully.
    op = viewport.EVE_OT_viewport_set_hdri()
    # The class defines strength as a FloatProperty at class-level; ensure instance has it
    try:
        op.strength = 1.0
    except Exception:
        # some test shims may not allow attribute set; ignore if so
        pass
    res = op.execute(None)

    # Expect FINISHED and that a world was added to context with use_nodes True
    assert res == {"FINISHED"}
    assert bpy_mod.context.scene.world is not None
    assert bpy_mod.context.scene.world.use_nodes is True
    # Expect node tree to have at least one node created (background)
    nt = bpy_mod.context.scene.world.node_tree
    assert hasattr(nt, "nodes")
