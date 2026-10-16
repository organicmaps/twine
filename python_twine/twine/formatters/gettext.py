"""
Gettext .po formatter.
"""

import re
from typing import TextIO

from twine import __version__
from twine.formatters import AbstractFormatter

COMMENT_REGEX = re.compile(r'#\.\s*"(.*)"$', re.MULTILINE)
SECTION_REGEX = re.compile(r'# SECTION: (.+)$', re.MULTILINE)
KEY_REGEX = re.compile(r'^[ \t]*msgctxt[ \t]+"((?:[^"\\]|\\.)*)"[ \t]*$', re.MULTILINE)
FLAGS_REGEX = re.compile(r'^#,(.*)$', re.MULTILINE)
VALUE_REGEX = re.compile(
    r'^[ \t]*msgstr[ \t]+("(?:[^"\\]|\\.)*"[ \t]*(?:\n[ \t]*"(?:[^"\\]|\\.)*"[ \t]*)*)',
    re.MULTILINE,
)


class GettextFormatter(AbstractFormatter):
    """Formatter for Gettext .po files."""

    def __init__(self):
        super().__init__()
        self.default_lang = None

    def format_name(self) -> str:
        return "gettext"

    def extension(self) -> str:
        return ".po"

    def default_file_name(self) -> str:
        return "strings.po"

    def read(self, io: TextIO, lang: str):
        """Read Gettext .po file."""

        content = io.read().replace("\r\n", "\n")
        items = re.split(r"\n[ \t]*\n", content)
        current_sections = None

        for item in items:
            if not item.strip() or item.startswith('msgid ""'):
                continue

            key = None
            value = None
            comment = None

            # Extract comment
            comment_match = COMMENT_REGEX.search(item)
            if comment_match:
                comment = comment_match.group(1)

            # Extract section
            section_match = SECTION_REGEX.search(item)
            if section_match:
                current_sections = section_match.group(1)

            # Fuzzy entries need translator approval before they can be used.
            flags = {flag.strip() for line in FLAGS_REGEX.findall(item) for flag in line.split(",")}
            if "fuzzy" in flags:
                continue

            # Extract key (msgctxt)
            key_match = KEY_REGEX.search(item)
            if key_match:
                key = key_match.group(1).replace('\\"', '"')

            # msgid is the source text; msgstr and its continuations are the translation.
            value_match = VALUE_REGEX.search(item)
            if value_match:
                value = "".join(re.findall(r'"((?:[^"\\]|\\.)*)"', value_match.group(1)))
                value = value.replace('\\"', '"')

            # An empty msgstr denotes an untranslated PO entry.
            if key and value:
                self.set_translation_for_key(key, lang, value, current_sections)

                if comment and not comment.startswith("SECTION:"):
                    self.set_comment_for_key(key, comment)

    def format_file(self, lang: str) -> str | None:
        """Format file, tracking default language."""
        self.default_lang = self.options.get("developer_language") or self.twine_file.get_developer_language_code()

        result = super().format_file(lang)
        self.default_lang = None
        return result

    def format_header(self, lang: str) -> str:
        """Generate .po file header."""
        header = 'msgid ""\nmsgstr ""\n'
        header += f'"Language: {lang}\\n"\n'
        header += '"Content-Type: text/plain; charset=UTF-8\\n"\n'
        header += f'"X-Generator: Twine {__version__}\\n"\n'
        return header

    def format_section_header(self, section) -> str:
        """Format section header as comment."""
        return f"# SECTION: {section.name}"

    def should_include_definition(self, definition, lang: str) -> bool:
        """Include only if default language translation exists."""
        if not super().should_include_definition(definition, lang):
            return False

        if self.default_lang:
            original = self.twine_file.definitions_by_key[definition.key]
            return original.translation_for_lang(self.default_lang) is not None

        return True

    def format_comment(self, definition, lang: str) -> str | None:
        """Format comment as translator comment."""
        if definition.comment:
            escaped = self.escape_quotes(definition.comment)
            return f'#. "{escaped}"\n'
        return None

    def format_key_value(self, definition, lang: str) -> str | None:
        """Format key-value with msgctxt, msgid, and msgstr."""
        value = definition.translation_for_lang(lang)
        if value is None:
            return None

        parts = []

        # msgctxt (key)
        parts.append(self.format_key(definition.key))

        # msgid (base translation from default language)
        parts.append(self.format_base_translation(definition))

        # msgstr (translation)
        parts.append(self.format_value(value))

        return "".join(parts)

    def format_key(self, key: str) -> str:
        """Format msgctxt line."""
        escaped = self.escape_quotes(key)
        return f'msgctxt "{escaped}"\n'

    def format_base_translation(self, definition) -> str:
        """Format msgid line with default language translation."""
        if self.default_lang:
            original = self.twine_file.definitions_by_key[definition.key]
            base_value = original.translation_for_lang(self.default_lang)
            escaped = self.escape_quotes(base_value)
            return f'msgid "{escaped}"\n'
        return 'msgid ""\n'

    def format_value(self, value: str) -> str:
        """Format msgstr line."""
        escaped = self.escape_quotes(value)
        return f'msgstr "{escaped}"\n'
