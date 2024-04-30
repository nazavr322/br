import os
from hashlib import file_digest
from zipfile import ZipFile

from PyQt6.QtWidgets import QTextBrowser
from PyQt6.QtCore import QTemporaryDir, QUrl
from ebooklib import epub

from br.book_utils import get_css_content, get_html_content


class BookReader(QTextBrowser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.book = None
        self.extract_dir = None
        self.setOpenLinks(False)
        self.setOpenExternalLinks(True)
        self.anchorClicked.connect(self.scroll_to_anchor)

    def load_book(self, book_path: str, ext_base_dir: str | None):
        self.book = epub.read_epub(book_path)
        if ext_base_dir is None:
            ext_base_dir = QTemporaryDir().path()
        with open(book_path, 'rb') as f:
            book_hash = file_digest(f, 'md5').hexdigest()
            self.extract_dir = os.path.join(ext_base_dir, book_hash)
            with ZipFile(f) as zip:
                zip.extractall(self.extract_dir)
        self.setSearchPaths([self.extract_dir])
        self.document().setDefaultStyleSheet(
            ''.join(list(get_css_content(self.book)))
        )
        self.setHtml(''.join(list(get_html_content(self.book))))

    def scroll_to_anchor(self, url: QUrl):
        try:
            _, anchor = url.url().rsplit('#', 1)
        except ValueError:
            return 
        self.scrollToAnchor(anchor)

