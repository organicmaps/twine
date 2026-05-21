"""
Qt ID-based TS formatter (Qt Linguist source format).

Emits files consumed by `lrelease` to produce .qm bundles, looked up at
runtime via `qtTrId(id, n)`. Uses an empty <name></name> context — required
by qtTrId for ID-based lookup. Supports numerus (plural) messages by
mapping Twine's CLDR-named plural categories to Qt's positional
<numerusform> entries via the table in qt_plural_rules.py.
"""

import html
import re
from typing import Dict, List, Optional, TextIO
from xml.etree import ElementTree as ET

from twine import TwineError
from twine.formatters import AbstractFormatter
from twine.formatters.qt_plural_rules import get_qt_numerus_forms
from twine.placeholders import PLACEHOLDER_REGEX
from twine.twine_file import TwineDefinition


# A "count-eligible" placeholder consumes a numeric argument: %d, %i, %u,
# %f, %1$d, %02d, etc. Qt's runtime substitutes the count argument from
# qtTrId(id, n) into %n; the first such placeholder in the source becomes
# %n during conversion.
#
# `s` (string) and `@` (Objective-C object) are deliberately omitted: in
# Twine's source format these never represent the plural count argument,
# so they should not be rewritten to %n.
_NUMERIC_TYPES = set("diufFeEgGxXoaA")

# Forms preferred as the source string for a plural definition, in order.
_SOURCE_PLURAL_PREFERENCE = ("other", "one", "few", "many", "two", "zero")


