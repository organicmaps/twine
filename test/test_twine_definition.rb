require 'twine_test'

class TestTwineDefinition < TwineTest
  class TestTags < TwineTest
    def setup
      super
      @definition = Twine::TwineDefinition.new 'key'
    end

    def test_include_untagged
      assert @definition.matches_tags?([[rand(100000).to_s]], true)
    end

    def test_matches_no_given_tags
      assert @definition.matches_tags?([], false)
    end

    def test_matches_tag
      @definition.tags = ['tag1']

      assert @definition.matches_tags?([['tag1']], false)
    end

    def test_matches_any_tag
      @definition.tags = ['tag1']

      assert @definition.matches_tags?([['tag0', 'tag1', 'tag2']], false)
    end

    def test_matches_all_tags
      @definition.tags = ['tag1', 'tag2']

      assert @definition.matches_tags?([['tag1'], ['tag2']], false)
    end

    def test_does_not_match_all_tags
      @definition.tags = ['tag1']

      refute @definition.matches_tags?([['tag1'], ['tag2']], false)
    end

    def test_does_not_match_excluded_tag
      @definition.tags = ['tag1']

      refute @definition.matches_tags?([['~tag1']], false)
    end

    def test_matches_excluded_tag
      @definition.tags = ['tag2']

      assert @definition.matches_tags?([['~tag1']], false)
    end

    def test_complex_rules
      @definition.tags = ['tag1', 'tag2', 'tag3']

      assert @definition.matches_tags?([['tag1']], false)
      assert @definition.matches_tags?([['tag1', 'tag4']], false)
      assert @definition.matches_tags?([['tag1'], ['tag2'], ['tag3']], false)
      refute @definition.matches_tags?([['tag1'], ['tag4']], false)

      assert @definition.matches_tags?([['tag4', '~tag5']], false)
    end
  end

  class TestReferences < TwineTest
    def setup
      super

      @reference = Twine::TwineDefinition.new 'reference-key'
      @reference.comment = 'reference comment'
      @reference.tags = ['ref1']
      @reference.translations['en'] = 'ref-value'

      @definition = Twine::TwineDefinition.new 'key'
      @definition.reference_key = @reference.key
      @definition.reference = @reference
    end

    def test_reference_comment_used
      assert_equal 'reference comment', @definition.comment
    end

    def test_reference_comment_override
      @definition.comment = 'definition comment'

      assert_equal 'definition comment', @definition.comment
    end

    def test_reference_tags_used
      assert @definition.matches_tags?([['ref1']], false)
    end

    def test_reference_tags_override
      @definition.tags = ['tag1']

      refute @definition.matches_tags?([['ref1']], false)
      assert @definition.matches_tags?([['tag1']], false)
    end

    def test_reference_translation_used
      assert_equal 'ref-value', @definition.translation_for_lang('en')
    end

    def test_reference_translation_override
      @definition.translations['en'] = 'value'

      assert_equal 'value', @definition.translation_for_lang('en')
    end

    def test_reference_respects_language_priority
      @definition.translations['en'] = 'Pedestrian Bridge'
      @reference.translations['fr'] = 'Pont'

      assert_equal 'Pont', @definition.translation_for_lang(%w(fr en))
      assert_equal 'Pont', @definition.translation_for_lang(%w(de fr en))
      assert_equal 'Pedestrian Bridge', @definition.translation_for_lang(%w(de en))
      assert_nil @definition.translation_for_lang(['de'])
      assert_nil @definition.translation_for_lang([])
    end

    def test_language_priority_through_reference_chain
      @definition.translations['en'] = 'Pedestrian Bridge'
      reference = Twine::TwineDefinition.new 'bridge'
      reference.translations['fr'] = 'Pont'
      @reference.reference = reference

      assert_equal 'Pont', @definition.translation_for_lang(%w(fr en))
    end

    def test_empty_translation_overrides_reference
      @definition.translations['en'] = ''

      assert_equal '', @definition.translation_for_lang(['en'])
    end
  end
end
