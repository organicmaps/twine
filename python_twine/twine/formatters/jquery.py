"""
jQuery-localize JSON formatter.
"""

import json
import re
from typing import Any, Optional, TextIO

from twine.formatters import AbstractFormatter


class JQueryFormatter(AbstractFormatter):
    """Formatter for jQuery-localize JSON files."""

    def format_name(self) -> str:
        return "jquery"

    def extension(self) -> str:
        return ".json"

    def default_file_name(self) -> str:
        return "localize.json"

    def output_path_for_language(self, lang: str) -> str:
        """Return the output path component for a language."""
        return f"{lang}.json"

    def determine_language_given_path(self, path: str) -> Optional[str]:
        """Extract language from filename like strings-en-US.json."""
        from pathlib import Path

        basename = Path(path).name
        match = re.match(r"^.+([a-z]{2}-[A-Z]{2})\.json$", basename)

        if match:
            return match.group(1)

        return super().determine_language_given_path(path)

    def set_translation_for_key_recursive(self, key: str, lang: str, value: Any):
        """Recursively set translations for nested JSON objects."""
        if isinstance(value, dict):
            for key2, value2 in value.items():
                self.set_translation_for_key_recursive(f"{key}.{key2}", lang, value2)
        else:
            self.set_translation_for_key(key, lang, str(value), section_name=None)

    def read(self, io: TextIO, lang: str):
        """Read jQuery-localize JSON file."""
        try:
            data = json.load(io)
        except json.JSONDecodeError as e:
            from twine import TwineError

            raise TwineError(f"Failed to parse JSON: {e}")

        if isinstance(data, dict):
            for key, value in data.items():
                self.set_translation_for_key_recursive(key, lang, value)

    def format_file(self, lang: str) -> Optional[str]:
        """Format file with JSON wrapper."""
        result = super().format_file(lang)
        if result:
            return f"{{\n{result}\n}}\n"
        return None

    def format_sections(self, twine_file, lang: str) -> str:
        """Format sections separated by commas."""
        sections = []

        for section in twine_file.sections:
            formatted = self.format_section(section, lang)
            if formatted:
                sections.append(formatted)

        return ",\n\n".join(sections)

    def format_section_header(self, section) -> Optional[str]:
        """No section headers in JSON."""
        return None

    def format_section(self, section, lang: str) -> Optional[str]:
        """Format section without headers."""
        definitions = [
            d for d in section.definitions if self.should_include_definition(d, lang)
        ]

        if not definitions:
            return None

        formatted_defs = []
        for definition in definitions:
            formatted = self.format_definition(definition, lang)
            if formatted:
                formatted_defs.append(formatted)

        if not formatted_defs:
            return None

        return ",\n".join(formatted_defs)

    def key_value_pattern(self) -> str:
        return '"%(key)s":"%(value)s"'

    def format_key(self, key: str) -> str:
        """Format key by escaping quotes."""
        return self.escape_quotes(key)

    def format_value(self, value: str) -> str:
        """Format value by escaping quotes."""
        return self.escape_quotes(value)
