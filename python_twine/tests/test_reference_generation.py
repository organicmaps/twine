"""Inherited localization data, output ownership, and formatter round trips."""

import io
import plistlib
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from twine import TwineError
from twine.formatters.android import AndroidFormatter
from twine.formatters.apple import AppleFormatter
from twine.formatters.apple_plural import ApplePluralFormatter
from twine.formatters.qt import QtFormatter
from twine.output_processor import OutputProcessor
from twine.runner import Runner
from twine.twine_file import TwineFile

PLURALS = (
    "[count]\nen:one = %d bridge\nen:other = %d bridges\n"
    "fr:one = %d pont\nfr:other = %d ponts\n"
    "[middle]\nref = count\n[alias]\nref = middle\n"
)


def read_twine(tmp_path: Path, content: str) -> TwineFile:
    path = tmp_path / "strings.txt"
    path.write_text(content, encoding="utf-8")
    result = TwineFile()
    result.read(str(path))
    return result


def format_file(twine_file, formatter_type, language, **options):
    formatter = formatter_type()
    formatter.twine_file = twine_file
    formatter.options = {"include": "all", **options}
    return formatter.format_file(language)


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("zh-CN", ["zh-Hans", "zh", "en"]),
        ("zh-HK", ["zh-Hant", "zh", "en"]),
        ("zh-MO", ["zh-Hant", "zh", "en"]),
        ("yue-HK", ["yue", "en"]),
        ("yue-MO", ["yue", "en"]),
        ("ast-ES", ["ast", "en"]),
        ("fr-CA", ["fr", "en"]),
        ("en", []),
    ],
)
def test_import_and_generation_share_fallback_order(tmp_path, language, expected):
    twine_file = read_twine(tmp_path, "[bridge]\nen = Bridge\n")
    assert twine_file.fallback_languages(language, True) == expected
    assert OutputProcessor(twine_file, {}).fallback_languages(language) == expected


def test_chinese_translation_survives_deduplication(tmp_path):
    twine_file = read_twine(
        tmp_path, "[bridge]\nen = Bridge\nzh-Hant = 橋\nzh-HK = 橋\n"
    )
    before = format_file(twine_file, AppleFormatter, "zh-HK")
    twine_file.optimize_duplicates()
    assert "zh-HK" not in twine_file.definitions_by_key["bridge"].translations
    assert format_file(twine_file, AppleFormatter, "zh-HK") == before
    assert "橋" in before


@pytest.mark.parametrize("include", ["all", "translated", "untranslated"])
def test_empty_inherited_value_counts_as_translated(tmp_path, include):
    twine_file = read_twine(tmp_path, "[base]\nen = Value\nfr = \n[alias]\nref = base\n")
    result = OutputProcessor(twine_file, {"include": include}).process("fr")
    if include == "untranslated":
        assert not result.definitions_by_key
    else:
        assert set(result.definitions_by_key) == {"base", "alias"}
        assert all(d.translations["fr"] == "" for d in result.definitions_by_key.values())


def test_plural_completion_owns_its_forms(tmp_path):
    twine_file = read_twine(
        tmp_path, "[count]\nen:one = %d bridge\nen:other = %d bridges\nfr:one = %d pont\n"
    )
    original = twine_file.definitions_by_key["count"]
    result = OutputProcessor(twine_file, {"include": "all"}).process("fr")
    generated = result.definitions_by_key["count"].plural_translations["fr"]
    assert generated == {"one": "%d pont", "other": "%d bridges"}
    assert original.plural_translations["fr"] == {"one": "%d pont"}
    generated["one"] = "changed"
    assert original.plural_translations["fr"]["one"] == "%d pont"


@pytest.mark.parametrize("language", ["fr", "fr-CA"])
def test_android_inherits_all_plural_forms(tmp_path, language):
    twine_file = read_twine(tmp_path, PLURALS)
    root = ET.fromstring(format_file(twine_file, AndroidFormatter, language))
    for key in ("count", "middle", "alias"):
        node = root.find(f"plurals[@name='{key}']")
        assert node is not None
        assert {item.get("quantity"): item.text for item in node} == {
            "one": "%d pont", "other": "%d ponts"
        }
    assert twine_file.definitions_by_key["alias"].plural_translations == {}


def test_apple_routes_plural_aliases_to_stringsdict(tmp_path):
    twine_file = read_twine(tmp_path, PLURALS)
    assert not format_file(twine_file, AppleFormatter, "fr-CA")
    output = format_file(twine_file, ApplePluralFormatter, "fr-CA")
    result = plistlib.loads(output.encode("utf-8"))
    assert set(result) == {"count", "middle", "alias"}
    for item in result.values():
        assert item["value"]["one"] == "%d pont"
        assert item["value"]["other"] == "%d ponts"


@pytest.mark.parametrize("include", ["all", "translated"])
@pytest.mark.parametrize("value", ["Passerelle", ""])
def test_singular_override_blocks_inherited_plurals(tmp_path, include, value):
    twine_file = read_twine(tmp_path, PLURALS + f"fr = {value}\n")
    root = ET.fromstring(format_file(twine_file, AndroidFormatter, "fr", include=include))
    node = root.find("string[@name='alias']")
    assert node is not None
    assert (node.text or "") == value
    assert root.find("plurals[@name='alias']") is None


