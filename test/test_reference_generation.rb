require 'twine_test'

class TestReferenceGeneration < TwineTest
  PLURALS = "[count]\nen:one = %d bridge\nen:other = %d bridges\n" \
            "fr:one = %d pont\nfr:other = %d ponts\n" \
            "[middle]\nref = count\n[alias]\nref = middle\n"

  def read_twine(text)
    path = File.join(@output_dir, 'strings.txt')
    File.write(path, text)
    result = Twine::TwineFile.new
    result.read(path)
    result
  end

  def format_file(twine_file, formatter_type, language, options = {})
    formatter = formatter_type.new
    formatter.twine_file = twine_file
    formatter.options = { include: :all }.merge(options)
    formatter.format_file(language)
  end

  def test_generated_fallbacks_do_not_mutate_source_or_depend_on_order
    base = "[base]\nen = Bridge\n"
    derived = "[alias]\nref = base\nen = Pedestrian Bridge\n"
    [base + derived, derived + base].each do |text|
      twine_file = read_twine(text)
      before = Marshal.dump(twine_file)
      processor = Twine::Processors::OutputProcessor.new(twine_file, include: :all)
      result = processor.process('fr-CA')
      assert_equal 'Pedestrian Bridge', result.definitions_by_key['alias'].translations['fr-CA']
      assert_equal before, Marshal.dump(twine_file)
      assert_equal result.definitions_by_key['alias'].translations, processor.process('fr-CA').definitions_by_key['alias'].translations
    end
  end

  def test_copied_plural_maps_are_independent
    twine_file = read_twine(PLURALS)
    source = twine_file.definitions_by_key['count']
    result = Twine::Processors::OutputProcessor.new(twine_file, {}).process('fr')
    result.definitions_by_key['count'].plural_translations['fr']['one'] = 'changed'
    assert_equal '%d pont', source.plural_translations['fr']['one']
  end

  def test_plural_completion_does_not_add_source_forms
    twine_file = read_twine(
      "[count]\nen:one = %d bridge\nen:other = %d bridges\nfr:one = %d pont\n"
    )
    result = Twine::Processors::OutputProcessor.new(twine_file, {}).process('fr')
    assert_equal({ 'one' => '%d pont', 'other' => '%d bridges' },
                 result.definitions_by_key['count'].plural_translations['fr'])
    assert_equal({ 'one' => '%d pont' }, twine_file.definitions_by_key['count'].plural_translations['fr'])
  end

  def test_android_plural_aliases_keep_all_forms
    %w(fr fr-CA).each do |language|
      twine_file = read_twine(PLURALS)
      output = format_file(twine_file, Twine::Formatters::Android, language)
      root = REXML::Document.new(output).root
      %w(count middle alias).each do |key|
        plural = root.elements["plurals[@name='#{key}']"]
        refute_nil plural
        assert_equal '%d pont', plural.elements["item[@quantity='one']"].text
        assert_equal '%d ponts', plural.elements["item[@quantity='other']"].text
      end
      assert_empty twine_file.definitions_by_key['alias'].plural_translations
    end
  end

  def test_apple_routes_plural_aliases_to_stringsdict
    twine_file = read_twine(PLURALS)
    regular = format_file(twine_file, Twine::Formatters::Apple, 'fr-CA')
    assert_empty regular.strip
    output = format_file(twine_file, Twine::Formatters::ApplePlural, 'fr-CA')
    root = REXML::Document.new(output).elements['plist/dict']
    keys = root.elements.to_a('key')
    assert_equal %w(count middle alias), keys.map(&:text)
    keys.each do |key|
      forms = key.next_element.elements['dict']
      values = forms.elements.to_a('key').to_h { |entry| [entry.text, entry.next_element.text] }
      assert_equal '%d pont', values['one']
      assert_equal '%d ponts', values['other']
    end
  end

  def test_singular_values_override_inherited_plural_type
    [:all, :translated].each do |include_option|
      ['Passerelle', ''].each do |value|
        twine_file = read_twine(PLURALS + "fr = #{value}\n")
        output = format_file(twine_file, Twine::Formatters::Android, 'fr', include: include_option)
        root = REXML::Document.new(output).root
        node = root.elements["string[@name='alias']"]
        refute_nil node
        assert_equal value, node.text.to_s
        assert_nil root.elements["plurals[@name='alias']"]
      end
    end
  end

  def test_empty_values_count_as_translated
    [:all, :translated, :untranslated].each do |include_option|
      twine_file = read_twine("[base]\nen = Bridge\nfr = \n[alias]\nref = base\n")
      result = Twine::Processors::OutputProcessor.new(twine_file, include: include_option).process('fr')
      if include_option == :untranslated
        assert_empty result.definitions_by_key
      else
        assert_equal %w(base alias), result.definitions_by_key.keys
        result.definitions_by_key.each_value { |definition| assert_equal '', definition.translations['fr'] }
      end
    end
  end

  def test_chinese_and_three_letter_fallbacks
    expected = {
      'zh-CN' => %w(zh-Hans zh en),
      'zh-HK' => %w(zh-Hant zh en),
      'zh-MO' => %w(zh-Hant zh en),
      'yue-HK' => %w(yue en),
      'yue-MO' => %w(yue en),
      'ast-ES' => %w(ast en),
      'en' => []
    }
    twine_file = read_twine("[base]\nen = Bridge\nzh-Hant = 橋\n")
    processor = Twine::Processors::OutputProcessor.new(twine_file, {})
    expected.each { |language, fallbacks| assert_equal fallbacks, processor.fallback_languages(language) }
    result = processor.process('zh-HK')
    assert_equal '橋', result.definitions_by_key['base'].translations['zh-HK']
  end

  def test_gettext_resolves_inherited_developer_text
    twine_file = read_twine(
      "[base]\nen = Bridge\nfr = Pont\n[middle]\nref = base\n[alias]\nref = middle\n"
    )
    output = format_file(twine_file, Twine::Formatters::Gettext, 'fr')
    assert_includes output, "msgctxt \"alias\"\nmsgid \"Bridge\"\nmsgstr \"Pont\""
  end

  def test_gettext_honors_developer_language_option
    twine_file = read_twine("[base]\nen = Bridge\nfr = Pont\n")
    output = format_file(twine_file, Twine::Formatters::Gettext, 'en', developer_language: 'fr')
    assert_includes output, "msgid \"Pont\"\nmsgstr \"Bridge\""
  end

  def test_empty_plural_output_is_skippable
    assert_nil format_file(Twine::TwineFile.new, Twine::Formatters::ApplePlural, 'fr')
  end

  def test_read_rejects_dangling_and_circular_references
    cases = [
      ["[alias]\nen = Alias\nref = absent\n", "Unknown reference 'absent'"],
      ["[alias]\nen = Alias\nref = alias\n", 'Circular reference'],
      ["[a]\nref = b\n[b]\nref = a\n", 'Circular reference']
    ]
    cases.each do |text, message|
      error = assert_raises(Twine::Error) { read_twine(text) }
      assert_includes error.message, message
    end
  end

  def test_forward_and_shared_references_are_valid
    twine_file = read_twine(
      "[alias]\nref = middle\n[other]\nref = middle\n[middle]\nref = base\n[base]\nen = Bridge\n"
    )
    assert_equal 'Bridge', twine_file.definitions_by_key['alias'].translation_for_lang('en')
    assert_equal 'Bridge', twine_file.definitions_by_key['other'].translation_for_lang('en')
  end

  def test_validation_rejects_a_mutated_cycle
    twine_file = read_twine("[base]\nen = Bridge\n[alias]\nref = base\n")
    definition = twine_file.definitions_by_key['alias']
    definition.reference = definition
    error = assert_raises(Twine::Error) { Twine::Runner.new({}, twine_file).validate_twine_file }
    assert_includes error.message, 'Circular reference'
  end
end
