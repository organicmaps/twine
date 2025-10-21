"""
Tests for formatter classes.
"""

import io
from pathlib import Path

import pytest

from twine.twine_file import TwineFile, TwineSection, TwineDefinition
from twine.formatters.android import AndroidFormatter
from twine.formatters.apple import AppleFormatter
from twine.formatters.gettext import GettextFormatter
from twine.formatters.jquery import JQueryFormatter


class TestAndroidFormatter:
    """Test Android XML formatter."""

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
        """Test reading Android XML format."""
        fixture_path = fixtures_dir / "formatter_android.xml"
        with open(fixture_path, "r", encoding="utf-8") as f:
            formatter.read(f, "en")

        # Check translations were read
        for i in range(1, 5):
            key = f"key{i}"
            assert key in formatter.twine_file.definitions_by_key
            assert (
                formatter.twine_file.definitions_by_key[key].translations["en"]
                == f"value{i}-english"
            )

        # Check comments
        assert formatter.twine_file.definitions_by_key["key1"].comment == "comment key1"
        assert formatter.twine_file.definitions_by_key["key4"].comment == "comment key4"

    def test_read_multiline_translation(self, formatter):
        """Test reading multiline translations."""
        content = """<?xml version="1.0" encoding="utf-8"?>
<resources>
  <string name="foo">This is
 a string</string>
</resources>"""

        formatter.read(io.StringIO(content), "en")

        # Twine stores newlines as escaped \n
        assert (
            formatter.twine_file.definitions_by_key["foo"].translations["en"]
            == "This is\\n a string"
        )

    def test_read_multiline_comment(self, formatter):
        """Test reading multiline comments."""
        content = """<?xml version="1.0" encoding="utf-8"?>
<resources>
  <!-- multiline
  comment -->
  <string name="foo">This is a string</string>
</resources>"""

        formatter.read(io.StringIO(content), "en")

        assert (
            formatter.twine_file.definitions_by_key["foo"].comment
            == "multiline comment"
        )

    def test_read_html_tags(self, formatter):
        """Test reading HTML tags in strings."""
        content = """<?xml version="1.0" encoding="utf-8"?>
<resources>
  <string name="foo">Hello, <b>BOLD</b></string>
</resources>"""

        formatter.read(io.StringIO(content), "en")

        assert (
            formatter.twine_file.definitions_by_key["foo"].translations["en"]
            == "Hello, <b>BOLD</b>"
        )

    def test_double_quotes_not_modified(self, formatter):
        """Test that double quotes in hrefs are preserved."""
        content = """<?xml version="1.0" encoding="utf-8"?>
<resources>
  <string name="foo">Hello, <a href="http://www.foo.com">BOLD</a></string>
</resources>"""

        formatter.read(io.StringIO(content), "en")

        assert (
            formatter.twine_file.definitions_by_key["foo"].translations["en"]
            == 'Hello, <a href="http://www.foo.com">BOLD</a>'
        )

    def test_escape_ampersand(self, formatter):
        """Test ampersand escaping."""
        formatter.set_translation_for_key("key1", "en", "this &amp; that", "Section A")
        assert (
            formatter.twine_file.definitions_by_key["key1"].translations["en"]
            == "this & that"
        )

    def test_escape_less_than(self, formatter):
        """Test less-than escaping."""
        formatter.set_translation_for_key("key1", "en", "this &lt; that", "Section B")
        assert (
            formatter.twine_file.definitions_by_key["key1"].translations["en"]
            == "this < that"
        )

    def test_escape_apostrophe(self, formatter):
        """Test apostrophe escaping."""
        formatter.set_translation_for_key("key1", "en", "it\\'s complicated", "Section C")
        assert (
            formatter.twine_file.definitions_by_key["key1"].translations["en"]
            == "it's complicated"
        )

    def test_placeholder_conversion(self, formatter):
        """Test placeholder conversion from %s to %@."""
        formatter.set_translation_for_key("key1", "en", "value %s", "Section D")
        assert (
            formatter.twine_file.definitions_by_key["key1"].translations["en"]
            == "value %@"
        )

    def test_writer_escape_ampersand(self, formatter):
        """Test ampersand escaping."""
        assert formatter.escape_value("&") == "&amp;"

        value_with_link = '<a href="omaps.app/?lang=en&theme=dark">Home</a>'
        assert formatter.escape_value(value_with_link) == value_with_link

        assert (formatter.escape_value('<a href="omaps.app/?lang=en&theme=dark">Left & Right</a>')
                == '<a href="omaps.app/?lang=en&theme=dark">Left &amp; Right</a>')

        value_with_cdata = "<![CDATA[<html>bla & bla</html>]]>"
        assert formatter.escape_value(value_with_cdata) == value_with_cdata

        assert (formatter.escape_value("<![CDATA[<html>bla & bla</html>]]> & test")
                == "<![CDATA[<html>bla & bla</html>]]> &amp; test")

    def test_writer_escape_quote(self, formatter):
        """Test ampersand escaping."""
        assert formatter.escape_value('"') == '\\"'

        assert (formatter.escape_value('<a href=\"omaps.app/?lang=en&theme=dark\">"Home"</a>')
                == '<a href="omaps.app/?lang=en&theme=dark">\\"Home\\"</a>')

        value_with_cdata = '<![CDATA["Back Home"]]>'
        assert formatter.escape_value(value_with_cdata) == value_with_cdata

        assert (formatter.escape_value('<![CDATA["Back Home"]]> & "Support"')
                == '<![CDATA["Back Home"]]> &amp; \\"Support\\"')

    def test_writer_escape_apostrophe(self, formatter):
        """Test ampersand escaping."""
        assert formatter.escape_value('"') == '\\"'

        assert (formatter.escape_value('<a href=\"omaps.app/?lang=en&theme=dark\">"Home"</a>')
                == '<a href="omaps.app/?lang=en&theme=dark">\\"Home\\"</a>')

        value_with_cdata = '<![CDATA["Back Home"]]>'
        assert formatter.escape_value(value_with_cdata) == value_with_cdata

        assert (formatter.escape_value('<![CDATA["Back Home"]]> & "Support"')
                == '<![CDATA["Back Home"]]> &amp; \\"Support\\"')

    def test_writer_escape_angle_bracket(self, formatter):
        """Test '<' escaping."""
        assert formatter.escape_value('<') == '&lt;'

        assert formatter.escape_value('<<< Turn Left') == '&lt;&lt;&lt; Turn Left'

        assert formatter.escape_value('Turn Right >>>') == 'Turn Right >>>'

        assert formatter.escape_value('<b>Home</b>') == '<b>Home</b>'
        assert formatter.escape_value('e<super>x</super>') == 'e<super>x</super>'
        assert formatter.escape_value('<script>alert("!")</script>') == '&lt;script>alert(\\"!\\")&lt;/script>'

        value_with_cdata = '<![CDATA[Hello <1> world]]>'
        assert formatter.escape_value(value_with_cdata) == value_with_cdata

        assert formatter.escape_value('<![C DATA[ <![CDATA[') == '&lt;![C DATA[ <![CDATA['

    def test_writer_escape_newline(self, formatter):
        """Test '\\n' escaping."""
        assert formatter.escape_value('\\n') == '\n\\n'
        assert formatter.escape_value('Downloading %@. You can now\\nproceed to the map.') == 'Downloading %\\@. You can now\n\\nproceed to the map.'

        cdata = '<![CDATA[ New\\nline\n ]]>'
        assert formatter.escape_value(cdata) == cdata