@pytest.mark.parametrize("include", ["all", "untranslated"])
@pytest.mark.parametrize("value", ["Passerelle", ""])
def test_regional_fallback_preserves_singular_override(tmp_path, include, value):
    twine_file = read_twine(tmp_path, PLURALS + f"fr = {value}\n")
    result = OutputProcessor(twine_file, {"include": include}).process("fr-CA")
    alias = result.definitions_by_key["alias"]
    assert alias.translations == {"fr-CA": value}
    assert alias.plural_translations == {}


@pytest.mark.parametrize("reference", ["count", "middle"])
def test_deduplication_preserves_singular_resource_type(tmp_path, reference):
    twine_file = read_twine(
        tmp_path, PLURALS.replace("ref = middle", f"ref = {reference}") + "fr = %d ponts\n"
    )
    before = format_file(twine_file, AndroidFormatter, "fr")
    twine_file.optimize_duplicates()
    path = tmp_path / "optimized.txt"
    twine_file.write(str(path))
    restored = TwineFile()
    restored.read(str(path))
    assert format_file(restored, AndroidFormatter, "fr") == before
    assert restored.definitions_by_key["alias"].translations["fr"] == "%d ponts"


@pytest.mark.parametrize(("language", "default_fallback"), [("fr-CA", False), ("de", True)])
def test_deduplication_keeps_singular_language_over_plural_fallback(tmp_path, language, default_fallback):
    twine_file = read_twine(tmp_path, PLURALS + f"{language} = %d bridges\n")
    # Use a local plural fallback whose default form equals the singular override.
    definition = twine_file.definitions_by_key["alias"]
    definition.reference = None
    definition.reference_key = None
    definition.plural_translations = {"en": {"one": "%d bridge", "other": "%d bridges"}}
    definition.translations["en"] = "%d bridges"
    if language == "fr-CA":
        definition.plural_translations["fr"] = definition.plural_translations["en"].copy()
        definition.translations["fr"] = "%d bridges"
    twine_file.fallback_to_default = default_fallback
    before = format_file(twine_file, AndroidFormatter, language)
    twine_file.optimize_duplicates()
    assert definition.translations[language] == "%d bridges"
    assert format_file(twine_file, AndroidFormatter, language) == before


@pytest.mark.parametrize("include", ["translated", "untranslated"])
def test_imported_android_plural_counts_as_translated(tmp_path, include):
    twine_file = read_twine(tmp_path, "[count]\nen = Bridges\n")
    formatter = AndroidFormatter()
    formatter.twine_file = twine_file
    formatter.read(
        io.StringIO(
            '<resources><plurals name="count"><item quantity="one">%d pont</item>'
            '<item quantity="other">%d ponts</item></plurals></resources>'
        ),
        "fr",
    )
    result = OutputProcessor(twine_file, {"include": include}).process("fr")
    if include == "untranslated":
        assert not result.definitions_by_key
    else:
        assert result.definitions_by_key["count"].translations["fr"] == "%d ponts"
        assert result.definitions_by_key["count"].plural_translations["fr"] == {
            "one": "%d pont", "other": "%d ponts"
        }


def test_output_owns_tag_list(tmp_path):
    twine_file = read_twine(tmp_path, "[bridge]\nen = Bridge\ntags = android,apple\n")
    result = OutputProcessor(twine_file, {}).process("en")
    result.definitions_by_key["bridge"].tags.append("qt")
    assert twine_file.definitions_by_key["bridge"].tags == ["android", "apple"]


@pytest.mark.parametrize("formatter_type", [AndroidFormatter, ApplePluralFormatter])
def test_formats_requiring_other_reject_unresolvable_plural(tmp_path, formatter_type):
    twine_file = read_twine(tmp_path, "[count]\nuk:one = %d річ\nuk:few = %d речі\nuk:many = %d речей\n")
    with pytest.raises(TwineError, match="has no 'other' form"):
        format_file(twine_file, formatter_type, "uk")


def test_singular_formats_skip_plural_without_default_text(tmp_path):
    twine_file = read_twine(tmp_path, "[count]\nuk:one = %d річ\nuk:few = %d речі\nuk:many = %d речей\n")
    assert format_file(twine_file, AppleFormatter, "uk") is None


def test_apple_plural_output_skips_singular_definitions(tmp_path):
    twine_file = read_twine(tmp_path, "[bridge]\nen = Bridge\n")
    assert format_file(twine_file, ApplePluralFormatter, "en") is None


def test_apple_plural_aliases_round_trip(tmp_path):
    twine_file = read_twine(tmp_path, PLURALS)
    output = format_file(twine_file, ApplePluralFormatter, "fr")
    formatter = ApplePluralFormatter()
    formatter.twine_file = twine_file
    formatter.read(io.StringIO(output), "fr")
    assert twine_file.definitions_by_key["alias"].plural_translations == {}


