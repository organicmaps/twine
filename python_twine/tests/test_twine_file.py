"""
Tests for core Twine data models.
"""

import tempfile
from pathlib import Path

import pytest
from twine.twine_file import TwineDefinition, TwineFile, TwineSection


class TestTwineDefinition:
    """Test TwineDefinition class."""

    def test_initialization(self):
        """Test basic initialization."""
        definition = TwineDefinition("test_key")
        assert definition.key == "test_key"
        assert definition.comment is None
        assert definition.tags is None
        assert definition.translations == {}

    def test_translation_for_lang(self):
        """Test translation retrieval."""
        definition = TwineDefinition("test_key")
        definition.translations = {"en": "Hello", "es": "Hola"}

        assert definition.translation_for_lang("en") == "Hello"
        assert definition.translation_for_lang("es") == "Hola"
        assert definition.translation_for_lang("fr") is None

    def test_matches_tags_no_filter(self):
        """Test tag matching with no filter."""
        definition = TwineDefinition("test_key")
        definition.tags = ["tag1", "tag2"]

        assert definition.matches_tags(None, True)
        assert definition.matches_tags([], True)

    def test_matches_tags_with_tags(self):
        """Test tag matching with tags."""
        definition = TwineDefinition("test_key")
        definition.tags = ["tag1", "tag2"]

        # OR logic: tag1 OR tag3
        assert definition.matches_tags([["tag1", "tag3"]], True)

        # Negation: NOT tag3
        assert definition.matches_tags([["~tag3"]], True)

        # Complex: (tag1 OR tag2) AND (NOT tag3)
        assert definition.matches_tags([["tag1", "tag2"], ["~tag3"]], True)

    def test_is_plural(self):
        """Test plural detection."""
        definition = TwineDefinition("test_key")
        assert not definition.is_plural()

        definition.plural_translations = {"en": {"one": "item", "other": "items"}}
        assert definition.is_plural()


class TestTwineSection:
    """Test TwineSection class."""

    def test_initialization(self):
        """Test section initialization."""
        section = TwineSection("Test Section")
        assert section.name == "Test Section"
        assert section.definitions == []

    def test_add_definitions(self):
        """Test adding definitions to section."""
        section = TwineSection("Test")
        def1 = TwineDefinition("key1")
        def2 = TwineDefinition("key2")

        section.definitions.append(def1)
        section.definitions.append(def2)

        assert len(section.definitions) == 2
        assert section.definitions[0].key == "key1"


class TestTwineFile:
    """Test TwineFile class."""

    def test_initialization(self):
        """Test file initialization."""
        twine_file = TwineFile()
        assert twine_file.sections == []
        assert twine_file.definitions_by_key == {}
        assert twine_file.language_codes == []

    def test_add_language_code(self):
        """Test adding language codes."""
        twine_file = TwineFile()

        twine_file.add_language_code("en")
        assert twine_file.language_codes == ["en"]

        twine_file.add_language_code("es")
        assert twine_file.language_codes == ["en", "es"]

        # Adding same language doesn't duplicate
        twine_file.add_language_code("en")
        assert twine_file.language_codes == ["en", "es"]

        # Adding same language doesn't duplicate
        twine_file.add_language_code("es")
        assert twine_file.language_codes == ["en", "es"]

        # Languages should be ordered except the first one
        twine_file.add_language_code("de")
        assert twine_file.language_codes == ["en", "de", "es"]


    def test_set_developer_language_code(self):
        """Test setting developer language."""
        twine_file = TwineFile()
        twine_file.language_codes = ["en", "es", "fr"]

        twine_file.set_developer_language_code("es")
        assert twine_file.language_codes[0] == "es"
        assert "en" in twine_file.language_codes
        assert "fr" in twine_file.language_codes

    def test_set_developer_language_code_insert(self):
        """Test setting developer language."""
        twine_file = TwineFile()
        twine_file.language_codes = ["en", "es", "fr"]

        twine_file.set_developer_language_code("uk")
        assert twine_file.language_codes[0] == "uk"
        assert "en" in twine_file.language_codes
        assert "es" in twine_file.language_codes
        assert "fr" in twine_file.language_codes

    def test_read_simple_file(self):
        """Test reading a simple Twine file."""
        content = """[[General]]
\t[hello]
\t\ten = Hello
\t\tes = Hola
\t\tcomment = A greeting
\t\ttags = common,greeting
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            twine_file = TwineFile()
            twine_file.read(temp_path)

            assert len(twine_file.sections) == 1
            assert twine_file.sections[0].name == "General"
            assert len(twine_file.sections[0].definitions) == 1

            definition = twine_file.definitions_by_key["hello"]
            assert definition.translations["en"] == "Hello"
            assert definition.translations["es"] == "Hola"
            assert definition.comment == "A greeting"
            assert definition.tags == ["common", "greeting"]
        finally:
            Path(temp_path).unlink()

    def test_write_file(self):
        """Test writing a Twine file."""
        twine_file = TwineFile()
        twine_file.language_codes = ["en", "es"]

        section = TwineSection("Test")
        definition = TwineDefinition("test_key")
        definition.translations = {"en": "Test", "es": "Prueba"}
        definition.comment = "A test string"
        definition.tags = ["test"]

        section.definitions.append(definition)
        twine_file.sections.append(section)
        twine_file.definitions_by_key["test_key"] = definition

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            temp_path = f.name

        try:
            twine_file.write(temp_path)

            # Read back and verify
            with open(temp_path, "r") as f:
                content = f.read()

            assert content == """[[Test]]

