import os
import html
from uuid import uuid4
from hashlib import file_digest
from zipfile import ZipFile
from base64 import b64decode
from abc import ABCMeta, ABC, abstractmethod
from typing import Iterable, Any
from functools import partial

from PyQt6.QtWidgets import (
    QTextBrowser,
    QDialog,
    QDialogButtonBox,
    QVBoxLayout,
    QPlainTextEdit,
    QGroupBox,
    QFormLayout,
    QHBoxLayout,
    QComboBox,
    QWidget,
    QSlider,
    QSpinBox,
    QTabWidget,
    QApplication,
    QLabel,
    QStackedLayout,
)
from PyQt6.QtCore import (
    QTemporaryDir, QUrl, Qt, QThreadPool, QObject, pyqtSignal
)
from PyQt6.QtGui import (
    QTextCursor,
    QTextBlockFormat,
    QContextMenuEvent,
    QAction,
    QPixmap,
    QTextDocument,
    QTextImageFormat,
    QFont,
)
from ebooklib import epub

from br.ui.utils import (
    get_css_content,
    get_html_content,
    remove_font_family,
    truncate_str,
    Illustration,
    scale_to_largest,
)
from br.imagen.backends import (
    SdWebUIBackend, GenerationParamType, OpenAIBackend
)
from br.imagen.backends.base import ImagenBackend
from br.ui.multithreading import Worker


CAPTION_TEMPLATE = '<br><i><small>{}</small></i>'
ILL_MAX_DIM = 768
NEG_PROMPT = """lowres, text, error, cropped, worst quality, low quality, jpeg artifacts, ugly, duplicate, morbid, mutilated, out of frame, extra fingers, mutated hands, poorly drawn hands, poorly drawn face, mutation, deformed, blurry, bad anatomy, bad proportions, extra limbs, cloned face, disfigured, gross proportions, malformed limbs, missing arms, missing legs, extra arms, extra legs, fused fingers, too many fingers, long neck, username, watermark, signature"""


class QMeta(ABCMeta, type(QObject)):
    pass


class GenerationParamMixin(ABC):
    @abstractmethod
    def param_value(self) -> Any:
        pass
 

