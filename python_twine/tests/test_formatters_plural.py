"""
Tests for formatter classes.
"""

from pathlib import Path

import pytest

from twine.twine_file import TwineFile, TwineDefinition, TwineSection
from twine.formatters.android import AndroidFormatter

class TestAndroidPluralFormatter:
    """Test Android XML formatter with <plural/> tags."""

    @pytest.fixture
    def formatter(self):
        """Create formatter with empty TwineFile."""
        twine_file = TwineFile()
        formatter = AndroidFormatter()
        formatter.twine_file = twine_file
        formatter.options = {"consume_all": True, "consume_comments": True}
        return formatter

    @pytest.fixture
    def fixtures_dir(self):
        """Get fixtures directory path."""
        return Path(__file__).parent / "fixtures"

    def test_read_format(self, formatter, fixtures_dir):
        """Test reading Android XML format with <plural/> tags."""
        fixture_path = fixtures_dir / "formatter_android_plurals.xml"
        with open(fixture_path, "r", encoding="utf-8") as f:
            formatter.read(f, "en")

        twine_file = formatter.twine_file

        assert "bookmarks_places" in twine_file.definitions_by_key
        translations1 = twine_file.definitions_by_key["bookmarks_places"].plural_translations
        assert translations1 == {"en": {"one": "%d bookmark", "other": "%d bookmarks"}}

        assert "tracks" in twine_file.definitions_by_key
        translations2 = twine_file.definitions_by_key["tracks"].plural_translations
        assert translations2 == {"en": {"one": "%d track", "other": "%d tracks"}}


class TestTwineFilePlural:
    @pytest.fixture
    def fixtures_dir(self):
        """Get fixtures directory path."""
        return Path(__file__).parent / "fixtures"

    def test_write_plural_format(self):
        import tempfile

        twine_file = TwineFile()
        num_edits_def = TwineDefinition("num_edits")

        twine_file.definitions_by_key["num_edits"] = num_edits_def
        twine_file.language_codes.append("en")
        twine_file.sections = [TwineSection("OSM")]
        twine_file.sections[0].definitions.append(num_edits_def)

        # Put plural translations
        num_edits_def.plural_translations["en"] = {
            "one": "%d edit",
            "other": "%d edits"
        }

        # Export
        with tempfile.TemporaryDirectory() as tmpdirname:
            tmp_twine_path = tmpdirname + "/plural.txt"
            twine_file.write(tmp_twine_path)
            with open(tmp_twine_path, "rt") as fout:
                twine_content = fout.read()

            assert twine_content == """[[OSM]]
\t[num_edits]
\t\ten:one = %d edit
\t\ten:other = %d edits
"""

    def test_read_plurals(self, fixtures_dir):
        twine_file = TwineFile()
        twine_file.read(str(fixtures_dir / "twine_plural_values.txt"))

        assert twine_file.language_codes == ["en", "ru"]

        assert "bookmarks_places" in twine_file.definitions_by_key
        definition = twine_file.definitions_by_key["bookmarks_places"]

        assert "en" in definition.translations
        assert definition.translations["en"] == "%d bookmarks"  # "en:other" value is copied to translations
        assert "en" in definition.plural_translations
        assert definition.plural_translations["en"] == {
            "one": "%d bookmark",
            "other": "%d bookmarks"
        }

        assert "ru" in definition.translations
        assert definition.translations["ru"] == "%d меток"  # "ru:other" value is copied to translations
        assert "ru" in definition.plural_translations
        assert definition.plural_translations["ru"] == {
            "one": "%d метка",
            "few": "%d метки",
            "many": "%d меток",
            "other": "%d меток"
        }
