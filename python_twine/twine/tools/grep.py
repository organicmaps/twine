import re
from typing import Set, List, Iterable
from glob import glob

def grep_folder(path:str, files_patterns:List[str], search_regex:re.Pattern) -> Set[str]:
    keys = set()
    for filepath in find_files_recursive(path, files_patterns):
        keys.update(find_keys_in_file(path + "/" + filepath, search_regex))
    return keys

def find_files_recursive(root_path:str, files_patterns:List[str]) -> Iterable[str]:
    for pttrn in files_patterns:
        yield from glob(f"**/{pttrn}", root_dir=root_path, recursive=True)

def find_keys_in_file(filepath:str, search_regex:re.Pattern)->List[str]:
    try:
        keys = []
        for line in open(filepath, "r"):
            m = search_regex.search(line)
            if m is not None:
                keys += m.groups()
        return keys
    except UnicodeDecodeError:
        return []
