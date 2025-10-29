"""
Abstract base formatter for all localization format implementations.
"""

import os
import re
from abc import ABC, abstractmethod
from typing import Optional, Dict, TextIO, List
from pathlib import Path

import twine
from twine.twine_file import TwineFile, TwineDefinition, TwineSection
from twine.output_processor import OutputProcessor

def flatten(input: List[List[str]]) -> List[str]:
    flat = []
    for group in input:
        flat += group
    return flat

class AbstractFormatter(ABC):
    """Base class for all format formatters."""

    SUPPORTS_PLURAL = False
    LANGUAGE_CODE_WITH_OPTIONAL_REGION_CODE = r"[a-z]{2}(?:-[A-Za-z]{2})?"

    def __init__(self):
        self.twine_file = TwineFile()
        self.options: Dict = {}
        self.validation_errors: List[str] = []

    @abstractmethod
    def format_name(self) -> str:
        """Return the format name (e.g., 'android', 'apple')."""
        raise NotImplementedError(
            "You must implement format_name in your formatter class."
        )

    @abstractmethod
    def extension(self) -> str:
        """Return the file extension (e.g., '.xml', '.strings')."""
        raise NotImplementedError(
            "You must implement extension in your formatter class."
        )

    def can_handle_directory(self, path: str) -> bool:
        """Check if this formatter can handle files in the given directory."""
        try:
            entries = os.listdir(path)
            ext = self.extension()
            return any(item.endswith(ext) for item in entries)
        except (OSError, IOError):
            return False

    @abstractmethod
    def default_file_name(self) -> str:
        """Return the default filename for this format."""
        raise NotImplementedError(
            "You must implement default_file_name in your formatter class."
        )

    def set_translation_for_key(self, key: str, lang: str, value: str, section_name:Optional[str]):
        """Set a translation value for a key in a specific language."""
        # Normalize newlines
        value = value.replace("\n", "\\n")

        if key in self.twine_file.definitions_by_key:
            definition = self.twine_file.definitions_by_key[key]
            reference = None

            if definition.reference_key:
                reference = self.twine_file.definitions_by_key.get(
                    definition.reference_key
                )

            # Only set if no reference or value differs from reference
            if not reference or value != reference.translations.get(lang):
                if lang in definition.translations and definition.translations[lang] != value:
                    msg = (f"Translation '{value}' overrides existing translation '{definition.translations[lang]}' "
                           f"for key '{key}' and lang '{lang}' (comment '{definition.comment}').")
                    self.add_validation_error(msg)
                definition.translations[lang] = value
            if "tags" in self.options:
                definition.add_tags(flatten(self.options["tags"]))

        elif self.options.get("consume_all"):
            print(f"Adding new definition '{key}' to twine file.", file=twine.stdout)

            current_section = self.get_section_or_create(section_name or "Uncategorized")

            current_definition = TwineDefinition(key)
            current_section.definitions.append(current_definition)
            if "tags" in self.options:
                current_definition.add_tags(flatten(self.options["tags"]))

            self.twine_file.definitions_by_key[key] = current_definition
            current_definition.translations[lang] = value

        else:
            print(f"WARNING: '{key}' not found in twine file.", file=twine.stdout)

        # Add language code if not present
        if lang not in self.twine_file.language_codes:
            self.twine_file.add_language_code(lang)

    def set_translation_for_key_plural(self, key: str, lang: str, values: Dict[str, str], section_name:Optional[str]):
        """ Set plular values translation for a key in a specific language.
            This method is similar to set_translation_for_key(). Let's keep both
            methods for simplicity.
        """
        # Normalize newlines
        values = {key:val.replace("\n", "\\n") for (key, val) in values.items()}

        if key in self.twine_file.definitions_by_key:
            definition = self.twine_file.definitions_by_key[key]
            reference = None

            if definition.reference_key:
                reference = self.twine_file.definitions_by_key.get(
                    definition.reference_key
                )

            # Only set if no reference or value differs from reference
            if not reference or values != reference.plural_translations.get(lang):
                if lang in definition.plural_translations and definition.plural_translations[lang] != values:
                    msg = (f"Translation '{values}' overrides existing translation '{definition.plural_translations[lang]}' "
                           f"for key '{key}' and lang '{lang}' (comment '{definition.comment}').")
                    self.add_validation_error(msg)
                definition.plural_translations[lang] = values
            if "tags" in self.options:
                definition.add_tags(flatten(self.options["tags"]))

        elif self.options.get("consume_all"):
            print(f"Adding new definition '{key}' to twine file.", file=twine.stdout)

            current_section = self.get_section_or_create(section_name or "Uncategorized")

            current_definition = TwineDefinition(key)
            current_section.definitions.append(current_definition)
            if "tags" in self.options:
                current_definition.add_tags(flatten(self.options["tags"]))

            self.twine_file.definitions_by_key[key] = current_definition
            current_definition.plural_translations[lang] = values

        else:
            print(f"WARNING: '{key}' not found in twine file.", file=twine.stdout)

        # Add language code if not present
        if lang not in self.twine_file.language_codes:
            self.twine_file.add_language_code(lang)

    def get_section(self, section_name) -> Optional[TwineSection]:
        # Find or create a section by name
        return next(
            (s for s in self.twine_file.sections if s.name == section_name), None
        )

    def get_section_or_create(self, section_name) -> TwineSection:
        section = self.get_section(section_name)

        if not section:
            section = TwineSection(section_name)
            self.twine_file.sections.insert(0, section)

        return section

    def set_comment_for_key(self, key: str, comment: str):
        """Set a comment for a key."""
        if not self.options.get("consume_comments"):
            return

        if key in self.twine_file.definitions_by_key:
            definition = self.twine_file.definitions_by_key[key]
            reference = None

            if definition.reference_key:
                reference = self.twine_file.definitions_by_key.get(
                    definition.reference_key
                )

            # Only set if no reference or comment differs from reference
            if not reference or comment != reference.raw_comment:
                if definition.comment is not None and definition.comment != comment:
                    msg = (f"Translation overrides comment '{definition.comment}' -> '{comment}'. "
                           f"The same key '{key}' has different comments in some translations.")
                    self.add_validation_error(msg)
                definition.comment = comment

    def determine_language_given_path(self, path: str) -> Optional[str]:
        """Determine the language code from a file path."""
        only_language_and_region = re.compile(
            rf"^{self.LANGUAGE_CODE_WITH_OPTIONAL_REGION_CODE}$", re.IGNORECASE
        )

        path_obj = Path(path)
        basename = path_obj.stem

        # Check if basename is a language code
        if only_language_and_region.match(basename):
            return basename

        # Check if basename is in known language codes
        if basename in self.twine_file.language_codes:
            return basename

        # Check path segments in reverse order
        parts = path_obj.parts
        for segment in reversed(parts):
            if only_language_and_region.match(segment):
                return segment

        return None

    def output_path_for_language(self, lang: str) -> str:
        """Return the output path component for a language."""
        return lang

    @abstractmethod
    def read(self, io: TextIO, lang: str):
        """Read and parse a localization file."""
        raise NotImplementedError("You must implement read in your formatter class.")

    def add_validation_error(self, msg: str):
        self.validation_errors.append(msg)

    def reset_validation_errors(self):
        self.validation_errors = []

    def format_file(self, lang: str) -> Optional[str]:
        """Format the complete file for a language."""
        output_processor = OutputProcessor(self.twine_file, self.options)
        processed_twine_file = output_processor.process(lang)

        if not processed_twine_file.definitions_by_key:
            return None

        result = ""
        header = self.format_header(lang)
        if header:
            result += header + "\n"

        result += self.format_sections(processed_twine_file, lang)
        return result

    def format_header(self, lang: str) -> Optional[str]:
        """Format the file header. Override in subclasses."""
        return None

    def format_sections(self, twine_file: TwineFile, lang: str) -> str:
        """Format all sections."""
        sections = [
            self.format_section(section, lang) for section in twine_file.sections
        ]
        sections = [s for s in sections if s]  # Remove None values
        return "\n".join(sections)

    def format_section_header(self, section: TwineSection) -> Optional[str]:
        """Format a section header. Override in subclasses."""
        return None

    def should_include_definition(self, definition: TwineDefinition, lang: str) -> bool:
        """Check if a definition should be included for a language."""
        return definition.translation_for_lang(lang) is not None

    def format_section(self, section: TwineSection, lang: str) -> Optional[str]:
        """Format a single section."""
        definitions = [
            d for d in section.definitions if self.should_include_definition(d, lang)
        ]

        if not definitions:
            return None

        result = ""

        # Add section header if section has a name
        if section.name:
            section_header = self.format_section_header(section)
            if section_header:
                result += f"\n{section_header}"

        # Format each definition
        formatted_defs = [self.format_definition(d, lang) for d in definitions]
        formatted_defs = [d for d in formatted_defs if d]  # Remove None

        result += "\n" + "\n".join(formatted_defs)

        return result

    def format_definition(
        self, definition: TwineDefinition, lang: str
    ) -> Optional[str]:
        """Format a single definition."""
        parts = []

        # Add comment
        comment = self.format_comment(definition, lang)
        if comment:
            parts.append(comment)

        # Add key-value or plural
        if self.SUPPORTS_PLURAL and definition.is_plural():
            plural = self.format_plural(definition, lang)
            if plural:
                parts.append(plural)
        else:
            kv = self.format_key_value(definition, lang)
            if kv:
                parts.append(kv)

        return "".join(parts) if parts else None

    def format_comment(self, definition: TwineDefinition, lang: str) -> Optional[str]:
        """Format a comment. Override in subclasses."""
        return None

    def format_key_value(self, definition: TwineDefinition, lang: str) -> Optional[str]:
        """Format a key-value pair."""
        value = definition.translation_for_lang(lang)
        if value is None:
            return None

        pattern = self.key_value_pattern()
        return pattern % {
            "key": self.format_key(definition.key),
            "value": self.format_value(value),
        }

    def format_plural(self, definition: TwineDefinition, lang: str) -> Optional[str]:
        """Format plural translations."""
        plural_hash = definition.plural_translation_for_lang(lang)
        if plural_hash:
            return self.format_plural_keys(definition.key, plural_hash)
        return None

    def key_value_pattern(self) -> str:
        """Return the key-value pattern string. Must be overridden."""
        raise NotImplementedError(
            "You must implement key_value_pattern in your formatter class."
        )

    def format_plural_keys(self, key: str, plural_hash: Dict[str, str]) -> str:
        """Format plural keys. Must be overridden if SUPPORTS_PLURAL is True."""
        raise NotImplementedError(
            "You must implement format_plural_keys in your formatter class."
        )

    def format_key(self, key: str) -> str:
        """Format a key. Override to customize."""
        return key

    def format_value(self, value: str) -> str:
        """Format a value. Override to customize."""
        return value

    def escape_quotes(self, text: str) -> str:
        """Escape double quotes in text."""
        return text.replace('"', '\\"')
