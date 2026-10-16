# Python Twine installation

Python 3.12 or newer is required. Runtime code has no third-party dependencies.

## Install

From `python_twine/`, inside your Python environment:

```sh
python3.12 -m pip install -e .
python3.12 twine_cli.py --help
```

The editable install exposes the `twine` command. Running `python3.12 twine_cli.py` from this directory uses the Python CLI directly.

## Development tools

```sh
python3.12 -m pip install -e '.[dev]' ruff
python3.12 -m pytest
ruff check --target-version=py312 .
```

The `dev` extra installs pytest and pytest-cov. Ruff is installed separately. Qt compilation tests require `lrelease` on `PATH`; pytest skips those tests when it is absent.

Run a focused suite or collect coverage:

```sh
python3.12 -m pytest tests/test_reference_generation.py
python3.12 -m pytest --cov=twine --cov-report=html
```

See [README.md](README.md) for generation, import, validation, and supported formats, and [TEST_PORTING_SUMMARY.md](TEST_PORTING_SUMMARY.md) for test responsibilities.
