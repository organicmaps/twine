"""
Output processor for filtering and processing Twine files.
"""

from twine.languages import fallback_languages
from twine.twine_file import TwineDefinition, TwineFile, TwineSection


class OutputProcessor:
    """Processes TwineFile for output, handling filtering and fallbacks."""

    def __init__(self, twine_file: TwineFile, options: dict):
        self.twine_file = twine_file
        self.options = options

    def default_language(self) -> str | None:
        """Get the default/developer language."""
        dev_lang = self.options.get("developer_language")
        if dev_lang:
            return dev_lang
        if self.twine_file.language_codes:
            return self.twine_file.language_codes[0]
        return None

    def fallback_languages(self, language: str) -> list[str]:
        """Use the same fallback order as translation deduplication."""
        return fallback_languages(language, self.default_language())

    def process(self, language: str) -> TwineFile:
        """
        Process the Twine file for a specific language.

        Args:
            language: Target language code

        Returns:
            Filtered TwineFile with only relevant definitions
        """
        result = TwineFile()
        result.language_codes = self.twine_file.language_codes.copy()
        fallbacks = self.fallback_languages(language)
        tags = self.options.get("tags")
        untagged = self.options.get("untagged", False)
        include_option = self.options.get("include")

        for section in self.twine_file.sections:
            new_section = TwineSection(section.name)

            for definition in section.definitions:
                # Check tag matching
                if not definition.matches_tags(tags, untagged):
                    continue

                value = definition.translation_for_lang(language)
                forms = definition.plural_translation_for_lang(language)

                # Handle include options
                has_translation = value is not None or forms is not None
                if has_translation and include_option == "untranslated":
                    continue
                if not has_translation and include_option == "translated":
                    continue

                # Keep the selected forms when only their default text needs fallback.
                # A singular fallback stops the search before another language's plurals.
                if value is None and forms is not None:
                    value = forms.get("other")
                if value is None:
                    for fallback in fallbacks:
                        if forms is None:
                            forms = definition.plural_translation_for_lang(fallback)
                        value = definition.translation_for_lang(fallback)
                        if value is None and forms is not None:
                            value = forms.get("other")
                        if value is not None:
                            break

                if value is None and forms is None:
                    continue

                new_definition = TwineDefinition(definition.key)
                new_definition.comment = definition.comment
                new_definition.tags = definition.tags.copy() if definition.tags is not None else None
                if forms is not None:
                    if value is not None:
                        forms.setdefault("other", value)
                    new_definition.plural_translations[language] = forms
                    # Non-plural formats need a representative default form.
                    value = forms.get("other")
                if value is not None:
                    new_definition.translations[language] = value

                new_section.definitions.append(new_definition)
                result.definitions_by_key[new_definition.key] = new_definition

            result.sections.append(new_section)

        return result
