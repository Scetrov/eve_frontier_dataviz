"""Pre-calculate semantic properties for shader-driven visualization.

These functions compute visualization properties during scene build,
storing them as custom properties on objects. Shaders can then read
these properties for instant strategy switching without Python iteration.
"""

from __future__ import annotations


def calculate_char_indices(name: str, max_chars: int = 10) -> list[float]:
    """Calculate normalized ordinal values for first N characters.

    Each character is converted to a float value:
    - Alphanumeric (A-Z, 0-9): Normalized to 0.0-1.0 based on ordinal value
    - Non-alphanumeric or missing: -1.0

    Args:
        name: System name to analyze
        max_chars: Number of character positions to calculate (default 10)

    Returns:
        List of floats, length = max_chars, each value in range [-1.0, 1.0]
        where -1.0 = non-alphanumeric/missing, 0.0-1.0 = alphanumeric position

    Example:
        "ABC-123" → [0.0, 0.03, 0.05, -1.0, 0.08, 0.11, 0.14, -1.0, -1.0, -1.0]
                     A    B    C    -    1    2    3    (empty positions)
    """
    result = []
    upper_name = name.upper() if name else ""

    for i in range(max_chars):
        if i >= len(upper_name):
            # Beyond string length
            result.append(-1.0)
            continue

        ch = upper_name[i]

        if "A" <= ch <= "Z":
            # A=0, Z=25, normalize to 0.0-0.72 (26 letters / 36 total alphanumeric)
            ord_val = ord(ch) - ord("A")
            normalized = ord_val / 35.0  # 36 alphanumeric chars (26 letters + 10 digits)
            result.append(normalized)
        elif "0" <= ch <= "9":
            # 0=26, 9=35, normalize to 0.72-1.0
            ord_val = ord(ch) - ord("0") + 26  # Offset by 26 letters
            normalized = ord_val / 35.0
            result.append(normalized)
        else:
            # Non-alphanumeric (dash, colon, pipe, etc.)
            result.append(-1.0)

    return result


def calculate_name_pattern_category(name: str) -> int:
    """Classify system name into pattern categories.

    Returns:
        0: DASH pattern (e.g., "ABC-123", 7 chars with dash at position 3)
        1: COLON pattern (e.g., "AB:123", 6 chars with colon)
        2: DOTSEQ pattern (e.g., "1.2.3", exactly 2 dots)
        3: PIPE pattern (e.g., "ABC|123", 7 chars with pipe at position 3)
        4: OTHER/unknown pattern
    """
    if not name:
        return 4
    up = name.upper()
    if len(up) == 7 and up[3] == "-":
        return 0  # DASH
    if ":" in up and len(up) == 6:
        return 1  # COLON
    if up.count(".") == 2:
        return 2  # DOTSEQ
    if len(up) == 7 and up[3] == "|" and up.count("|") == 1:
        return 3  # PIPE
    return 4  # OTHER


def calculate_name_char_bucket(name: str) -> int:
    """Map first character to one of 9 alphabetic buckets.

    Divides A-Z into 9 groups of ~3 characters each, plus digits.
    Returns -1 for empty/invalid names (fallback to neutral gray).

    Returns:
        -1: Empty/invalid (neutral gray fallback)
         0: A-C
         1: D-F
         2: G-I
         3: J-L
         4: M-O
         5: P-R
         6: S-U
         7: V-X
         8: Y-Z and 0-9
    """
    if not name:
        return -1
    ch = name.upper()[0]

    # A-C (ord 65-67)
    if "A" <= ch <= "C":
        return 0
    # D-F (ord 68-70)
    if "D" <= ch <= "F":
        return 1
    # G-I (ord 71-73)
    if "G" <= ch <= "I":
        return 2
    # J-L (ord 74-76)
    if "J" <= ch <= "L":
        return 3
    # M-O (ord 77-79)
    if "M" <= ch <= "O":
        return 4
    # P-R (ord 80-82)
    if "P" <= ch <= "R":
        return 5
    # S-U (ord 83-85)
    if "S" <= ch <= "U":
        return 6
    # V-X (ord 86-88)
    if "V" <= ch <= "X":
        return 7
    # Y-Z (ord 89-90) and digits 0-9
    if "Y" <= ch <= "Z" or "0" <= ch <= "9":
        return 8
    # Fallback for special characters
    return -1


def calculate_child_metrics(planets: list) -> tuple[int, int]:
    """Calculate planet and moon counts from system data.

    Args:
        planets: List of Planet dataclass instances with .moons attribute

    Returns:
        Tuple of (planet_count, moon_count)
    """
    planet_count = len(planets)
    moon_count = sum(len(p.moons) for p in planets)
    return planet_count, moon_count


# Blackhole detection (future: could be a property too)
_BLACKHOLE_NAMES = frozenset(["J055520", "J110909", "J164710", "J174618", "J175552"])


def is_blackhole_system(name: str) -> bool:
    """Check if system name is a known blackhole system.

    Args:
        name: System name to check

    Returns:
        True if name matches a known blackhole system
    """
    return name in _BLACKHOLE_NAMES
