"""
Tests for placeholder conversion utilities.
"""

import pytest
from twine.placeholders import (
    number_of_twine_placeholders,
    convert_twine_string_placeholder,
    convert_placeholders_from_twine_to_android,
    convert_placeholders_from_android_to_twine,
    convert_placeholders_from_twine_to_flash,
    convert_placeholders_from_flash_to_twine,
    contains_python_specific_placeholder,
)
from twine import TwineError


class TestPlaceholders:
    """Test placeholder conversion functions."""

    def test_number_of_twine_placeholders(self):
        """Test counting placeholders."""
        assert number_of_twine_placeholders("Hello world") == 0
        assert number_of_twine_placeholders("Hello %@") == 1
        assert number_of_twine_placeholders("Hello %@ and %@") == 2
        assert number_of_twine_placeholders("Number: %d") == 1
        assert number_of_twine_placeholders("Float: %f, Int: %d") == 2

    def test_convert_twine_string_placeholder(self):
        """Test converting %@ to %s."""
        assert convert_twine_string_placeholder("Hello %@") == "Hello %s"
        assert convert_twine_string_placeholder("Hello %@ and %@") == "Hello %s and %s"
        assert convert_twine_string_placeholder("Number: %d") == "Number: %d"
        assert (
            convert_twine_string_placeholder("Mixed: %@ and %d") == "Mixed: %s and %d"
        )

    def test_convert_placeholders_from_twine_to_android_simple(self):
        """Test Android conversion with simple placeholders."""
        assert convert_placeholders_from_twine_to_android("Hello") == "Hello"
        assert convert_placeholders_from_twine_to_android("Hello %@") == "Hello %s"

    def test_convert_placeholders_from_twine_to_android_multiple(self):
        """Test Android conversion with multiple placeholders."""
        result = convert_placeholders_from_twine_to_android("Hello %@ and %@")
        assert result == "Hello %1$s and %2$s"

        result = convert_placeholders_from_twine_to_android("%@ has %d items")
        assert result == "%1$s has %2$d items"

    def test_convert_placeholders_from_twine_to_android_percent_escaping(self):
        """Test Android conversion escapes single percent signs."""
        result = convert_placeholders_from_twine_to_android("50% off: %@")
        assert result == "50%% off: %s"

    def test_convert_placeholders_from_android_to_twine(self):
        """Test converting Android placeholders to Twine."""
        assert convert_placeholders_from_android_to_twine("Hello %s") == "Hello %@"
        assert convert_placeholders_from_android_to_twine("Hello %1$s") == "Hello %1$@"
        assert convert_placeholders_from_android_to_twine("%s and %s") == "%@ and %@"

    def test_convert_placeholders_from_twine_to_flash(self):
        """Test Flash placeholder conversion."""
        assert convert_placeholders_from_twine_to_flash("Hello") == "Hello"
        assert convert_placeholders_from_twine_to_flash("Hello %@") == "Hello {0}"
        assert convert_placeholders_from_twine_to_flash("%@ and %@") == "{0} and {1}"

    def test_convert_placeholders_from_flash_to_twine(self):
        """Test converting Flash placeholders to Twine."""
        assert convert_placeholders_from_flash_to_twine("Hello {0}") == "Hello %@"
        assert convert_placeholders_from_flash_to_twine("{0} and {1}") == "%@ and %@"
        assert (
            convert_placeholders_from_flash_to_twine("Hello {0}, {1}, {2}")
            == "Hello %@, %@, %@"
        )

    def test_contains_python_specific_placeholder(self):
        """Test Python-specific placeholder detection."""
        assert not contains_python_specific_placeholder("Hello %@")
        assert not contains_python_specific_placeholder("Hello %s")
        assert contains_python_specific_placeholder("Hello %(name)s")
        assert contains_python_specific_placeholder("%(count)d items")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
