module Twine
  module Formatters
    class ApplePlural < Apple
      include Twine::Placeholders

      SUPPORTS_PLURAL = true

      def format_name
        'apple-plural'
      end

      def extension
        '.stringsdict'
      end

      def default_file_name
        'Localizable.stringsdict'
      end

      def format_footer(lang)
        footer = "</dict>\n</plist>"
      end

      def format_file(lang)
        result = super
        result += format_footer(lang)
      end

      def format_header(lang)
        header =  "<\?xml version=\"1.0\" encoding=\"UTF-8\"\?>\n"
        header += "<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">\n"
        header += "<plist version=\"1.0\">\n<dict>"
      end

      def format_section_header(section)
        "<!-- ********** #{section.name} **********/ -->\n"
      end

      def format_plural_keys(key, plural_hash)
        result = "#{tab(2)}<key>#{key}</key>\n"
        result += "#{tab(2)}<dict>\n"
        result += "#{tab(4)}<key>NSStringLocalizedFormatKey</key>\n"
        result += "#{tab(4)}<string>\%\#@value@</string>\n"
        result += "#{tab(4)}<key>value</key>\n"
        result += "#{tab(4)}<dict>\n"
        result += "#{tab(6)}<key>NSStringFormatSpecTypeKey</key>\n"
        result += "#{tab(6)}<string>NSStringPluralRuleType</string>\n"
        result += "#{tab(6)}<key>NSStringFormatValueTypeKey</key>\n"
        "#{tab(6)}<string>d</string>\n"
        # Replace Android's %s with iOS %@
        result += plural_hash.map{|quantity,value| "#{tab(6)}<key>#{quantity}</key>\n#{tab(6)}<string>#{convert_placeholders_from_android_to_twine(value)}</string>"}.join("\n")
        result += "\n"
        result += "#{tab(4)}</dict>\n"
        result += "#{tab(2)}</dict>\n"
      end

      def format_comment(definition, lang)
        "<!-- #{definition.comment.gsub('--', '—')} -->\n" if definition.comment
      end

      def read(io, lang)
        raise NotImplementedError.new("Reading \".stringdict\" files not implemented yet")
      end

      def tab(level)
        ' ' * level
      end

      def should_include_definition(definition, lang)
        return definition.is_plural? && definition.plural_translation_for_lang(lang)
      end
    end
  end
end

Twine::Formatters.formatters << Twine::Formatters::ApplePlural.new
