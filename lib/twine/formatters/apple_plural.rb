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
        footer = "</dict>\n</plist>\n"
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
        result = "\t<key>#{key}</key>\n"
        result += "\t<dict>\n"
        result += "\t\t<key>NSStringLocalizedFormatKey</key>\n"
        result += "\t\t<string>\%\#@value@</string>\n"
        result += "\t\t<key>value</key>\n"
        result += "\t\t<dict>\n"
        result += "\t\t\t<key>NSStringFormatSpecTypeKey</key>\n"
        result += "\t\t\t<string>NSStringPluralRuleType</string>\n"
        result += "\t\t\t<key>NSStringFormatValueTypeKey</key>\n"
        result += "\t\t\t<string>d</string>\n"
        # Replace Android's %s with iOS %@
        result += plural_hash.map{|quantity,value| "\t\t\t<key>#{quantity}</key>\n\t\t\t<string>#{convert_placeholders_from_android_to_twine(value)}</string>"}.join("\n")
        result += "\n"
        result += "\t\t</dict>\n"
        result += "\t</dict>\n"
      end

      def format_comment(definition, lang)
        "<!-- #{definition.comment.gsub('--', '—')} -->\n" if definition.comment
      end

      def read(io, lang)
        raise NotImplementedError.new("Reading \".stringdict\" files not implemented yet")
      end

      def should_include_definition(definition, lang)
        return definition.is_plural? && definition.plural_translation_for_lang(lang)
      end
    end
  end
end

Twine::Formatters.formatters << Twine::Formatters::ApplePlural.new
