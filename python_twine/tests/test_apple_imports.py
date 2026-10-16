"""New Apple localization keys follow the common consume-all policy."""

import io
import plistlib

import pytest

from twine.formatters.apple import AppleFormatter
from twine.formatters.apple_plural import ApplePluralFormatter
from twine.twine_file import TwineFile


@pytest.mark.parametrize("formatter_type", [AppleFormatter, ApplePluralFormatter])
@pytest.mark.parametrize("consume_all", [False, True])
def test_new_foreign_language_key_respects_consume_all(tmp_path, formatter_type, consume_all):
    path = tmp_path / "strings.txt"
    path.write_text("[hello]\nen = Hello\n", encoding="utf-8")
    twine_file = TwineFile()
    twine_file.read(str(path))
    formatter = formatter_type()
    formatter.twine_file = twine_file
    formatter.options = {"consume_all": consume_all}
    content = '"new" = "Nouveau";\n'
    if formatter_type is ApplePluralFormatter:
        content = plistlib.dumps({
            "new": {
                "NSStringLocalizedFormatKey": "%#@value@",
                "value": {
                    "NSStringFormatSpecTypeKey": "NSStringPluralRuleType",
                    "NSStringFormatValueTypeKey": "d",
                    "one": "%d pont",
                    "other": "%d ponts",
                },
            },
        }).decode("utf-8")

    formatter.read(io.StringIO(content), "fr")

    assert ("new" in twine_file.definitions_by_key) == consume_all
    if consume_all:
        definition = twine_file.definitions_by_key["new"]
        assert definition.translation_for_lang("fr") == (
            "%d ponts" if formatter_type is ApplePluralFormatter else "Nouveau"
        )
        assert "fr" in twine_file.language_codes
