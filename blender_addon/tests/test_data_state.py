from addon import data_state
from addon.data_loader import System


def test_data_state_roundtrip():
    # Initially empty
    assert data_state.get_loaded_systems() is None
    systems = [System(id=1, name="Alpha", x=0.0, y=0.0, z=0.0, security=None, planets=[])]
    data_state.set_loaded_systems(systems)
    got = data_state.get_loaded_systems()
    assert got is systems
    data_state.clear_loaded_systems()
    assert data_state.get_loaded_systems() is None
