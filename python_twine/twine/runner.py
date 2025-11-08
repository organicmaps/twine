"""
Runner orchestrates command execution for Twine.
"""

from pathlib import Path
from typing import Optional, Dict, Any, Iterable, Tuple

import twine
from twine.formatters import AbstractFormatter
from twine.twine_file import TwineFile
from twine import TwineError


class NullOutput:
    """Output sink that discards all messages."""

    def write(self, message: str):
        pass

    def flush(self):
        pass


class Runner:
    """Executes Twine commands."""

    def __init__(
        self,
        options: Optional[Dict[str, Any]] = None,
        twine_file: Optional[TwineFile] = None,
    ):
        self.options = options or {}
        self.twine_file = twine_file or TwineFile()

        # Handle quiet mode
        if self.options.get("quiet"):
            twine.stdout = NullOutput()

    def run(self):
        """Execute the command specified in options."""
        command = self.options.get("command")

        if not command:
            raise TwineError("No command specified")

        # Load Twine file for most commands
        if command != "help":
            twine_file_path = self.options.get("twine_file")
            if twine_file_path:
                self.twine_file.read(twine_file_path)
                if self.options.get("developer_language"):
                    self.twine_file.set_developer_language_code(self.options.get("developer_language"))

        # Dispatch to appropriate method
        method_name = command.replace("-", "_")
        method = getattr(self, method_name, None)

        if method:
            return method()
        else:
            raise TwineError(f"Unknown command: {command}")

    def write_twine_data(self, path: str):
        """Write Twine data to file."""
        if self.options.get("developer_language"):
            self.twine_file.set_developer_language_code(
                self.options["developer_language"]
            )
        self.twine_file.write(path)

    def generate_localization_file(self):
        """Generate a single localization file."""
        if self.options.get("validate"):
            self.validate_twine_file()

        lang = None
        if self.options.get("languages"):
            lang = self.options["languages"][0]

        formatter, lang = self._prepare_read_write(self.options["output_path"], lang)

        output = formatter.format_file(lang)

        if not output:
            raise TwineError(
                "Nothing to generate! The resulting file would not contain any translations."
            )

        encoding = self.options.get("encoding", "UTF-8")
        with open(self.options["output_path"], "w", encoding=encoding) as f:
            f.write(output)

        print(f"Generated {self.options['output_path']}", file=twine.stdout)

    def generate_all_localization_files(self):
        """Generate localization files for all languages."""
        if self.options.get("validate"):
            self.validate_twine_file()

        output_path = Path(self.options["output_path"])

        # Create output directory if needed
        if not output_path.is_dir():
            if self.options.get("create_folders"):
                output_path.mkdir(parents=True, exist_ok=True)
            else:
                raise TwineError(f"Directory does not exist: {output_path}")

        # Determine formatter
        formatter = self._get_formatter()

        file_name = self.options.get("file_name") or formatter.default_file_name()
        encoding = self.options.get("encoding", "UTF-8")

        if self.options.get("create_folders"):
            # Create folders for all languages
            for lang in self.twine_file.language_codes:
                lang_path = output_path / formatter.output_path_for_language(lang)
                lang_path.mkdir(parents=True, exist_ok=True)

                file_path = lang_path / file_name
                output = formatter.format_file(lang)

                if not output:
                    print(
                        f"Skipping {file_path} since it would not contain any translations.",
                        file=twine.stdout,
                    )
                    continue

                with open(file_path, "w", encoding=encoding) as f:
                    f.write(output)

                print(f"Generated {file_path}", file=twine.stdout)
        else:
            # Find existing language directories
            language_found = False

            for item in output_path.iterdir():
                if not item.is_dir():
                    continue

                lang = formatter.determine_language_given_path(str(item))
                if not lang:
                    continue

                language_found = True

                file_path = item / file_name
                output = formatter.format_file(lang)

                if not output:
                    print(
                        f"Skipping {file_path} since it would not contain any translations.",
                        file=twine.stdout,
                    )
                    continue

                with open(file_path, "w", encoding=encoding) as f:
                    f.write(output)

                print(f"Generated {file_path}", file=twine.stdout)

            if not language_found:
                raise TwineError(
                    f"Failed to generate any files: No languages found at {output_path}"
                )

    def consume_localization_file(self):
        """Import translations from a localization file."""
        lang = None
        if self.options.get("languages"):
            lang = self.options["languages"][0]

        if bool(self.options.get("fallback_to_default")):
            self.twine_file.fallback_to_default = True

        formatter, lang = self._prepare_read_write(self.options["input_path"], lang)

        with open(self.options["input_path"], "r", encoding="UTF-8") as f:
            formatter.read(f, lang)

        self.write_twine_data(self.options["twine_file"])
        print(f"Consumed {self.options['input_path']}", file=twine.stdout)

        if formatter.validation_errors:
            for msg in formatter.validation_errors:
                print(f"  WARNING: {msg}")

    def consume_all_localization_files(self):
        """Import translations from all localization files."""
        input_path = Path(self.options["input_path"])

        if not input_path.is_dir():
            raise TwineError(f"Directory does not exist: {input_path}")

        if bool(self.options.get("fallback_to_default")):
            self.twine_file.fallback_to_default = True

        formatter = self._get_formatter()

        files_consumed = 0
        validation_errors = {}

        lang2file = dict(self.find_translation_files(input_path, formatter))

        # Parse developer_language file first (if it's available).
        if self.options.get("developer_language"):
            default_lang = self.options.get("developer_language")
            if default_lang in lang2file:
                # First parse default language file.
                # Apple .strings file for not-translated keys fallbacks to default value.
                # We need to compare translations values to default values.
                default_lang_path = lang2file[default_lang]
                with open(default_lang_path, "r", encoding="UTF-8") as f:
                    formatter.read(f, default_lang)

                print(f"Consumed {default_lang_path}", file=twine.stdout)
                if formatter.validation_errors:
                    validation_errors[default_lang_path] = formatter.validation_errors
                    for msg in formatter.validation_errors:
                        print(f"  WARNING: {msg}")
                formatter.reset_validation_errors()
                files_consumed += 1

                del lang2file[default_lang]

        # Parse all files.
        for lang, file_path in lang2file.items():
            with open(file_path, "r", encoding="UTF-8") as f:
                formatter.read(f, lang)

            print(f"Consumed {file_path}", file=twine.stdout)
            if formatter.validation_errors:
                validation_errors[file_path] = formatter.validation_errors
                for msg in formatter.validation_errors:
                    print(f"  WARNING: {msg}")
            formatter.reset_validation_errors()
            files_consumed += 1

        if files_consumed == 0:
            raise TwineError(f"No files consumed from {input_path}")

        # Export to Twine.
        self.twine_file.optimize_duplicates()
        self.write_twine_data(self.options["twine_file"])

    def find_translation_files(self, input_path: Path, formatter: AbstractFormatter) -> Iterable[Tuple[str, Path]]:
        """ Iterate over files in `input_path` to find consumable by the formatter. """
        file_name = self.options.get("file_name") or formatter.default_file_name()

        for item in input_path.iterdir():
            if not item.is_dir():
                continue

            lang = formatter.determine_language_given_path(str(item))
            if not lang:
                continue

            file_path = item / file_name
            if not file_path.exists():
                continue
            yield lang, file_path

    def validate_twine_file(self):
        """Validate the Twine data file."""
        import re
        from twine.placeholders import contains_python_specific_placeholder

        total_definitions = 0
        all_keys = set()
        duplicate_keys = set()
        keys_without_tags = set()
        invalid_keys = set()
        keys_with_python_only_placeholders = set()
        valid_key_regex = re.compile(r"^[A-Za-z0-9_.]+$")  # Allow dots for nested keys

        for section in self.twine_file.sections:
            for definition in section.definitions:
                total_definitions += 1

                # Check for duplicates
                if definition.key in all_keys:
                    duplicate_keys.add(definition.key)
                all_keys.add(definition.key)

                # Check for missing tags
                if not definition.tags or len(definition.tags) == 0:
                    keys_without_tags.add(definition.key)

                # Check for invalid characters
                if not valid_key_regex.match(definition.key):
                    invalid_keys.add(definition.key)

                # Check for Python-specific placeholders
                for value in definition.translations.values():
                    if contains_python_specific_placeholder(value):
                        keys_with_python_only_placeholders.add(definition.key)
                        break

        errors = []

        # Report duplicate keys
        if duplicate_keys:
            key_list = "\n  ".join(sorted(duplicate_keys))
            errors.append(f"Found duplicate key(s):\n  {key_list}")

        # Report missing tags (only in pedantic mode)
        if self.options.get("pedantic"):
            if len(keys_without_tags) == total_definitions:
                errors.append("None of your definitions have tags.")
            elif keys_without_tags:
                key_list = "\n  ".join(sorted(keys_without_tags))
                errors.append(f"Found definitions without tags:\n  {key_list}")

        # Report invalid keys
        if invalid_keys:
            key_list = "\n  ".join(sorted(invalid_keys))
            errors.append(f"Found key(s) with invalid characters:\n  {key_list}")

        # Report Python-specific placeholders
        if keys_with_python_only_placeholders:
            key_list = "\n  ".join(sorted(keys_with_python_only_placeholders))
            errors.append(
                f"Found key(s) with placeholders that are only supported by Python:\n  {key_list}"
            )

        if errors:
            error_message = "\n\n".join(errors)
            raise TwineError(error_message)

        # Warnings for missing tags (non-pedantic mode)
        if not self.options.get("pedantic") and keys_without_tags:
            for key in sorted(keys_without_tags):
                print(f"WARNING: Definition '{key}' has no tags")

        print("Validation passed")

    def _get_formatter(self):
        """Get the appropriate formatter based on options."""
        from twine.formatters.registry import get_registry

        registry = get_registry()

        # If format specified explicitly
        if self.options.get("format"):
            formatter = registry.get(self.options["format"])
            if not formatter:
                raise TwineError(f"Unknown format: {self.options['format']}")
            # Clone formatter to avoid shared state
            import copy

            formatter = copy.deepcopy(formatter)
            formatter.twine_file = self.twine_file
            formatter.options = self.options
            return formatter

        # Try to determine from path
        output_path = self.options.get("output_path") or self.options.get("input_path")
        if output_path:
            formatter = registry.find_by_path(output_path)
            if formatter:
                import copy

                formatter = copy.deepcopy(formatter)
                formatter.twine_file = self.twine_file
                formatter.options = self.options
                return formatter

        raise TwineError(
            "Could not determine format. Please specify with --format option."
        )

    def _prepare_read_write(self, path: str, lang: Optional[str]):
        """Prepare formatter and language for read/write operations."""

        # Get formatter
        formatter = self._get_formatter()

        # Determine language if not provided
        if not lang:
            lang = formatter.determine_language_given_path(path)
            if not lang:
                # Fall back to developer language or first language
                if self.options.get("developer_language"):
                    lang = self.options["developer_language"]
                elif self.twine_file.language_codes:
                    lang = self.twine_file.language_codes[0]
                else:
                    raise TwineError(
                        f"Could not determine language from path: {path}. "
                        "Please specify with --lang option."
                    )

        return formatter, lang
