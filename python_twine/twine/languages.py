"""Language fallback order shared by import optimization and generation."""

import re

FALLBACK_LANGS_MAPPING = {
    "zh-CN": "zh-Hans",
    "zh-TW": "zh-Hant",
    "zh-MO": "zh-Hant",
    "zh-HK": "zh-Hant",
}
REGIONAL_LANG_REGEX = re.compile(r"([a-zA-Z]{2,3})-[a-zA-Z]+")


def fallback_languages(language: str, default_language: str | None = None) -> list[str]:
    """Prefer the script mapping, then the base language, then the default."""
    candidates = []
    if language in FALLBACK_LANGS_MAPPING:
        candidates.append(FALLBACK_LANGS_MAPPING[language])
    match = REGIONAL_LANG_REGEX.match(language)
    if match:
        candidates.append(match.group(1))
    if default_language and default_language != language:
        candidates.append(default_language)
    return list(dict.fromkeys(candidates))
