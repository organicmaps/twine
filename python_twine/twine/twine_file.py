"""
Core data models for Twine.
"""

import re
from typing import Dict, List, Optional


class TwineDefinition:
    """Represents a single translatable string definition."""

    PLURAL_KEYS = ["zero", "one", "two", "few", "many", "other"]

    def __init__(self, key: str):
        self.key = key
        self._comment: Optional[str] = None
        self.tags: Optional[List[str]] = None
        self.translations: Dict[str, str] = {}
        self.plural_translations: Dict[str, Dict[str, str]] = {}
        self.reference: Optional["TwineDefinition"] = None
        self.reference_key: Optional[str] = None

    @property
    def comment(self) -> Optional[str]:
        """Get comment, falling back to reference if available."""
        if self._comment:
            return self._comment
        if self.reference:
            return self.reference.comment
        return None

    @comment.setter
    def comment(self, value: Optional[str]):
        self._comment = value

    @property
    def raw_comment(self) -> Optional[str]:
        """Get the raw comment without reference fallback."""
        return self._comment

    def matches_tags(
        self, tags: Optional[List[List[str]]], include_untagged: bool
    ) -> bool:
        """
        Check if definition matches the given tag filters.

        Args:
            tags: List of tag sets, e.g. [['tag1', 'tag2'], ['~tag3']]
                  means (tag1 OR tag2) AND (!tag3)
            include_untagged: Whether to include definitions without tags

        Returns:
            True if the definition matches the tag criteria
        """
        # No tag filter specified - everything passes
        if not tags:
            return True

        # Definition has no tags - check reference or include_untagged
        if self.tags is None:
            if self.reference:
                return self.reference.matches_tags(tags, include_untagged)
            return include_untagged

        if not self.tags:
            return include_untagged

        # Check all tag sets (AND logic between sets)
        for tag_set in tags:
            regular_tags = [t for t in tag_set if not t.startswith("~")]
            negated_tags = [t[1:] for t in tag_set if t.startswith("~")]

            matches_regular = regular_tags and any(t in self.tags for t in regular_tags)
            matches_negated = negated_tags and all(
                t not in self.tags for t in negated_tags
            )

            if not (matches_regular or matches_negated):
                return False

        return True

    def translation_for_lang(self, lang: str | List[str]) -> Optional[str]:
        """
        Get translation for a language, checking reference if not found.

        Args:
            lang: Language code (can be str or list)

        Returns:
            Translation string or None
        """
        # Handle both single lang and list of langs
        if isinstance(lang, list):
            for ln in lang:
                if ln in self.translations:
                    return self.translations[ln]
            lang_to_check = lang
        else:
            if lang in self.translations:
                return self.translations[lang]
            lang_to_check = [lang]

        # Check reference
        if self.reference:
            return self.reference.translation_for_lang(lang_to_check)

        return None

    def plural_translation_for_lang(self, lang: str) -> Optional[Dict[str, str]]:
        """
        Get plural translations for a language, sorted by PLURAL_KEYS order.

        Args:
            lang: Language code

        Returns:
            Ordered dict of plural translations or None
        """
        if lang in self.plural_translations:
            plural_trans = self.plural_translations[lang].copy()
            # Sort by PLURAL_KEYS order
            return dict(
                sorted(
                    plural_trans.items(),
                    key=lambda x: (
                        self.PLURAL_KEYS.index(x[0])
                        if x[0] in self.PLURAL_KEYS
                        else 999
                    ),
                )
            )
        return None

    def is_plural(self) -> bool:
        """Check if this definition has plural translations."""
        return bool(self.plural_translations)


class TwineSection:
    """Represents a section grouping multiple definitions."""

    def __init__(self, name: str):
        self.name = name
        self.definitions: List[TwineDefinition] = []


