# Python feature support

The Python package implements Twine's shared text model, references, named plural forms, placeholder conversion, tag filters, language fallback, formatter registry, and command runner. Supported formats and usage examples are maintained in [README.md](README.md).

## CLI commands

- `generate-localization-file`: generate one file for a selected language.
- `generate-all-localization-files`: generate files in existing or newly created language folders.
- `consume-localization-file`: import one localization file.
- `consume-all-localization-files`: import existing language folders and deduplicate values.
- `validate-twine-file`: validate references, keys, placeholders, and optional tag requirements.
- `validate-unused-strings`: compare keys with references in Android, Apple, and C++ source.

The argparse CLI provides command-specific `--help`. Language selection with `--lang` applies to single-file generation and import commands.

## Format limitations

Android and Apple stringsdict support named plural imports and exports. Qt writes ID-based TS files with positional numerus forms and reads singular messages; plural imports are skipped because the category mapping is lossy. Other formats use singular values.

The Python CLI does not implement localization archives or external formatter plugins. The Ruby implementation provides those features.

## Tests and development

See [INSTALLATION.md](INSTALLATION.md) for dependencies and [TEST_PORTING_SUMMARY.md](TEST_PORTING_SUMMARY.md) for the Python test suites. Test totals are obtained from pytest rather than recorded in this document.
