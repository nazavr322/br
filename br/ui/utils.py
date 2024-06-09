import re
from typing import Generator, NamedTuple

import ebooklib
from ebooklib.epub import EpubBook
from PyQt6.QtGui import QImage, QPixmap


class Illustration(NamedTuple):
    img_data: str
    block_num: int
    caption: str | None = None


def _get_content(book: EpubBook, item_type: int) -> Generator[str, None, None]:
    yield from (
        item.get_content().decode('utf-8')
        for item in book.get_items_of_type(item_type)
    )


def get_html_content(book: EpubBook) -> Generator[str, None, None]: 
    return _get_content(book, ebooklib.ITEM_DOCUMENT)


def get_css_content(book: EpubBook) -> Generator[str, None, None]:
    return _get_content(book, ebooklib.ITEM_STYLE)


def remove_font_family(s: str) -> str:
    return re.sub(r'(?<=;|"|\s)font-family[^;]*(;)?', '', s)


def truncate_str(s: str, l: int = 79, trun_char: str = '...') -> str:
    return s[:l - len(trun_char)] + trun_char if len(s) > l else s


def scale_to_largest(w: int, h: int, largest_side: int) -> tuple[int, int]:
    if w > h:
        scale = largest_side / w
    else:
        scale = largest_side / h
    return int(w * scale), int(h * scale)

