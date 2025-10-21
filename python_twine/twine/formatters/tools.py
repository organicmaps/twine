from typing import Callable


def replace_with_filter(txt:str, old:str, new:str, do_replace:Callable[[int], bool]):
    """ Search in `txt` for `old` occurrences and replace with `new` but only
        if `do_replace` function/lambda returns True.
    """
    result = ""
    tail = txt
    offset = 0
    while old in tail:
        idx = tail.index(old)
        if do_replace(offset + idx):
            result += tail[:idx] + new
            offset += idx + len(old)
        else:
            result += tail[:idx] + old
            offset += idx + len(old)
        tail = tail[idx+len(old):]
    return result + tail
