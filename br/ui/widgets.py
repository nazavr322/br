import os
from hashlib import file_digest
from zipfile import ZipFile

from PyQt6.QtWidgets import QTextBrowser
from PyQt6.QtCore import QTemporaryDir, QUrl, Qt
from PyQt6.QtGui import (
    QFont, QTextCursor, QTextBlockFormat, QContextMenuEvent, QAction
)
from ebooklib import epub

from br.book_utils import get_css_content, get_html_content, remove_font_family


class BookReader(QTextBrowser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.book = None
        self.extract_dir = None

        self.gi_action = QAction('Generate Illustration', self)
        self.set_gi_action_enabled(False)

        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setOpenLinks(False)
        self.setOpenExternalLinks(True)
        self.setFont(QFont('Literata', 15))
        self.document().setDocumentMargin(50)

        self.anchorClicked.connect(self.scroll_to_anchor)
        self.copyAvailable.connect(self.set_gi_action_enabled)

    def _modify_block_format(
        self,
        line_height: float | None = None,
        text_indent: float | None = None,
    ):
        assert line_height is not None or text_indent is not None
        block_fmt = QTextBlockFormat()
        if line_height is not None:
            block_fmt.setLineHeight(
                line_height,
                QTextBlockFormat.LineHeightTypes.ProportionalHeight.value,
            )
        if text_indent is not None:
            block_fmt.setTextIndent(text_indent)
        cursor = self.textCursor()
        cursor.clearSelection()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.mergeBlockFormat(block_fmt)
        cursor.clearSelection()

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
            remove_font_family(''.join(list(get_css_content(self.book))))
        )
        self.setHtml(
            remove_font_family(''.join(list(get_html_content(self.book))))
        )
        self._modify_block_format(150, 50)

    def scroll_to_anchor(self, url: QUrl):
        try:
            _, anchor = url.url().rsplit('#', 1)
        except ValueError:
            return 
        self.scrollToAnchor(anchor)

    def contextMenuEvent(self, e: QContextMenuEvent | None) -> None:
        scroll_pos = e.pos()
        scroll_pos.setX(scroll_pos.x() + self.horizontalScrollBar().value())
        scroll_pos.setY(scroll_pos.y() + self.verticalScrollBar().value())
        menu = self.createStandardContextMenu(scroll_pos)
        menu.addAction(self.gi_action)
        menu.exec(e.globalPos())

    def set_gi_action_enabled(self, enabled: bool):
        self.gi_action.setEnabled(enabled)