class TestAppleFormatter:
    """Test Apple .strings formatter."""

    @pytest.fixture
    def formatter(self):
        """Create formatter with empty TwineFile."""
        twine_file = TwineFile()
        formatter = AppleFormatter()
        formatter.twine_file = twine_file
        formatter.options = {"consume_all": True, "consume_comments": True}
        return formatter

    @pytest.fixture
    def fixtures_dir(self):
        """Get fixtures directory path."""
        return Path(__file__).parent / "fixtures"

    def test_read_format(self, formatter, fixtures_dir):
        """Test reading Apple .strings format."""
        fixture_path = fixtures_dir / "formatter_apple.strings"
        with open(fixture_path, "r", encoding="utf-8") as f:
            formatter.read(f, "en")

        # Check translations were read
        for i in range(1, 5):
            key = f"key{i}"
            assert key in formatter.twine_file.definitions_by_key
            assert (
                formatter.twine_file.definitions_by_key[key].translations["en"]
                == f"value{i}-english"
            )

        # Check comments
        assert formatter.twine_file.definitions_by_key["key1"].comment == "comment key1"
        assert formatter.twine_file.definitions_by_key["key4"].comment == "comment key4"

    def test_format_file(self, formatter):
        """Test generating Apple .strings output."""
        # Add some definitions
        formatter.twine_file.language_codes = ["en"]
        section = TwineSection("Test")

        def1 = TwineDefinition("greeting")
        def1.translations["en"] = "Hello World"
        def1.comment = "A greeting"
        section.definitions.append(def1)

        formatter.twine_file.sections.append(section)
        formatter.twine_file.definitions_by_key = {"greeting": def1}

        output = formatter.format_file("en")

        assert "/* A greeting */" in output
        assert '"greeting" = "Hello World";' in output


