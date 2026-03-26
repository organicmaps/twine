"""
Command-line interface for Twine.
"""

import argparse
import sys

from typing import Optional, Dict, List

from twine import __version__
from twine.runner import Runner


class CLI:
    """Command-line interface handler."""

    @staticmethod
    def create_parser() -> argparse.ArgumentParser:
        """Create and configure the argument parser."""
        parser = argparse.ArgumentParser(
            prog="twine",
            description="Twine - Manage your strings and their translations",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        parser.add_argument(
            "--version", action="version", version=f"%(prog)s {__version__}"
        )

        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        # generate-localization-file
        gen_file = subparsers.add_parser(
            "generate-localization-file", help="Generate a single localization file"
        )
        gen_file.add_argument("twine_file", help="Path to Twine data file")
        gen_file.add_argument("output_path", help="Output file path")
        CLI._add_common_arguments(gen_file)
        CLI._add_language_argument(gen_file)

        # generate-all-localization-files
        gen_all = subparsers.add_parser(
            "generate-all-localization-files",
            help="Generate localization files for all languages",
        )
        gen_all.add_argument("twine_file", help="Path to Twine data file")
        gen_all.add_argument("output_path", help="Output directory path")
        CLI._add_common_arguments(gen_all)
        gen_all.add_argument(
            "-r",
            "--create-folders",
            action="store_true",
            help="Create output folders for all languages if they don't exist",
        )
        gen_all.add_argument(
            "-n", "--file-name", help="Output file name (default: format-specific)"
        )

        # consume-localization-file
        consume_file = subparsers.add_parser(
            "consume-localization-file",
            help="Import translations from a localization file",
        )
        consume_file.add_argument("twine_file", help="Path to Twine data file")
        consume_file.add_argument("input_path", help="Input file path")
        consume_file.add_argument(
            "--fallback-to-default",
            action="store_true",
            help="Remove translations matching default language",
        )
        CLI._add_common_arguments(consume_file)
        CLI._add_language_argument(consume_file)
        CLI._add_consume_arguments(consume_file)

        # consume-all-localization-files
        consume_all = subparsers.add_parser(
            "consume-all-localization-files",
            help="Import translations from all localization files",
        )
        consume_all.add_argument("twine_file", help="Path to Twine data file")
        consume_all.add_argument("input_path", help="Input directory path")
        consume_all.add_argument(
            "--fallback-to-default",
            action="store_true",
            help="Remove translations matching default language",
        )
        consume_all.add_argument(
            "-n", "--file-name", help="Input file name (default: format-specific)"
        )
        CLI._add_common_arguments(consume_all)
        CLI._add_consume_arguments(consume_all)

        # validate-twine-file
        validate_twine = subparsers.add_parser(
            "validate-twine-file", help="Validate the Twine data file"
        )
        validate_twine.add_argument("twine_file", help="Path to Twine data file")
        validate_twine.add_argument(
            "--pedantic",
            action="store_true",
            help="Enable pedantic validation (e.g., require tags)",
        )

        # validate-unused-strings
        validate_unused = subparsers.add_parser(
            "validate-unused-strings", help="Search through Android and iOS source code to find unused strings"
        )
        validate_unused.add_argument("twine_file", help="Path to Twine data file")
        validate_unused.add_argument(
            "--android-src-root",
            help="Path to Android source root directory",
            default=None
        )
        validate_unused.add_argument(
            "--ios-src-root",
            help="Path to iOS source root directory",
            default=None
        )
        validate_unused.add_argument(
            "--core-src-root",
            help="Path to C++ source root directory",
            default=None
        )

        return parser

    @staticmethod
    def _add_common_arguments(parser: argparse.ArgumentParser):
        """Add common arguments to a subcommand parser."""
        parser.add_argument(
            "-f",
            "--format",
            help="Localization file format (android, apple, gettext, jquery, django, tizen, flash)",
        )
        parser.add_argument(
            "--tags",
            action="append",
            help="Filter definitions by tags (can be used multiple times)",
        )
        parser.add_argument(
            "-u",
            "--untagged",
            action="store_true",
            default=True,
            help="Include untagged definitions",
        )
        parser.add_argument(
            "--no-untagged",
            dest="untagged",
            action="store_false",
            help="Exclude untagged definitions",
        )
        parser.add_argument(
            "-d", "--developer-language", help="Developer language code"
        )
        parser.add_argument(
            "-e", "--encoding", default="UTF-8", help="Output encoding (default: UTF-8)"
        )
        parser.add_argument(
            "--validate",
            action="store_true",
            help="Validate Twine file before processing",
        )
        parser.add_argument(
            "--include",
            choices=["all", "translated", "untranslated"],
            default="all",
            help="Which definitions to include",
        )

    @staticmethod
    def _add_language_argument(parser: argparse.ArgumentParser):
        """Add language argument."""
        parser.add_argument(
            "-l",
            "--lang",
            dest="languages",
            action="append",
            help="Language code(s) to process",
        )

    @staticmethod
    def _add_consume_arguments(parser: argparse.ArgumentParser):
        """Add consume-specific arguments."""
        parser.add_argument(
            "-a",
            "--consume-all",
            action="store_true",
            help="Add new definitions from input files",
        )
        parser.add_argument(
            "-c",
            "--consume-comments",
            action="store_true",
            help="Import comments from input files",
        )

    @staticmethod
    def parse(args: Optional[List[str]] = None) -> Optional[Dict]:
        """Parse command-line arguments."""
        parser = CLI.create_parser()

        if args is None:
            args = sys.argv[1:]

        if not args:
            parser.print_help()
            return None

        parsed = parser.parse_args(args)

        if not parsed.command:
            parser.print_help()
            return None

        # Convert to dict for compatibility
        options = vars(parsed)

        # Parse tags into groups. Tags within a group have "OR" meaning. Groups are joined with "AND".
        # For example `--tags android,apple --tags maps` means filter by "(android OR apple) AND (maps)"
        # Or another `--tags android-sdk --tags ~android-app` means filter by "(android-sdk) AND (not android-app)"
        if "tags" in options and options["tags"]:
            # Convert list of tag strings to list of lists
            tag_groups = []
            for tag_group in options["tags"]:
                tags = [t.strip() for t in tag_group.split(",")]
                tag_groups.append(tags)
            options["tags"] = tag_groups
        else:
            options["tags"] = None

        return options


def main():
    """Main entry point for the CLI."""
    options = CLI.parse()
    if options:
        runner = Runner(options)
        try:
            runner.run()
        except Exception as e:
            import traceback
            print(f"Error: {e}", file=sys.stderr)
            traceback.print_exception(e)
            sys.exit(1)


if __name__ == "__main__":
    main()
