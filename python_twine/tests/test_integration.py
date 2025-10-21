"""
Integration test for Twine Python implementation.
"""

import tempfile
from pathlib import Path

from twine.twine_file import TwineFile
from twine.formatters.registry import get_registry


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


if __name__ == "__main__":
    test_complete_workflow()
