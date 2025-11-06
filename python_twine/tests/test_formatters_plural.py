"""
Tests for formatter classes.
"""

from pathlib import Path

import pytest

from twine.formatters.apple_plural import ApplePluralFormatter
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

    @pytest.fixture
    def twine_file(self):
        # Prepare TwineFile data
        twine_file = TwineFile()
        num_edits_def = TwineDefinition("num_edits")

        twine_file.definitions_by_key["num_edits"] = num_edits_def
        twine_file.language_codes = ["en", "de"]
        twine_file.sections = [TwineSection("OSM")]
        twine_file.sections[0].definitions.append(num_edits_def)

        # Put plural translation
        num_edits_def.plural_translations["en"] = {
            "one": "%d edit",
            "other": "%d edits"
        }
        num_edits_def.translations["en"] = "%d edits"

        num_edits_def.plural_translations["de"] = {
            "zero": "%d Bearbeitungen",
            "one": "%d Bearbeitung",
            "other": "%d Bearbeitungen"
        }
        num_edits_def.translations["de"] = "%d Bearbeitungen"

        return twine_file

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

    def test_write_format(self, formatter, twine_file):
        formatter.twine_file = twine_file

        en_plural_content = formatter.format_file("en")
        assert en_plural_content == """<?xml version="1.0" encoding="utf-8"?>
<resources>

    <!-- SECTION: OSM -->
    <plurals name="num_edits">
        <item quantity="one">%d edit</item>
        <item quantity="other">%d edits</item>
    </plurals>
</resources>
"""

        de_plural_content = formatter.format_file("de")
        assert de_plural_content == """<?xml version="1.0" encoding="utf-8"?>
<resources>

    <!-- SECTION: OSM -->
    <plurals name="num_edits">
        <item quantity="zero">%d Bearbeitungen</item>
        <item quantity="one">%d Bearbeitung</item>
        <item quantity="other">%d Bearbeitungen</item>
    </plurals>
</resources>
"""


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

[num_edits]
en:one = %d edit
en:other = %d edits
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


class TestApplePluralFormatter:
    @pytest.fixture
    def formatter(self) -> ApplePluralFormatter:
        """Create formatter with empty TwineFile."""
        formatter = ApplePluralFormatter()
        formatter.options = {"consume_all": True, "consume_comments": True}
        return formatter

    @pytest.fixture
    def fixtures_dir(self) -> Path:
        """Get fixtures directory path."""
        return Path(__file__).parent / "fixtures"

    @pytest.fixture
    def twine_file(self) -> TwineFile:
        # Prepare TwineFile data
        twine_file = TwineFile()
        num_edits_def = TwineDefinition("num_edits")

        twine_file.definitions_by_key["num_edits"] = num_edits_def
        twine_file.language_codes = ["en", "de"]
        twine_file.sections = [TwineSection("OSM")]
        twine_file.sections[0].definitions.append(num_edits_def)

        # Put plural translation
        num_edits_def.plural_translations["en"] = {
            "one": "%d edit",
            "other": "%d edits"
        }
        num_edits_def.translations["en"] = "%d edits"

        num_edits_def.plural_translations["de"] = {
            "zero": "%d Bearbeitungen",
            "one": "%d Bearbeitung",
            "other": "%d Bearbeitungen"
        }
        num_edits_def.translations["de"] = "%d Bearbeitungen"

        return twine_file

    def test_read_stringsdict(self, formatter:ApplePluralFormatter, fixtures_dir):
        """Test reading Android XML format with <plural/> tags."""
        fixture_path = fixtures_dir / "formatter_apple_plurals.stringsdict"
        with open(fixture_path, "r", encoding="utf-8") as f:
            formatter.read(f, "en")

        twine_file = formatter.twine_file

        assert "bookmarks_places" in twine_file.definitions_by_key
        translations1 = twine_file.definitions_by_key["bookmarks_places"].plural_translations
        assert translations1 == {"en": {"one": "%d bookmark", "other": "%d bookmarks"}}

        assert "tracks" in twine_file.definitions_by_key
        translations2 = twine_file.definitions_by_key["tracks"].plural_translations
        assert translations2 == {"en": {"one": "%d track", "other": "%d tracks"}}


    def test_write_plural_format(self, formatter, twine_file):
        formatter.twine_file = twine_file

        en_plural_content = formatter.format_file("en")
        assert en_plural_content == """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>

<!-- ********** OSM **********/ -->

\t<key>num_edits</key>
\t<dict>
\t\t<key>NSStringLocalizedFormatKey</key>
\t\t<string>%#@value@</string>
\t\t<key>value</key>
\t\t<dict>
\t\t\t<key>NSStringFormatSpecTypeKey</key>
\t\t\t<string>NSStringPluralRuleType</string>
\t\t\t<key>NSStringFormatValueTypeKey</key>
\t\t\t<string>d</string>
\t\t\t<key>one</key>
\t\t\t<string>%d edit</string>
\t\t\t<key>other</key>
\t\t\t<string>%d edits</string>
\t\t</dict>
\t</dict>

</dict>
</plist>"""

        de_plural_content = formatter.format_file("de")
        assert de_plural_content == """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>

<!-- ********** OSM **********/ -->

\t<key>num_edits</key>
\t<dict>
\t\t<key>NSStringLocalizedFormatKey</key>
\t\t<string>%#@value@</string>
\t\t<key>value</key>
\t\t<dict>
\t\t\t<key>NSStringFormatSpecTypeKey</key>
\t\t\t<string>NSStringPluralRuleType</string>
\t\t\t<key>NSStringFormatValueTypeKey</key>
\t\t\t<string>d</string>
\t\t\t<key>zero</key>
\t\t\t<string>%d Bearbeitungen</string>
\t\t\t<key>one</key>
\t\t\t<string>%d Bearbeitung</string>
\t\t\t<key>other</key>
\t\t\t<string>%d Bearbeitungen</string>
\t\t</dict>
\t</dict>

</dict>
</plist>"""
