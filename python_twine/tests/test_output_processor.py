"""
Tests for OutputProcessor class.
"""

import pytest
from twine.output_processor import OutputProcessor
from twine.twine_file import TwineDefinition, TwineFile, TwineSection


class TestOutputProcessor:
    """Test output processor functionality."""

    @pytest.fixture
    def twine_file(self):
        """Create a test TwineFile."""
        twine_file = TwineFile()
        twine_file.language_codes = ["en", "fr"]

        section = TwineSection("Section")

        # Definition with tag1
        def1 = TwineDefinition("key1")
        def1.translations["en"] = "value1"
        def1.tags = ["tag1"]
        section.definitions.append(def1)

        # Definition with tag1 and tag2
        def2 = TwineDefinition("key2")
        def2.translations["en"] = "value2"
        def2.tags = ["tag1", "tag2"]
        section.definitions.append(def2)

        # Definition with tag2
        def3 = TwineDefinition("key3")
        def3.translations["en"] = "value3"
        def3.tags = ["tag2"]
        section.definitions.append(def3)

        # Definition with translations in both languages
        def4 = TwineDefinition("key4")
        def4.translations["en"] = "value4-en"
        def4.translations["fr"] = "value4-fr"
        section.definitions.append(def4)

        twine_file.sections.append(section)
        twine_file.definitions_by_key = {
            "key1": def1,
            "key2": def2,
            "key3": def3,
            "key4": def4,
        }

        return twine_file

    def test_includes_all_keys_by_default(self, twine_file):
        """Test that all keys are included by default."""
        processor = OutputProcessor(twine_file, {})
        result = processor.process("en")

        assert sorted(result.definitions_by_key.keys()) == [
            "key1",
            "key2",
            "key3",
            "key4",
        ]

    def test_filter_by_tag(self, twine_file):
        """Test filtering by a single tag."""
        processor = OutputProcessor(twine_file, {"tags": [["tag1"]]})
        result = processor.process("en")

        assert sorted(result.definitions_by_key.keys()) == ["key1", "key2"]

    def test_filter_by_multiple_tags(self, twine_file):
        """Test filtering by multiple tags (OR logic)."""
        processor = OutputProcessor(twine_file, {"tags": [["tag1", "tag2"]]})
        result = processor.process("en")

        assert sorted(result.definitions_by_key.keys()) == ["key1", "key2", "key3"]

    def test_filter_untagged(self, twine_file):
        """Test including untagged definitions."""
        processor = OutputProcessor(twine_file, {"tags": [["tag1"]], "untagged": True})
        result = processor.process("en")

        assert sorted(result.definitions_by_key.keys()) == ["key1", "key2", "key4"]

    def test_include_translated(self, twine_file):
        """Test including only translated definitions."""
        processor = OutputProcessor(twine_file, {"include": "translated"})
        result = processor.process("fr")

        assert sorted(result.definitions_by_key.keys()) == ["key4"]

    def test_include_untranslated(self, twine_file):
        """Test including only untranslated definitions."""
        processor = OutputProcessor(twine_file, {"include": "untranslated"})
        result = processor.process("fr")

        assert sorted(result.definitions_by_key.keys()) == ["key1", "key2", "key3"]


class TestTranslationFallback:
    """Test translation fallback functionality."""

    @pytest.fixture
    def twine_file(self):
        """Create a test TwineFile with translations."""
        twine_file = TwineFile()
        twine_file.language_codes = ["en", "fr", "de"]

        section = TwineSection("Section")

        # Definition with en and fr translations
        def1 = TwineDefinition("key1")
        def1.translations["en"] = "value1-en"
        def1.translations["fr"] = "value1-fr"
        section.definitions.append(def1)

        twine_file.sections.append(section)
        twine_file.definitions_by_key = {"key1": def1}

        return twine_file

    def test_fallback_to_default_language(self, twine_file):
        """Test fallback to default language (first in language_codes)."""
        processor = OutputProcessor(twine_file, {})
        result = processor.process("de")

        assert result.definitions_by_key["key1"].translations["de"] == "value1-en"

    def test_fallback_to_developer_language(self, twine_file):
        """Test fallback to specified developer language."""
        processor = OutputProcessor(twine_file, {"developer_language": "fr"})
        result = processor.process("de")

        assert result.definitions_by_key["key1"].translations["de"] == "value1-fr"


class TestPluralEdgeCases:
    """Regression tests for plural-definition handling that previously
    raised KeyError / TypeError before the OutputProcessor fix."""

    def test_include_translated_with_singular_target_does_not_raise(self):
        """A plural definition whose target language has only a non-plural
        translation must not raise under include='translated'. The plural
        slot stays absent — the formatter then emits it as a regular message."""
        twine_file = TwineFile()
        twine_file.language_codes = ["en", "ja"]
        section = TwineSection("Section")
        twine_file.sections.append(section)

        d = TwineDefinition("partial")
        d.translations["en"] = "%d items"
        d.translations["ja"] = "アイテム"
        d.plural_translations["en"] = {"one": "%d item", "other": "%d items"}
        twine_file.definitions_by_key["partial"] = d
        section.definitions.append(d)

        result = OutputProcessor(twine_file, {"include": "translated"}).process("ja")

        processed = result.definitions_by_key["partial"]
        assert processed.translations["ja"] == "アイテム"
        assert "ja" not in processed.plural_translations

    def test_no_plural_fallback_available_does_not_raise(self):
        """When no fallback language has plural data, the OutputProcessor
        must skip the plural augmentation rather than assigning None and
        TypeError-ing on `"other" not in None`."""
        twine_file = TwineFile()
        twine_file.language_codes = ["en", "fr"]
        section = TwineSection("Section")
        twine_file.sections.append(section)

        d = TwineDefinition("isolated")
        d.translations["en"] = "items"
        d.translations["fr"] = "éléments"
        # Plural data only for a language that is not in fr's fallback chain.
        d.plural_translations["es"] = {"one": "artículo", "other": "artículos"}
        twine_file.definitions_by_key["isolated"] = d
        section.definitions.append(d)

        result = OutputProcessor(twine_file, {"include": "all"}).process("fr")

        assert "isolated" in result.definitions_by_key
        assert result.definitions_by_key["isolated"].translations["fr"] == "éléments"
