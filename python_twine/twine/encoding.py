"""
Encoding utilities for detecting file encodings.
"""



def get_bom(path: str) -> str | None:
    """
    Detect BOM (Byte Order Mark) in a file.

    Args:
        path: Path to the file

    Returns:
        Encoding name ('UTF-16BE' or 'UTF-16LE') or None
    """
    try:
        with open(path, "rb") as f:
            first_bytes = f.read(2)

        if not first_bytes or len(first_bytes) < 2:
            return None

        # Check for UTF-16 BOMs
        if first_bytes == b"\xfe\xff":
            return "UTF-16BE"
        elif first_bytes == b"\xff\xfe":
            return "UTF-16LE"

        return None
    except OSError:
        return None


def has_bom(path: str) -> bool:
    """Check if a file has a BOM."""
    return get_bom(path) is not None


def encoding_for_path(path: str) -> str:
    """
    Determine the encoding for a file.

    Args:
        path: Path to the file

    Returns:
        Encoding name (defaults to 'UTF-8')
    """
    bom_encoding = get_bom(path)
    return bom_encoding if bom_encoding else "UTF-8"
