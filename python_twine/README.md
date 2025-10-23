# Twine - Python Implementation

This is a Python 3.12 implementation of Twine, a command-line tool for managing translations across multiple localization formats.

## Installation

```bash
cd python_twine
pip install -e .
```

## Usage

### Generate Android resource files from string.txt

```bash
# Generate a single localization file
python twine_cli.py generate-localization-file \
    strings.txt \
    strings.xml \
    --tags android-app \
    --lang en

# Generate all localization files for Spanish
python twine_cli.py generate-all-localization-files \
    strings.txt \
    $OMAPS_REPO/android/app/src/main/res \
    --tags android-app \
    --lang es

# Generate all localization files for all available languages
python twine_cli.py generate-all-localization-files \
    strings.txt \
    $OMAPS_REPO/android/sdk/src/main/res \
    --tags android,android-sdk

# Consume a translation file and update strings.txt file
# It's better to assign developer language with `-d en` because of Apple .strings file.
# Untranslated values are replaced with default (English) values in .strings
# And Twine needs to know default lang to ignore untranslated strings.
python twine_cli.py consume-localization-file \
    strings.txt \
    $OMAPS_REPO/android/app/src/main/res/values-ja/strings.xml
    -t android,android-app
    -f android \
    -d en \
    --lang ja

# Consume all translations and update strings.txt file
# It's better to assign developer language with `-d en` because of Apple .strings file.
# Untranslated values are replaced with default (English) values in .strings
# And Twine needs to know default lang to ignore untranslated strings.
python twine_cli.py consume-all-localization-files \
    strings.txt \
    $OMAPS_REPO/iphone/Maps/LocalizedStrings
    -t apple,apple-maps \
    -f apple \
    -d en \
    --lang ja

# Validate Twine file
python twine_cli.py validate-twine-file strings.txt
```

## Project Structure

```
python_twine/
├── twine/                    # Main package
│   ├── __init__.py          # Package initialization
│   ├── twine_file.py        # Core data models (TwineFile, TwineDefinition, TwineSection)
│   ├── cli.py               # Command-line interface
│   ├── runner.py            # Command orchestration
│   ├── placeholders.py      # Placeholder conversion utilities
│   ├── output_processor.py  # Output filtering and processing
│   ├── encoding.py          # Encoding detection
│   └── formatters/          # Format implementations
│       ├── __init__.py      # Abstract formatter base
│       ├── android.py       # Android XML strings
│       ├── apple.py         # iOS/macOS .strings
│       ├── gettext.py       # Gettext .po files
│       └── ...              # Other formatters
├── tests/                    # Test suite
├── pyproject.toml           # Project configuration
└── README.md                # This file
```

## Architecture

### Core Data Model

- **TwineFile**: Central data structure containing sections and definitions
  - Manages language codes with developer language at index 0
  - Reads/writes Twine data files in INI-like format

- **TwineDefinition**: Represents a translatable string
  - Key, translations dict, tags, comments
  - Support for plural translations
  - Reference system for inheritance

- **TwineSection**: Groups related definitions

### Formatter Pattern

All format support uses the Abstract Formatter pattern:

```python
from twine.formatters import AbstractFormatter

class MyFormatter(AbstractFormatter):
    def format_name(self) -> str:
        return "myformat"

    def extension(self) -> str:
        return ".ext"

    def read(self, io: TextIO, lang: str):
        # Parse format
        pass

    def format_file(self, lang: str) -> str:
        # Generate format
        pass
```

### Placeholder Conversion

Twine uses `@` for string placeholders (iOS convention):
- `%@` is the standard Twine placeholder
- Converted to `%s` for Android
- Converted to `{0}` for Flash
- Module: `twine.placeholders`

## Development

### Running Tests

```bash
poetry install --extras dev
pytest
```

### Key Differences from Ruby Version

1. **Type Hints**: Full type annotations for better IDE support
2. **Pathlib**: Uses `pathlib.Path` instead of string paths
3. **ABC Module**: Uses Python's `abc` for abstract base classes
4. **Argparse**: Uses argparse instead of OptionParser
5. **Context Managers**: Proper file handling with `with` statements

## Conversion Status

### ✅ Completed
- Core data models (TwineFile, TwineDefinition, TwineSection)
- Placeholder conversion utilities
- Output processor
- Encoding detection
- Abstract formatter base
- CLI infrastructure
- Runner orchestration

### 🚧 In Progress
- Concrete formatters (Android, Apple, Gettext, etc.)

### 📋 TODO
- Complete all formatters
- Test suite conversion
- Archive support (zip handling)
- Plugin system

## Contributing

When adding new formatters:

1. Inherit from `AbstractFormatter` in `twine/formatters/`
2. Implement required methods: `format_name()`, `extension()`, `read()`, `default_file_name()`
3. Handle language code mapping in `determine_language_given_path()`
4. Implement `key_value_pattern()` for output formatting
5. Add tests in `tests/formatters/test_<format>.py`

## License

MIT License (same as Ruby version)
