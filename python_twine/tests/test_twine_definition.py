"""
Tests for TwineDefinition class.
"""

import pytest

from twine.twine_file import TwineDefinition


class TestTags:
    """Test tag matching functionality."""

    @pytest.fixture
    def definition(self):
        """Create a test TwineDefinition."""
        return TwineDefinition("key")

    def test_include_untagged(self, definition):
        """Test that untagged definitions match when include_untagged is True."""
        # Random tag that doesn't exist, but include_untagged=True should match
        assert definition.matches_tags([["random_tag_12345"]], include_untagged=True)

    def test_matches_no_given_tags(self, definition):
        """Test that definitions match when no tags are specified."""
        assert definition.matches_tags([], include_untagged=False)

    def test_matches_tag(self, definition):
        """Test matching a single tag."""
        definition.tags = ["tag1"]

        assert definition.matches_tags([["tag1"]], include_untagged=False)

    def test_matches_any_tag(self, definition):
        """Test matching any tag in a group (OR logic)."""
        definition.tags = ["tag1"]

        assert definition.matches_tags(
            [["tag0", "tag1", "tag2"]], include_untagged=False
        )

    def test_matches_all_tags(self, definition):
        """Test matching all tag groups (AND logic)."""
        definition.tags = ["tag1", "tag2"]

        assert definition.matches_tags([["tag1"], ["tag2"]], include_untagged=False)

    def test_does_not_match_all_tags(self, definition):
        """Test not matching when missing a required tag."""
        definition.tags = ["tag1"]

        assert not definition.matches_tags([["tag1"], ["tag2"]], include_untagged=False)

    def test_does_not_match_excluded_tag(self, definition):
        """Test that excluded tag (with ~) prevents matching."""
        definition.tags = ["tag1"]

        assert not definition.matches_tags([["~tag1"]], include_untagged=False)

    def test_matches_excluded_tag(self, definition):
        """Test that definitions without excluded tag match."""
        definition.tags = ["tag2"]

        assert definition.matches_tags([["~tag1"]], include_untagged=False)

    def test_complex_rules(self, definition):
        """Test complex tag matching rules."""
        definition.tags = ["tag1", "tag2", "tag3"]

        # Should match tag1 alone
        assert definition.matches_tags([["tag1"]], include_untagged=False)

        # Should match tag1 OR tag4 (has tag1)
        assert definition.matches_tags([["tag1", "tag4"]], include_untagged=False)

        # Should match tag1 AND tag2 AND tag3
        assert definition.matches_tags(
            [["tag1"], ["tag2"], ["tag3"]], include_untagged=False
        )

        # Should NOT match tag1 AND tag4 (missing tag4)
        assert not definition.matches_tags([["tag1"], ["tag4"]], include_untagged=False)

        # Should match tag4 OR NOT tag5 (doesn't have tag5)
        assert definition.matches_tags([["tag4", "~tag5"]], include_untagged=False)


class TestReferences:
    """Test reference functionality."""

    @pytest.fixture
    def setup_references(self):
        """Create reference and definition."""
        reference = TwineDefinition("reference-key")
        reference.comment = "reference comment"
        reference.tags = ["ref1"]
        reference.translations["en"] = "ref-value"

        definition = TwineDefinition("key")
        definition.reference_key = reference.key
        definition.reference = reference

        return definition

    def test_reference_comment_used(self, setup_references):
        """Test that reference comment is used when definition has none."""
        definition = setup_references

        assert definition.comment == "reference comment"

    def test_reference_comment_override(self, setup_references):
        """Test that definition comment overrides reference."""
        definition = setup_references
        definition.comment = "definition comment"

        assert definition.comment == "definition comment"

    def test_reference_tags_used(self, setup_references):
        """Test that reference tags are used when definition has none."""
        definition = setup_references

        assert definition.matches_tags([["ref1"]], include_untagged=False)

    def test_reference_tags_override(self, setup_references):
        """Test that definition tags override reference."""
        definition = setup_references
        definition.tags = ["tag1"]

        assert not definition.matches_tags([["ref1"]], include_untagged=False)
        assert definition.matches_tags([["tag1"]], include_untagged=False)

    def test_reference_translation_used(self, setup_references):
        """Test that reference translation is used when definition has none."""
        definition = setup_references

        assert definition.translation_for_lang("en") == "ref-value"

    def test_reference_translation_override(self, setup_references):
        """Test that definition translation overrides reference."""
        definition = setup_references
        definition.translations["en"] = "value"

        assert definition.translation_for_lang("en") == "value"
