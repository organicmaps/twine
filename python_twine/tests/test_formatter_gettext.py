"""Gettext source context and translated PO values."""

import gettext
import io
import shutil
import subprocess
from pathlib import Path

import pytest

from twine.formatters.gettext import GettextFormatter
from twine.twine_file import TwineFile


def read_twine(tmp_path: Path, content: str) -> TwineFile:
    path = tmp_path / "strings.txt"
    path.write_text(content, encoding="utf-8")
    result = TwineFile()
    result.read(str(path))
    return result


def format_file(twine_file, language, **options):
    formatter = GettextFormatter()
    formatter.twine_file = twine_file
    formatter.options = {"include": "all", **options}
    return formatter.format_file(language)


def test_gettext_exports_inherited_source_and_translation(tmp_path):
    twine_file = read_twine(
        tmp_path, "[base]\nen = Bridge\nfr = Pont\n[middle]\nref = base\n[alias]\nref = middle\n"
    )
    output = format_file(twine_file, "fr")
    assert 'msgctxt "alias"\nmsgid "Bridge"\nmsgstr "Pont"' in output
    formatter = GettextFormatter()
    formatter.twine_file = read_twine(
        tmp_path, "[base]\nen = Bridge\n[middle]\nref = base\n[alias]\nref = middle\n"
    )
    formatter.read(io.StringIO(output), "fr")
    assert formatter.twine_file.definitions_by_key["alias"].translation_for_lang("fr") == "Pont"


def test_gettext_honors_developer_language_option(tmp_path):
    twine_file = read_twine(tmp_path, "[base]\nen = Bridge\nfr = Pont\n")
    output = format_file(twine_file, "en", developer_language="fr")
    assert 'msgid "Pont"\nmsgstr "Bridge"' in output


@pytest.mark.parametrize(
    ("translation", "expected"),
    [
        ('"Bonjour"', "Bonjour"),
        ('"multi"\n"line\\n"\n"string"', "multiline\\nstring"),
        ('"Pont \\"ancien\\""', 'Pont "ancien"'),
        ('""', None),
    ],
)
def test_gettext_imports_msgstr_and_continuations(tmp_path, translation, expected):
    formatter = GettextFormatter()
    formatter.twine_file = read_twine(tmp_path, "[hello]\nen = Hello\n")
    formatter.read(
        io.StringIO(f'msgctxt "hello"\nmsgid "Hello"\nmsgstr {translation}\n'),
        "fr",
    )
    assert formatter.twine_file.definitions_by_key["hello"].translations.get("fr") == expected


@pytest.mark.parametrize(
    "msgstr",
    [
        'msgstr "Bon"  \n"jour"',
        'msgstr ""\n"Bon"\t \n "jour"',
        '  msgstr "Bonjour"',
    ],
)
def test_gettext_accepts_whitespace_around_quoted_fragments(tmp_path, msgstr):
    formatter = GettextFormatter()
    formatter.twine_file = read_twine(tmp_path, "[hello]\nen = Hello\n")
    formatter.read(io.StringIO(f'msgctxt "hello"\nmsgid "Hello"\n{msgstr}\n'), "fr")
    assert formatter.twine_file.definitions_by_key["hello"].translations["fr"] == "Bonjour"


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_gettext_accepts_context_whitespace_and_line_endings(tmp_path, newline):
    formatter = GettextFormatter()
    formatter.twine_file = read_twine(tmp_path, "[hello]\nen = Hello\n")
    content = newline.join(['  msgctxt "hello"  ', 'msgid "Hello"', 'msgstr "Bonjour"', ''])
    formatter.read(io.StringIO(content), "fr")
    assert formatter.twine_file.definitions_by_key["hello"].translations["fr"] == "Bonjour"


@pytest.mark.parametrize("flags", ["fuzzy", "c-format, fuzzy", "fuzzy, c-format"])
def test_gettext_skips_fuzzy_entries_and_keeps_following_translations(tmp_path, flags):
    formatter = GettextFormatter()
    formatter.twine_file = read_twine(tmp_path, "[hello]\nen = Hello\n[bye]\nen = Bye\n")
    formatter.read(
        io.StringIO(
            f'#, {flags}\nmsgctxt "hello"\nmsgid "Hello"\nmsgstr "Ancien"\n\n'
            'msgctxt "bye"\nmsgid "Bye"\nmsgstr "Au revoir"\n'
        ),
        "fr",
    )
    assert "fr" not in formatter.twine_file.definitions_by_key["hello"].translations
    assert formatter.twine_file.definitions_by_key["bye"].translations["fr"] == "Au revoir"


@pytest.mark.parametrize("separator", ["\n \t\n", "\r\n\r\n"])
def test_gettext_accepts_entry_separator_whitespace(tmp_path, separator):
    formatter = GettextFormatter()
    formatter.twine_file = read_twine(tmp_path, "[hello]\nen = Hello\n[bye]\nen = Bye\n")
    formatter.read(
        io.StringIO(
            'msgctxt "hello"\nmsgid "Hello"\nmsgstr "Bonjour"' + separator
            + 'msgctxt "bye"\nmsgid "Bye"\nmsgstr "Au revoir"\n'
        ),
        "fr",
    )
    assert formatter.twine_file.definitions_by_key["hello"].translations["fr"] == "Bonjour"
    assert formatter.twine_file.definitions_by_key["bye"].translations["fr"] == "Au revoir"


@pytest.mark.skipif(shutil.which("msgfmt") is None, reason="GNU msgfmt is not installed")
@pytest.mark.parametrize("value", ["Été", 'Pont "ancien"', "Première ligne\\nsuite"])
def test_generated_gettext_compiles_and_preserves_translation(tmp_path, value):
    twine_file = read_twine(tmp_path, f"[hello]\nen = Hello\nfr = {value}\n")
    output = format_file(twine_file, "fr")
    po_path = tmp_path / "fr.po"
    mo_path = tmp_path / "fr.mo"
    po_path.write_text(output, encoding="utf-8")
    result = subprocess.run(
        ["msgfmt", "-o", str(mo_path), str(po_path)],
        check=False, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert not result.stderr
    with mo_path.open("rb") as stream:
        catalog = gettext.GNUTranslations(stream)
    assert catalog.info()["language"] == "fr"
    assert catalog.pgettext("hello", "Hello") == value.replace("\\n", "\n")
