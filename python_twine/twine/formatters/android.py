"""
Android XML strings formatter.
"""

import re
import html
from typing import Dict, Optional, TextIO
from xml.etree import ElementTree as ET

from twine.formatters import AbstractFormatter
from twine.placeholders import (
    convert_placeholders_from_android_to_twine,
    convert_placeholders_from_twine_to_android,
    number_of_twine_placeholders,
)


class AndroidFormatter(AbstractFormatter):
    """Formatter for Android XML string resources."""

    SUPPORTS_PLURAL = True

    # Language code mappings for Android
    LANG_CODES = {
        "zh": "zh-Hans",
        "zh-CN": "zh-Hans",
        "zh-HK": "zh-Hant",
        # Legacy language codes
        "iw": "he",
        "in": "id",
        "ji": "yi",
    }

    def format_name(self) -> str:
        return "android"

    def extension(self) -> str:
        return ".xml"

    def can_handle_directory(self, path: str) -> bool:
        """Check if directory contains Android values folders."""
        import os

        try:
            entries = os.listdir(path)
            return any(re.match(r"^values.*$", item) for item in entries)
        except (OSError, IOError):
            return False

    def default_file_name(self) -> str:
        return "strings.xml"

    def determine_language_given_path(self, path: str) -> Optional[str]:
        """Extract language from Android path like values-es-rMX."""
        from pathlib import Path

        path_parts = Path(path).parts

        for segment in path_parts:
            # Default values folder is developer language
            if segment == "values":
                if self.twine_file.language_codes:
                    return self.twine_file.language_codes[0]
                return None

            # values-{lang} or values-{lang}-r{region}
            match = re.match(
                r"^values-([a-z]{2}(-r[a-z]{2})?)$", segment, re.IGNORECASE
            )
            if match:
                lang = match.group(1).replace("-r", "-")
                return self.LANG_CODES.get(lang, lang)

        return super().determine_language_given_path(path)

    def output_path_for_language(self, lang: str) -> str:
        """Get Android values folder name for language."""
        if self.twine_file.language_codes and lang == self.twine_file.language_codes[0]:
            return "values"
        else:
            # Convert en-US to values-en-rUS
            result = f"values-{lang}"
            result = re.sub(r"-([A-Z])", r"-r\1", result)
            return result

    def set_translation_for_key(self, key: str, lang: str, value: str):
        """Set translation, handling Android-specific unescaping."""
        # Unescape HTML entities
        value = html.unescape(value)

        # Unescape Android escapes
        value = value.replace("\\'", "'")
        value = value.replace('\\"', '"')

        # Convert placeholders from Android to Twine
        value = convert_placeholders_from_android_to_twine(value)

        # Unescape @ signs
        value = value.replace("\\@", "@")

        # Convert \u0020 space escapes
        def replace_spaces(match):
            spaces = match.group(0)
            return " " * (len(spaces) // 6)

        value = re.sub(r"(\\u0020)+", replace_spaces, value)

        super().set_translation_for_key(key, lang, value)

    def read(self, io: TextIO, lang: str):
        """Read Android XML strings file."""
        content = io.read()

        # Parse with comment support
        try:
            parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
            root = ET.fromstring(content, parser)
        except ET.ParseError as e:
            from twine import TwineError

            raise TwineError(f"Failed to parse XML: {e}")

        comment = None

        for child in root:
            # Handle comments (they have a callable tag function)
            if callable(child.tag):
                content_text = child.text.strip() if child.text else ""
                content_text = re.sub(r"\s+", " ", content_text)
                if content_text and not content_text.startswith("SECTION:"):
                    comment = content_text

            # Handle string elements
            elif child.tag == "string":
                key = child.get("name")
                if not key:
                    continue

                # Get inner XML (text + nested elements)
                # Start with the text before any child element
                value = child.text or ""

                # Add each child element's XML and tail
                for subelement in child:
                    value += ET.tostring(subelement, encoding="unicode", method="html")

                # Add tail text if any (text after the last child element)
                # Note: child.tail is text AFTER the element, not inside

                self.set_translation_for_key(key, lang, value)

                if comment:
                    self.set_comment_for_key(key, comment)
                    comment = None

    def format_header(self, lang: str) -> str:
        return '<?xml version="1.0" encoding="utf-8"?>'

    def format_sections(self, twine_file, lang: str) -> str:
        result = "<resources>"

        sections_content = super().format_sections(twine_file, lang)
        if sections_content:
            result += "\n" + sections_content + "\n"

        result += "</resources>\n"
        return result

    def format_section_header(self, section) -> str:
        return f"    <!-- SECTION: {section.name} -->"

    def format_comment(self, definition, lang: str) -> Optional[str]:
        if definition.comment:
            # Replace -- with em dash to avoid XML comment issues
            comment = definition.comment.replace("--", "—")
            return f"    <!-- {comment} -->\n"
        return None

    def key_value_pattern(self) -> str:
        return '    <string name="%(key)s">%(value)s</string>'

    def format_plural_keys(self, key: str, plural_hash: Dict[str, str]) -> str:
        """Format Android plurals."""
        result = f'    <plurals name="{key}">\n'

        items = []
        for quantity, value in plural_hash.items():
            escaped_value = self.escape_value(value)
            items.append(f'        <item quantity="{quantity}">{escaped_value}</item>')

        result += "\n".join(items)
        result += "\n    </plurals>"
        return result

    def escape_value(self, value: str) -> str:
        """
        Escape value for Android XML.

        http://developer.android.com/guide/topics/resources/string-resource.html#FormattingAndStyling
        """

        # Check if inside CDATA or opening tag
        def inside_cdata(text: str, pos: int) -> bool:
            before = text[:pos]
            # Check if we're inside a CDATA that hasn't closed
            return (
                "<![CDATA[" in before
                and "]]>" not in before[before.rfind("<![CDATA[") :]
            )

        def inside_opening_tag(text: str, pos: int) -> bool:
            before = text[:pos]
            # Check if we're inside an opening tag
            match = re.search(r"<(a|font|span|p)\s+[^>]*$", before)
            return match is not None

        # Escape quotes and ampersands
        result = value

        # Escape double quotes (unless in CDATA or opening tag)
        new_result = []
        i = 0
        while i < len(result):
            if result[i] == '"':
                if not (inside_cdata(result, i) or inside_opening_tag(result, i)):
                    new_result.append('\\"')
                else:
                    new_result.append('"')
            else:
                new_result.append(result[i])
            i += 1
        result = "".join(new_result)

        # Escape single quotes (unless in CDATA)
        new_result = []
        i = 0
        while i < len(result):
            if result[i] == "'":
                if not inside_cdata(result, i):
                    new_result.append("\\'")
                else:
                    new_result.append("'")
            else:
                new_result.append(result[i])
            i += 1
        result = "".join(new_result)

        # Escape ampersands (unless in CDATA or opening tag)
        new_result = []
        i = 0
        while i < len(result):
            if result[i] == "&":
                if not (inside_cdata(result, i) or inside_opening_tag(result, i)):
                    new_result.append("&amp;")
                else:
                    new_result.append("&")
            else:
                new_result.append(result[i])
            i += 1
        result = "".join(new_result)

        # Escape angle brackets based on placeholder presence
        has_placeholders = number_of_twine_placeholders(value) > 0

        if has_placeholders or self.options.get("escape_all_tags"):
            # Escape all < except <![CDATA
            angle_bracket_regex = re.compile(r"<(?!(\/?(\!\[CDATA)))")
        else:
            # Escape < except supported tags
            angle_bracket_regex = re.compile(
                r"<(?!(\/?(b|em|i|cite|dfn|big|small|font|tt|s|strike|del|u|super|sub|ul|li|br|div|span|p|a|\!\[CDATA)))"
            )

        new_result = []
        i = 0
        while i < len(result):
            if result[i] == "<":
                if not inside_cdata(result, i):
                    # Check if this < should be escaped
                    remaining = result[i:]
                    if angle_bracket_regex.match(remaining):
                        new_result.append("&lt;")
                    else:
                        new_result.append("<")
                else:
                    new_result.append("<")
            else:
                new_result.append(result[i])
            i += 1
        result = "".join(new_result)

        # Escape newlines (unless in CDATA)
        new_result = []
        i = 0
        while i < len(result):
            if result[i : i + 2] == "\\n":
                if not inside_cdata(result, i):
                    new_result.append("\n\\n")
                    i += 2
                    continue
                else:
                    new_result.append("\\n")
                    i += 2
                    continue
            new_result.append(result[i])
            i += 1
        result = "".join(new_result)

        # Escape @ signs that aren't resource identifiers
        resource_identifier_regex = re.compile(r"@(?!([a-z\.]+:)?[a-z+]+\/[a-zA-Z_]+)")
        result = resource_identifier_regex.sub(r"\\@", result)

        return result

    def format_value(self, value: str) -> str:
        """Format value for Android output."""
        # Convert placeholders
        value = convert_placeholders_from_twine_to_android(value)

        # Handle xliff:g tags
        xliff_tags = []

        def save_xliff(match):
            xliff_tags.append(match.group(0))
            return "TWINE_XLIFF_TAG_PLACEHOLDER"

        value = re.sub(r"<xliff:g.+?</xliff:g>", save_xliff, value)

        # Escape everything outside xliff tags
        value = self.escape_value(value)

        # Restore xliff tags with escaped content
        for xliff_tag in xliff_tags:
            # Escape content inside xliff tags
            escaped_xliff = re.sub(
                r"(<xliff:g.*?>)(.*)(</xliff:g>)",
                lambda m: m.group(1) + self.escape_value(m.group(2)) + m.group(3),
                xliff_tag,
            )
            value = value.replace("TWINE_XLIFF_TAG_PLACEHOLDER", escaped_xliff, 1)

        # Replace beginning and end spaces with \u0020
        value = re.sub(r"^ +| +$", lambda m: "\\u0020" * len(m.group(0)), value)

        return value
