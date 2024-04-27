import sys
from argparse import ArgumentParser

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtCore import QTemporaryDir
from PyQt6.QtGui import QCloseEvent

from br.ui.widgets import BookReader


class MainWindow(QMainWindow):
    def __init__(self, book_path: str, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.temp_dir = QTemporaryDir()
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.book_reader = BookReader()
        self.book_reader.load_book(book_path, self.temp_dir.path())
        main_layout.addWidget(self.book_reader)

        main_widget = QWidget()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
    
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

