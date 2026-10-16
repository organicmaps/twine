module Twine
  module Processors

    class OutputProcessor
      FALLBACK_MAPPING = {
        'zh-CN' => 'zh-Hans',
        'zh-TW' => 'zh-Hant',
        'zh-HK' => 'zh-Hant',
        'zh-MO' => 'zh-Hant'
      }.freeze
      REGIONAL_LANGUAGE = /\A([a-zA-Z]{2,3})-[a-zA-Z]+/

      def initialize(twine_file, options)
        @twine_file = twine_file
        @options = options
      end

      def default_language
        @options[:developer_language] || @twine_file.language_codes[0]
      end

      def fallback_languages(language)
        match = REGIONAL_LANGUAGE.match(language)
        [FALLBACK_MAPPING[language], match && match[1], default_language]
          .compact.uniq.reject { |candidate| candidate == language }
      end

      def process(language)
        result = TwineFile.new
        fallbacks = fallback_languages(language)
        include_option = @options[:include]
        tags = @options[:tags]
        untagged = @options[:untagged]

        result.language_codes.concat @twine_file.language_codes
        @twine_file.sections.each do |section|
          new_section = TwineSection.new section.name

          section.definitions.each do |definition|
            next unless definition.matches_tags?(tags, untagged)

            value = definition.translation_for_lang(language)
            has_translation = !value.nil?

            next if has_translation && include_option == :untranslated

            if !has_translation && include_option != :translated
              value = definition.translation_for_lang(fallbacks)
            end

            next unless value

            new_definition = definition.dup
            new_definition.translations[language] = value

            forms = definition.plural_translation_for_lang(language)
            if forms.nil? && !has_translation && include_option != :translated
              fallbacks.each do |fallback|
                forms = definition.plural_translation_for_lang(fallback)
                break unless forms.nil?
              end
            end
            if forms
              forms['other'] = value unless forms.key?('other')
              new_definition.plural_translations[language] = forms
              new_definition.translations[language] = forms['other']
            end

            new_section.definitions << new_definition
            result.definitions_by_key[new_definition.key] = new_definition
          end

          result.sections << new_section
        end

        return result
      end
    end

  end
end
