"""
Core data models for Twine.
"""

import re
from typing import Any

from twine import TwineError
from twine.languages import fallback_languages


class TwineDefinition:
    """Represents a single translatable string definition."""

    PLURAL_KEYS = ("zero", "one", "two", "few", "many", "other")

    def __init__(self, key: str):
        self.key = key
        self._comment: str | None = None
        self.tags: list[str] | None = None
        self.translations: dict[str, str] = {}
        self.plural_translations: dict[str, dict[str, str]] = {}
        self.reference: TwineDefinition | None = None
        self.reference_key: str | None = None

    @property
    def comment(self) -> str | None:
        """Get comment, falling back to reference if available."""
        if self._comment:
            return self._comment
        if self.reference:
            return self.reference.comment
        return None

    @comment.setter
    def comment(self, value: str | None):
        self._comment = value

    @property
    def raw_comment(self) -> str | None:
        """Get the raw comment without reference fallback."""
        return self._comment

    def add_tags(self, tags: list[str]):
        if self.tags:
            self.tags += tags
        else:
            self.tags = tags
        self.tags = sorted(set(self.tags)) # Remove duplicates and sort

    def matches_tags(
        self, tags: list[list[str]] | None, include_untagged: bool
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

    def translation_for_lang(self, lang: str | list[str]) -> str | None:
        """Resolve languages in priority order, including inherited translations."""
        if isinstance(lang, list):
            for language in lang:
                translation = self.translation_for_lang(language)
                if translation is not None:
                    return translation
            return None

        if lang in self.translations:
            return self.translations[lang]
        if self.reference:
            return self.reference.translation_for_lang(lang)
        return None

    def plural_translation_for_lang(self, lang: str) -> dict[str, str] | None:
        """
        Get plural translations for a language, sorted by PLURAL_KEYS order.

        Args:
            lang: Language code

        Returns:
            Ordered dict of plural translations or None
        """
        if lang in self.plural_translations:
            plural_trans = self.plural_translations[lang]
            # Sort by PLURAL_KEYS order
            return dict(
                sorted(
                    plural_trans.items(),
                    key=lambda x: self.PLURAL_KEYS.index(x[0]),
                )
            )
        # An explicit singular value overrides plural forms from a reference.
        if lang not in self.translations and self.reference is not None:
            return self.reference.plural_translation_for_lang(lang)
        return None

    def is_plural(self) -> bool:
        """Check whether this definition or its reference supplies plural forms."""
        return bool(self.plural_translations) or (
            self.reference is not None and self.reference.is_plural()
        )
class TwineSection:
    """Represents a section grouping multiple definitions."""

    def __init__(self, name: str):
        self.name = name
        self.definitions: list[TwineDefinition] = []


class TwineFile:
    """Main Twine data file containing sections and definitions."""

    def __init__(self, fallback_to_default: bool = False):
        """Control whether deduplication also compares with the developer language."""
        self.sections: list[TwineSection] = []
        self.definitions_by_key: dict[str, TwineDefinition] = {}
        self.language_codes: list[str] = []
        self.fallback_to_default = fallback_to_default

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

    def get_developer_language_code(self) -> str | None:
        if self.language_codes:
            return self.language_codes[0]
        return None

    def optimize_duplicates(self):
        """Remove translations only when their effective fallback is identical."""
        referenced = {
            definition.reference for definition in self.definitions_by_key.values()
            if definition.reference is not None
        }
        developer_language = self.get_developer_language_code()
        for key, definition in self.definitions_by_key.items():
            # Apply deletions one at a time so subsequent comparisons see the
            # translations that will actually remain available.
            for lang, value in list(definition.translations.items()):
                forms = definition.plural_translation_for_lang(lang)
                inherited = (
                    definition.reference.translation_for_lang(lang)
                    if definition.reference is not None else None
                )
                if inherited is not None:
                    # Equal text can still be a singular override of inherited plurals.
                    if inherited == value and forms == definition.reference.plural_translation_for_lang(lang):
                        del definition.translations[lang]
                    continue

                # Aliases inherit exact-language values, without regional
                # fallback. The developer language is also a terminal fallback.
                if definition in referenced or lang == developer_language:
                    continue
                for fallback_lang in self.fallback_languages(lang, self.fallback_to_default):
                    fallback = definition.translation_for_lang(fallback_lang)
                    fallback_forms = definition.plural_translation_for_lang(fallback_lang)
                    if fallback is None and fallback_forms is None:
                        continue
                    if fallback == value and forms == fallback_forms:
                        print(f"Warning: key '{key}' in lang '{lang}' matches its fallback translation")
                        del definition.translations[lang]
                    break

            definition.plural_translations = {lang:value for (lang, value) in definition.plural_translations.items() \
                                              if not self.match_fallback_lang(definition.plural_translations, lang, key, value)}

    def match_fallback_lang(self, translations: dict, lang:str, key:str, value: Any) -> bool:
        # TODO: this method is invoked for each key and lang. Optimize: cache all fallback languages in a dict
        for fallback_lang in self.fallback_languages(lang, self.fallback_to_default):
            if translations.get(fallback_lang) == value:
                if isinstance(value, str):
                    definition = self.definitions_by_key[key]
                    if definition.plural_translation_for_lang(lang) != definition.plural_translation_for_lang(fallback_lang):
                        continue
                print(f"Warning: key '{key}' in lang '{lang}' matches value from fallback language '{fallback_lang}'")
                return True
        return False

    def fallback_languages(self, language: str, include_default:bool = False) -> list[str]:
        default = self.get_developer_language_code() if include_default else None
        return fallback_languages(language, default)

    def read(self, path: str):
        """
        Read and parse a Twine file.

        Args:
            path: Path to the Twine file

        Raises:
            TwineError: If the file is missing, malformed, or has invalid references.
        """
        from pathlib import Path

        file_path = Path(path)
        if not file_path.is_file():
            raise TwineError(f"File does not exist: {path}")

        current_section: TwineSection | None = None
        current_definition: TwineDefinition | None = None

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
                                    raise TwineError(
                                        f"Unknown plural key '{plural_key}' at line {line_num} of {path}"
                                    )

                                if key not in current_definition.plural_translations:
                                    current_definition.plural_translations[key] = {}
                                current_definition.plural_translations[key][
                                    plural_key
                                ] = value

                        parsed = True

                if not parsed:
                    raise TwineError(
                        f"Unable to parse line {line_num} of {path}: {line}"
                    )

        # Resolve references
        for key, definition in self.definitions_by_key.items():
            if definition.reference_key:
                try:
                    definition.reference = self.definitions_by_key[definition.reference_key]
                except KeyError:
                    raise TwineError(
                        f"Unknown reference '{definition.reference_key}' in [{key}]"
                    ) from None
        self.validate_references()

    def validate_references(self):
        """Reject dangling references and cycles before inherited lookups run."""
        finished = set()
        for definition in self.definitions_by_key.values():
            current = definition
            path = set()
            while current is not None and current not in finished:
                if current in path:
                    raise TwineError(f"Circular reference at [{current.key}]")
                if current.reference_key is not None and current.reference is None:
                    raise TwineError(
                        f"Unknown reference '{current.reference_key}' in [{current.key}]"
                    )
                path.add(current)
                current = current.reference
            finished.update(path)

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
                    f.write(f"\n[{definition.key}]\n")

                    # Write comment
                    if definition.raw_comment:
                        f.write(f"comment = {definition.raw_comment}\n")

                    # Write reference
                    if definition.reference_key:
                        f.write(f"ref = {definition.reference_key}\n")

                    # Write tags
                    if definition.tags:
                        tag_str = ",".join(definition.tags)
                        f.write(f"tags = {tag_str}\n")

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
    ) -> str | None:
        """Write a single translation value to file."""
        output = None
        if language in definition.plural_translations:
            # Write plurals:
            #   ru:one = %d метка
            #   ru:few = %d метки
            #   ru:many = %d меток
            #   ru:other = %d меток
            output = ""
            for quantity, value in definition.plural_translation_for_lang(language).items():
                output += f"{language}:{quantity} = {escape_spaces_backticks(value)}\n"

        elif language in definition.translations:
            singular_value = definition.translations[language]
            # Write singular
            output = f"{language} = {escape_spaces_backticks(singular_value)}\n"

        if output:
            file.write(output)
        return output


def escape_spaces_backticks(txt: str) -> str:
    # Wrap in backticks if starts/ends with space or already has backticks
    if (
        txt.startswith(" ")
        or txt.endswith(" ")
        or (txt.startswith("`") and txt.endswith("`"))
    ):
        return f"`{txt}`"
    return txt
