"""
Placeholder conversion utilities for different localization formats.
"""

import re


# Note: the ` ` (single space) flag is NOT supported
PLACEHOLDER_FLAGS_WIDTH_PRECISION_LENGTH = (
    r"([-+0#])?(\d+|\*)?(\.(\d+|\*))?(hh?|ll?|L|z|j|t|q)?"
)
PLACEHOLDER_PARAMETER_FLAGS_WIDTH_PRECISION_LENGTH = (
    r"(\d+\$)?" + PLACEHOLDER_FLAGS_WIDTH_PRECISION_LENGTH
)
PLACEHOLDER_TYPES = r"[diufFeEgGxXoscpaA@]"  # Added @ for Twine placeholders
PLACEHOLDER_REGEX = re.compile(
    r"%" + PLACEHOLDER_PARAMETER_FLAGS_WIDTH_PRECISION_LENGTH + PLACEHOLDER_TYPES
)


def number_of_twine_placeholders(input_str: str) -> int:
    """Count the number of printf-style placeholders in a string."""
    return len(PLACEHOLDER_REGEX.findall(input_str))


def convert_twine_string_placeholder(input_str: str) -> str:
    """Convert Twine string placeholder from %@ to %s."""
    pattern = re.compile(
        r"(%" + PLACEHOLDER_PARAMETER_FLAGS_WIDTH_PRECISION_LENGTH + r")@"
    )
    return pattern.sub(r"\1s", input_str)


def convert_placeholders_from_twine_to_android(input_str: str) -> str:
    """
    Convert placeholders from Twine format to Android format.

    - %@ -> %s
    - Single % -> %% (escaped)
    - Multiple placeholders -> numbered (%1$s, %2$s, etc.)

    http://developer.android.com/guide/topics/resources/string-resource.html#FormattingAndStyling
    """
    from twine import TwineError

    # %@ -> %s
    value = convert_twine_string_placeholder(input_str)

    num_placeholders = number_of_twine_placeholders(value)

    if num_placeholders == 0:
        return value

    # Got placeholders -> need to double single percent signs
    # % -> %% (but %% -> %%, %d -> %d)
    placeholder_syntax = (
        PLACEHOLDER_PARAMETER_FLAGS_WIDTH_PRECISION_LENGTH + PLACEHOLDER_TYPES
    )
    single_percent_regex = re.compile(r"([^%])(%)(?!(%|" + placeholder_syntax + r"))")
    value = single_percent_regex.sub(r"\1%%", value)

    if num_placeholders < 2:
        return value

    # Number placeholders if there are multiple
    non_numbered_placeholder_regex = re.compile(
        r"%(" + PLACEHOLDER_FLAGS_WIDTH_PRECISION_LENGTH + PLACEHOLDER_TYPES + r")"
    )

    non_numbered_matches = non_numbered_placeholder_regex.findall(value)
    num_non_numbered = len(non_numbered_matches)

    if num_non_numbered == 0:
        return value

    if num_placeholders != num_non_numbered:
        raise TwineError(
            f'The value "{input_str}" contains numbered and non-numbered placeholders'
        )

    # %d -> %1$d, %s -> %2$s, etc.
    index = 0

    def number_placeholder(match):
        nonlocal index
        index += 1
        return f"%{index}${match.group(1)}"

    value = non_numbered_placeholder_regex.sub(number_placeholder, value)

    return value


def convert_placeholders_from_android_to_twine(input_str: str) -> str:
    """Convert Android string placeholders (%s) to Twine format (%@)."""
    placeholder_regex = re.compile(
        r"(%" + PLACEHOLDER_PARAMETER_FLAGS_WIDTH_PRECISION_LENGTH + r")s"
    )
    return placeholder_regex.sub(r"\1@", input_str)


def convert_placeholders_from_twine_to_flash(input_str: str) -> str:
    """
    Convert placeholders from Twine format to Flash/Flex format.

    %@ -> {0}, {1}, etc.

    http://help.adobe.com/en_US/FlashPlatform/reference/actionscript/3/mx/resources/IResourceManager.html#getString()
    """
    value = convert_twine_string_placeholder(input_str)

    matches = list(PLACEHOLDER_REGEX.finditer(value))

    # Replace in reverse order to maintain positions
    for index, match in enumerate(reversed(matches)):
        actual_index = len(matches) - index - 1
        start, end = match.span()
        value = value[:start] + f"{{{actual_index}}}" + value[end:]

    return value


def convert_placeholders_from_flash_to_twine(input_str: str) -> str:
    """Convert Flash placeholders ({0}, {1}) to Twine format (%@)."""
    return re.sub(r"\{\d+\}", "%@", input_str)


def contains_python_specific_placeholder(input_str: str) -> bool:
    """
    Check if string contains Python-specific placeholders.

    Python supports placeholders like %(amount)03d
    See https://docs.python.org/3/library/stdtypes.html#printf-style-string-formatting
    """
    pattern = re.compile(
        r"%\([a-zA-Z0-9_-]+\)"
        + PLACEHOLDER_PARAMETER_FLAGS_WIDTH_PRECISION_LENGTH
        + PLACEHOLDER_TYPES
    )
    return pattern.search(input_str) is not None
