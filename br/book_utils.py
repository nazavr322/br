import re
from collections.abc import Generator

import ebooklib
from ebooklib.epub import EpubBook


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

