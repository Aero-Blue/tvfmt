from pathlib import Path
from typing import List, Tuple

from questionary import Choice


def find_by_attr(lst, attr, value):
    for i in lst:
        if hasattr(i, attr) and getattr(i, attr) == value:
            return i


def as_choices(lst):
    return [Choice(title=str(i), value=i) for i in lst]


# Get all files in specified directory
def get_files(path: Path, sort: bool = True) -> List[Path]:
    files = []
    for f in Path.iterdir(path):
        # ignore dotfiles
        if f.is_file() and not f.name.startswith("."):
            files.append(f)
    if sort:
        files.sort()
    return files


def rename_files(paths: List[Tuple[Path, Path]]):
    for old_file, new_file in paths:
        old_file.rename(new_file)


def short_path(path: Path) -> str:
    return path.as_posix().replace(str(Path.home()), "~")
