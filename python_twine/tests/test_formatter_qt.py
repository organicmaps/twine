"""
Tests for the Qt ID-based TS formatter (non-plural messages).
"""

import io

import pytest

from twine import TwineError
from twine.formatters.qt import QtFormatter
from twine.twine_file import TwineDefinition, TwineFile, TwineSection


@pytest.fixture
def formatter():
    twine_file = TwineFile()
    formatter = QtFormatter()
    formatter.twine_file = twine_file
    formatter.options = {"consume_all": True, "consume_comments": True}
    return formatter


def _make_simple_twine_file() -> TwineFile:
    twine_file = TwineFile()
    twine_file.language_codes = ["en", "ru"]
    section = TwineSection("General")
    twine_file.sections.append(section)

    back = TwineDefinition("back")
    back.translations["en"] = "Back"
    back.translations["ru"] = "Назад"
    twine_file.definitions_by_key["back"] = back
    section.definitions.append(back)

    return twine_file


class TestQtFormatterBasics:
    def test_format_name(self, formatter):
        assert formatter.format_name() == "qt"
        assert formatter.extension() == ".ts"
        assert formatter.default_file_name() == "omim.ts"

    def test_output_path_for_language(self, formatter):
        assert formatter.output_path_for_language("ru") == "ru"
        assert formatter.output_path_for_language("zh-Hans") == "zh-Hans"


class TestQtFormatterWrite:
    def test_simple_strings(self, formatter):
        formatter.twine_file = _make_simple_twine_file()

        en_output = formatter.format_file("en")
        assert en_output == (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<TS version="2.1" language="en">\n'
            '<context>\n<name></name>\n'
            '<message id="back">\n'
            '<source>Back</source>\n'
            '<translation>Back</translation>\n'
            '</message>\n'
            '</context>\n'
            '</TS>\n'
        )

        ru_output = formatter.format_file("ru")
        assert ru_output == (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<TS version="2.1" language="ru">\n'
            '<context>\n<name></name>\n'
            '<message id="back">\n'
            '<source>Back</source>\n'
            '<translation>Назад</translation>\n'
            '</message>\n'
            '</context>\n'
            '</TS>\n'
        )

    def test_placeholder_conversion_sequential(self, formatter):
        twine_file = TwineFile()
        twine_file.language_codes = ["en"]
        section = TwineSection("Routing")
        twine_file.sections.append(section)

        download = TwineDefinition("download_country_failed")
        download.translations["en"] = "%@ download has failed"
        twine_file.definitions_by_key["download_country_failed"] = download
        section.definitions.append(download)

        share = TwineDefinition("my_position_share_sms")
        share.translations["en"] = "Check %@ or %@ for more"
        twine_file.definitions_by_key["my_position_share_sms"] = share
        section.definitions.append(share)

        formatter.twine_file = twine_file
        output = formatter.format_file("en")

        assert "<translation>%1 download has failed</translation>" in output
        assert "<translation>Check %1 or %2 for more</translation>" in output

    def test_placeholder_conversion_numbered_preserved(self, formatter):
        twine_file = TwineFile()
        twine_file.language_codes = ["en"]
        section = TwineSection("Messages")
        twine_file.sections.append(section)

        msg = TwineDefinition("info_message")
        msg.translations["en"] = "First %1$@, then %2$@, finally %1$@"
        twine_file.definitions_by_key["info_message"] = msg
        section.definitions.append(msg)

        formatter.twine_file = twine_file
        output = formatter.format_file("en")
        assert "<translation>First %1, then %2, finally %1</translation>" in output

    def test_newlines_preserved(self, formatter):
        twine_file = TwineFile()
        twine_file.language_codes = ["en"]
        section = TwineSection("Misc")
        twine_file.sections.append(section)

        d = TwineDefinition("wait_message")
        d.translations["en"] = "This can take several minutes.\\nPlease wait…"
        twine_file.definitions_by_key["wait_message"] = d
        section.definitions.append(d)

        formatter.twine_file = twine_file
        output = formatter.format_file("en")
        assert (
            "<translation>This can take several minutes.\n"
            "Please wait…</translation>"
        ) in output

    def test_xml_special_chars_escaped(self, formatter):
        twine_file = TwineFile()
        twine_file.language_codes = ["en"]
        section = TwineSection("Misc")
        twine_file.sections.append(section)

        d = TwineDefinition("ampersand_test")
        d.translations["en"] = 'Tom & Jerry <fast> "go"'
        twine_file.definitions_by_key["ampersand_test"] = d
        section.definitions.append(d)

        formatter.twine_file = twine_file
        output = formatter.format_file("en")
        assert (
            '<translation>Tom &amp; Jerry &lt;fast&gt; &quot;go&quot;</translation>'
        ) in output

    def test_boundary_spaces_escaped(self, formatter):
        twine_file = TwineFile()
        twine_file.language_codes = ["en"]
        section = TwineSection("Misc")
        twine_file.sections.append(section)

        d = TwineDefinition("padded")
        d.translations["en"] = "  hello  "
        twine_file.definitions_by_key["padded"] = d
        section.definitions.append(d)

        formatter.twine_file = twine_file
        output = formatter.format_file("en")
        assert "<translation>&#32;&#32;hello&#32;&#32;</translation>" in output

    def test_source_uses_developer_language(self, formatter):
        """`<source>` always carries the developer-language string regardless
        of the target translation language."""
        twine_file = TwineFile()
        twine_file.language_codes = ["en", "ru"]  # en is developer language
        section = TwineSection("General")
        twine_file.sections.append(section)

        back = TwineDefinition("back")
        back.translations["en"] = "Back"
        back.translations["ru"] = "Назад"
        twine_file.definitions_by_key["back"] = back
        section.definitions.append(back)

        formatter.twine_file = twine_file
        output = formatter.format_file("ru")
        assert "<source>Back</source>" in output
        assert "<translation>Назад</translation>" in output

    def test_empty_section_skipped(self, formatter):
        twine_file = TwineFile()
        twine_file.language_codes = ["en", "ru"]
        empty = TwineSection("Empty")
        twine_file.sections.append(empty)

        present = TwineSection("Present")
        twine_file.sections.append(present)

        d = TwineDefinition("hello")
        d.translations["en"] = "Hi"
        twine_file.definitions_by_key["hello"] = d
        present.definitions.append(d)

        formatter.twine_file = twine_file
        output = formatter.format_file("en")
        # Only one <context> block emitted (the empty section is omitted).
        assert output.count("<context>") == 1

    def test_single_context_wraps_multiple_sections(self, formatter):
        """All sections share one <context> block (qtTrId ignores name and
        Qt's TS schema prefers one context per file)."""
        twine_file = TwineFile()
        twine_file.language_codes = ["en"]

        section_a = TwineSection("A")
        twine_file.sections.append(section_a)
        d1 = TwineDefinition("a_key")
        d1.translations["en"] = "A value"
        twine_file.definitions_by_key["a_key"] = d1
        section_a.definitions.append(d1)

        section_b = TwineSection("B")
        twine_file.sections.append(section_b)
        d2 = TwineDefinition("b_key")
        d2.translations["en"] = "B value"
        twine_file.definitions_by_key["b_key"] = d2
        section_b.definitions.append(d2)

        formatter.twine_file = twine_file
        output = formatter.format_file("en")
        assert output.count("<context>") == 1
        assert output.count("</context>") == 1
        assert 'id="a_key"' in output
        assert 'id="b_key"' in output

    def test_comment_emitted_as_extracomment(self, formatter):
        twine_file = TwineFile()
        twine_file.language_codes = ["en"]
        section = TwineSection("General")
        twine_file.sections.append(section)

        d = TwineDefinition("back")
        d.translations["en"] = "Back"
        d.comment = "Navigation back action"
        twine_file.definitions_by_key["back"] = d
        section.definitions.append(d)

        formatter.twine_file = twine_file
        output = formatter.format_file("en")
        assert "<extracomment>Navigation back action</extracomment>" in output

    def test_extracomment_xml_escaped(self, formatter):
        twine_file = TwineFile()
        twine_file.language_codes = ["en"]
        section = TwineSection("General")
        twine_file.sections.append(section)

        d = TwineDefinition("warn")
        d.translations["en"] = "Warning"
        d.comment = 'Use for "soft" warnings & alerts'
        twine_file.definitions_by_key["warn"] = d
        section.definitions.append(d)

        formatter.twine_file = twine_file
        output = formatter.format_file("en")
        assert "<extracomment>Use for &quot;soft&quot; warnings &amp; alerts</extracomment>" in output

    def test_missing_comment_omits_extracomment(self, formatter):
        formatter.twine_file = _make_simple_twine_file()
        output = formatter.format_file("en")
        assert "<extracomment>" not in output

    def test_boundary_tabs_escaped(self, formatter):
        twine_file = TwineFile()
        twine_file.language_codes = ["en"]
        section = TwineSection("Misc")
        twine_file.sections.append(section)

        d = TwineDefinition("tabbed")
        d.translations["en"] = "\thello\t"
        twine_file.definitions_by_key["tabbed"] = d
        section.definitions.append(d)

        formatter.twine_file = twine_file
        output = formatter.format_file("en")
        assert "<translation>&#9;hello&#9;</translation>" in output

    def test_boundary_nbsp_escaped(self, formatter):
        twine_file = TwineFile()
        twine_file.language_codes = ["en"]
        section = TwineSection("Misc")
        twine_file.sections.append(section)

        d = TwineDefinition("nbsp_pad")
        d.translations["en"] = " word "
        twine_file.definitions_by_key["nbsp_pad"] = d
        section.definitions.append(d)

        formatter.twine_file = twine_file
        output = formatter.format_file("en")
        assert "<translation>&#160;word&#160;</translation>" in output


