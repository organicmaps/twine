# Twine Copilot Instructions

Twine is a command-line tool for managing translations across multiple localization formats. This project has both Ruby (original) and Python 3.12 implementations.

## Python Implementation (python_twine/)

The Python version is a modern port of the Ruby codebase:

### Core Architecture
- **TwineFile** (`twine/twine_file.py`): Central data model with sections and definitions
- **TwineDefinition**: Translatable string with key, translations dict, tags, comments, references
- **TwineSection**: Groups related definitions
- **AbstractFormatter** (`twine/formatters/__init__.py`): ABC base class for all formatters
- Uses Python 3.12+ type hints, pathlib, and dataclass patterns

### Command Flow
1. `CLI.parse()` (argparse) → `Runner.run()` → command method
2. TwineFile loaded via custom parser (regex-based)
3. Formatter selected via `--format` or path detection
4. OutputProcessor handles filtering, tag matching, and language fallbacks

### Key Modules
- `twine/placeholders.py`: Printf-style placeholder conversion (`%@` → `%s`, `{0}`, etc.)
- `twine/output_processor.py`: Tag filtering, language fallback (zh-CN → zh-Hans → en)
- `twine/encoding.py`: BOM detection (UTF-16BE/LE)
- `twine/cli.py`: Argparse-based CLI with subcommands
- `twine/runner.py`: Command orchestration

## Ruby Implementation (lib/)

Original implementation still maintained:

### Core Architecture
- **TwineFile** (`lib/twine/twine_file.rb`): Central data structure
- **TwineDefinition**: Translatable string with attr_accessors
- **TwineSection**: Groups related definitions
- **Abstract Formatter**: `lib/twine/formatters/abstract.rb` with NotImplementedError pattern

### Command Flow
1. `CLI.parse()` → `Runner.run()` → specific command method
2. TwineFile loaded from disk using custom DSL parser
3. Formatter selected based on `--format` or file extension detection
4. Operations performed via OutputProcessor for filtering/processing

## Development Conventions

### Adding New Formatters (Python)
1. Inherit from `AbstractFormatter` in `twine/formatters/`
2. Implement abstract methods: `format_name()`, `extension()`, `read()`, `default_file_name()`
3. Override `determine_language_given_path()` for custom path parsing
4. Implement `key_value_pattern()` for output format
5. Set `SUPPORTS_PLURAL = True` if format supports plural forms
6. Add type hints to all methods

### Adding New Formatters (Ruby)
1. Inherit from `Abstract` in `lib/twine/formatters/`
2. Implement required methods: `format_name`, `extension`, `read`, `format_file`
3. Handle language code mapping in `determine_language_given_path()`
4. Register in `lib/twine.rb` require statements
5. Add to `formatters.rb` registration

### Placeholder Handling
- Use `@` for string placeholders (iOS convention), not `%s`
- Python: import from `twine.placeholders` module
- Ruby: Include `Twine::Placeholders` module
- Convert between Twine format and target format in `set_translation_for_key()`
- Functions: `convert_placeholders_from_twine_to_android()`, `convert_placeholders_from_android_to_twine()`, etc.

### Language Code Patterns
- Primary language is `twine_file.language_codes[0]` (developer language)
- Use `LANGUAGE_CODE_WITH_OPTIONAL_REGION_CODE` regex: `[a-z]{2}(?:-[A-Za-z]{2})?`
- Handle platform-specific mapping (Android: `values-en-rUS`, iOS: `en.lproj`)
- Fallback chain: specific mapping (zh-CN → zh-Hans) → generic (es-MX → es) → default

### Tag Matching Logic
Tag format: `[['tag1', 'tag2'], ['~tag3']]` means (tag1 OR tag2) AND (NOT tag3)
- Inner lists = OR logic
- Outer list = AND logic across groups
- Tilde (~) prefix = negation


## Testing Approach

### Python Tests
- Framework: pytest
- Test files: `tests/test_*.py`
- Fixtures: `tests/fixtures/`
- Use `io.StringIO` to capture stdout/stderr
- Mock file system with `tempfile.TemporaryDirectory`
- Type hints in test functions

### Ruby Tests
- Base class: `TwineTest` with `TwineFileDSL` helpers
- Fixtures in `test/fixtures/` for each format
- Use `StringIO` to capture stdout/stderr during tests
- Mock file system with `Dir.mktmpdir` and cleanup in `teardown`

### Key Test Patterns (Ruby)
```ruby
def setup
  Twine::stdout = StringIO.new
  @output_dir = Dir.mktmpdir
end

def execute(command)
  Twine::Runner.run(command.split(" "))
end
```

## File Organization

### Python
- `twine/__init__.py`: Package init, version, TwineError exception
- `twine/cli.py`: Argparse-based CLI with subcommands
- `twine/runner.py`: Command execution orchestration
- `twine/output_processor.py`: Filtering and tag-based processing
- `twine/placeholders.py`: Format-specific placeholder conversion
- `pyproject.toml`: Modern Python packaging

### Ruby
- `lib/twine/cli.rb`: Command-line argument parsing with extensive option definitions
- `lib/twine/runner.rb`: Command execution orchestration
- `lib/twine/output_processor.rb`: Filtering and tag-based processing
- `lib/twine/placeholders.rb`: Format-specific placeholder conversion
- `twine.gemspec`: Gem specification

## Critical Build Commands

### Python
- `cd python_twine && pip install -e .`: Install in development mode
- `pytest`: Run full test suite
- `pytest tests/test_specific.py`: Run specific test file
- `python -m twine.cli --help`: Run CLI directly

### Ruby
- `rake test`: Run full test suite (default task)
- `gem build twine.gemspec`: Build gem
- No complex build system - pure Ruby gem structure

## Migration Notes (Ruby → Python)

When converting Ruby to Python:
1. Ruby attr_accessor → Python @property decorators
2. Ruby symbols → Python strings
3. Ruby blocks/yield → Python functions/lambdas
4. Ruby's nil → Python's None
5. Ruby's && → Python's and
6. Ruby string interpolation "#{var}" → Python f"{var}"
7. File.open → with open(...) context managers
8. require → import
9. Ruby regex /pattern/ → Python re.compile(r'pattern')
10. Ruby's .each → Python's for loop or list comprehension