[test_key]
comment = A test string
tags = test
en = Test
es = Prueba
"""
        finally:
            Path(temp_path).unlink()


class TestTwineFileReader:
    @pytest.fixture
    def fixtures_dir(self):
        """Get fixtures directory path."""
        return Path(__file__).parent / "fixtures"

    def test_accent_symbol(self, fixtures_dir):
        twine_file = TwineFile()
        twine_file.read(str(fixtures_dir / "twine_accent_values.txt"))
        assert twine_file.definitions_by_key["value_with_leading_accent"].translations["en"] == '`value'
        assert twine_file.definitions_by_key["value_with_trailing_accent"].translations["en"] == 'value`'
        assert twine_file.definitions_by_key["value_with_leading_space"].translations["en"] == ' value'
        assert twine_file.definitions_by_key["value_with_trailing_space"].translations["en"] == 'value '
        assert twine_file.definitions_by_key["value_wrapped_by_spaces"].translations["en"] == ' value '
        assert twine_file.definitions_by_key["value_wrapped_by_accents"].translations["en"] == '`value`'

class TestTwineFileOptimizations:
    @pytest.fixture
    def fixture_twine_file(self) -> TwineFile:
        twine_file = TwineFile()
        fixtures_dir = Path(__file__).parent / "fixtures"
        twine_file.read(str(fixtures_dir / "twine_preoptimized.txt"))
        return twine_file

    def test_deduplication_local_langs(self, fixture_twine_file: TwineFile):
        definitionA = fixture_twine_file.definitions_by_key['value_with_local_lang_codes']
        assert definitionA.translations['pt'] == definitionA.translations['pt-BR']
        assert definitionA.translations['es'] == definitionA.translations['es-MX']

        fixture_twine_file.fallback_to_default = False
        fixture_twine_file.optimize_duplicates()

        # Check that 'pt-BR' and 'es-MX' are removed from the TwineFile
        definitionA = fixture_twine_file.definitions_by_key['value_with_local_lang_codes']
        assert 'pt-BR' not in definitionA.translations
        assert 'pt' in definitionA.translations
        assert 'es-MX' not in definitionA.translations
        assert 'es' in definitionA.translations
        assert definitionA.translations['es'] == definitionA.translations['en']

    def test_deduplication_default_lang(self, fixture_twine_file: TwineFile):
        definitionB = fixture_twine_file.definitions_by_key['value_with_duplicated']
        assert definitionB.translations['en'] == definitionB.translations['de']

        fixture_twine_file.fallback_to_default = True
        fixture_twine_file.optimize_duplicates()

        # Check that 'de' lang is removed from the TwineFile because it matches 'en'
        definitionB = fixture_twine_file.definitions_by_key['value_with_duplicated']
        assert 'de' not in definitionB.translations
        assert 'fr' in definitionB.translations


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
