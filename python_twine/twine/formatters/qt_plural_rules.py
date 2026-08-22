"""
Qt plural-rule table for the qt formatter.

Maps a two- or three-letter language code (with optional region) to the
positional list of CLDR plural categories that Qt's lrelease/QTranslator
expects in <numerusform> entries.

The table is derived from Qt's source at
qttools/src/linguist/shared/numerus.cpp (numerusTable[]). When generating
a Qt TS file for a language, the formatter emits one <numerusform> per
entry in QT_NUMERUS_FORMS[lang], in order.
"""


# 1 form: Universal (lookup returns "other")
_JAPANESE_STYLE: list[str] = ["other"]

# 2 forms: n != 1 → other
_ENGLISH_STYLE: list[str] = ["one", "other"]

# 2 forms: n <= 1 → one. Same positional shape as english style.
_FRENCH_STYLE: list[str] = ["one", "other"]

# 2 forms: n%10==1 && n%100!=11 → one, else other.
_ICELANDIC: list[str] = ["one", "other"]

# 3 forms: one, other, zero. Note: Qt's positional order puts zero last.
_LATVIAN: list[str] = ["one", "other", "zero"]

# 3 forms: n==1, n==2, else.
_IRISH_STYLE: list[str] = ["one", "two", "other"]

# 4 forms: 1/11, 2/12, 3-19, else.
_GAELIC_STYLE: list[str] = ["one", "two", "few", "other"]

# 3 forms: 1, 2-4, else.
_SLOVAK_STYLE: list[str] = ["one", "few", "other"]

# 3 forms: %100==1, %100==2, else.
_MACEDONIAN: list[str] = ["one", "two", "other"]

# 3 forms: %10==1 & %100!=11; %10!=0 & %100 not in 10-19; else.
_LITHUANIAN: list[str] = ["one", "few", "many"]

# 3 forms: %10==1 & %100!=11; %10 in 2-4 & %100 not in 10-19; else.
# Used by ru, uk, be, hr, sr, bs.
_RUSSIAN_STYLE: list[str] = ["one", "few", "many"]

# 3 forms: 1; %10 in 2-4 & %100 not in 10-19; else.
_POLISH: list[str] = ["one", "few", "many"]

# 3 forms: 1; 0 or %100 in 1-19; else.
_ROMANIAN: list[str] = ["one", "few", "other"]

# 4 forms: %100==1; %100==2; %100 in 3-4; else.
_SLOVENIAN: list[str] = ["one", "two", "few", "other"]

# 4 forms: 1; 0 or %100 in 1-10; %100 in 11-19; else.
_MALTESE: list[str] = ["one", "few", "many", "other"]

# 5 forms: 0; 1; 2-5; 6; else.
_WELSH: list[str] = ["zero", "one", "two", "few", "other"]

# 6 forms: 0; 1; 2; %100 in 3-10; %100 >= 11; else.
_ARABIC: list[str] = ["zero", "one", "two", "few", "many", "other"]