class ComboBoxParam(GenerationParamMixin, QComboBox, metaclass=QMeta):
    def __init__(self, options: Iterable[str], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.addItems(options)

    def param_value(self) -> str:
        return self.currentText()


class IntNumberParam(GenerationParamMixin, QWidget, metaclass=QMeta):
    def __init__(
        self,
        *args,
        min_value: int = 0,
        max_value: int = 100,
        init_value: int = 0,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.spin_box = QSpinBox()
        self.slider.setRange(min_value, max_value)
        self.spin_box.setRange(min_value, max_value)
        self.slider.valueChanged.connect(self.update_spin_box)
        self.spin_box.valueChanged.connect(self.update_slider)
        self.slider.setValue(init_value)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.slider)
        layout.addWidget(self.spin_box)
        self.setLayout(layout)

    def update_spin_box(self, new_value: int):
        self.spin_box.blockSignals(True)
        self.spin_box.setValue(new_value)
        self.spin_box.blockSignals(False)

    def update_slider(self, new_value: int):
        self.slider.blockSignals(True)
        self.slider.setValue(new_value)
        self.slider.blockSignals(False)

    def param_value(self) -> int:
        return self.spin_box.value()


class GenerationParamsBox(QGroupBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._param_type2widget = {
            GenerationParamType.COMBO_BOX: ComboBoxParam,
            GenerationParamType.INT_NUMBER: IntNumberParam,
        }
        self._label2row_num = {}

        layout = QFormLayout()
        layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        self.setLayout(layout)

    def add_param(
        self, type: GenerationParamType, label: str, *args, **kwargs
    ) -> int:
        if label in self._label2row_num:
            raise ValueError(f'Widget with label {label} already exists')
        widget = self._param_type2widget[type](*args, **kwargs)
        self.layout().addRow(label, widget)
        row_num, _ = self.layout().getWidgetPosition(widget)
        self._label2row_num[label] = row_num
        return row_num

    def fieldForLabel(self, label: str) -> GenerationParamMixin | None:
        row_num = self._label2row_num.get(label)
        if row_num is None:
            return row_num
        return self.layout().itemAt(
            row_num, QFormLayout.ItemRole.FieldRole
        ).widget()


class PromptEditor(QPlainTextEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFont(QFont('Monospace', 10))


class GIDialog(QDialog):
    def __init__(self, pos_prompt: str, neg_prompt: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle(
            f'{QApplication.applicationName()} - Configure Illustration'
        )
        self._backend_factory = {
            'Stable Diffusion WebUI': partial(
                SdWebUIBackend,
                os.environ['SD_WEB_UI_API_HOST'],
                int(os.environ['SD_WEB_UI_API_PORT']),
            ),
            'OpenAI': OpenAIBackend,
        }
        self._backends: list[ImagenBackend | None] = [
            None for _ in self._backend_factory
        ]

        main_layout = QVBoxLayout()
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        left_panel_layout = QVBoxLayout()
        left_panel_layout.setContentsMargins(0, 0, 0, 0)

        left_panel_layout.addWidget(QLabel('Backend'))
        self.backend_cbox = QComboBox()
        self.backend_cbox.addItems(self._backend_factory)
        self.backend_cbox.currentIndexChanged.connect(
            self._on_backend_cbox_change
        )
        left_panel_layout.addWidget(self.backend_cbox)

        self.generation_params_box_layout = QStackedLayout()
        left_panel_layout.addLayout(self.generation_params_box_layout)
        controls_layout.addLayout(left_panel_layout)

        self.pos_prompt_ed = PromptEditor(pos_prompt)
        self.neg_prompt_ed = PromptEditor(neg_prompt)
        self.prompt_tabs = QTabWidget(self)
        self.prompt_tabs.setUsesScrollButtons(False)
        self.prompt_tabs.addTab(self.pos_prompt_ed, 'Positive Prompt')
        self.prompt_tabs.addTab(self.neg_prompt_ed, 'Negative Prompt')
        controls_layout.addWidget(self.prompt_tabs)
        main_layout.addLayout(controls_layout)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel, self
        )
        self.button_box.addButton(
            'Generate', QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self.setLayout(main_layout)

        self._on_backend_cbox_change(0)

    def _get_param_value(self, label: str):
        param = self.generation_params_box.fieldForLabel(label)
        if param is None:
            raise RuntimeError(f"Parameter '{label}' is missing")
        return param.param_value()

    @property
    def generation_params_box(self) -> GenerationParamsBox:
        return self.generation_params_box_layout.currentWidget()

    @property
    def pos_prompt(self) -> str:
        return self.pos_prompt_ed.toPlainText()

    @property
    def neg_prompt(self) -> str:
        return self.neg_prompt_ed.toPlainText()

    @property
    def backend(self) -> ImagenBackend:
        return self._backends[self.backend_cbox.currentIndex()]

    @property
    def generation_params(self) -> dict[str, Any]:
        return {
            name: self._get_param_value(param['display_name'])
            for name, param in self.backend.generation_params.items()
        }
    
    def _on_backend_cbox_change(self, idx: int):
        backend = self._backends[idx] 
        if backend is None:
            backend = self._backend_factory[self.backend_cbox.currentText()]()
            self._backends[idx] = backend
            gen_params_box = GenerationParamsBox('Generation Parameters')
            for param in backend.generation_params.values():
                gen_params_box.add_param(
                    param['type'], param['display_name'], **param['params']
                )
            self.generation_params_box_layout.addWidget(gen_params_box)
        self.generation_params_box_layout.setCurrentIndex(idx)
        self.prompt_tabs.setTabEnabled(
            self.prompt_tabs.indexOf(self.neg_prompt_ed),
            backend.supports_neg_prompt,
        )


class BookReader(QTextBrowser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.book = None
        self.extract_dir = None
        self.thread_pool = QThreadPool(self)

        self.gi_action = QAction('Generate Illustration', self)
        self.gi_action.setEnabled(False)
        self.gi_action.triggered.connect(self.open_gi_dialog)

        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setOpenLinks(False)
        self.setOpenExternalLinks(True)
        self.document().setDocumentMargin(50)

        self.anchorClicked.connect(self.scroll_to_anchor)
        self.copyAvailable.connect(self.gi_action.setEnabled)

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

    def _move_cursor_to_block_n(self, n: int) -> QTextCursor:
        cursor = QTextCursor(self.document().findBlockByNumber(n))
        self.setTextCursor(cursor)
        return cursor

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

    def insert_illustration(
        self,
        name: QUrl,
        pos: int,
        width: float | None = None,
        height: float | None = None,
        caption: str | None = None,
    ):
        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.setPosition(pos)
        block_fmt = QTextBlockFormat()
        block_fmt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        block_fmt.setTopMargin(20)
        block_fmt.setBottomMargin(20)
        cursor.insertBlock(block_fmt)
        ill_fmt = QTextImageFormat()
        ill_fmt.setName(name.url())
        if width and height:
            ill_fmt.setWidth(width) 
            ill_fmt.setHeight(height)
        cursor.insertImage(ill_fmt)
        if caption:
            cursor.insertHtml(CAPTION_TEMPLATE.format(html.escape(caption)))
        cursor.endEditBlock()

    def handle_illustration(self, ill: Illustration):
        img = QPixmap()
        img_data = b64decode(ill.img_data)
        img.loadFromData(img_data)
        with open('test.png', 'wb') as f:
            f.write(img_data)
        img_id = QUrl(uuid4().hex)
        self.document().addResource(
            QTextDocument.ResourceType.ImageResource.value, img_id, img
        )
        ill_w, ill_h = img.width(), img.height()
        if ill_w > ILL_MAX_DIM or ill_h > ILL_MAX_DIM:
            ill_w, ill_h = scale_to_largest(ill_w, ill_h, ILL_MAX_DIM)
        self.textCursor().clearSelection()
        cursor = self._move_cursor_to_block_n(ill.block_num)
        cursor.movePosition(cursor.MoveOperation.EndOfBlock)
        self.insert_illustration(
            img_id, cursor.position(), ill_w, ill_h, ill.caption
        )

    def open_gi_dialog(self):
        cursor = self.textCursor()
        if not cursor.hasSelection():
            return
        dlg = GIDialog(cursor.selectedText(), NEG_PROMPT, self)
        if dlg.exec() == GIDialog.DialogCode.Accepted:
            def generate_illustration(*args, **kwargs) -> Illustration:
                return Illustration(
                    dlg.backend.generate_image(*args, **kwargs),
                    cursor.blockNumber(),
                    truncate_str(cursor.selectedText()),
                )
            worker = Worker(
                generate_illustration,
                pos_prompt=dlg.pos_prompt,
                neg_prompt=dlg.neg_prompt,
                **dlg.generation_params,
            )
            worker.signals.result.connect(self.handle_illustration)
            self.thread_pool.start(worker)

    def set_font(self, new_font: QFont):
        font = self.font()
        font.setFamily(new_font.family())
        self.setFont(font)

    def set_font_pt_size(self, new_size: int):
        font = self.font()
        font.setPointSize(new_size)
        self.setFont(font)


class DecoratedLabel(QLabel):
    def __init__(self, *args, prefix: str = '', suffix: str = '', **kwargs):
        super().__init__(*args, **kwargs)
        self._prefix = prefix
        self._suffix = suffix

    @property
    def prefix(self) -> str:
        return self._prefix

    @property
    def suffix(self) -> str:
        return self._suffix

    def setText(self, a0: str | None):
        if a0:
            super().setText(f'{self._prefix}{a0}{self._suffix}')
        else:
            super().setText(a0)
    
    def setNum(self, a0: int | float):
        self.setText(str(a0))


class DecoratedComboBox(QComboBox):
    currentTextChangedUndec = pyqtSignal(str)

    def __init__(
        self,
        options: Iterable,
        *args,
        prefix: str = '',
        suffix: str = '',
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._prefix = prefix
        self._suffix = suffix
        for opt in options:
            self.addItem(f'{self._prefix}{opt}{self._suffix}')
        self.currentTextChanged.connect(self.on_current_text_changed)

    @property
    def prefix(self) -> str:
        return self._prefix

    @property
    def suffix(self) -> str:
        return self._suffix
    
    def on_current_text_changed(self, text: str):
        self.currentTextChangedUndec.emit(
            text.removeprefix(self._prefix).removesuffix(self._suffix)
        )