class TestQtFormatterRead:
    def test_read_simple(self, formatter):
        ts = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<TS version="2.1" language="ru">\n'
            '<context>\n<name></name>\n'
            '<message id="back">\n'
            '<source>Back</source>\n'
            '<translation>Назад</translation>\n'
            '</message>\n'
            '<message id="cancel">\n'
            '<source>Cancel</source>\n'
            '<translation>Отмена</translation>\n'
            '</message>\n'
            '</context>\n'
            '</TS>\n'
        )
        formatter.read(io.StringIO(ts), "ru")
        twine_file = formatter.twine_file
        assert twine_file.definitions_by_key["back"].translations["ru"] == "Назад"
        assert twine_file.definitions_by_key["cancel"].translations["ru"] == "Отмена"

    def test_read_skips_numerus(self, formatter):
        """Plural messages are not consumed (lossy round-trip)."""
        ts = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<TS version="2.1" language="en">\n'
            '<context>\n<name></name>\n'
            '<message id="tracks" numerus="yes">\n'
            '<source>%n tracks</source>\n'
            '<translation>\n'
            '<numerusform>%n track</numerusform>\n'
            '<numerusform>%n tracks</numerusform>\n'
            '</translation>\n'
            '</message>\n'
            '</context>\n'
            '</TS>\n'
        )
        formatter.read(io.StringIO(ts), "en")
        # The plural definition is not created during read.
        assert "tracks" not in formatter.twine_file.definitions_by_key

    def test_read_malformed_xml_raises(self, formatter):
        with pytest.raises(TwineError, match="Failed to parse Qt TS"):
            formatter.read(io.StringIO("<TS>not closed"), "en")
