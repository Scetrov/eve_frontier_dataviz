from addon import data_state


def test_data_state_roundtrip():
    # ensure clear state, then set and get systems and jumps
    data_state.clear_loaded_systems()
    data_state.clear_loaded_jumps()

    assert data_state.get_loaded_systems() is None
    assert data_state.get_loaded_jumps() is None

    sample_systems = [object(), object()]
    sample_jumps = [object()]

    data_state.set_loaded_systems(sample_systems)
    data_state.set_loaded_jumps(sample_jumps)

    assert data_state.get_loaded_systems() is sample_systems
    assert data_state.get_loaded_jumps() is sample_jumps
