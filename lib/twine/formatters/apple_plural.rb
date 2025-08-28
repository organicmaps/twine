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
        require 'rexml/document'
        begin
          document = REXML::Document.new(io)
        rescue REXML::ParseException => e
          raise Twine::Error.new("Unable to parse .stringsdict file: #{e.message}")
        end

        root_dict = document.elements['plist/dict'] #|| document.root && document.root.name == 'dict' ? document.root : nil
        return unless root_dict

        # Iterate through top-level <key> elements. Each should be followed by a <dict> describing the plural.
        root_children = root_dict.children
        root_children.each_with_index do |node, idx|
          next unless node.is_a?(REXML::Element) && node.name == 'key'
          key_name = node.text
          next unless key_name && key_name.length > 0

          value_container = node.next_element
          next unless value_container && value_container.name == 'dict'

          # Attempt to capture a comment immediately preceding the <key> element.
          comment_text = nil
          back = idx - 1
          while back >= 0
            prev = root_children[back]
            if prev.is_a?(REXML::Comment)
              comment_text = prev.string.strip
              break
            elsif prev.is_a?(REXML::Element) || (prev.is_a?(REXML::Text) && prev.to_s.strip.length > 0)
              break # Stop at previous non-whitespace content element.
            end
            back -= 1
          end

          plural_hash = {}

          # Inside value_container we look for <key>value</key><dict> ... plural entries ... </dict>
          value_container.elements.each('key') do |inner_key|
            next unless inner_key.text == 'value'
            plural_dict = inner_key.next_element
            next unless plural_dict && plural_dict.name == 'dict'

            plural_dict.elements.each('key') do |pkey_elem|
              pkey = pkey_elem.text
              next unless Twine::TwineDefinition::PLURAL_KEYS.include?(pkey)
              string_elem = pkey_elem.next_element
              next unless string_elem && string_elem.name == 'string'
              pvalue = string_elem.text.to_s
              # Apple's placeholders already match Twine's (%@, %d, etc.), so store directly.
              plural_hash[pkey] = pvalue
            end
          end

          next if plural_hash.empty?

          # Ensure definition exists (reuse logic similar to set_translation_for_key for creation when consume_all)
          definition = @twine_file.definitions_by_key[key_name]
          unless definition
            if @options[:consume_all]
              Twine::stdout.puts "Adding new plural definition '#{key_name}' to twine file."
              current_section = @twine_file.sections.find { |s| s.name == 'Uncategorized' }
              unless current_section
                current_section = Twine::TwineSection.new('Uncategorized')
                @twine_file.sections.insert(0, current_section)
              end
              definition = Twine::TwineDefinition.new(key_name)
              current_section.definitions << definition
              @twine_file.definitions_by_key[key_name] = definition
            else
              Twine::stdout.puts "WARNING: '#{key_name}' not found in twine file (plural)."
              next
            end
          end

          # Merge plural translations
          lang_hash = (definition.plural_translations[lang] ||= {})
          plural_hash.each do |pk, pv|
            lang_hash[pk] = pv
          end

          # Set base translation to 'other' (fallback) if present
            if plural_hash['other']
              set_translation_for_key(key_name, lang, plural_hash['other'])
            end

          # Record comment if requested
          if comment_text && @options[:consume_comments]
            set_comment_for_key(key_name, comment_text)
          end

          # Ensure language code present
          unless @twine_file.language_codes.include?(lang)
            @twine_file.add_language_code(lang)
          end
        end
      end

      def should_include_definition(definition, lang)
        return definition.is_plural? && definition.plural_translation_for_lang(lang)
      end
    end
  end
end

Twine::Formatters.formatters << Twine::Formatters::ApplePlural.new
