import re
from collections.abc import Iterable
from glob import glob


def grep_folder(path:str, files_patterns:list[str], search_regex:re.Pattern) -> set[str]:
    """
    Scan directory for files in `path` directory by files pattern (e.g. "*.cpp", "*.swift")
    and scans each files with search_regex to extract all matches.
    """
    keys = set()
    for filepath in find_files_recursive(path, files_patterns):
        keys.update(find_keys_in_file(path + "/" + filepath, search_regex))
    return keys

def find_files_recursive(root_path:str, files_patterns:list[str]) -> Iterable[str]:
    """
    Scan directory for files matching patterns. Patterns expected in format "*.java", "strings.xml", etc.

    :return: relative files paths.
    """
    for pttrn in files_patterns:
        yield from glob(f"**/{pttrn}", root_dir=root_path, recursive=True)

def find_keys_in_file(filepath:str, search_regex:re.Pattern)->list[str]:
    """
    Scan file at `filepath` using regexp. All groups found by `search_regex` are merged
    to result list.

    :param filepath: path to text file
    :param search_regex: pattern to search source code for a string key
    :return: list of found keys
    """
    try:
        keys = []
        with open(filepath) as f:
            for line in f:
                m = search_regex.search(line)
                if m is not None:
                    keys += [k for k in m.groups() if k is not None]
        return keys
    except UnicodeDecodeError:
        return []