class TestGettextFormatter:
    """Test Gettext .po formatter."""

    @pytest.fixture
    def formatter(self):
        """Create formatter with empty TwineFile."""
        twine_file = TwineFile()
        formatter = GettextFormatter()
        formatter.twine_file = twine_file
        formatter.options = {"consume_all": True, "consume_comments": True}
        return formatter

    @pytest.fixture
    def fixtures_dir(self):
        """Get fixtures directory path."""
        return Path(__file__).parent / "fixtures"

    def test_read_format(self, formatter, fixtures_dir):
        """Test reading Gettext .po format."""
        fixture_path = fixtures_dir / "formatter_gettext.po"
        with open(fixture_path, "r", encoding="utf-8") as f:
            formatter.read(f, "en")

        # Check translations were read
        for i in range(1, 5):
            key = f"key{i}"
            assert key in formatter.twine_file.definitions_by_key
            assert (
                formatter.twine_file.definitions_by_key[key].translations["en"]
                == f"value{i}-english"
            )

    def test_read_multiline_po(self, formatter, fixtures_dir):
        """Test reading multiline Gettext format."""
        fixture_path = fixtures_dir / "gettext_multiline.po"
        with open(fixture_path, "r", encoding="utf-8") as f:
            formatter.read(f, "en")

        # Should have read multiline string correctly
        assert len(formatter.twine_file.definitions_by_key) > 0


class TestJQueryFormatter:
    """Test jQuery JSON formatter."""

    @pytest.fixture
    def formatter(self):
        """Create formatter with empty TwineFile."""
        twine_file = TwineFile()
        formatter = JQueryFormatter()
        formatter.twine_file = twine_file
        formatter.options = {"consume_all": True}
        return formatter

    @pytest.fixture
    def fixtures_dir(self):
        """Get fixtures directory path."""
        return Path(__file__).parent / "fixtures"

    def test_read_format(self, formatter, fixtures_dir):
        """Test reading jQuery JSON format."""
        fixture_path = fixtures_dir / "formatter_jquery.json"
        with open(fixture_path, "r", encoding="utf-8") as f:
            formatter.read(f, "en")

        # Check translations were read
        for i in range(1, 5):
            key = f"key{i}"
            assert key in formatter.twine_file.definitions_by_key
            assert (
                formatter.twine_file.definitions_by_key[key].translations["en"]
                == f"value{i}-english"
            )

    def test_read_nested_format(self, formatter, fixtures_dir):
        """Test reading nested jQuery JSON format."""
        fixture_path = fixtures_dir / "formatter_jquery_nested.json"
        with open(fixture_path, "r", encoding="utf-8") as f:
            formatter.read(f, "en")

        # Check nested keys
        assert "key5.key5a" in formatter.twine_file.definitions_by_key
        assert (
            formatter.twine_file.definitions_by_key["key5.key5a"].translations["en"]
            == "value5a-english"
        )

    def test_format_file(self, formatter):
        """Test generating jQuery JSON output."""
        formatter.twine_file.language_codes = ["en"]
        section = TwineSection("Test")

        def1 = TwineDefinition("greeting")
        def1.translations["en"] = "Hello World"
        section.definitions.append(def1)

        formatter.twine_file.sections.append(section)
        formatter.twine_file.definitions_by_key = {"greeting": def1}

        output = formatter.format_file("en")

        assert '"greeting":"Hello World"' in output
