from collections.abc import Generator

from PyQt6.QtCore import QDirIterator


def q_iter_dir(*args, **kwargs) -> Generator[str, None, None]:
    dir_it = QDirIterator(*args, **kwargs)
    while dir_it.hasNext():
        yield dir_it.next()