class QtFormatter(AbstractFormatter):
    """Formatter for Qt ID-based .ts localization files."""

    SUPPORTS_PLURAL = True

    def format_name(self) -> str:
        return "qt"

    def extension(self) -> str:
        return ".ts"

    def default_file_name(self) -> str:
        return "omim.ts"

    def output_path_for_language(self, lang: str) -> str:
        return lang

    # ---- read --------------------------------------------------------------

    def read(self, io: TextIO, lang: str):
        """Parse Qt TS into the in-memory TwineFile. Plural messages are
        currently not consumed — Qt's positional numerusforms are lossy to
        round-trip back into CLDR-named categories, and no current pipeline
        feeds Qt TS back to strings.txt."""
        try:
            root = ET.parse(io).getroot()
        except ET.ParseError as e:
            raise TwineError(f"Failed to parse Qt TS: {e}") from e

        for message in root.iter("message"):
            key = message.get("id")
            if not key:
                continue

            translation = message.find("translation")
            if translation is None or translation.find("numerusform") is not None:
                continue

            if translation.text is not None:
                self.set_translation_for_key(key, lang, self._unformat_value(translation.text), section_name=None)

    # ---- write -------------------------------------------------------------

    def format_header(self, lang: str) -> str:
        return f'<?xml version="1.0" encoding="utf-8"?>\n<TS version="2.1" language="{self._escape(lang)}">'

    def format_file(self, lang: str) -> Optional[str]:
        result = super().format_file(lang)
        if result:
            result += "\n</TS>\n"
        return result

    def format_sections(self, twine_file, lang: str) -> str:
        """Emit a single <context> wrapping all messages from every section.
        qtTrId() requires an empty Qt context for ID-based lookup, and one
        context per file matches Qt's TS schema better than multiple empty
        contexts."""
        bodies = []
        for section in twine_file.sections:
            body = self.format_section(section, lang)
            if body:
                bodies.append(body)
        if not bodies:
            return ""
        return "<context>\n<name></name>\n" + "\n".join(bodies) + "\n</context>"

    def format_section(self, section, lang: str) -> Optional[str]:
        definitions = [d for d in section.definitions if self.should_include_definition(d, lang)]
        if not definitions:
            return None
        formatted = [self.format_definition(d, lang) for d in definitions]
        return "\n".join(f for f in formatted if f)

    # ---- non-plural --------------------------------------------------------

    def key_value_pattern(self) -> str:
        return '<message id="%(key)s">%(comment)s\n<source>%(source)s</source>\n<translation>%(value)s</translation>\n</message>'

    def format_key_value(self, definition: TwineDefinition, lang: str) -> Optional[str]:
        value = definition.translation_for_lang(lang)
        if value is None:
            return None
        return self.key_value_pattern() % {
            "key": self._escape(definition.key),
            "comment": self._format_extracomment(definition),
            "source": self._format_source(definition),
            "value": self.format_value(value),
        }

    def _format_extracomment(self, definition: TwineDefinition) -> str:
        """Twine 'comment' → Qt <extracomment> (translator-facing context).
        Empty string when no comment is present so the format pattern keeps
        a clean structure with no blank lines."""
        comment = definition.comment
        if not comment:
            return ""
        return f"\n<extracomment>{self._escape(comment)}</extracomment>"

    def _format_source(self, definition: TwineDefinition) -> str:
        """<source> is the developer-language string with placeholders mapped
        to Qt %1/%2 form. Falls back to the key if no developer translation
        exists. Reads from the original (unprocessed) twine_file since the
        OutputProcessor strips non-target translations from the copy."""
        default_lang = self.twine_file.get_developer_language_code()
        original = self.twine_file.definitions_by_key.get(definition.key, definition)
        value = original.translation_for_lang(default_lang) if default_lang else None
        return self.format_value(value if value is not None else definition.key)

    # ---- plural ------------------------------------------------------------

    def format_plural(self, definition: TwineDefinition, lang: str) -> Optional[str]:
        forms = get_qt_numerus_forms(lang)
        if forms is None:
            raise TwineError(
                f"Qt has no plural rule for language '{lang}' "
                f"(key '{definition.key}'). Add it to qt_plural_rules.py."
            )

        # Always read from the original twine_file — the processed definition
        # only carries target-lang plurals (after the OutputProcessor may have
        # filled the slot from a fallback language). We need both target and
        # developer forms for the per-form fallback chain.
        original = self.twine_file.definitions_by_key.get(definition.key, definition)
        translated = original.plural_translation_for_lang(lang) or {}
        fallback = self._developer_plural_forms(original)

        numerusforms: List[str] = []
        for category in forms:
            raw = self._pick_plural_value(definition.key, lang, category, translated, fallback)
            converted = self._convert_plural_value(raw)
            numerusforms.append(
                f"<numerusform>{self._escape_boundary_spaces(self._escape(converted))}</numerusform>"
            )

        source = self._format_plural_source(definition)
        extracomment = self._format_extracomment(definition)
        return (
            f'<message id="{self._escape(definition.key)}" numerus="yes">{extracomment}\n'
            f'<source>{source}</source>\n'
            f'<translation>\n' + "\n".join(numerusforms) + "\n</translation>\n"
            '</message>'
        )

    def format_plural_keys(self, key: str, plural_hash: Dict[str, str]) -> str:
        # Not used — format_plural() is overridden directly to access the
        # full definition (needed for the developer-language fallback).
        raise NotImplementedError

    def _developer_plural_forms(self, definition: TwineDefinition) -> Dict[str, str]:
        default_lang = self.twine_file.get_developer_language_code()
        if not default_lang:
            return {}
        return definition.plural_translation_for_lang(default_lang) or {}

    def _pick_plural_value(self, key: str, lang: str, category: str,
                            translated: Dict[str, str],
                            fallback: Dict[str, str]) -> str:
        """Per-form fallback chain:
          1. translated[category]
          2. translated['other']
          3. fallback (developer-language) [category]
          4. fallback (developer-language) ['other']
          Fails with a clear error if all four are missing.
        """
        for source in (translated, fallback):
            if category in source:
                return source[category]
            if "other" in source:
                return source["other"]
        raise TwineError(
            f"Cannot resolve plural form '{category}' for key '{key}' in "
            f"language '{lang}': neither translated nor developer-language "
            f"forms contain a usable fallback."
        )

    def _format_plural_source(self, definition: TwineDefinition) -> str:
        """Pick a representative source string for the plural — used by Qt
        Linguist as the displayed source text. Prefer developer-language
        'other', fall back through other CLDR categories, then through any
        other language. Reads from the original twine_file to access dev-lang
        forms."""
        original = self.twine_file.definitions_by_key.get(definition.key, definition)
        candidates = [self._developer_plural_forms(original)]
        candidates.extend(original.plural_translations.values())
        for plural in candidates:
            for category in _SOURCE_PLURAL_PREFERENCE:
                if category in plural:
                    return self._convert_plural_value_for_source(plural[category])
        return self._escape(definition.key)

    def _convert_plural_value_for_source(self, value: str) -> str:
        return self._escape_boundary_spaces(self._escape(self._convert_plural_value(value)))

    # ---- value formatting --------------------------------------------------

    def format_value(self, value: str) -> str:
        """Non-plural value: sequential %@/%d → %1, %2, …; preserve numbered
        forms; restore real newlines; escape XML and boundary spaces."""
        converted = self._convert_placeholders_sequential(value).replace("\\n", "\n")
        return self._escape_boundary_spaces(self._escape(converted))

    def _convert_plural_value(self, value: str) -> str:
        """Plural value: first count-eligible placeholder becomes %n; the
        rest are numbered sequentially starting from %1."""
        return self._convert_placeholders_plural(value).replace("\\n", "\n")

    @staticmethod
    def _convert_placeholders_sequential(value: str) -> str:
        """Twine/Apple placeholders → Qt positional. `%N$x` is preserved as
        `%N` (already numbered); unnumbered placeholders are assigned
        sequentially from 1."""
        next_index = 1

        def replace(match: re.Match) -> str:
            nonlocal next_index
            placeholder = match.group(0)
            numbered = re.match(r"%(\d+)\$", placeholder)
            if numbered:
                return f"%{numbered.group(1)}"
            result = f"%{next_index}"
            next_index += 1
            return result

        return PLACEHOLDER_REGEX.sub(replace, value)

    @staticmethod
    def _convert_placeholders_plural(value: str) -> str:
        """Like _convert_placeholders_sequential, but the first
        count-eligible placeholder (numeric type) becomes %n."""
        n_assigned = False
        next_index = 1

        def is_count_eligible(placeholder: str) -> bool:
            return placeholder[-1] in _NUMERIC_TYPES

        def replace(match: re.Match) -> str:
            nonlocal n_assigned, next_index
            placeholder = match.group(0)
            numbered = re.match(r"%(\d+)\$", placeholder)

            if not n_assigned and is_count_eligible(placeholder):
                n_assigned = True
                return "%n"

            if numbered:
                return f"%{numbered.group(1)}"
            result = f"%{next_index}"
            next_index += 1
            return result

        return PLACEHOLDER_REGEX.sub(replace, value)

    # ---- escaping / helpers ------------------------------------------------

    @staticmethod
    def _unformat_value(value: str) -> str:
        """Inverse of inserting real newlines: collapse '\\n' back for the
        Twine in-memory representation."""
        return value.replace("\n", "\\n")

    @staticmethod
    def _escape(value: str) -> str:
        return html.escape(value, quote=True)

    @staticmethod
    def _escape_boundary_spaces(value: str) -> str:
        """Qt strips leading/trailing whitespace inside <translation> and
        <numerusform>; replace any boundary whitespace character (space,
        tab, NBSP, …) with its numeric entity per line so it survives
        lrelease."""
        def to_entities(s: str) -> str:
            return "".join(f"&#{ord(c)};" for c in s)

        def escape_line(line: str) -> str:
            if not line:
                return line
            stripped = line.strip()
            if not stripped:
                return to_entities(line)
            leading = len(line) - len(line.lstrip())
            trailing_end = len(line) - (len(line) - len(line.rstrip()))
            return to_entities(line[:leading]) + line[leading:trailing_end] + to_entities(line[trailing_end:])

        return "\n".join(escape_line(line) for line in value.split("\n"))
