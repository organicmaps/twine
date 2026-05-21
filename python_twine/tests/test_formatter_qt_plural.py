"""
Tests for the Qt formatter's plural (numerus) message handling.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from twine import TwineError
from twine.formatters.qt import QtFormatter
from twine.formatters.qt_plural_rules import (
    QT_NUMERUS_FORMS,
    get_qt_numerus_forms,
)
from twine.twine_file import TwineFile, TwineSection, TwineDefinition


@pytest.fixture
def formatter():
    twine_file = TwineFile()
    formatter = QtFormatter()
    formatter.twine_file = twine_file
    formatter.options = {"consume_all": True, "consume_comments": True}
    return formatter


def _set_plural(definition: TwineDefinition, lang: str, forms: dict):
    """Mirror how the strings.txt parser populates a plural: store both
    plural_translations[lang] and translations[lang] (=other or first form)."""
    definition.plural_translations[lang] = forms
    if "other" in forms:
        definition.translations[lang] = forms["other"]
    elif forms:
        definition.translations[lang] = next(iter(forms.values()))


def _tracks_twine_file() -> TwineFile:
    """Mirrors the [tracks] entry in OM's strings.txt at the time of writing."""
    twine_file = TwineFile()
    twine_file.language_codes = ["en", "ru", "ar", "ja", "fr", "uk"]
    section = TwineSection("Bookmarks")
    twine_file.sections.append(section)

    tracks = TwineDefinition("tracks")
    _set_plural(tracks, "en", {"one": "%d track", "other": "%d tracks"})
    _set_plural(tracks, "ru", {
        "one": "%d трек", "few": "%d трека",
        "many": "%d треков", "other": "%d трека",
    })
    _set_plural(tracks, "ar", {
        "zero": "%d مسار", "one": "%d مسار", "two": "%d مساران",
        "few": "%d مسارات", "many": "%d مسارا", "other": "%d مسار",
    })
    _set_plural(tracks, "ja", {"other": "%d トラック"})
    _set_plural(tracks, "fr", {"one": "%d piste", "other": "%d pistes"})
    _set_plural(tracks, "uk", {
        "one": "%d трек", "few": "%d треки", "many": "%d треків"
    })

    twine_file.definitions_by_key["tracks"] = tracks
    section.definitions.append(tracks)
    return twine_file


class TestPluralRulesTable:
    def test_table_covers_common_languages(self):
        """Sanity check on the derived table from numerus.cpp."""
        assert QT_NUMERUS_FORMS["en"] == ["one", "other"]
        assert QT_NUMERUS_FORMS["ru"] == ["one", "few", "many"]
        assert QT_NUMERUS_FORMS["ar"] == ["zero", "one", "two", "few", "many", "other"]
        assert QT_NUMERUS_FORMS["ja"] == ["other"]
        assert QT_NUMERUS_FORMS["fr"] == ["one", "other"]
        assert QT_NUMERUS_FORMS["pl"] == ["one", "few", "many"]
        assert QT_NUMERUS_FORMS["cs"] == ["one", "few", "other"]
        assert QT_NUMERUS_FORMS["sk"] == ["one", "few", "other"]
        assert QT_NUMERUS_FORMS["ro"] == ["one", "few", "other"]
        assert QT_NUMERUS_FORMS["sl"] == ["one", "two", "few", "other"]
        assert QT_NUMERUS_FORMS["lv"] == ["one", "other", "zero"]

    def test_region_fallback(self):
        assert get_qt_numerus_forms("es-MX") == ["one", "other"]
        assert get_qt_numerus_forms("en-GB") == ["one", "other"]
        assert get_qt_numerus_forms("fr-CA") == ["one", "other"]

    def test_pt_br_overrides_pt(self):
        """Brazilian Portuguese uses french-style rule (n <= 1 → one); the
        positional shape is the same as english style, but Qt internally
        applies different selection rules."""
        assert get_qt_numerus_forms("pt") == ["one", "other"]
        assert get_qt_numerus_forms("pt-BR") == ["one", "other"]

    def test_chinese_variants(self):
        assert get_qt_numerus_forms("zh-Hans") == ["other"]
        assert get_qt_numerus_forms("zh-Hant") == ["other"]
        assert get_qt_numerus_forms("zh") == ["other"]

    def test_unknown_language_returns_none(self):
        assert get_qt_numerus_forms("xx") is None


