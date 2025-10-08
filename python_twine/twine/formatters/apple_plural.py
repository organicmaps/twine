"""
Apple .stringsdict formatter for plural localization.
"""

import re
from typing import Dict, Optional, TextIO
from xml.etree import ElementTree as ET

from twine.formatters.apple import AppleFormatter
from twine.placeholders import convert_placeholders_from_android_to_twine
from twine.twine_file import TwineDefinition, TwineSection


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
        header = '<?xml version="1.0" encoding="UTF-8"?>\n'
        header += '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        header += '<plist version="1.0">\n<dict>'
        return header

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
        result = f"\t<key>{key}</key>\n"
        result += "\t<dict>\n"
        result += "\t\t<key>NSStringLocalizedFormatKey</key>\n"
        result += "\t\t<string>%#@value@</string>\n"
        result += "\t\t<key>value</key>\n"
        result += "\t\t<dict>\n"
        result += "\t\t\t<key>NSStringFormatSpecTypeKey</key>\n"
        result += "\t\t\t<string>NSStringPluralRuleType</string>\n"
        result += "\t\t\t<key>NSStringFormatValueTypeKey</key>\n"
        result += "\t\t\t<string>d</string>\n"

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
        import twine
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
                if isinstance(prev, ET.Comment):
                    comment_text = prev.text.strip() if prev.text else None
                    break
                elif prev.tag is not None:  # Hit another element
                    break

            # Extract plural hash
            plural_hash = {}

            # Find <key>value</key><dict> inside value_container
            value_dict = None
            value_children = list(value_container)

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
                                    plural_hash[pkey] = pvalue

                    j += 1

            if not plural_hash:
                i += 2
                continue

            # Get or create definition
            definition = self.twine_file.definitions_by_key.get(key_name)

            if not definition:
                if self.options.get("consume_all"):
                    print(
                        f"Adding new plural definition '{key_name}' to twine file.",
                        file=twine.stdout,
                    )

                    # Find or create Uncategorized section
                    current_section = next(
                        (
                            s
                            for s in self.twine_file.sections
                            if s.name == "Uncategorized"
                        ),
                        None,
                    )

                    if not current_section:
                        current_section = TwineSection("Uncategorized")
                        self.twine_file.sections.insert(0, current_section)

                    definition = TwineDefinition(key_name)
                    current_section.definitions.append(definition)
                    self.twine_file.definitions_by_key[key_name] = definition
                else:
                    print(
                        f"WARNING: '{key_name}' not found in twine file (plural).",
                        file=twine.stdout,
                    )
                    i += 2
                    continue

            # Merge plural translations
            if lang not in definition.plural_translations:
                definition.plural_translations[lang] = {}

            definition.plural_translations[lang].update(plural_hash)

            # Set base translation to 'other' if present
            if "other" in plural_hash:
                self.set_translation_for_key(key_name, lang, plural_hash["other"])

            # Set comment if requested
            if comment_text and self.options.get("consume_comments"):
                self.set_comment_for_key(key_name, comment_text)

            # Ensure language code present
            if lang not in self.twine_file.language_codes:
                self.twine_file.add_language_code(lang)

            i += 2

    def should_include_definition(self, definition, lang: str) -> bool:
        """Only include plural definitions."""
        return (
            definition.is_plural()
            and definition.plural_translation_for_lang(lang) is not None
        )
