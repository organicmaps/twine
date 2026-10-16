# Python test suite

The pytest suite exercises the Python data model, localization formats, and CLI workflows. It does not imply complete parity with the Ruby implementation; Python's supported features are listed in [CONVERSION_STATUS.md](CONVERSION_STATUS.md).

## Suite responsibilities

- `test_twine_file.py` and `test_twine_definition.py`: parsing, writing, references, tags, and deduplication.
- `test_output_processor.py`: filtering, developer-language fallback, and per-language resource selection.
- `test_reference_generation.py`: inherited plural forms, singular overrides, output ownership, regional fallback, and format round trips.
- `test_formatters.py` and `test_formatters_plural.py`: formatter fixtures, escaping, placeholder conversion, and named plural import/export.
- `test_apple_imports.py`: unknown Apple keys and the consume-all policy.
- `test_formatter_qt.py` and `test_formatter_qt_plural.py`: Qt TS structure, numerus rules, placeholders, whitespace, and optional compilation through `lrelease`.
- `test_commands.py` and `test_integration.py`: validation and generation workflows, including localization folder classification.
- `test_placeholders.py` and `test_tools.py`: placeholder and utility behavior.

Fixtures live in `tests/fixtures/`. Input parsing tests use Twine text where parser behavior affects generation; hand-built definitions exercise model and formatter operations directly.

## Run tests

From `python_twine/`:

```sh
python3.12 -m pip install -e '.[dev]' ruff
python3.12 -m pytest
python3.12 -m pytest tests/test_reference_generation.py -v
python3.12 -m pytest tests/test_formatters.py::TestAndroidFormatter
ruff check --target-version=py312 .
```

Qt compilation tests run only when `lrelease` is installed. Collect the available tests or generate a coverage report with:

```sh
python3.12 -m pytest --collect-only -q
python3.12 -m pytest --cov=twine --cov-report=html
```

Coverage reports measure executed Python paths; they do not prove complete format compatibility or Ruby feature parity.
