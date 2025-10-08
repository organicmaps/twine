# Twine - Python Implementation

This is a Python 3.12 implementation of Twine, a command-line tool for managing translations across multiple localization formats.

## Installation

```bash
cd python_twine
pip install -e .
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

## Usage

Once complete, usage will match the Ruby version:

```bash
# Generate a single localization file
twine generate-localization-file twine.txt output.xml --lang en

# Generate all localization files
twine generate-all-localization-files twine.txt ./locales/

# Consume translations
twine consume-localization-file twine.txt input.xml --lang es

# Validate Twine file
twine validate-twine-file twine.txt
```

## Contributing

When adding new formatters:

1. Inherit from `AbstractFormatter` in `twine/formatters/`
2. Implement required methods: `format_name()`, `extension()`, `read()`, `default_file_name()`
3. Handle language code mapping in `determine_language_given_path()`
4. Implement `key_value_pattern()` for output formatting
5. Add tests in `tests/formatters/test_<format>.py`

## License

MIT License (same as Ruby version)
