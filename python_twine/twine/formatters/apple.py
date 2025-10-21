"""
Apple .strings formatter for iOS/macOS localization.
"""

import re
from typing import Optional, TextIO

from twine.formatters import AbstractFormatter
from twine.placeholders import convert_placeholders_from_android_to_twine


class AppleFormatter(AbstractFormatter):
    """Formatter for Apple .strings files."""

    def format_name(self) -> str:
        return "apple"

    def extension(self) -> str:
        return ".strings"

    def can_handle_directory(self, path: str) -> bool:
        """Check if directory contains .lproj folders."""
        import os

        try:
            entries = os.listdir(path)
            return any(item.endswith(".lproj") for item in entries)
        except (OSError, IOError):
            return False

    def default_file_name(self) -> str:
        return "Localizable.strings"

    def determine_language_given_path(self, path: str) -> Optional[str]:
        """Extract language from Apple .lproj path."""
        from pathlib import Path

        path_parts = Path(path).parts

        for segment in path_parts:
            if segment.endswith(".lproj"):
                lang = segment[:-6]
                # Base.lproj is the developer language
                if lang == "Base":
                    return self.options.get("developer_language")
                else:
                    return lang

        return super().determine_language_given_path(path)

    def output_path_for_language(self, lang: str) -> str:
        """Get .lproj folder name for language."""
        return f"{lang}.lproj"

    def read(self, io: TextIO, lang: str):
        """Read Apple .strings file."""
        last_comment = None

        for line in io:
            # Match: key = "value" or "key" = "value"
            # Key may be quoted or unquoted, value is always quoted
            match = re.match(
                r'^\s*((?:"(?:[^"\\]|\\.)+")| (?:[^"\s=]+))\s*=\s*"((?:[^"\\]|\\.)*)"',
                line,
            )

            if match:
                key = match.group(1).strip()
                value = match.group(2)

                # Remove quotes from key if quoted
                if key.startswith('"') and key.endswith('"'):
                    key = key[1:-1]

                # Unescape quotes
                key = key.replace('\\"', '"')
                value = value.replace('\\"', '"')

                self.set_translation_for_key(key, lang, value)

                if last_comment:
                    self.set_comment_for_key(key, last_comment)
                    last_comment = None

            # Match comments: /* comment */
            comment_match = re.match(r"/\* (.*) \*/", line)
            if comment_match:
                last_comment = comment_match.group(1)
            elif not match:  # Reset comment if line doesn't match key=value
                last_comment = None

    def format_file(self, lang: str) -> Optional[str]:
        """Format file with trailing newline."""
        result = super().format_file(lang)
        if result:
            result += "\n"
        return result

    def format_section_header(self, section) -> str:
        """Format section header with asterisks."""
        return f"\n/********** {section.name} **********/\n"

    def key_value_pattern(self) -> str:
        return '"%(key)s" = "%(value)s";'

    def format_comment(self, definition, lang: str) -> Optional[str]:
        """Format comment, escaping */ sequences."""
        if definition.comment:
            # Escape */ to avoid breaking comment
            comment = definition.comment.replace("*/", "* /")
            return f"\n/* {comment} */\n"
        return None

    def format_key(self, key: str) -> str:
        """Format key by escaping quotes."""
        return self.escape_quotes(key)

    def format_value(self, value: str) -> str:
        """Format value, converting Android placeholders if needed."""
        # Convert Android %s back to iOS %@
        value = convert_placeholders_from_android_to_twine(value)
        return self.escape_quotes(value)

    def should_include_definition(self, definition, lang: str) -> bool:
        """Exclude plural definitions from .strings (use .stringsdict instead)."""
        return not definition.is_plural() and super().should_include_definition(
            definition, lang
        )
