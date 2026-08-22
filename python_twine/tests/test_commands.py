"""
Tests for command functionality.
"""

import tempfile
from pathlib import Path

import pytest

from twine import TwineError
from twine.runner import Runner
from twine.twine_file import TwineDefinition, TwineFile, TwineSection


class TestValidateTwineFile:
    """Test validate-twine-file command."""

    @pytest.fixture
    def twine_file(self):
        """Create a valid TwineFile."""
        twine_file = TwineFile()
        twine_file.language_codes = ["en"]

        section1 = TwineSection("Section 1")

        def1 = TwineDefinition("key1")
        def1.translations["en"] = "value1"
        def1.tags = ["tag1"]
        section1.definitions.append(def1)

        def2 = TwineDefinition("key2")
        def2.translations["en"] = "value2"
        def2.tags = ["tag1"]
        section1.definitions.append(def2)

        section2 = TwineSection("Section 2")

        def3 = TwineDefinition("key3")
        def3.translations["en"] = "value3"
        def3.tags = ["tag1", "tag2"]
        section2.definitions.append(def3)

        def4 = TwineDefinition("key4")
        def4.translations["en"] = "value4"
        def4.tags = ["tag2"]
        section2.definitions.append(def4)

        twine_file.sections.extend([section1, section2])
        twine_file.definitions_by_key = {
            "key1": def1,
            "key2": def2,
            "key3": def3,
            "key4": def4,
        }

        return twine_file

    def test_recognizes_valid_file(self, twine_file):
        """Test that valid file passes validation."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            twine_path = f.name

        try:
            options = {"twine_file": twine_path}
            runner = Runner(options, twine_file)

            # Should not raise an error
            runner.validate_twine_file()
        finally:
            Path(twine_path).unlink(missing_ok=True)

    def test_reports_duplicate_keys(self, twine_file):
        """Test that duplicate keys are detected."""
        # Add a duplicate definition
        twine_file.sections[0].definitions.append(twine_file.sections[0].definitions[0])

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            twine_path = f.name

        try:
            options = {"twine_file": twine_path}
            runner = Runner(options, twine_file)

            with pytest.raises(TwineError):
                runner.validate_twine_file()
        finally:
            Path(twine_path).unlink(missing_ok=True)

    def test_reports_invalid_characters_in_keys(self):
        """Test that invalid characters in keys are detected."""
        twine_file = TwineFile()
        twine_file.language_codes = ["en"]

        section = TwineSection("Section")

        # Create definition with invalid character in key
        def1 = TwineDefinition("key!")  # '!' is invalid
        def1.translations["en"] = "value"
        section.definitions.append(def1)

        twine_file.sections.append(section)
        twine_file.definitions_by_key = {"key!": def1}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            twine_path = f.name

        try:
            options = {"twine_file": twine_path}
            runner = Runner(options, twine_file)

            with pytest.raises(TwineError):
                runner.validate_twine_file()
        finally:
            Path(twine_path).unlink(missing_ok=True)

    def test_reports_missing_tags_in_pedantic_mode(self, twine_file):
        """Test that missing tags are detected in pedantic mode."""
        # Remove tags from one definition
        twine_file.definitions_by_key["key1"].tags = []

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            twine_path = f.name

        try:
            options = {"twine_file": twine_path, "pedantic": True}
            runner = Runner(options, twine_file)

            with pytest.raises(TwineError):
                runner.validate_twine_file()
        finally:
            Path(twine_path).unlink(missing_ok=True)

    def test_allows_missing_tags_by_default(self, twine_file):
        """Test that missing tags are allowed by default."""
        # Remove tags from one definition
        twine_file.definitions_by_key["key1"].tags = []

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            twine_path = f.name

        try:
            options = {"twine_file": twine_path}
            runner = Runner(options, twine_file)

            # Should not raise an error
            runner.validate_twine_file()
        finally:
            Path(twine_path).unlink(missing_ok=True)


class TestGenerateLocalizationFile:
    """Test generate-localization-file command."""

    @pytest.fixture
    def twine_file(self):
        """Create a TwineFile with translations."""
        twine_file = TwineFile()
        twine_file.language_codes = ["en", "fr", "es"]

        section = TwineSection("Test")

        def1 = TwineDefinition("greeting")
        def1.translations["en"] = "Hello"
        def1.translations["fr"] = "Bonjour"
        def1.translations["es"] = "Hola"
        section.definitions.append(def1)

        twine_file.sections.append(section)
        twine_file.definitions_by_key = {"greeting": def1}

        return twine_file

    def test_generates_android_format(self, twine_file):
        """Test generating Android XML file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "strings.xml"

            options = {
                "twine_file": "input.txt",
                "output_path": str(output_path),
                "languages": ["en"],
                "format": "android",
            }

            runner = Runner(options, twine_file)
            runner.generate_localization_file()

            # Check file was created
            assert output_path.exists()

            # Check content
            content = output_path.read_text()
            assert "<?xml version=" in content
            assert '<string name="greeting">Hello</string>' in content

    def test_generates_apple_format(self, twine_file):
        """Test generating Apple .strings file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "Localizable.strings"

            options = {
                "twine_file": "input.txt",
                "output_path": str(output_path),
                "languages": ["fr"],
                "format": "apple",
            }

            runner = Runner(options, twine_file)
            runner.generate_localization_file()

            # Check file was created
            assert output_path.exists()

            # Check content
            content = output_path.read_text()
            assert '"greeting" = "Bonjour";' in content

    def test_deducts_format_from_extension(self, twine_file):
        """Test that format is deduced from file extension."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "strings.xml"

            options = {
                "twine_file": "input.txt",
                "output_path": str(output_path),
                "languages": ["en"],
                # No format specified
            }

            runner = Runner(options, twine_file)
            runner.generate_localization_file()

            # Check Android file was created
            assert output_path.exists()
            content = output_path.read_text()
            assert "<?xml version=" in content
