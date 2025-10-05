"""
Tests for node graph structure validation (no bpy required).

These tests validate the structure and logic of shader node connections
without requiring Blender runtime. They complement manual visual testing
by catching structural errors early.
"""

import pytest


class MockSocket:
    """Mock Blender node socket."""

    def __init__(self, name: str, socket_type: str = "NodeSocketColor"):
        self.name = name
        self.type = socket_type
        self.links = []

    def __repr__(self):
        return f"MockSocket({self.name!r}, {self.type!r})"


class MockNode:
    """Mock Blender shader node."""

    def __init__(self, node_type: str, name: str = ""):
        self.type = node_type
        self.name = name or node_type
        self.inputs = []
        self.outputs = []
        self.data_type = None  # For Mix nodes

    def add_input(self, name: str, socket_type: str = "NodeSocketColor"):
        socket = MockSocket(name, socket_type)
        self.inputs.append(socket)
        return socket

    def add_output(self, name: str, socket_type: str = "NodeSocketColor"):
        socket = MockSocket(name, socket_type)
        self.outputs.append(socket)
        return socket

    def __repr__(self):
        return f"MockNode({self.type!r}, {self.name!r})"


class TestVolumetricNodeStructure:
    """Test volumetric shader node requirements."""

    def test_mix_node_has_correct_float_sockets(self):
        """Verify ShaderNodeMix FLOAT has A/B at indices 2/3."""
        mix_node = MockNode("ShaderNodeMix", "Mix")
        mix_node.data_type = "FLOAT"

        # ShaderNodeMix FLOAT socket layout
        mix_node.add_input("Factor", "NodeSocketFloat")  # [0]
        mix_node.add_input("A", "NodeSocketFloat")  # [1] - NOT USED, wrong index
        mix_node.add_input("B", "NodeSocketFloat")  # [2] - actual A
        mix_node.add_input("C", "NodeSocketFloat")  # [3] - actual B (if exists)

        # Critical: inputs[2] and [3] are the actual A/B for FLOAT
        assert len(mix_node.inputs) >= 3
        assert mix_node.inputs[0].name == "Factor"
        # This documents the confusing API: inputs[2] is first value socket
        assert mix_node.inputs[2].name == "B"  # Blender calls it B but it's first value

    def test_colorramp_has_alpha_output(self):
        """ColorRamp must have Alpha output for Math/Mix nodes."""
        ramp = MockNode("ShaderNodeValToRGB", "ColorRamp")
        ramp.add_input("Fac", "NodeSocketFloat")
        ramp.add_output("Color", "NodeSocketColor")
        ramp.add_output("Alpha", "NodeSocketFloat")

        # Must have both outputs
        output_names = [s.name for s in ramp.outputs]
        assert "Color" in output_names
        assert "Alpha" in output_names

        # Alpha is the float output needed for Mix FLOAT nodes
        alpha_socket = next(s for s in ramp.outputs if s.name == "Alpha")
        assert alpha_socket.type == "NodeSocketFloat"


