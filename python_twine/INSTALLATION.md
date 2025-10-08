# Python Twine Installation Guide

## Installation

### Development Installation

To install the Python version of Twine in development mode:

```bash
cd python_twine
pip install -e .
```

This will install Twine and all dependencies in editable mode, allowing you to make changes to the code without reinstalling.

### Dependencies

The Python implementation requires Python 3.12+ and has no external dependencies beyond the standard library.

## Testing

### Run All Tests

```bash
cd python_twine
pytest
```

### Run Specific Test File

```bash
pytest tests/test_twine_file.py
pytest tests/test_placeholders.py
pytest tests/test_integration.py
```

### Run Integration Test

```bash
python3 tests/test_integration.py
```

## Usage

After installation, you can use Twine from the command line:

```bash
# Generate localization files
twine generate-localization-file strings.txt values-en/strings.xml --format android --lang en

# Consume a localization file
twine consume-localization-file strings.txt es.lproj/Localizable.strings --lang es

# Validate a Twine file
twine validate-twine-file strings.txt
```

## Conversion Status

The Python implementation is a complete port of the Ruby version with the following components:

### ✅ Completed

1. **Core Models**
   - `TwineFile`: Main data structure
   - `TwineDefinition`: Individual translatable strings
   - `TwineSection`: Grouping mechanism

2. **Formatters (8 total)**
   - Android XML (`.xml`)
   - Apple Strings (`.strings`)
   - Apple Plural (`.stringsdict`)
   - Gettext (`.po`)
   - Django (`.po`)
   - jQuery JSON (`.json`)
   - Tizen XML (`.xml`)
   - Flash Properties (`.properties`)

3. **Utilities**
   - `placeholders.py`: Printf-style placeholder conversion
   - `output_processor.py`: Tag filtering and language fallbacks
   - `encoding.py`: BOM detection for UTF-16

4. **CLI & Runner**
   - Complete argparse-based CLI
   - All commands implemented
   - Formatter registry system

5. **Testing Framework**
   - pytest setup
   - Sample unit tests
   - Integration test

### 🔄 Remaining Work

1. **Full Test Suite**
   - Port remaining Ruby tests from `test/` directory
   - Add formatter-specific tests with fixtures
   - Edge case coverage

2. **Archive Support**
   - ZIP file handling for `consume-localization-archive`
   - ZIP file generation for `generate-localization-archive`

3. **Advanced Features**
   - Plugin system (if needed)
   - Performance optimization
   - Additional error handling

## Architecture

The Python implementation follows modern Python best practices:

- **Type Hints**: Full type annotations using Python 3.12+ syntax
- **Path Handling**: Uses `pathlib.Path` instead of string paths
- **ABC Pattern**: Abstract base class for formatters
- **Context Managers**: Proper file handling with `with` statements
- **Modern Packaging**: Uses `pyproject.toml` with setuptools

## Comparison with Ruby Version

| Feature | Ruby | Python |
|---------|------|--------|
| Language Version | Ruby 2.0+ | Python 3.12+ |
| Type System | Duck typing | Static type hints |
| Path Handling | `File` module | `pathlib.Path` |
| CLI | Custom parser | argparse |
| Testing | Minitest | pytest |
| Packaging | `.gemspec` | `pyproject.toml` |
| Formatters | 8 formatters | 8 formatters ✅ |

## Next Steps

1. Install the package: `pip install -e .`
2. Run tests: `pytest`
3. Try the integration test: `python3 tests/test_integration.py`
4. Port additional tests from Ruby as needed
5. Add archive support if required
