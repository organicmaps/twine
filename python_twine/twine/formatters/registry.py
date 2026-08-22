"""
Formatter registry and management.
"""

from twine.formatters import AbstractFormatter


class FormatterRegistry:
    """Registry for managing formatter instances."""

    def __init__(self):
        self._formatters: dict[str, AbstractFormatter] = {}

    def register(self, formatter: AbstractFormatter):
        """Register a formatter instance."""
        self._formatters[formatter.format_name()] = formatter

    def get(self, format_name: str) -> AbstractFormatter | None:
        """Get a formatter by name."""
        return self._formatters.get(format_name)

    def all(self) -> list[AbstractFormatter]:
        """Get all registered formatters."""
        return list(self._formatters.values())

    def find_by_extension(self, extension: str) -> AbstractFormatter | None:
        """Find a formatter by file extension."""
        for formatter in self._formatters.values():
            if formatter.extension() == extension:
                return formatter
        return None

    def find_by_path(self, path: str) -> AbstractFormatter | None:
        """Find a formatter that can handle the given path."""
        import os
        from pathlib import Path

        # Try by extension first
        ext = Path(path).suffix
        formatter = self.find_by_extension(ext)
        if formatter:
            return formatter

        # If path is a directory, check if any formatter can handle it
        if os.path.isdir(path):
            for formatter in self._formatters.values():
                if formatter.can_handle_directory(path):
                    return formatter

        return None


# Global registry instance
_registry = FormatterRegistry()


def get_registry() -> FormatterRegistry:
    """Get the global formatter registry."""
    return _registry


def register_all_formatters():
    """Register all built-in formatters."""
    from twine.formatters.android import AndroidFormatter
    from twine.formatters.apple import AppleFormatter
    from twine.formatters.apple_plural import ApplePluralFormatter
    from twine.formatters.django import DjangoFormatter
    from twine.formatters.flash import FlashFormatter
    from twine.formatters.gettext import GettextFormatter
    from twine.formatters.jquery import JQueryFormatter
    from twine.formatters.qt import QtFormatter
    from twine.formatters.tizen import TizenFormatter

    registry = get_registry()

    # Register all formatters
    registry.register(AndroidFormatter())
    registry.register(AppleFormatter())
    registry.register(ApplePluralFormatter())
    registry.register(DjangoFormatter())
    registry.register(FlashFormatter())
    registry.register(GettextFormatter())
    registry.register(JQueryFormatter())
    registry.register(QtFormatter())
    registry.register(TizenFormatter())


# Auto-register on import
register_all_formatters()
