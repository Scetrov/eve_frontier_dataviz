import importlib

from addon.operators import _shared


def test_generated_collections_includes_systemsbyname():
    """Ensure GENERATED_COLLECTIONS includes SystemsByName so clear_generated()
    will remove the new top-level collection created by the scene builder.
    """
    # Reload to ensure latest code is used
    importlib.reload(_shared)
    assert "SystemsByName" in _shared.GENERATED_COLLECTIONS