@pytest.mark.parametrize("formatter_type", [AndroidFormatter, AppleFormatter])
def test_imported_singular_other_text_overrides_inherited_plurals(tmp_path, formatter_type):
    twine_file = read_twine(tmp_path, PLURALS)
    formatter = formatter_type()
    formatter.twine_file = twine_file
    content = (
        '<resources><string name="alias">%d ponts</string></resources>'
        if formatter_type is AndroidFormatter else '"alias" = "%d ponts";\n'
    )
    formatter.read(io.StringIO(content), "fr")
    twine_file.optimize_duplicates()
    alias = OutputProcessor(twine_file, {}).process("fr").definitions_by_key["alias"]
    assert alias.translations["fr"] == "%d ponts"
    assert alias.plural_translations == {}


def test_imported_plural_replaces_a_singular_reference_override(tmp_path):
    twine_file = read_twine(tmp_path, PLURALS + "fr = Passerelle\n")
    formatter = AndroidFormatter()
    formatter.twine_file = twine_file
    formatter.read(
        io.StringIO(
            '<resources><plurals name="alias"><item quantity="one">%d pont</item>'
            '<item quantity="other">%d ponts</item></plurals></resources>'
        ),
        "fr",
    )
    alias = OutputProcessor(twine_file, {}).process("fr").definitions_by_key["alias"]
    assert alias.translations["fr"] == "%d ponts"
    assert alias.plural_translations["fr"] == {"one": "%d pont", "other": "%d ponts"}


def test_qt_inherits_regional_plural_forms(tmp_path):
    twine_file = read_twine(tmp_path, PLURALS)
    root = ET.fromstring(format_file(twine_file, QtFormatter, "fr-CA"))
    for key in ("count", "middle", "alias"):
        message = root.find(f".//message[@id='{key}']")
        assert message.get("numerus") == "yes"
        assert [node.text for node in message.findall("translation/numerusform")] == [
            "%n pont", "%n ponts"
        ]


def test_qt_partial_exact_forms_keep_developer_fallback(tmp_path):
    twine_file = read_twine(
        tmp_path, PLURALS.replace("[middle]", "fr-CA:one = %d pont canadien\n[middle]")
    )
    root = ET.fromstring(format_file(twine_file, QtFormatter, "fr-CA"))
    forms = root.findall(".//message[@id='count']/translation/numerusform")
    assert [node.text for node in forms] == ["%n pont canadien", "%n bridges"]


@pytest.mark.parametrize("with_developer_fallback", [False, True])
@pytest.mark.parametrize("include", ["translated", "untranslated"])
def test_qt_complete_plural_without_cldr_other(tmp_path, include, with_developer_fallback):
    developer_text = "en:one = %d item\nen:other = %d items\n" if with_developer_fallback else ""
    twine_file = read_twine(
        tmp_path, "[count]\n" + developer_text + "uk:one = %d річ\nuk:few = %d речі\nuk:many = %d речей\n"
    )
    output = format_file(twine_file, QtFormatter, "uk", include=include)
    if include == "untranslated":
        assert output is None
    else:
        message = ET.fromstring(output).find(".//message[@id='count']")
        assert [node.text for node in message.findall("translation/numerusform")] == [
            "%n річ", "%n речі", "%n речей"
        ]


@pytest.mark.parametrize(("value", "expected"), [("Pont", "Pont"), ("Bridge", None)])
def test_apple_consumes_reference_chains(tmp_path, value, expected):
    formatter = AppleFormatter()
    formatter.twine_file = read_twine(
        tmp_path, "[base]\nen = Bridge\n[middle]\nref = base\n[alias]\nref = middle\n"
    )
    formatter.read(io.StringIO(f'"alias" = "{value}";\n'), "fr")
    assert formatter.twine_file.definitions_by_key["alias"].translations.get("fr") == expected


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("[alias]\nen = Alias\nref = absent\n", "Unknown reference 'absent'"),
        ("[alias]\nen = Alias\nref = alias\n", "Circular reference"),
        ("[a]\nref = b\n[b]\nref = a\n", "Circular reference"),
    ],
)
def test_read_rejects_invalid_reference_graphs(tmp_path, content, message):
    with pytest.raises(TwineError, match=message):
        read_twine(tmp_path, content)


def test_forward_and_shared_references_are_valid(tmp_path):
    twine_file = read_twine(
        tmp_path, "[alias]\nref = middle\n[other]\nref = middle\n"
        "[middle]\nref = base\n[base]\nen = Bridge\n"
    )
    assert twine_file.definitions_by_key["alias"].translation_for_lang("en") == "Bridge"
    assert twine_file.definitions_by_key["other"].translation_for_lang("en") == "Bridge"


def test_validation_rejects_a_mutated_cycle(tmp_path):
    twine_file = read_twine(tmp_path, "[base]\nen = Bridge\n[alias]\nref = base\n")
    alias = twine_file.definitions_by_key["alias"]
    alias.reference = alias
    with pytest.raises(TwineError, match="Circular reference"):
        Runner({}, twine_file).validate_twine_file()
