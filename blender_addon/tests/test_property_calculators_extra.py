"""Extra focused tests for property_calculators to improve coverage.

These tests exercise unicode and edge cases for is_proper_noun and a couple
additional paths in calculate_char_indices and calculate_name_char_bucket.
"""

from __future__ import annotations

from addon.operators.property_calculators import (
    calculate_char_indices,
    calculate_name_char_bucket,
    is_proper_noun,
)


def test_is_proper_noun_basic_true():
    assert is_proper_noun("Nod") is True


def test_is_proper_noun_with_space():
    assert is_proper_noun("New Eden") is True


def test_is_proper_noun_unicode_latin():
    # Latin-1 supplement capital Å (U+00C5) should be treated as a letter
    assert is_proper_noun("Åland") is True


def test_is_proper_noun_unicode_cyrillic():
    # Cyrillic uppercase first letter + lowercase letters should pass
    assert is_proper_noun("Мир") is True


def test_is_proper_noun_false_cases():
    # starts with lowercase
    assert is_proper_noun("nod") is False
    # contains digit
    assert is_proper_noun("Nod1") is False
    # contains punctuation/hyphen
    assert is_proper_noun("Nod-Name") is False
    # empty
    assert is_proper_noun("") is False


def test_calculate_char_indices_zero_digit_mapping():
    # '0' should map to 26/35 per implementation
    result = calculate_char_indices("0", max_chars=1)
    assert result[0] == 26.0 / 35.0


def test_calculate_char_indices_extended_letter_returns_minus_one():
    # Extended unicode letter like 'Å' is not in A-Z range in this impl
    # and therefore should be treated as non-alphanumeric (-1.0)
    result = calculate_char_indices("Å", max_chars=1)
    assert result[0] == -1.0


def test_name_char_bucket_accented_returns_fallback():
    # Accented first character outside ASCII A-Z should fall back to -1
    assert calculate_name_char_bucket("Éclair") == -1
