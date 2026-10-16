# Twine for Python

Twine manages translations in a shared text file and imports or generates platform localization files. The Python implementation requires Python 3.12 or newer and uses only the standard library at runtime.

## Installation

From this directory:

```sh
python3.12 -m pip install -e .
python3.12 twine_cli.py --help
```

The package also installs the `twine` command. See [INSTALLATION.md](INSTALLATION.md) for development dependencies.

## Supported formats

| Format option | File type | Plural support |
| --- | --- | --- |
| `android` | Android `.xml` | Read and write named forms |
| `apple` | Apple `.strings` | Singular values; use `apple-plural` for plurals |
| `apple-plural` | Apple `.stringsdict` | Read and write named forms |
| `qt` | Qt ID-based `.ts` | Write positional numerus forms; read singular messages |
| `gettext` | Gettext `.po` | Singular values |
| `django` | Django `.po` | Singular values |
| `jquery` | jQuery-localize `.json` | Singular values |
| `tizen` | Tizen `.xml` | Singular values |
| `flash` | Flash `.properties` | Singular values |

Use `--format` when an extension is shared by several formats. Qt plural imports are skipped because positional numerus forms do not uniquely identify CLDR categories.

## Generate localization files

Generate one Spanish Android file, with explicit format and language:

```sh
python3.12 twine_cli.py generate-localization-file \
    strings.txt strings-es.xml \
    --format android --lang es --tags android-app
```

Generate files in existing Android language folders:

```sh
python3.12 twine_cli.py generate-all-localization-files \
    strings.txt "$OMAPS_REPO/android/sdk/src/main/res" \
    --format android --tags android,android-sdk --include translated
```

`generate-all-localization-files` scans existing language folders. Add `--create-folders` to create folders for languages listed in the Twine file. This command has no `--lang` option; use single-file generation to select one language. `--file-name` overrides the formatter's default filename.

`--include translated` selects definitions with a translation or plural forms for the requested language, including inherited values. `--include untranslated` selects definitions without them. The default, `all`, also uses language fallbacks.

## Import translations

Import one Android file:

```sh
python3.12 twine_cli.py consume-localization-file \
    strings.txt "$OMAPS_REPO/android/app/src/main/res/values-ja/strings.xml" \
    --format android --lang ja --developer-language en --tags android,android-app
```

Import all existing Apple language folders and deduplicate matching values:

```sh
python3.12 twine_cli.py consume-all-localization-files \
    strings.txt "$OMAPS_REPO/iphone/Maps/LocalizedStrings" \
    --format apple --developer-language en --tags apple,apple-maps
```

The developer language defaults to the first language in the Twine file. Apple imports compare against developer text because generated resources can contain developer-language fallbacks. `--consume-all` adds unknown keys; otherwise they are reported and skipped. `--consume-comments` imports comments.

## Definitions, references, and fallbacks

`TwineFile` stores sections, definitions, and language codes. Definitions can inherit translations, plural forms, comments, and tag matching through `ref`. An explicit singular translation, including an empty value, overrides inherited plural forms for that language.

`OutputProcessor` filters definitions and selects language text and forms into independent output collections. Regional fallback prefers an explicit Chinese script mapping, then the base language, then the developer language. Partial plural forms can use fallback text for a missing `other` form. Android and Apple plural output require `other` and fail if it cannot be resolved; Qt uses its positional plural rule table and per-form developer fallback.

Twine placeholders use `%@` for object/string arguments. Formatters convert them to the target platform's syntax, such as `%s` on Android or numbered arguments in Qt.

Tags separated by commas form an OR group. Repeated `--tags` options combine groups with AND; for example, `--tags android,apple --tags ~deprecated`. The CLI includes untagged definitions by default; `--no-untagged` excludes them.

## Validation

```sh
python3.12 twine_cli.py validate-twine-file strings.txt --pedantic
```

Reading a Twine file rejects malformed lines, unknown plural categories, dangling references, and reference cycles. Explicit validation also checks duplicate keys, invalid key characters, and Python-specific placeholders. `--pedantic` makes missing tags an error.

Find keys that are not referenced by application source:

```sh
python3.12 twine_cli.py validate-unused-strings \
    "$OMAPS_REPO/data/strings/strings.txt" \
    --android-src-root "$OMAPS_REPO/android" \
    --core-src-root "$OMAPS_REPO/libs" \
    --ios-src-root "$OMAPS_REPO/iphone"
```

## Development

```sh
python3.12 -m pip install -e '.[dev]' ruff
python3.12 -m pytest
ruff check --target-version=py312 .
```

The [test guide](TEST_PORTING_SUMMARY.md) describes the suite. Qt compilation tests run when `lrelease` is available and are skipped otherwise.

Core modules are `twine_file.py` (models and parsing), `languages.py` (fallback order), `output_processor.py` (output selection), `runner.py` (commands), and `formatters/` (format-specific import and generation). New formatters inherit `AbstractFormatter`, implement its abstract methods and formatting hooks, register in `formatters/registry.py`, and add tests in `tests/test_*.py`.

Archive commands and external formatter plugins are not implemented in the Python CLI. See [CONVERSION_STATUS.md](CONVERSION_STATUS.md) for the supported command list.

## License

MIT; see the repository's [LICENSE](../LICENSE).