class TestPluralWrite:
    def test_english_two_forms(self, formatter):
        formatter.twine_file = _tracks_twine_file()
        output = formatter.format_file("en")
        assert '<message id="tracks" numerus="yes">' in output
        assert "<source>%n tracks</source>" in output
        assert (
            "<translation>\n"
            "<numerusform>%n track</numerusform>\n"
            "<numerusform>%n tracks</numerusform>\n"
            "</translation>"
        ) in output

    def test_russian_three_forms_drops_cldr_other(self, formatter):
        formatter.twine_file = _tracks_twine_file()
        output = formatter.format_file("ru")
        # Russian uses one/few/many positionally — CLDR 'other' is discarded.
        assert (
            "<translation>\n"
            "<numerusform>%n трек</numerusform>\n"
            "<numerusform>%n трека</numerusform>\n"
            "<numerusform>%n треков</numerusform>\n"
            "</translation>"
        ) in output

    def test_arabic_six_forms(self, formatter):
        formatter.twine_file = _tracks_twine_file()
        output = formatter.format_file("ar")
        # zero, one, two, few, many, other — six forms in positional order.
        assert output.count("<numerusform>") == 6
        assert "<numerusform>%n مسار</numerusform>" in output  # zero
        assert "<numerusform>%n مساران</numerusform>" in output  # two
        assert "<numerusform>%n مسارات</numerusform>" in output  # few

    def test_japanese_universal_form_only(self, formatter):
        formatter.twine_file = _tracks_twine_file()
        output = formatter.format_file("ja")
        assert output.count("<numerusform>") == 1
        assert "<numerusform>%n トラック</numerusform>" in output

    def test_uk_per_form_fallback_uses_developer_other(self, formatter):
        """Ukrainian strings.txt provides one/few/many. The Qt-uk table is
        ['one', 'few', 'many'] so no fallback needed; this checks that we
        don't accidentally insert a 4th form."""
        formatter.twine_file = _tracks_twine_file()
        output = formatter.format_file("uk")
        assert output.count("<numerusform>") == 3
        assert "<numerusform>%n трек</numerusform>" in output

    def test_french_two_forms(self, formatter):
        formatter.twine_file = _tracks_twine_file()
        output = formatter.format_file("fr")
        assert output.count("<numerusform>") == 2
        assert "<numerusform>%n piste</numerusform>" in output
        assert "<numerusform>%n pistes</numerusform>" in output

    def test_source_from_developer_other_form(self, formatter):
        """`<source>` is the developer-language 'other' form, with %d → %n."""
        formatter.twine_file = _tracks_twine_file()
        for lang in ["en", "ru", "ar", "ja", "fr"]:
            output = formatter.format_file(lang)
            assert "<source>%n tracks</source>" in output


class TestPluralFallback:
    def test_missing_form_falls_back_to_translated_other(self, formatter):
        twine_file = TwineFile()
        twine_file.language_codes = ["en", "ru"]
        section = TwineSection("Bookmarks")
        twine_file.sections.append(section)

        d = TwineDefinition("partial")
        _set_plural(d, "en", {"one": "%d edit", "other": "%d edits"})
        # Russian has only 'other' — 'one' and 'few' should fall back to 'other'.
        _set_plural(d, "ru", {"other": "%d правок"})
        twine_file.definitions_by_key["partial"] = d
        section.definitions.append(d)

        formatter.twine_file = twine_file
        output = formatter.format_file("ru")
        # All three Russian positional forms should be the translated 'other'.
        assert (
            "<numerusform>%n правок</numerusform>\n"
            "<numerusform>%n правок</numerusform>\n"
            "<numerusform>%n правок</numerusform>"
        ) in output

    def test_missing_language_falls_back_to_developer_other(self, formatter):
        twine_file = TwineFile()
        twine_file.language_codes = ["en", "ru"]
        section = TwineSection("Bookmarks")
        twine_file.sections.append(section)

        d = TwineDefinition("untranslated")
        _set_plural(d, "en", {"one": "%d edit", "other": "%d edits"})
        # Russian has no plural data at all — fall back through dev lang.
        twine_file.definitions_by_key["untranslated"] = d
        section.definitions.append(d)
        # include=all triggers OutputProcessor to fill missing target with dev fallback
        formatter.options = {**formatter.options, "include": "all"}

        formatter.twine_file = twine_file
        output = formatter.format_file("ru")
        # Each of the 3 Russian positional slots resolves via the dev-lang
        # chain. 'one' matches; 'few' and 'many' fall back to dev-lang 'other'.
        assert "<numerusform>%n edit</numerusform>" in output  # one
        assert output.count("<numerusform>%n edits</numerusform>") == 2  # few + many

    def test_unknown_language_raises(self, formatter):
        twine_file = TwineFile()
        twine_file.language_codes = ["en", "xx"]
        section = TwineSection("Bookmarks")
        twine_file.sections.append(section)

        d = TwineDefinition("foo")
        _set_plural(d, "en", {"one": "%d edit", "other": "%d edits"})
        _set_plural(d, "xx", {"one": "uno", "other": "many"})
        twine_file.definitions_by_key["foo"] = d
        section.definitions.append(d)

        formatter.twine_file = twine_file
        with pytest.raises(TwineError, match="Qt has no plural rule for language 'xx'"):
            formatter.format_file("xx")

    def test_per_form_placeholder_difference_allowed(self, formatter):
        """Real translations sometimes drop the count in certain forms — e.g.,
        Arabic's 'zero' form ('no files were found') has no %n while non-zero
        forms do. Qt accepts this; we don't enforce per-form consistency."""
        twine_file = TwineFile()
        twine_file.language_codes = ["en", "ar"]
        section = TwineSection("Bookmarks")
        twine_file.sections.append(section)

        d = TwineDefinition("found")
        _set_plural(d, "en", {"one": "%d file found", "other": "%d files found"})
        _set_plural(d, "ar", {
            "zero": "no files",
            "one": "%d file",
            "two": "%d files",
            "few": "%d files",
            "many": "%d files",
            "other": "%d files",
        })
        twine_file.definitions_by_key["found"] = d
        section.definitions.append(d)

        formatter.twine_file = twine_file
        output = formatter.format_file("ar")
        assert "<numerusform>no files</numerusform>" in output
        assert "<numerusform>%n file</numerusform>" in output


