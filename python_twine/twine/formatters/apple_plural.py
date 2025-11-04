"""
Apple .stringsdict formatter for plural localization.
"""

from typing import Dict, Optional, TextIO
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element

from twine.formatters.apple import AppleFormatter
from twine.placeholders import convert_placeholders_from_android_to_twine
from twine.twine_file import TwineDefinition


class ApplePluralFormatter(AppleFormatter):
    """Formatter for Apple .stringsdict plural files."""

    SUPPORTS_PLURAL = True

    def format_name(self) -> str:
        return "apple-plural"

    def extension(self) -> str:
        return ".stringsdict"

    def default_file_name(self) -> str:
        return "Localizable.stringsdict"

    def format_header(self, lang: str) -> str:
        """Generate plist XML header."""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>'''

    def format_footer(self, lang: str) -> str:
        """Generate plist XML footer."""
        return "</dict>\n</plist>"

    def format_file(self, lang: str) -> Optional[str]:
        """Format file with plist footer."""
        result = super().format_file(lang)
        if result:
            result += self.format_footer(lang)
        return result

    def format_section_header(self, section) -> str:
        """Format section header as XML comment."""
        return f"<!-- ********** {section.name} **********/ -->\n"

    def format_comment(self, definition, lang: str) -> Optional[str]:
        """Format comment as XML comment."""
        if definition.comment:
            # Replace -- with em dash for XML compatibility
            comment = definition.comment.replace("--", "—")
            return f"<!-- {comment} -->\n"
        return None

    def format_plural_keys(self, key: str, plural_hash: Dict[str, str]) -> str:
        """Format plural entries in stringsdict format."""
        result = f"""\t<key>{key}</key>
\t<dict>
\t\t<key>NSStringLocalizedFormatKey</key>
\t\t<string>%#@value@</string>
\t\t<key>value</key>
\t\t<dict>
\t\t\t<key>NSStringFormatSpecTypeKey</key>
\t\t\t<string>NSStringPluralRuleType</string>
\t\t\t<key>NSStringFormatValueTypeKey</key>
\t\t\t<string>d</string>
"""

        # Add plural entries
        for quantity, value in plural_hash.items():
            # Convert Android placeholders to iOS
            converted_value = convert_placeholders_from_android_to_twine(value)
            result += f"\t\t\t<key>{quantity}</key>\n"
            result += f"\t\t\t<string>{converted_value}</string>\n"

        result += "\t\t</dict>\n"
        result += "\t</dict>\n"

        return result

    def read(self, io: TextIO, lang: str):
        """Read Apple .stringsdict file."""
        from twine import TwineError

        content = io.read()

        try:
            root = ET.fromstring(content)
        except ET.ParseError as e:
            raise TwineError(f"Unable to parse .stringsdict file: {e}")

        # Find root dict
        root_dict = root.find("dict")
        if root_dict is None:
            return

        # Process each key-dict pair
        children = list(root_dict)
        i = 0

        while i < len(children):
            node = children[i]

            # Look for <key> elements
            if node.tag != "key":
                i += 1
                continue

            key_name = node.text
            if not key_name:
                i += 1
                continue

            # Next element should be dict
            if i + 1 >= len(children):
                i += 1
                continue

            value_container = children[i + 1]
            if value_container.tag != "dict":
                i += 1
                continue

            # Look for comment before this key
            comment_text = None
            for j in range(i - 1, -1, -1):
                prev = children[j]
                # Handle comments (they have a callable tag function)
                if callable(prev.tag):
                    comment_text = prev.text.strip() if prev.text else None
                    break
                elif prev.tag is not None:  # Hit another element
                    break

            # Extract plural hash
            plural_hash = self.extract_plural_dict(value_container)

            if not plural_hash:
                i += 2
                continue

            # Get or create definition
            if not self.match_default_lang_translation(key_name, lang, plural_hash):
                self.set_translation_for_key_plural(key_name, lang, plural_hash, section_name=None)

                # Set base translation to 'other' if present
                if "other" in plural_hash:
                    self.set_translation_for_key(key_name, lang, plural_hash["other"], section_name=None)

            # Set comment if requested
            if comment_text and self.options.get("consume_comments"):
                self.set_comment_for_key(key_name, comment_text)

            # Ensure language code present
            if lang not in self.twine_file.language_codes:
                self.twine_file.add_language_code(lang)

            i += 2

    def extract_plural_dict(self, value_element: Element) -> dict:
        """ Parse next XML structure to extract key-value pairs:
        	<dict>
                <key>NSStringLocalizedFormatKey</key>
                <string>%#@value@</string>
                <key>value</key>
                <dict>
                    <key>NSStringFormatSpecTypeKey</key>
                    <string>NSStringPluralRuleType</string>
                    <key>NSStringFormatValueTypeKey</key>
                    <string>d</string>
                    <key>one</key>
                    <string>%d bookmark</string>
                    <key>other</key>
                    <string>%d bookmarks</string>
                </dict>
            </dict>
        """
        plural_dict = {}

        # Find <key>value</key><dict> inside value_element
        value_dict = None
        value_children = list(value_element)

        for j, inner_key in enumerate(value_children):
            if inner_key.tag == "key" and inner_key.text == "value":
                if j + 1 < len(value_children):
                    value_dict = value_children[j + 1]
                    break

        if value_dict is not None and value_dict.tag == "dict":
            # Extract plural entries
            plural_children = list(value_dict)
            j = 0

            while j < len(plural_children):
                pkey_elem = plural_children[j]

                if pkey_elem.tag == "key":
                    pkey = pkey_elem.text

                    if pkey in TwineDefinition.PLURAL_KEYS:
                        if j + 1 < len(plural_children):
                            string_elem = plural_children[j + 1]

                            if string_elem.tag == "string":
                                pvalue = string_elem.text or ""
                                plural_dict[pkey] = pvalue

                j += 1
        return plural_dict

    def should_include_definition(self, definition, lang: str) -> bool:
        """Only include plural definitions."""
        return (
            definition.is_plural()
            and definition.plural_translation_for_lang(lang) is not None
        )

    def match_default_lang_translation(self, key:str, lang:str, value:dict) -> bool:
        """ Apple strings file for non-default language (es, de, fr, etc) contains
            default value for not translated keys. That's why in Slovenian .strings
            file you can find english words.
            If `value` matches translation from default language, it means that
            this string is not translated.
        """
        default_lang = self.twine_file.get_developer_language_code()
        if default_lang is None:
            return False
        if default_lang == lang:
            return False
        return self.twine_file.definitions_by_key[key].plural_translations[default_lang] == value
