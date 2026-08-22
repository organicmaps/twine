"""
Twine - A command line tool for managing strings and their translations.
"""

__version__ = "0.1.0"

import sys

# Global stdout/stderr handles for testing
stdout = sys.stdout
stderr = sys.stderr


class TwineError(Exception):
    """Base exception for Twine errors."""

