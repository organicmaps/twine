"""
Integration test for Twine Python implementation.
"""

import tempfile
from pathlib import Path

from twine.formatters.registry import get_registry
from twine.runner import Runner
from twine.twine_file import TwineFile


def test_complete_workflow():
    """Test complete read/write workflow."""

    # Create a test Twine file
    twine_content = """[[General]]
\t[hello]
\t\ten = Hello <a href="https://omaps.app/">World</a>
\t\tes = Hola <a href="https://omaps.app/">Mundo</a>
\t\tcomment = A greeting
\t\ttags = common

[[Messages]]
\t[goodbye]
\t\ten = Goodbye
\t\tes = Adiós
"""

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Write Twine file
        twine_file_path = temp_path / "strings.txt"
        twine_file_path.write_text(twine_content)

        # Read Twine file
        twine_file = TwineFile()
        twine_file.read(str(twine_file_path))

        # Verify reading
        assert len(twine_file.sections) == 2
        assert "hello" in twine_file.definitions_by_key
        assert (
            twine_file.definitions_by_key["hello"].translations["en"] == 'Hello <a href="https://omaps.app/">World</a>'
        )
        assert twine_file.definitions_by_key["hello"].comment == "A greeting"

        print("✓ Twine file reading works")

        # Test Android formatter
        registry = get_registry()
        android_fmt = registry.get("android")
        android_fmt.twine_file = twine_file
        android_fmt.options = {}

        android_output = android_fmt.format_file("en")
        assert "<?xml version=" in android_output
        assert '<string name="hello">Hello <a href="https://omaps.app/">World</a></string>' in android_output

        print("✓ Android formatter works")

        # Test Apple formatter
        apple_fmt = registry.get("apple")
        apple_fmt.twine_file = twine_file
        apple_fmt.options = {}

        apple_output = apple_fmt.format_file("es")
        assert '"hello" = "Hola <a href=\\"https://omaps.app/\\">Mundo</a>";' in apple_output
        assert '"goodbye" = "Adiós";' in apple_output

        print("✓ Apple formatter works")

        # Test jQuery formatter
        jquery_fmt = registry.get("jquery")
        jquery_fmt.twine_file = twine_file
        jquery_fmt.options = {}

        jquery_output = jquery_fmt.format_file("en")
        assert '"hello":"Hello <a href=\\"https://omaps.app/\\">World</a>"' in jquery_output

        print("✓ jQuery formatter works")

        print("\n✅ All integration tests passed!")


def test_generate_all_skips_non_language_folders():
    """Only language folders get files, whatever the output path's ancestors look like.

    Regression test: the classifier used to be handed the whole path, so a short
    lowercase ancestor (/tmp, /var, /opt, /home/ab) matched the language regex and
    every non-language subfolder was written to as if it were a language.
    """
    twine_content = """[[General]]
\t[hello]
\t\ten = Hello
\t\tde = Hallo
"""

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        twine_file_path = temp_path / "strings.txt"
        twine_file_path.write_text(twine_content)

        twine_file = TwineFile()
        twine_file.read(str(twine_file_path))

        output_path = temp_path / "out"
        for folder in ("en.lproj", "de.lproj", "Views", "ChartData", "raw", "xml"):
            (output_path / folder).mkdir(parents=True)

        runner = Runner(
            options={
                "output_path": str(output_path),
                "format": "apple",
                # English fallback, so a bogus language would still produce a file.
                "include": "all",
            },
            twine_file=twine_file,
        )
        runner.generate_all_localization_files()

        for folder in ("en.lproj", "de.lproj"):
            assert (output_path / folder / "Localizable.strings").is_file()

        for folder in ("Views", "ChartData", "raw", "xml"):
            assert not (output_path / folder / "Localizable.strings").exists()


def test_generate_all_skips_non_language_folders_without_a_convention():
    """The folder name alone decides, for formatters with no fixed folder shape.

    gettext has no .lproj/values marker, so this is what actually exercises the
    runner: handed the full path, the temp directory's own ancestors match the
    language regex and every folder becomes a language.
    """
    twine_content = """[[General]]
\t[hello]
\t\ten = Hello
\t\tde = Hallo
"""

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        twine_file_path = temp_path / "strings.txt"
        twine_file_path.write_text(twine_content)

        twine_file = TwineFile()
        twine_file.read(str(twine_file_path))

        output_path = temp_path / "out"
        for folder in ("en", "de", "Views"):
            (output_path / folder).mkdir(parents=True)

        runner = Runner(
            options={
                "output_path": str(output_path),
                "format": "gettext",
                "include": "all",
            },
            twine_file=twine_file,
        )
        runner.generate_all_localization_files()

        for folder in ("en", "de"):
            assert (output_path / folder / "strings.po").is_file()

        assert not (output_path / "Views" / "strings.po").exists()


def test_folder_classification_is_stricter_than_path_classification():
    """Folder scanning is strict; naming a file directly still resolves its language.

    determine_language_given_path() is also reached from _prepare_read_write(), where
    a missing language silently falls back to the developer language — so tightening
    it there would make `consume-localization-file de.strings` import German as English.
    """
    for fmt, folders in (
        ("apple", ("Views", "ChartData", "raw", "xml")),
        ("android", ("raw", "xml", "drawable", "anim", "font")),
    ):
        formatter = get_registry().get(fmt)
        formatter.twine_file = TwineFile()
        formatter.options = {}

        for folder in folders:
            assert formatter.language_for_folder_name(folder) is None

    apple = get_registry().get("apple")
    apple.twine_file = TwineFile()
    apple.options = {}
    assert apple.language_for_folder_name("de.lproj") == "de"
    assert apple.determine_language_given_path("de.strings") == "de"

    android = get_registry().get("android")
    android.twine_file = TwineFile()
    android.options = {}
    assert android.language_for_folder_name("values-fi") == "fi"
    assert android.determine_language_given_path("de.xml") == "de"


if __name__ == "__main__":
    test_complete_workflow()
