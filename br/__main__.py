import sys
from argparse import ArgumentParser

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QHBoxLayout, QWidget, QStatusBar, QLabel
)
from PyQt6.QtCore import QTemporaryDir, QDirIterator
from PyQt6.QtGui import QCloseEvent, QFontDatabase

import br.resources
from br.utils import q_iter_dir
from br.ui.widgets import BookReader, DecoratedLabel


class MainWindow(QMainWindow):
    def __init__(self, book_path: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        dir_it = q_iter_dir(
            ':/fonts/',
            ['*.ttf'],
            flags=QDirIterator.IteratorFlag.Subdirectories,
        )
        for font_file in dir_it:
            QFontDatabase.addApplicationFont(font_file)

        self.temp_dir = QTemporaryDir()
        
        self.main_layout = QHBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        screen_width = QApplication.primaryScreen().availableSize().width()
        self.book_reader = BookReader()
        self.book_reader.load_book(book_path, self.temp_dir.path())
        self.book_reader.setMaximumWidth(screen_width // 2)
        self.main_layout.addWidget(self.book_reader)
        self.setWindowTitle(
            f'{QApplication.applicationName()} - {self.book_reader.book.title}'
        )

        status_bar = QStatusBar()
        status_bar.setSizeGripEnabled(False)
        status_bar.addWidget(QLabel(self.book_reader.book.title))
        self.book_progress_label = DecoratedLabel(
            prefix='Progress: ', postfix=' %'
        )
        self._update_book_prog_label(
            self.book_reader.verticalScrollBar().value()
        )
        self.book_reader.verticalScrollBar().valueChanged.connect(
            self._update_book_prog_label
        )
        status_bar.addPermanentWidget(self.book_progress_label)
        self.setStatusBar(status_bar)

        main_widget = QWidget()
        main_widget.setLayout(self.main_layout)
        self.setCentralWidget(main_widget)

    def _update_book_prog_label(self, new_value: int):
        try:
            p = int(
                new_value / self.book_reader.verticalScrollBar().maximum() * 100
            )
        except Exception:
            p = 0
        self.book_progress_label.setNum(p)

    def closeEvent(self, event: QCloseEvent | None):
        self.temp_dir.remove()
        super().closeEvent(event)


def create_parser(*args, **kwargs) -> ArgumentParser:
    parser = ArgumentParser(*args, **kwargs)
    parser.add_argument('file', help='Path to the book')
    return parser


if __name__ == '__main__':
    parser = create_parser(prog='br')
    known_args, unknown_args = parser.parse_known_args()

    app = QApplication(sys.argv[:1] + unknown_args)
    app.setApplicationName('br')

    main_window = MainWindow(known_args.file)
    main_window.show()
    
    sys.exit(app.exec())

