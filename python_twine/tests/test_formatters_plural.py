"""
Tests for formatter classes.
"""

from pathlib import Path

import pytest

from twine.twine_file import TwineFile, TwineDefinition, TwineSection


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