class TwineFile:
    """Main Twine data file containing sections and definitions."""

    def __init__(self):
        self.sections: List[TwineSection] = []
        self.definitions_by_key: Dict[str, TwineDefinition] = {}
        self.language_codes: List[str] = []

    def add_language_code(self, code: str):
        """Add a language code, maintaining developer language at position 0."""
        if not self.language_codes:
            self.language_codes.append(code)
        elif code not in self.language_codes:
            if len(self.language_codes) == 1:
                # Just append `code`
                self.language_codes.append(code)
            else:
                # Append `code` and sort languages from index 1
                self.language_codes = [self.language_codes[0]] + sorted(self.language_codes[1:] + [code])

    def set_developer_language_code(self, code: str):
        """Set the developer language (moves it to position 0)."""
        if code in self.language_codes:
            self.language_codes.remove(code)
        self.language_codes.insert(0, code)

    def read(self, path: str):
        """
        Read and parse a Twine file.

        Args:
            path: Path to the Twine file

        Raises:
            TwineError: If file doesn't exist or parsing fails
        """
        from pathlib import Path
        from twine import TwineError

        file_path = Path(path)
        if not file_path.is_file():
            raise TwineError(f"File does not exist: {path}")

        current_section: Optional[TwineSection] = None
        current_definition: Optional[TwineDefinition] = None

        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip empty lines
                if not line:
                    continue

                parsed = False

                # Section header [[Section Name]]
                if len(line) > 4 and line.startswith("[["):
                    if line.endswith(']]'):
                        current_section = TwineSection(line[2:-2])
                        self.sections.append(current_section)
                        parsed = True

                # Definition key [key]
                elif len(line) > 2 and line.startswith("["):
                    if line.endswith(']'):
                        key = line[1:-1]
                        current_definition = TwineDefinition(key)
                        self.definitions_by_key[key] = current_definition

                        if not current_section:
                            current_section = TwineSection("")
                            self.sections.append(current_section)

                        current_section.definitions.append(current_definition)
                        parsed = True

                # Key-value pairs
                else:
                    match = re.match(r"^([^:=]+)(?::([^=]+))?=(.*)$", line)
                    if match and current_definition:
                        key = match.group(1).strip()
                        plural_key = (match.group(2) or "").strip()
                        value = match.group(3).strip()

                        # Remove backtick wrapping
                        if value.startswith("`") and value.endswith("`"):
                            value = value[1:-1]

                        if key == "comment":
                            current_definition.comment = value
                        elif key == "tags":
                            current_definition.tags = value.split(",")
                        elif key == "ref":
                            current_definition.reference_key = value
                        else:
                            # Language translation
                            if key not in self.language_codes:
                                self.add_language_code(key)

                            # Backward compatibility for non-plural or 'other'
                            if not plural_key or plural_key == "other":
                                current_definition.translations[key] = value

                            # Plural translations
                            if plural_key:
                                if plural_key not in TwineDefinition.PLURAL_KEYS:
                                    import twine

                                    print(
                                        f"Warning: Unknown plural key {plural_key}",
                                        file=twine.stderr,
                                    )
                                    continue

                                if key not in current_definition.plural_translations:
                                    current_definition.plural_translations[key] = {}
                                current_definition.plural_translations[key][
                                    plural_key
                                ] = value

                        parsed = True

                if not parsed:
                    from twine import TwineError

                    raise TwineError(
                        f"Unable to parse line {line_num} of {path}: {line}"
                    )

        # Resolve references
        for key, definition in self.definitions_by_key.items():
            if definition.reference_key:
                definition.reference = self.definitions_by_key.get(
                    definition.reference_key
                )

    def write(self, path: str):
        """
        Write the Twine file to disk.

        Args:
            path: Output path for the Twine file
        """
        import twine

        dev_lang = self.language_codes[0] if self.language_codes else None

        with open(path, "w", encoding="utf-8") as f:
            for section in self.sections:
                if f.tell() > 0:
                    f.write("\n")

                f.write(f"[[{section.name}]]\n")

                for definition in section.definitions:
                    f.write(f"\t[{definition.key}]\n")

                    # Write comment
                    if definition.raw_comment:
                        f.write(f"\t\tcomment = {definition.raw_comment}\n")

                    # Write reference
                    if definition.reference_key:
                        f.write(f"\t\tref = {definition.reference_key}\n")

                    # Write tags
                    if definition.tags:
                        tag_str = ",".join(definition.tags)
                        f.write(f"\t\ttags = {tag_str}\n")

                    # Write developer language first
                    if dev_lang:
                        value = self._write_value(definition, dev_lang, f)
                        if not value and not definition.reference_key:
                            print(
                                f"WARNING: {definition.key} does not exist in "
                                f"developer language '{dev_lang}'",
                                file=twine.stdout,
                            )

                    # Write other languages
                    for lang in self.language_codes[1:]:
                        self._write_value(definition, lang, f)

    def _write_value(
        self, definition: TwineDefinition, language: str, file
    ) -> Optional[str]:
        """Write a single translation value to file."""
        value = definition.translations.get(language)
        if not value:
            return None

        # Wrap in backticks if starts/ends with space or already has backticks
        if (
            value.startswith(" ")
            or value.endswith(" ")
            or (value.startswith("`") and value.endswith("`"))
        ):
            value = f"`{value}`"

        file.write(f"\t\t{language} = {value}\n")
        return value