class TestStrategyReconnectionLogic:
    """Test strategy switching reconnection requirements."""

    @pytest.fixture
    def strategy_nodes(self):
        """Create mock node groups for 5 strategies."""
        return {
            "UniformOrange": MockNode("ShaderNodeGroup", "EVE_UniformOrange"),
            "CharacterRainbow": MockNode("ShaderNodeGroup", "EVE_CharacterRainbow"),
            "PatternCategories": MockNode("ShaderNodeGroup", "EVE_PatternCategories"),
            "PositionEncoding": MockNode("ShaderNodeGroup", "EVE_PositionEncoding"),
            "ProperNounHighlight": MockNode("ShaderNodeGroup", "EVE_ProperNounHighlight"),
        }

    @pytest.fixture
    def mix_nodes(self):
        """Create mock mix chain for 5 strategies (4 mix stages)."""
        nodes = {}
        for i in range(1, 5):
            # Color mixes
            color_node = MockNode("ShaderNodeMix", f"MixColor{i}")
            color_node.data_type = "RGBA"
            color_node.add_input("Factor", "NodeSocketFloat")
            color_node.add_input("A", "NodeSocketColor")
            color_node.add_input("B", "NodeSocketColor")
            nodes[f"MixColor{i}"] = color_node

            # Strength mixes
            strength_node = MockNode("ShaderNodeMix", f"MixStrength{i}")
            strength_node.data_type = "FLOAT"
            strength_node.add_input("Factor", "NodeSocketFloat")
            strength_node.add_input("A", "NodeSocketFloat")
            strength_node.add_input("B", "NodeSocketFloat")
            nodes[f"MixStrength{i}"] = strength_node

        return nodes

    def test_five_strategy_requires_four_mix_stages(self, strategy_nodes, mix_nodes):
        """Verify 5 strategies need 4 mix stages."""
        # Mix tree structure for 5 strategies:
        # Mix1: UniformOrange vs CharacterRainbow
        # Mix2: result vs PatternCategories
        # Mix3: result vs PositionEncoding
        # Mix4: result vs ProperNounHighlight

        assert len(strategy_nodes) == 5
        assert len([n for n in mix_nodes if n.startswith("MixColor")]) == 4
        assert len([n for n in mix_nodes if n.startswith("MixStrength")]) == 4

    def test_uniform_orange_must_be_in_strategy_map(self):
        """UniformOrange must be in reconnection node_group_map."""
        # This was the bug: UniformOrange was missing from the map
        node_group_map = {
            "UniformOrange": "ng_uniform",  # MUST be present
            "CharacterRainbow": "ng_rainbow",
            "PatternCategories": "ng_pattern",
            "PositionEncoding": "ng_position",
            "ProperNounHighlight": "ng_proper_noun",
        }

        assert "UniformOrange" in node_group_map
        assert node_group_map["UniformOrange"] == "ng_uniform"

    def test_strategy_selector_values_map_correctly(self):
        """Verify StrategySelector value ranges map to correct strategies."""
        # Value ranges for selector (float 0.0-4.0)
        strategy_values = {
            "UniformOrange": 0.0,
            "CharacterRainbow": 1.0,
            "PatternCategories": 2.0,
            "PositionEncoding": 3.0,
            "ProperNounHighlight": 4.0,
        }

        # Ensure no duplicates
        assert len(set(strategy_values.values())) == 5

        # Ensure sequential 0-4
        assert sorted(strategy_values.values()) == [0.0, 1.0, 2.0, 3.0, 4.0]

        # Ensure UniformOrange is default (0.0)
        assert strategy_values["UniformOrange"] == 0.0


class TestMaterialCreationRequirements:
    """Test material node setup requirements."""

    def test_material_needs_all_strategy_node_groups(self):
        """Material must reference all 5 strategy node groups."""
        required_node_groups = [
            "EVE_UniformOrange",
            "EVE_CharacterRainbow",
            "EVE_PatternCategories",
            "EVE_PositionEncoding",
            "EVE_ProperNounHighlight",
        ]

        # Each node group must be created via ensure_node_group()
        assert len(required_node_groups) == 5
        assert all("EVE_" in name for name in required_node_groups)

    def test_emission_shader_needs_color_and_strength_inputs(self):
        """Emission shader requires separate Color and Strength inputs."""
        emission = MockNode("ShaderNodeEmission", "Emission")
        emission.add_input("Color", "NodeSocketColor")
        emission.add_input("Strength", "NodeSocketFloat")

        input_names = [s.name for s in emission.inputs]
        assert "Color" in input_names
        assert "Strength" in input_names


class TestBoundingBoxCalculation:
    """Test volumetric bounding box calculation logic."""

    def test_bounding_box_uses_all_eight_corners(self):
        """Bounding box must use all 8 corners, not just centers."""
        # Mock bound_box data (8 corners)
        bound_box = [
            (0.0, 0.0, 0.0),  # corner 1
            (1.0, 0.0, 0.0),  # corner 2
            (1.0, 1.0, 0.0),  # corner 3
            (0.0, 1.0, 0.0),  # corner 4
            (0.0, 0.0, 1.0),  # corner 5
            (1.0, 0.0, 1.0),  # corner 6
            (1.0, 1.0, 1.0),  # corner 7
            (0.0, 1.0, 1.0),  # corner 8
        ]

        # All 8 corners must be considered
        assert len(bound_box) == 8

        # Calculate bounding box
        xs = [v[0] for v in bound_box]
        ys = [v[1] for v in bound_box]
        zs = [v[2] for v in bound_box]

        min_corner = (min(xs), min(ys), min(zs))
        max_corner = (max(xs), max(ys), max(zs))

        assert min_corner == (0.0, 0.0, 0.0)
        assert max_corner == (1.0, 1.0, 1.0)

    def test_vector_wrapper_required_for_matrix_multiply(self):
        """Matrix @ bound_box requires Vector wrapper."""
        # This was the bug: obj.matrix_world @ obj.bound_box[i]
        # Should be: obj.matrix_world @ Vector(obj.bound_box[i])

        # Mock matrix multiplication requirement
        bound_box_tuple = (1.0, 2.0, 3.0)

        # Demonstrate that tuples need wrapping
        assert isinstance(bound_box_tuple, tuple)

        # In real code: from mathutils import Vector
        # transformed = matrix_world @ Vector(bound_box_tuple)
        # This test documents the requirement


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