class TestPluralPlaceholderConversion:
    def test_first_numeric_becomes_n(self, formatter):
        """The first numeric placeholder is rewritten to %n; other
        placeholders remain sequentially numbered from %1."""
        twine_file = TwineFile()
        twine_file.language_codes = ["en"]
        section = TwineSection("Misc")
        twine_file.sections.append(section)

        d = TwineDefinition("multi")
        _set_plural(d, "en", {
            "one": "%d file at %@",
            "other": "%d files at %@",
        })
        twine_file.definitions_by_key["multi"] = d
        section.definitions.append(d)

        formatter.twine_file = twine_file
        output = formatter.format_file("en")
        assert "<numerusform>%n file at %1</numerusform>" in output
        assert "<numerusform>%n files at %1</numerusform>" in output

    def test_no_numeric_placeholder_is_ok(self, formatter):
        """A plural without any count-eligible placeholder generates a
        numerus message anyway (every form just has zero %n's). Qt still
        picks the right form by n, just won't substitute the number."""
        twine_file = TwineFile()
        twine_file.language_codes = ["en"]
        section = TwineSection("Misc")
        twine_file.sections.append(section)

        d = TwineDefinition("descriptive")
        _set_plural(d, "en", {
            "one": "one item",
            "other": "many items",
        })
        twine_file.definitions_by_key["descriptive"] = d
        section.definitions.append(d)

        formatter.twine_file = twine_file
        output = formatter.format_file("en")
        assert "<numerusform>one item</numerusform>" in output
        assert "<numerusform>many items</numerusform>" in output


@pytest.mark.skipif(shutil.which("lrelease") is None, reason="lrelease is not installed")
class TestLreleaseCompilation:
    """Compile generated TS through Qt's lrelease to catch schema or
    encoding regressions that pure XML assertions miss. Skipped in
    environments without Qt installed."""

    @staticmethod
    def _compile(ts_content: str) -> tuple[int, str]:
        with tempfile.TemporaryDirectory() as tmp:
            ts_path = Path(tmp) / "test.ts"
            qm_path = Path(tmp) / "test.qm"
            ts_path.write_text(ts_content, encoding="utf-8")
            result = subprocess.run(
                ["lrelease", str(ts_path), "-qm", str(qm_path)],
                capture_output=True, text=True,
            )
            combined = (result.stderr + result.stdout).lower()
            return result.returncode, combined

    def _assert_clean(self, output: str) -> None:
        rc, msg = self._compile(output)
        assert rc == 0, msg
        assert "warning" not in msg, msg
        assert "error" not in msg, msg

    def test_compiles_english_plural(self, formatter):
        formatter.twine_file = _tracks_twine_file()
        self._assert_clean(formatter.format_file("en"))

    def test_compiles_russian_plural(self, formatter):
        formatter.twine_file = _tracks_twine_file()
        self._assert_clean(formatter.format_file("ru"))

    def test_compiles_arabic_plural(self, formatter):
        formatter.twine_file = _tracks_twine_file()
        self._assert_clean(formatter.format_file("ar"))

    def test_compiles_japanese_plural(self, formatter):
        formatter.twine_file = _tracks_twine_file()
        self._assert_clean(formatter.format_file("ja"))

    def test_compiles_with_extracomment_and_boundary_whitespace(self, formatter):
        """Mixed-feature smoke test: extracomment + tab-bounded translation +
        plural in the same context block."""
        twine_file = TwineFile()
        twine_file.language_codes = ["en"]
        section = TwineSection("Mixed")
        twine_file.sections.append(section)

        plain = TwineDefinition("plain")
        plain.translations["en"] = "\tIndented\t"
        plain.comment = "Has leading & trailing tabs"
        twine_file.definitions_by_key["plain"] = plain
        section.definitions.append(plain)

        plural = TwineDefinition("count")
        _set_plural(plural, "en", {"one": "%d item", "other": "%d items"})
        plural.comment = "Item counter"
        twine_file.definitions_by_key["count"] = plural
        section.definitions.append(plural)

        formatter.twine_file = twine_file
        self._assert_clean(formatter.format_file("en"))
