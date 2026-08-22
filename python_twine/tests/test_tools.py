from twine.formatters.tools import replace_with_filter


class TestTools:
    def test_replace_with_filter(self):
        # Edge case
        assert replace_with_filter("", "11", "22", lambda x: True) == ""

        # Test lambda invocation
        assert replace_with_filter("aaaaaaaa", "a", "N", lambda idx: idx%2 == 0) == "NaNaNaNa"

        # Test lambda with captured `txt` variable
        txt = "001100110011"
        def is_in_second_half(idx:int):
            nonlocal txt
            return idx >= len(txt)//2
        assert replace_with_filter(txt, "11", "22", is_in_second_half) == "001100220022"

        # Test lambda with captured `txt` variable
        txt = "& [&] &"
        def is_in_braces(idx:int):
            return "[" in txt[:idx] and \
                "]" not in txt[txt.rfind("[", 0, idx):idx]
        assert replace_with_filter(txt, "&", "&amp;", is_in_braces) == "& [&amp;] &"

        # Make sure symbols from `new` are not subject to replace
        txt = "((("
        assert replace_with_filter(txt, "(", "((", lambda x: True) == "(((((("

        # Replace only if the previous match was more than 2 symbols before
        last_idx = None
        def is_far_enough(idx):
            nonlocal last_idx
            if last_idx is None:
                last_idx = idx
                return False
            else:
                answer = (idx - last_idx) > 2
                last_idx = idx
                return answer
        txt = "^_^__^___^_^_^"
        assert replace_with_filter(txt, "^", "#", is_far_enough) == "^_^__#___#_^_^"
