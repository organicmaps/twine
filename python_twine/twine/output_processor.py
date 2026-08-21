"""
Output processor for filtering and processing Twine files.
"""

import re

from twine.twine_file import TwineFile, TwineSection


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
        """
        Get fallback languages for a given language.

        Returns a list of fallback languages in priority order:
        1. Specific mapping (e.g., zh-CN -> zh-Hans)
        2. Generic language (e.g., es-MX -> es)
        3. Default language
        """
        fallback_mapping = {
            "zh-CN": "zh-Hans",  # Chinese Simplified
            "zh-TW": "zh-Hant",  # Chinese Traditional
            # 3-letter language codes don't match the regex below, so map explicitly.
            "yue-HK": "yue",  # Cantonese (Hong Kong)
            "yue-MO": "yue",  # Cantonese (Macau)
        }

        fallbacks = []

        # Check specific mapping
        if language in fallback_mapping:
            fallbacks.append(fallback_mapping[language])

        # Regional dialect fallbacks to generic language
        # e.g., 'es-MX' -> 'es'
        match = re.match(r"([a-zA-Z]{2})-[a-zA-Z]+", language)
        if match:
            generic_language = match.group(1)
            fallbacks.append(generic_language)

        # Default language as final fallback
        default = self.default_language()
        if default:
            fallbacks.append(default)

        # Remove duplicates while preserving order
        seen = set()
        result = []
        for lang in fallbacks:
            if lang not in seen:
                seen.add(lang)
                result.append(lang)

        return result

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

        for section in self.twine_file.sections:
            new_section = TwineSection(section.name)

            for definition in section.definitions:
                # Check tag matching
                tags = self.options.get("tags")
                untagged = self.options.get("untagged", False)  # Default to False
                if not definition.matches_tags(tags, untagged):
                    continue

                # Get translation
                value = definition.translation_for_lang(language)

                # Handle include options
                include_option = self.options.get("include")
                if value and include_option == "untranslated":
                    continue

                # Try fallback languages if no translation found
                if value is None and include_option != "translated":
                    value = definition.translation_for_lang(fallbacks)

                # Skip if still no value
                if value is None:
                    continue

                # Create new definition with the translation
                new_definition = definition.copy_lang(language)
                new_definition.translations[language] = value

                # Handle plural translations
                if definition.is_plural():
                    if language not in new_definition.plural_translations \
                            and include_option != "translated":
                        lng = definition.find_plural_lang_fallback(fallbacks)
                        if lng is not None:
                            new_definition.plural_translations[language] = definition.plural_translation_for_lang(lng)

                    # Ensure 'other' key exists for plurals. Skip when no
                    # plural slot exists for the target language (e.g.
                    # include=translated and only a non-plural translation
                    # is present) — the definition falls through to the
                    # non-plural path in the formatter.
                    if language in new_definition.plural_translations \
                            and "other" not in new_definition.plural_translations[language]:
                        new_definition.plural_translations[language]["other"] = value

                new_section.definitions.append(new_definition)
                result.definitions_by_key[new_definition.key] = new_definition

            result.sections.append(new_section)

        return result
