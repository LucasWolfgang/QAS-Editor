""""
Question and Answer Sheet Editor <https://github.com/LucasWolfgang/QAS-Editor>
Copyright (C) 2022  Lucas Wolfgang

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import List, Callable
    from PyQt5.QtGui import QKeyEvent
import re
import traceback
import logging
from os.path import splitext
from uuid import uuid4
from ..enums import Format
from ..wrappers import FText, Tags
from PyQt5.QtCore import Qt, QSize, QPoint, QPointF, pyqtSignal
from PyQt5.QtGui import QFont, QImage, QTextDocument, QKeySequence, QIcon, QColor, QPainter
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QFrame, QTextEdit, QToolBar, \
                            QFontComboBox, QComboBox, QActionGroup, QAction, QLineEdit, \
                            QPushButton, QLabel, QMessageBox, QApplication

img_path = __file__.replace('\\', '/').rsplit('/', 2)[0] + "/images"
log = logging.getLogger(__name__)

def action_handler(function: Callable) -> Callable:
    def wrapper(*args, **kwargs):
        try:
            function(*args, **kwargs)
        except Exception:
            log.exception(f"Error calling function {function.__name__}")
            self_arg = args[0]
            while not isinstance(self_arg, QWidget): self_arg = self_arg.parent()
            dlg = QMessageBox(self_arg)
            dlg.setText(traceback.format_exc())
            dlg.setIcon(QMessageBox.Critical)
            dlg.show()
    return wrapper

# ----------------------------------------------------------------------------------------

class GTextEditor(QTextEdit):
    """
    #TODO - Take a look on http://doc.qt.io/qt-5/qplaintextedit.html
            It may be way faster than using QTextEdit
    """

    def __init__(self, toolbar: "GTextToolbar") -> None:
        super().__init__()
        self.toolbar = toolbar
        self.text_format: Format = Format.HTML
        self.math_type = 0
        self.setAutoFormatting(QTextEdit.AutoAll)
        self.setFont(QFont('Times', 12))
        self.setFontPointSize(12)
        self.textChanged.connect(self.__flag_update)
        self.__tags: List[tuple] = []
        self.__need_update = True

    def __flag_update(self): 
        self.__need_update = True

    def __selected_tag(self):
        if not self.__tags: return
        if self.__need_update: self.__update_tags()
        tc = self.textCursor()
        if tc.position() > self.__tags[-1][1]: return
        for tag in self.__tags:
            if tc.position() < tag[0]: break
            if tc.position() < tag[1] + 1:
                return tag

    def __update_tags(self):
        self.__tags.clear()
        for i in re.finditer("\[\[[0-9]+\]\]", self.toPlainText()):
            self.__tags.append(i.span())
        self.__need_update = False

    def _update_format(self, index):
        self.text_format = list(GTextToolbar.FORMATS.values())[index]

    def canInsertFromMimeData(self, source) -> bool:
        """[summary]

        Args:
            source ([type]): [description]

        Returns:
            bool: [description]
        """
        return source.hasImage() or super().canInsertFromMimeData(source)

    def focusInEvent(self, e) -> None:
        self.toolbar.update_editor(self)
        return super().focusOutEvent(e)

    def focusOutEvent(self, e) -> None:
        if not self.toolbar.hasFocus():
            self.toolbar.setDisabled(True)
        return super().focusOutEvent(e)

    def getFText(self) -> FText:
        """[summary]

        Returns:
            FText: [description]
        """
        if self.text_format == Format.MD:
            txt = self.toMarkdown()
        elif self.text_format == Format.HTML:
            txt = self.toHtml()
        else:
            txt = self.toPlainText()
        return FText(txt, self.text_format)

    def insertFromMimeData(self, source):
        """[summary]

        Args:
            source ([type]): [description]
        """
        cursor = self.textCursor()
        document = self.document()

        if source.hasUrls():
            for u in source.urls():
                file_ext = splitext(str(u.toLocalFile()))[1].lower()
                if u.isLocalFile() and file_ext in ['.jpg','.png','.bmp']:
                    image = QImage(u.toLocalFile())
                    document.addResource(QTextDocument.ImageResource, u, image)
                    cursor.insertImage(u.toLocalFile())
                else:
                    break
            else:
                return
        elif source.hasImage():
            image = source.imageData()
            uuid = uuid4().hex
            document.addResource(QTextDocument.ImageResource, uuid, image)
            cursor.insertImage(uuid)
            return
        super(GTextEditor, self).insertFromMimeData(source)

    def keyPressEvent(self, e: QKeyEvent) -> None:
        if e.text() or e.key() in [Qt.Key_Backspace, Qt.Key_Enter, Qt.Key_Tab, Qt.Key_Space]:
            if self.__selected_tag(): return
        return super().keyPressEvent(e)

    def setFText(self, text: FText) -> None:
        if text.formatting == Format.MD:
            self.setMarkdown(text.text)
        elif text.formatting == Format.HTML:
            self.setHtml(text.text)
        else:
            self.setPlainText(text.text)
        self.text_format = text.formatting
        self.__update_tags()

# ----------------------------------------------------------------------------------------

class GTextToolbar(QToolBar):

    FORMATS = {"MarkDown": Format.MD, "HTML": Format.HTML, "PlainText": Format.PLAIN}

    def __init__(self, *args, **kwargs):
        super(GTextToolbar, self).__init__(*args, **kwargs)

        self.editor: GTextEditor = None
        self.setIconSize(QSize(16, 16))

        self.fonts = QFontComboBox(self)
        self.addWidget(self.fonts)

        self.text_type = QComboBox(self)
        self.text_type.addItems(list(self.FORMATS.keys()))
        self.addWidget(self.text_type)

        self.math_type = QComboBox(self)
        self.math_type.addItems(["LaTex", "MathML", "Ignore"])
        self.addWidget(self.math_type)

        self.fontsize = QComboBox(self)
        self.fontsize.addItems(["7", "8", "9", "10", "11", "12", "13", "14", "18", "24", "36", "48", "64"])
        self.addWidget(self.fontsize)
        self.addSeparator()

        self.bold_action = QAction(QIcon(f"{img_path}/edit-bold.png"), "Bold", self)
        self.bold_action.setStatusTip("Bold")
        self.bold_action.setShortcut(QKeySequence.Bold)
        self.bold_action.setCheckable(True)
        self.addAction(self.bold_action)

        self.italic_action = QAction(QIcon(f"{img_path}/edit-italic.png"), "Italic", self)
        self.italic_action.setStatusTip("Italic")
        self.italic_action.setShortcut(QKeySequence.Italic)
        self.italic_action.setCheckable(True)
        self.addAction(self.italic_action)

        self.underline_action = QAction(QIcon(f"{img_path}/edit-underline.png"), "Underline", self)
        self.underline_action.setStatusTip("Underline")
        self.underline_action.setShortcut(QKeySequence.Underline)
        self.underline_action.setCheckable(True)
        self.addAction(self.underline_action)
        self.addSeparator()

        self.alignl_action = QAction(QIcon(f"{img_path}/edit-alignment.png"), "Align left", self)
        self.alignl_action.setStatusTip("Align text left")
        self.alignl_action.setCheckable(True)
        self.addAction(self.alignl_action)

        self.alignc_action = QAction(QIcon(f"{img_path}/edit-alignment-center.png"), "Align center", self)
        self.alignc_action.setStatusTip("Align text center")
        self.alignc_action.setCheckable(True)
        self.addAction(self.alignc_action)

        self.alignr_action = QAction(QIcon(f"{img_path}/edit-alignment-right.png"), "Align right", self)
        self.alignr_action.setStatusTip("Align text right")
        self.alignr_action.setCheckable(True)
        self.addAction(self.alignr_action)

        self.alignj_action = QAction(QIcon(f"{img_path}/edit-alignment-justify.png"), "Justify", self)
        self.alignj_action.setStatusTip("Justify text")
        self.alignj_action.setCheckable(True)
        self.addAction(self.alignj_action)

        format_group = QActionGroup(self)
        format_group.setExclusive(True)
        format_group.addAction(self.alignl_action)
        format_group.addAction(self.alignc_action)
        format_group.addAction(self.alignr_action)
        format_group.addAction(self.alignj_action)

        self.wrap_action = QAction(QIcon(f"{img_path}/arrow-continue.png"), "Wrap text to window", self)
        self.wrap_action.setStatusTip("Toggle wrap text to window")
        self.wrap_action.setCheckable(True)
        self.wrap_action.setChecked(True)
        self.addAction(self.wrap_action)

        # A list of all format-related widgets/actions, so we can disable/enable signals when updating.
        self._format_actions = [ self.fonts, self.fontsize, self.bold_action, 
                                 self.underline_action, self.italic_action ]
        # We don't need to disable signals for alignment, as they are paragraph-wide.
        self.setFocusPolicy(Qt.ClickFocus)
        self.setDisabled(True)

    def hasFocus(self) -> bool:
        return super().hasFocus() or self.fonts.hasFocus() or self.fontsize.hasFocus() \
                or self.math_type.hasFocus() or self.text_type.hasFocus()

    def update_editor(self, text_editor: GTextEditor) -> None:
        """Update the font format toolbar/actions when a new text selection is made. 
        This is neccessary to keep toolbars/etc. in sync with the current edit state.
        """ 
        self.setDisabled(text_editor is None)
        if text_editor == self.editor: return # Nothing to do here
        if self.editor is not None:
            self.text_type.currentIndexChanged.disconnect()
            self.fonts.currentFontChanged.disconnect()
            self.fontsize.currentIndexChanged[str].disconnect()
            self.bold_action.toggled.disconnect()
            self.underline_action.toggled.disconnect()
            self.italic_action.toggled.disconnect()
            self.alignl_action.triggered.disconnect()
            self.alignc_action.triggered.disconnect()
            self.alignr_action.triggered.disconnect()
            self.alignj_action.triggered.disconnect()
            self.wrap_action.triggered.disconnect()
        self.editor = text_editor  
        if self.editor is not None:
            for o in self._format_actions:  # Disable signals for all format widgets
                o.blockSignals(True)
            self.fonts.setCurrentFont(self.editor.currentFont())
            self.fontsize.setCurrentText(str(int(self.editor.fontPointSize())))
            self.italic_action.setChecked(self.editor.fontItalic())
            self.underline_action.setChecked(self.editor.fontUnderline())
            self.bold_action.setChecked(self.editor.fontWeight() == QFont.Bold)
            self.alignl_action.setChecked(self.editor.alignment() == Qt.AlignLeft)
            self.alignc_action.setChecked(self.editor.alignment() == Qt.AlignCenter)
            self.alignr_action.setChecked(self.editor.alignment() == Qt.AlignRight)
            self.alignj_action.setChecked(self.editor.alignment() == Qt.AlignJustify)
            self.text_type.setCurrentText(self.editor.text_format.name)
            for o in self._format_actions:
                o.blockSignals(False)
            self.text_type.currentIndexChanged.connect(self.editor._update_format)
            self.fonts.currentFontChanged.connect(self.editor.setCurrentFont)
            self.underline_action.toggled.connect(self.editor.setFontUnderline)
            self.italic_action.toggled.connect(self.editor.setFontItalic)
            self.fontsize.currentIndexChanged[str].connect(lambda s: 
                    self.editor.setFontPointSize(float(s)))
            self.bold_action.toggled.connect(lambda x: 
                    self.editor.setFontWeight(QFont.Bold if x else QFont.Normal))
            self.alignl_action.triggered.connect(lambda: 
                    self.editor.setAlignment(Qt.AlignLeft))
            self.alignc_action.triggered.connect(lambda: 
                    self.editor.setAlignment(Qt.AlignCenter))
            self.alignr_action.triggered.connect(lambda: 
                    self.editor.setAlignment(Qt.AlignRight))
            self.alignj_action.triggered.connect(lambda: 
                    self.editor.setAlignment(Qt.AlignJustify))
            self.wrap_action.triggered.connect(lambda: 
                    self.editor.setLineWrapMode(int(self.editor.lineWrapMode() == 0)))

# ----------------------------------------------------------------------------------------
class GArrow(QFrame):
    def __init__(self, parent=None, collapsed=False):
        QFrame.__init__(self, parent=parent)
        self.setMaximumSize(24, 24)
        self._arrow_horizontal = (QPointF(7.0, 8.0), QPointF(17.0, 8.0), QPointF(12.0, 13.0))
        self._arrow_vertical = (QPointF(8.0, 7.0), QPointF(13.0, 12.0), QPointF(8.0, 17.0))
        self._arrow = None
        self.setArrow(int(collapsed))

    def setArrow(self, arrow_dir: bool):
        self._arrow = self._arrow_vertical if arrow_dir else self._arrow_horizontal
        self.update() # Fix bug where arrows do not update if children dont fill top layout

    def paintEvent(self, event):
        painter = QPainter()
        painter.begin(self)
        painter.setBrush(QColor(192, 192, 192))
        painter.setPen(QColor(64, 64, 64))
        painter.drawPolygon(*self._arrow)
        painter.end()

# ----------------------------------------------------------------------------------------
class GTitleFrame(QFrame):

    clicked = pyqtSignal()

    def __init__(self, parent=None, title="", collapsed=False):
        QFrame.__init__(self, parent=parent)
        self.setFrameShadow(QFrame.Sunken)
        self.setStyleSheet("border:1px solid rgb(41, 41, 41); background-color: #acc5f2;")

        self._hlayout = QHBoxLayout(self)
        self._hlayout.setContentsMargins(0, 0, 0, 0)
        self._hlayout.setSpacing(0)

        self._arrow = GArrow(collapsed=collapsed)
        self._arrow.setStyleSheet("border:0px")
        self._title = QLabel(title)
        self._title.setFixedHeight(24)
        self._title.move(QPoint(24, 0))
        self._title.setStyleSheet("border:0px")

        self._hlayout.addWidget(self._arrow)
        self._hlayout.addWidget(self._title)

    def mousePressEvent(self, event):
        self.clicked.emit()
        return super(GTitleFrame, self).mousePressEvent(event)

# ----------------------------------------------------------------------------------------
class GFrameLayout(QVBoxLayout):
    def __init__(self, parent=None, title: str=None):
        QVBoxLayout.__init__(self)

        self._is_collasped = True
        self._title_frame = GTitleFrame(parent, title, True)
        self._title_frame.clicked.connect(self.toggleCollapsed)
        super().addWidget(self._title_frame)
        self._content = QWidget()
        self._content.setStyleSheet(".QWidget{border:1px solid rgb(41, 41, 41); \
                                    background-color: #f0f6ff}")
        self._content.setVisible(not self._is_collasped)
        super().addWidget(self._content)

    def addWidget(self, a0: QWidget, stretch = ..., alignment = ...) -> None:
        raise AttributeError("Method is not supported") # Invalidates method

    def addLayout(self, layout, stretch: int = ...) -> None:
        raise AttributeError("Method is not supported") # Invalidates method

    def setLayout(self, layout) -> None:
        self._content.setLayout(layout)

    def toggleCollapsed(self):
        self._content.setVisible(self._is_collasped)
        self._is_collasped = not self._is_collasped
        self._title_frame._arrow.setArrow(int(self._is_collasped))

# ----------------------------------------------------------------------------------------
class GTagBar(QFrame):

    def __init__(self):
        super(GTagBar, self).__init__()
        self.tags = []
        self.setStyleSheet("QPushButton { border:0px sunken; font-weight:bold} "+
            "QLabel { background:#c4edc2; font-size:12px; border-radius:4px; padding-left:2px} "+
            ".GTagBar { border:1px sunken; background: #d1d1d1; padding:2px}")
        self.h_layout = QHBoxLayout()
        self.h_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.h_layout)
        self.line_edit = QLineEdit()
        self.refresh()
        self.line_edit.returnPressed.connect(self.create_tags)

    def add_tag_to_bar(self, text):
        tag = QLabel(text+"    ")
        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 5)
        x_button = QPushButton('x')
        x_button.setFixedSize(16, 16)
        x_button.clicked.connect(lambda: self.delete_tag(text))
        hbox.addWidget(x_button, 0, Qt.AlignRight)
        tag.setLayout(hbox)
        self.h_layout.addWidget(tag)

    def delete_tag(self, tag_name):
        self.tags.remove(tag_name)
        self.refresh()

    def create_tags(self):
        new_tags = self.line_edit.text().split(',')
        self.line_edit.setText('')
        self.tags.extend(new_tags)
        self.tags = list(set(self.tags))
        self.tags.sort(key=lambda x: x.lower())
        self.refresh()

    def from_obj(self, obj: Tags) -> None:
        self.tags = list(obj)

    def refresh(self):
        for i in reversed(range(self.h_layout.count())):
            self.h_layout.itemAt(i).widget().setParent(None)
        for tag in self.tags:
            self.add_tag_to_bar(tag)
        self.h_layout.addWidget(self.line_edit)
        self.line_edit.setFocus()

    def to_obj(self):
        return Tags(self.tags)

# ----------------------------------------------------------------------------------------