# Map from CLDR/ISO language code → positional CLDR-category list.
# Region-specific overrides go through region-aware lookup below.
QT_NUMERUS_FORMS: dict[str, list[str]] = {
    # japaneseStyle
    "bi": _JAPANESE_STYLE,
    "my": _JAPANESE_STYLE,
    "zh": _JAPANESE_STYLE,
    "zh-Hans": _JAPANESE_STYLE,
    "zh-Hant": _JAPANESE_STYLE,
    "dz": _JAPANESE_STYLE,
    "fj": _JAPANESE_STYLE,
    "gn": _JAPANESE_STYLE,
    "hu": _JAPANESE_STYLE,
    "id": _JAPANESE_STYLE,
    "ja": _JAPANESE_STYLE,
    "jv": _JAPANESE_STYLE,
    "ko": _JAPANESE_STYLE,
    "ms": _JAPANESE_STYLE,
    "na": _JAPANESE_STYLE,
    "om": _JAPANESE_STYLE,
    "fa": _JAPANESE_STYLE,
    "su": _JAPANESE_STYLE,
    "tt": _JAPANESE_STYLE,
    "th": _JAPANESE_STYLE,
    "bo": _JAPANESE_STYLE,
    "tr": _JAPANESE_STYLE,
    "vi": _JAPANESE_STYLE,
    "yo": _JAPANESE_STYLE,
    "za": _JAPANESE_STYLE,

    # englishStyle
    "ab": _ENGLISH_STYLE,
    "aa": _ENGLISH_STYLE,
    "af": _ENGLISH_STYLE,
    # Asturian (ast) is not in Qt's numerusTable, but CLDR places it in the
    # english-style 2-form group (one = n==1, other = else).
    "ast": _ENGLISH_STYLE,
    "sq": _ENGLISH_STYLE,
    "am": _ENGLISH_STYLE,
    "as": _ENGLISH_STYLE,
    "ay": _ENGLISH_STYLE,
    "az": _ENGLISH_STYLE,
    "ba": _ENGLISH_STYLE,
    "eu": _ENGLISH_STYLE,
    "bn": _ENGLISH_STYLE,
    "bg": _ENGLISH_STYLE,
    "ca": _ENGLISH_STYLE,
    "kw": _ENGLISH_STYLE,
    "co": _ENGLISH_STYLE,
    "da": _ENGLISH_STYLE,
    "nl": _ENGLISH_STYLE,
    "en": _ENGLISH_STYLE,
    "eo": _ENGLISH_STYLE,
    "et": _ENGLISH_STYLE,
    "fo": _ENGLISH_STYLE,
    "fi": _ENGLISH_STYLE,
    "fur": _ENGLISH_STYLE,
    "fy": _ENGLISH_STYLE,
    "gl": _ENGLISH_STYLE,
    "lg": _ENGLISH_STYLE,
    "ka": _ENGLISH_STYLE,
    "de": _ENGLISH_STYLE,
    "el": _ENGLISH_STYLE,
    "kl": _ENGLISH_STYLE,
    "gu": _ENGLISH_STYLE,
    "ha": _ENGLISH_STYLE,
    "he": _ENGLISH_STYLE,
    "hi": _ENGLISH_STYLE,
    "ia": _ENGLISH_STYLE,
    "ie": _ENGLISH_STYLE,
    "it": _ENGLISH_STYLE,
    "kn": _ENGLISH_STYLE,
    "ks": _ENGLISH_STYLE,
    "kk": _ENGLISH_STYLE,
    "km": _ENGLISH_STYLE,
    "rw": _ENGLISH_STYLE,
    "ky": _ENGLISH_STYLE,
    "ku": _ENGLISH_STYLE,
    "lo": _ENGLISH_STYLE,
    "la": _ENGLISH_STYLE,
    "ln": _ENGLISH_STYLE,
    "lb": _ENGLISH_STYLE,
    "mg": _ENGLISH_STYLE,
    "ml": _ENGLISH_STYLE,
    "mr": _ENGLISH_STYLE,
    "mn": _ENGLISH_STYLE,
    "ne": _ENGLISH_STYLE,
    "nso": _ENGLISH_STYLE,
    "nb": _ENGLISH_STYLE,
    "nn": _ENGLISH_STYLE,
    "oc": _ENGLISH_STYLE,
    "or": _ENGLISH_STYLE,
    "ps": _ENGLISH_STYLE,
    # "pt" (default Portugal) is englishStyle; "pt-BR" is overridden below.
    "pt": _ENGLISH_STYLE,
    "pa": _ENGLISH_STYLE,
    "qu": _ENGLISH_STYLE,
    "rm": _ENGLISH_STYLE,
    "rn": _ENGLISH_STYLE,
    "sn": _ENGLISH_STYLE,
    "sd": _ENGLISH_STYLE,
    "si": _ENGLISH_STYLE,
    "so": _ENGLISH_STYLE,
    "st": _ENGLISH_STYLE,
    "es": _ENGLISH_STYLE,
    "sw": _ENGLISH_STYLE,
    "ss": _ENGLISH_STYLE,
    "sv": _ENGLISH_STYLE,
    "tg": _ENGLISH_STYLE,
    "ta": _ENGLISH_STYLE,
    "te": _ENGLISH_STYLE,
    "to": _ENGLISH_STYLE,
    "ts": _ENGLISH_STYLE,
    "tn": _ENGLISH_STYLE,
    "tk": _ENGLISH_STYLE,
    "ug": _ENGLISH_STYLE,
    "ur": _ENGLISH_STYLE,
    "uz": _ENGLISH_STYLE,
    "vo": _ENGLISH_STYLE,
    "wo": _ENGLISH_STYLE,
    "xh": _ENGLISH_STYLE,
    "yi": _ENGLISH_STYLE,
    "zu": _ENGLISH_STYLE,

    # frenchStyle (Qt rule: n <= 1 → one).
    "hy": _FRENCH_STYLE,
    "br": _FRENCH_STYLE,
    "fr": _FRENCH_STYLE,
    "fil": _FRENCH_STYLE,
    "ti": _FRENCH_STYLE,
    "wa": _FRENCH_STYLE,
    # pt-BR overrides the "pt" → englishStyle entry above.
    "pt-BR": _FRENCH_STYLE,

    # irishStyle
    "dv": _IRISH_STYLE,
    "iu": _IRISH_STYLE,
    "ik": _IRISH_STYLE,
    "ga": _IRISH_STYLE,
    "gv": _IRISH_STYLE,
    "mi": _IRISH_STYLE,
    "se": _IRISH_STYLE,
    "sm": _IRISH_STYLE,
    "sa": _IRISH_STYLE,

    # russianStyle
    "bs": _RUSSIAN_STYLE,
    "be": _RUSSIAN_STYLE,
    "hr": _RUSSIAN_STYLE,
    "ru": _RUSSIAN_STYLE,
    "sr": _RUSSIAN_STYLE,
    "uk": _RUSSIAN_STYLE,

    # slovakStyle
    "sk": _SLOVAK_STYLE,
    "cs": _SLOVAK_STYLE,

    # standalone groups
    "ar": _ARABIC,
    "cy": _WELSH,
    "is": _ICELANDIC,
    "lv": _LATVIAN,
    "lt": _LITHUANIAN,
    "mk": _MACEDONIAN,
    "mt": _MALTESE,
    "pl": _POLISH,
    "ro": _ROMANIAN,
    "sl": _SLOVENIAN,
    "gd": _GAELIC_STYLE,
}


def _base_language(lang: str) -> str:
    """Strip region tag: 'es-MX' → 'es', 'zh-Hans' → 'zh-Hans' (unchanged)."""
    # zh-Hans / zh-Hant are first-class entries; only strip plain region tags.
    if lang in QT_NUMERUS_FORMS:
        return lang
    if "-" in lang:
        return lang.split("-", 1)[0]
    return lang


def get_qt_numerus_forms(lang: str) -> list[str] | None:
    """
    Return positional CLDR-category list for `lang`, or None if Qt has no
    plural rule for this language.

    Lookup order:
      1. Exact match (e.g., 'pt-BR', 'zh-Hans').
      2. Base-language fallback (e.g., 'es-MX' → 'es').
    """
    forms = QT_NUMERUS_FORMS.get(lang)
    if forms is not None:
        return forms
    base = _base_language(lang)
    if base != lang:
        return QT_NUMERUS_FORMS.get(base)
    return None
