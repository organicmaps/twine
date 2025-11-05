"""
Android XML strings formatter.
"""

import re
import html
from typing import Dict, Optional, TextIO
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element

from twine.formatters import AbstractFormatter
from twine.formatters.tools import replace_with_filter
from twine.placeholders import (
    convert_placeholders_from_android_to_twine,
    convert_placeholders_from_twine_to_android,
    number_of_twine_placeholders,
)


def inner_xml(node:Element) -> str:
    # Get inner XML (text + nested elements)
    # Start with the text before any child element
    value = node.text or ""

    # Add each child element's XML and tail
    for subelement in node:
        value += ET.tostring(subelement, encoding="unicode", method="html")
    return value

class AndroidFormatter(AbstractFormatter):
    """Formatter for Android XML string resources."""

    SUPPORTS_PLURAL = True

    # Language code mappings for Android
    ANDROID_TO_TWINE_LANG_CODES = {
        "zh": "zh-Hans",
        "zh-TW": "zh-Hant",
        "zh-CN": "zh-Hans",
        "zh-HK": "zh-Hant",
        # Legacy language codes
        "iw": "he",
        "in": "id",
        "ji": "yi",
    }

    TWINE_TO_ANDROID_LANG_CODES = {
        "zh-Hans": "zh",
        "zh-Hant": "zh-TW",
        "he": "iw",
        "id": "in",
        "yi": "ji",
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
            return any(item.startswith("values") for item in entries)
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
                r"^values-([a-z]{2,3}(-r[a-z]{2,4})?)$", segment, re.IGNORECASE
            )
            if match:
                lang = match.group(1).replace("-r", "-")
                return self.ANDROID_TO_TWINE_LANG_CODES.get(lang, lang)

        return super().determine_language_given_path(path)

    def output_path_for_language(self, lang: str) -> str:
        """Get Android values folder name for language."""
        if self.twine_file.language_codes and lang == self.twine_file.language_codes[0]:
            return "values"
        else:
            lang = self.TWINE_TO_ANDROID_LANG_CODES.get(lang, lang)
            # Convert en-US to values-en-rUS
            result = f"values-{lang}"
            result = re.sub(r"-([A-Z])", r"-r\1", result)
            return result

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
        current_section = None

        for child in root:
            # Handle comments (they have a callable tag function)
            if callable(child.tag):
                content_text = child.text.strip() if child.text else ""
                content_text = re.sub(r"\s+", " ", content_text)
                if content_text:
                    if content_text.startswith("SECTION:"):
                        current_section = content_text[8:].strip()
                    else:
                        comment = content_text

            # Handle string elements
            elif child.tag == "string":
                key = child.get("name")
                if not key:
                    continue

                value = self.unescape_value(inner_xml(child))
                self.set_translation_for_key(key, lang, value, current_section)

                if comment:
                    self.set_comment_for_key(key, comment)
                    comment = None

            # Handle plural strings elements:
            #  <plurals name="bookmarks_places">
            #    <item quantity="one">%d bookmark</item>
            #    <item quantity="other">%d bookmarks</item>
            #  </plurals>
            elif child.tag == "plurals":
                key = child.get("name")
                if not key:
                    continue

                plural_values = {}
                for subelement in child:
                    if subelement.tag == "item":
                        quantity = subelement.get("quantity")
                        if not quantity:
                            continue
                        plural_values[quantity] = self.unescape_value(inner_xml(subelement))

                if plural_values:
                    self.set_translation_for_key_plural(key, lang, plural_values, current_section)

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

    @staticmethod
    def unescape_value(value: str) -> str:
        """ Unescape HTML entities """
        value = html.unescape(value)

        # Unescape Android escapes
        value = value.replace("\\'", "'")
        value = value.replace('\\"', '"')

        # Convert placeholders from Android to Twine
        value = convert_placeholders_from_android_to_twine(value)

        # Unescape @ signs
        value = value.replace("\\@", "@")

        # Unescape \n
        value = value.replace("\n\\n", "\n")

        # Convert \u0020 space escapes
        def replace_spaces(match):
            spaces = match.group(0)
            return " " * (len(spaces) // 6)

        return re.sub(r"(\\u0020)+", replace_spaces, value)

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

        # Escape double quotes (unless in CDATA or opening tag)
        result = replace_with_filter(value, '"', '\\"',
            lambda i: not (inside_cdata(value, i) or inside_opening_tag(value, i))
        )

        # Escape single quotes (unless in CDATA)
        result = replace_with_filter(result, "'", "\\'",
            lambda i: not inside_cdata(result, i)
        )

        # Escape ampersands (unless in CDATA or opening tag)
        result = replace_with_filter(result, "&", "&amp;",
            lambda i: not (inside_cdata(result, i) or inside_opening_tag(result, i))
        )

        # Escape angle brackets based on placeholder presence
        has_placeholders = number_of_twine_placeholders(value) > 0

        if has_placeholders or self.options.get("escape_all_tags"):
            # Escape all < except <![CDATA
            angle_bracket_regex = re.compile(r"<(?!(\/?(\!\[CDATA)))")
        else:
            # Escape < except supported tags
            angle_bracket_regex = re.compile(
                r"<(?!(\/?(b|em|i|cite|dfn|big|small|font|tt|s|strike|del|u|super|sub|ul|li|br|div|span|p|a|\!\[CDATA))\b)"
            )

        def is_non_tag(result:str, i:int):
            if inside_cdata(result, i):
                return False
            # Check if this '<' isn't a known tag
            remaining = result[i:]
            return angle_bracket_regex.match(remaining) #is not None

        result = replace_with_filter(result, "<", "&lt;",
            lambda i: is_non_tag(result, i)
        )

        # Escape newlines (unless in CDATA)
        result = replace_with_filter(result, "\\n", "\n\\n",
            lambda i: not inside_cdata(result, i)
        )

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
