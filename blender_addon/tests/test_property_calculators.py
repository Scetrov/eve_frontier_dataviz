"""Tests for visualization property calculators."""

from __future__ import annotations

from addon.operators.property_calculators import (
    calculate_child_metrics,
    calculate_name_char_bucket,
    calculate_name_pattern_category,
    is_blackhole_system,
)


class TestNamePatternCategory:
    """Test system name pattern classification."""

    def test_dash_pattern(self):
        assert calculate_name_pattern_category("ABC-123") == 0
        assert calculate_name_pattern_category("abc-def") == 0
        assert calculate_name_pattern_category("123-456") == 0

    def test_colon_pattern(self):
        assert calculate_name_pattern_category("AB:123") == 1
        assert calculate_name_pattern_category("XY:999") == 1

    def test_dotseq_pattern(self):
        assert calculate_name_pattern_category("1.2.3") == 2
        assert calculate_name_pattern_category("10.20.30") == 2
        assert calculate_name_pattern_category("A.B.C") == 2

    def test_pipe_pattern(self):
        assert calculate_name_pattern_category("ABC|123") == 3
        assert calculate_name_pattern_category("XYZ|999") == 3

    def test_other_pattern(self):
        assert calculate_name_pattern_category("Random") == 4
        assert calculate_name_pattern_category("J055520") == 4  # blackhole
        assert calculate_name_pattern_category("") == 4

    def test_near_miss_patterns(self):
        # Wrong length for dash
        assert calculate_name_pattern_category("AB-123") == 4  # 6 chars not 7
        # Multiple pipes
        assert calculate_name_pattern_category("A|B|C|D") == 4
        # Wrong dot count
        assert calculate_name_pattern_category("1.2.3.4") == 4  # 3 dots not 2


class TestNameCharBucket:
    """Test first character bucketing."""

    def test_bucket_0_a_to_c(self):
        assert calculate_name_char_bucket("Alpha") == 0
        assert calculate_name_char_bucket("Bravo") == 0
        assert calculate_name_char_bucket("Charlie") == 0
        assert calculate_name_char_bucket("a123") == 0  # lowercase

    def test_bucket_1_d_to_f(self):
        assert calculate_name_char_bucket("Delta") == 1
        assert calculate_name_char_bucket("Echo") == 1
        assert calculate_name_char_bucket("Foxtrot") == 1

    def test_bucket_2_g_to_i(self):
        assert calculate_name_char_bucket("Golf") == 2
        assert calculate_name_char_bucket("Hotel") == 2
        assert calculate_name_char_bucket("India") == 2

    def test_bucket_3_j_to_l(self):
        assert calculate_name_char_bucket("Juliet") == 3
        assert calculate_name_char_bucket("Kilo") == 3
        assert calculate_name_char_bucket("Lima") == 3

    def test_bucket_4_m_to_o(self):
        assert calculate_name_char_bucket("Mike") == 4
        assert calculate_name_char_bucket("November") == 4
        assert calculate_name_char_bucket("Oscar") == 4

    def test_bucket_5_p_to_r(self):
        assert calculate_name_char_bucket("Papa") == 5
        assert calculate_name_char_bucket("Quebec") == 5
        assert calculate_name_char_bucket("Romeo") == 5

    def test_bucket_6_s_to_u(self):
        assert calculate_name_char_bucket("Sierra") == 6
        assert calculate_name_char_bucket("Tango") == 6
        assert calculate_name_char_bucket("Uniform") == 6

    def test_bucket_7_v_to_x(self):
        assert calculate_name_char_bucket("Victor") == 7
        assert calculate_name_char_bucket("Whiskey") == 7
        assert calculate_name_char_bucket("Xray") == 7

    def test_bucket_8_y_z_and_digits(self):
        assert calculate_name_char_bucket("Yankee") == 8
        assert calculate_name_char_bucket("Zulu") == 8
        assert calculate_name_char_bucket("0ABC") == 8
        assert calculate_name_char_bucket("9XYZ") == 8
        assert calculate_name_char_bucket("5-Test") == 8

    def test_fallback_bucket(self):
        assert calculate_name_char_bucket("") == -1
        assert calculate_name_char_bucket("-ABC") == -1  # starts with special char
        assert calculate_name_char_bucket("@System") == -1


class TestChildMetrics:
    """Test planet/moon counting."""

    def test_no_planets(self):
        assert calculate_child_metrics([]) == (0, 0)

    def test_planets_no_moons(self):
        class Planet:
            def __init__(self):
                self.moons = []

        planets = [Planet(), Planet(), Planet()]
        assert calculate_child_metrics(planets) == (3, 0)

    def test_planets_with_moons(self):
        class Planet:
            def __init__(self, moon_count):
                self.moons = [None] * moon_count

        planets = [Planet(2), Planet(5), Planet(0), Planet(3)]
        assert calculate_child_metrics(planets) == (4, 10)


class TestBlackholeDetection:
    """Test blackhole system detection."""

    def test_known_blackholes(self):
        assert is_blackhole_system("J055520") is True
        assert is_blackhole_system("J110909") is True
        assert is_blackhole_system("J164710") is True
        assert is_blackhole_system("J174618") is True
        assert is_blackhole_system("J175552") is True

    def test_non_blackholes(self):
        assert is_blackhole_system("J055521") is False  # similar but not exact
        assert is_blackhole_system("Random") is False
        assert is_blackhole_system("") is False

    def test_case_sensitive(self):
        # Blackhole names should be exact match (case-sensitive)
        assert is_blackhole_system("j055520") is False
        assert is_blackhole_system("J055520") is True
