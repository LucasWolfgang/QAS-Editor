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
import re
import traceback
import logging
from os.path import splitext
from uuid import uuid4
from typing import TYPE_CHECKING
from PyQt5.QtCore import Qt, QSize, QPoint, QPointF
from PyQt5.QtGui import QFont, QImage, QTextDocument, QKeySequence, QIcon,\
                        QColor, QPainter
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QFrame,\
                            QTextEdit, QToolBar, QFontComboBox, QComboBox,\
                            QActionGroup, QAction, QLineEdit, QPushButton,\
                            QLabel, QMessageBox, QCheckBox
from ..enums import Format
if TYPE_CHECKING:
    from typing import List, Callable
    from PyQt5.QtGui import QKeyEvent
IMG_PATH = __file__.replace('\\', '/').rsplit('/', 2)[0] + "/images"
LOG = logging.getLogger(__name__)


def action_handler(function: Callable) -> Callable:
    """_summary_

    Args:
        function (Callable): _description_

    Returns:
        Callable: _description_
    """
    def wrapper(*args, **kwargs):
        try:
            function(*args, **kwargs)
        except Exception:   # pylint: disable=W0703
            LOG.exception(f"Error calling function {function.__name__}")
            self_arg = args[0]
            while not isinstance(self_arg, QWidget):
                self_arg = self_arg()
            dlg = QMessageBox(self_arg)
            dlg.setText(traceback.format_exc())
            dlg.setIcon(QMessageBox.Critical)
            dlg.show()
    return wrapper


class GTextEditor(QTextEdit):
    """
    #TODO - Take a look on http://doc.qt.io/qt-5/qplaintextedit.html
            It may be way faster than using QTextEdit
    """

    def __init__(self, toolbar: "GTextToolbar", attribute: str) -> None:
        super().__init__()
        self.toolbar = toolbar
        self.__obj = None
        self.__attr = attribute
        self.textChanged.connect(self.__flag_update)
        self.__tags: List[tuple] = []
        self.__need_update = True

    def __flag_update(self):
        self.__need_update = True

    def __selected_tag(self) -> tuple:
        if not self.__tags:
            return None
        if self.__need_update:
            self.__update_tags()
        _tc = self.textCursor()
        if _tc.position() > self.__tags[-1][1]:
            return None
        for tag in self.__tags:
            if _tc.position() < tag[0]:
                break
            if _tc.position() < tag[1] + 1:
                return tag
        return None

    def __update_tags(self):
        self.__tags.clear()
        for i in re.finditer(r"\[\[[0-9]+\]\]", self.toPlainText()):
            self.__tags.append(i.span())
        self.__need_update = False

    def _update_fmt(self, index):
        self.__obj.formatting = list(GTextToolbar.FORMATS.values())[index]

    def canInsertFromMimeData(self, source) -> bool:  # pylint: disable=C0103
        """[summary]

        Args:
            source ([type]): [description]

        Returns:
            bool: [description]
        """
        return source.hasImage() or super().canInsertFromMimeData(source)

    def focusInEvent(self, event) -> None:  # pylint: disable=C0103
        """_summary_

        Args:
            event (_type_): _description_
        """
        self.toolbar.update_editor(self)
        return super().focusOutEvent(event)

    def focusOutEvent(self, event) -> None:  # pylint: disable=C0103
        """_summary_

        Args:
            event (_type_): _description_
        """
        if not self.toolbar.hasFocus():
            self.toolbar.setDisabled(True)
        return super().focusOutEvent(event)

    def get_attr(self):
        return self.__attr

    def insertFromMimeData(self, source):  # pylint: disable=C0103
        """[summary]

        Args:
            source ([type]): [description]
        """
        cursor = self.textCursor()
        doc = self.document()

        if source.hasUrls():
            for url in source.urls():
                file_ext = splitext(str(url.toLocalFile()))[1].lower()
                if url.isLocalFile() and file_ext in ['.jpg', '.png', '.bmp']:
                    image = QImage(url.toLocalFile())
                    doc.addResource(QTextDocument.ImageResource, url, image)
                    cursor.insertImage(url.toLocalFile())
                else:
                    break
            else:
                return
        elif source.hasImage():
            image = source.imageData()
            uuid = uuid4().hex
            doc.addResource(QTextDocument.ImageResource, uuid, image)
            cursor.insertImage(uuid)
            return
        super(GTextEditor, self).insertFromMimeData(source)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # pylint: disable=C0103
        """_summary_

        Args:
            event (QKeyEvent): _description_
        """
        if event.text() or event.key() in [Qt.Key_Backspace, Qt.Key_Enter,
                                           Qt.Key_Tab, Qt.Key_Space]:
            if self.__selected_tag():
                return None
        return super().keyPressEvent(event)

    def from_obj(self, obj, standard=True) -> None:
        """_summary_

        Args:
            text (FText): _description_
        """
        self.__obj = getattr(obj, self.__attr)
        if self.__obj.formatting == Format.MD:
            self.setMarkdown(self.__obj.text)
        elif self.__obj.formatting == Format.HTML:
            self.setHtml(self.__obj.text)
        else:
            self.setPlainText(self.__obj.text)
        self.__update_tags()


class GTextToolbar(QToolBar):
    """A toolbar for the Editor UI instanciated in a window.
    """

    FORMATS = {"MarkDown": Format.MD, "HTML": Format.HTML,
               "PlainText": Format.PLAIN}

    def __init__(self, *args, **kwargs):  # pylint: disable=R0915
        super(GTextToolbar, self).__init__(*args, **kwargs)

        self.editor: GTextEditor = None
        self.setIconSize(QSize(16, 16))

        self._fonts = QFontComboBox(self)
        self.addWidget(self._fonts)

        self._ttype = QComboBox(self)
        self._ttype.addItems(list(self.FORMATS.keys()))
        self.addWidget(self._ttype)

        self._mtype = QComboBox(self)
        self._mtype.addItems(["LaTex", "MathML", "Ignore"])
        self.addWidget(self._mtype)

        self._fsize = QComboBox(self)
        self._fsize.addItems(["7", "8", "9", "10", "11", "12", "13", "14",
                              "18", "24", "36", "48", "64"])
        self.addWidget(self._fsize)
        self.addSeparator()

        self._bold = QAction(QIcon(f"{IMG_PATH}/bold.png"), "Bold", self)
        self._bold.setStatusTip("Bold")
        self._bold.setShortcut(QKeySequence.Bold)
        self._bold.setCheckable(True)
        self.addAction(self._bold)

        self._italic = QAction(QIcon(f"{IMG_PATH}/italic.png"), "Italic", self)
        self._italic.setStatusTip("Italic")
        self._italic.setShortcut(QKeySequence.Italic)
        self._italic.setCheckable(True)
        self.addAction(self._italic)

        self._underline = QAction(QIcon(f"{IMG_PATH}/underline.png"),
                                  "Underline", self)
        self._underline.setStatusTip("Underline")
        self._underline.setShortcut(QKeySequence.Underline)
        self._underline.setCheckable(True)
        self.addAction(self._underline)
        self.addSeparator()

        self._alignl = QAction(QIcon(f"{IMG_PATH}/alignment.png"),
                               "Align left", self)
        self._alignl.setStatusTip("Align text left")
        self._alignl.setCheckable(True)
        self.addAction(self._alignl)

        self._alignc = QAction(QIcon(f"{IMG_PATH}/align_center.png"),
                               "Align center", self)
        self._alignc.setStatusTip("Align text center")
        self._alignc.setCheckable(True)
        self.addAction(self._alignc)

        self._alignr = QAction(QIcon(f"{IMG_PATH}/align_right.png"),
                               "Align right", self)
        self._alignr.setStatusTip("Align text right")
        self._alignr.setCheckable(True)
        self.addAction(self._alignr)

        self._alignj = QAction(QIcon(f"{IMG_PATH}/align_justify.png"),
                               "Justify", self)
        self._alignj.setStatusTip("Justify text")
        self._alignj.setCheckable(True)
        self.addAction(self._alignj)

        format_group = QActionGroup(self)
        format_group.setExclusive(True)
        format_group.addAction(self._alignl)
        format_group.addAction(self._alignc)
        format_group.addAction(self._alignr)
        format_group.addAction(self._alignj)

        self._wrap = QAction(QIcon(f"{IMG_PATH}/wrap.png"),
                             "Wrap text to window", self)
        self._wrap.setStatusTip("Toggle wrap text to window")
        self._wrap.setCheckable(True)
        self._wrap.setChecked(True)
        self.addAction(self._wrap)

        # Format-related widgets/actions, used to disable/enable signals.
        self._format_actions = [self._fonts, self._fsize, self._bold,
                                self._underline, self._italic]
        # No need to disable signals for alignment, as they are paragraph-wide.
        self.setFocusPolicy(Qt.ClickFocus)
        self.setDisabled(True)

    def __align_left(self):
        self.editor.setAlignment(Qt.AlignLeft)

    def __align_center(self):
        self.editor.setAlignment(Qt.AlignCenter)

    def __align_right(self):
        self.editor.setAlignment(Qt.AlignRight)

    def __align_justf(self):
        self.editor.setAlignment(Qt.AlignJustify)

    def __wrap_text(self):
        self.editor.setLineWrapMode(int(self.editor.lineWrapMode() == 0))

    def hasFocus(self) -> bool:  # pylint: disable=C0103
        """_summary_

        Returns:
            bool: _description_
        """
        return super().hasFocus() or self._fonts.hasFocus() or \
            self._fsize.hasFocus() or self._mtype.hasFocus() or \
            self._ttype.hasFocus()

    def update_editor(self, text_editor: GTextEditor) -> None:
        """Update the font format toolbar/actions when a new text selection
        is made. This is neccessary to keep toolbars/etc. in sync with the
        current edit state.
        """
        self.setDisabled(text_editor is None)
        if text_editor == self.editor:
            return
        if self.editor is not None:
            self._ttype.currentIndexChanged.disconnect()
            self._fonts.currentFontChanged.disconnect()
            self._fsize.currentIndexChanged[str].disconnect()
            self._bold.toggled.disconnect()
            self._underline.toggled.disconnect()
            self._italic.toggled.disconnect()
            self._alignl.triggered.disconnect()
            self._alignc.triggered.disconnect()
            self._alignr.triggered.disconnect()
            self._alignj.triggered.disconnect()
            self._wrap.triggered.disconnect()
        self.editor = text_editor
        if self.editor is not None:
            for _obj in self._format_actions:
                _obj.blockSignals(True)
            self._fonts.setCurrentFont(self.editor.currentFont())
            self._fsize.setCurrentText(str(int(self.editor.fontPointSize())))
            self._italic.setChecked(self.editor.fontItalic())
            self._underline.setChecked(self.editor.fontUnderline())
            self._bold.setChecked(self.editor.fontWeight() == QFont.Bold)
            self._alignl.setChecked(self.editor.alignment() == Qt.AlignLeft)
            self._alignc.setChecked(self.editor.alignment() == Qt.AlignCenter)
            self._alignr.setChecked(self.editor.alignment() == Qt.AlignRight)
            self._alignj.setChecked(self.editor.alignment() == Qt.AlignJustify)
            self._ttype.setCurrentText(self.editor.text_format.name)
            for _obj in self._format_actions:
                _obj.blockSignals(False)
            self._ttype.currentIndexChanged.connect(self.editor._update_fmt)
            self._fonts.currentFontChanged.connect(self.editor.setCurrentFont)
            self._underline.toggled.connect(self.editor.setFontUnderline)
            self._italic.toggled.connect(self.editor.setFontItalic)
            self._fsize.currentIndexChanged[str].connect(
                    lambda s: self.editor.setFontPointSize(float(s)))
            self._bold.toggled.connect(lambda x: self.editor.setFontWeight(
                    QFont.Bold if x else QFont.Normal))
            self._alignl.triggered.connect(self.__align_left)
            self._alignc.triggered.connect(self.__align_center)
            self._alignr.triggered.connect(self.__align_right)
            self._alignj.triggered.connect(self.__align_justf)
            self._wrap.triggered.connect(self.__wrap_text)


class GArrow(QFrame):
    """Arrow used in the TitleFrame class to represent open/close status
    """

    def __init__(self, parent=None, collapsed=False):
        QFrame.__init__(self, parent=parent)
        self.setMaximumSize(24, 24)
        self.__hori = (QPointF(7, 8), QPointF(17, 8), QPointF(12, 13))
        self.__vert = (QPointF(8, 7), QPointF(13, 12), QPointF(8, 17))
        self._arrow = None
        self.set_arrow(int(collapsed))

    def set_arrow(self, arrow_dir: bool):
        """_summary_

        Args:
            arrow_dir (bool): _description_
        """
        self._arrow = self.__vert if arrow_dir else self.__hori
        self.update()

    def paintEvent(self, _):    # pylint: disable=C0103
        """_summary_

        Args:
            _ (_type_): _description_
        """
        painter = QPainter()
        painter.begin(self)
        painter.setBrush(QColor(192, 192, 192))
        painter.setPen(QColor(64, 64, 64))
        painter.drawPolygon(*self._arrow)
        painter.end()


class GTitleFrame(QFrame):
    """Used as header in a GCollapsible class.
    """

    def __init__(self, parent, toogle_func, title=""):
        QFrame.__init__(self, parent=parent)
        self.setFrameShadow(QFrame.Sunken)
        self.setStyleSheet("border:1px solid rgb(41, 41, 41); "
                           "background-color: #acc5f2;")
        self._hlayout = QHBoxLayout(self)
        self._hlayout.setContentsMargins(0, 0, 0, 0)
        self._hlayout.setSpacing(0)
        self._arrow = GArrow(collapsed=True)
        self._arrow.setStyleSheet("border:0px")
        self._title = QLabel(title)
        self._title.setFixedHeight(24)
        self._title.move(QPoint(24, 0))
        self._title.setStyleSheet("border:0px")
        self._hlayout.addWidget(self._arrow)
        self._hlayout.addWidget(self._title)
        self.__toogle_func = toogle_func

    def mousePressEvent(self, a0) -> None:
        self.__toogle_func()
        return super().mousePressEvent(a0)


class GCollapsible(QVBoxLayout):
    """Custom widget that gives a collapsable (dropdown style) window that
    contains other QWidgets.
    """
    addWidget = property(doc='(!) Disallowed inherited')
    addLayout = property(doc='(!) Disallowed inherited')

    def __init__(self, parent=None, title="", content=None):
        QVBoxLayout.__init__(self)
        self._is_collasped = True
        self._title_frame = GTitleFrame(parent, self.toggle_collapsed, title)
        super().addWidget(self._title_frame)
        self._content = QWidget(parent) if content is None else content
        self._content.setStyleSheet(".QWidget{border:1px solid rgb(41, 41, 41)"
                                    "; background-color: #f0f6ff}")
        self._content.setVisible(not self._is_collasped)
        super().addWidget(self._content)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(0)

    def setLayout(self, layout) -> None:  # pylint: disable=C0103
        """_summary_

        Args:
            layout (_type_): _description_
        """
        self._content.setLayout(layout)

    def toggle_collapsed(self):
        """_summary_
        """
        self._content.setVisible(self._is_collasped)
        self._is_collasped = not self._is_collasped
        self._title_frame._arrow.set_arrow(int(self._is_collasped))


class GTagBar(QFrame):
    """Custom widget that allows the user to enter tags and provides a
    interface to later get these tags as a list.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.tags = []
        self.setStyleSheet("QPushButton {border:0px sunken; font-weight:bold} "
                           "QLabel {background:#c4edc2; font-size:12px; border"
                           "-radius:4px; padding-left:2px} .GTagBar {border:"
                           "1px sunken; background: #d1d1d1; padding:2px}")
        self.h_layout = QHBoxLayout()
        self.h_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.h_layout)
        self.line_edit = QLineEdit()
        self.refresh()
        self.line_edit.returnPressed.connect(self.create_tags)

    def add_tag_to_bar(self, text):
        """_summary_

        Args:
            text (_type_): _description_
        """
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
        """_summary_

        Args:
            tag_name (_type_): _description_
        """
        self.tags.remove(tag_name)
        self.refresh()

    def create_tags(self):
        """_summary_
        """
        new_tags = self.line_edit.text().split(',')
        self.line_edit.setText('')
        self.tags.extend(new_tags)
        self.tags = list(set(self.tags))
        self.tags.sort(key=lambda x: x.lower())
        self.refresh()

    def from_obj(self, obj) -> None:
        """_summary_

        Args:
            obj (Tags): _description_
        """
        self.tags = obj.tags

    def get_attr(self):
        return "tags"

    def refresh(self):
        """_summary_
        """
        for i in reversed(range(self.h_layout.count())):
            self.h_layout.itemAt(i).widget().setParent(None)
        for tag in self.tags:
            self.add_tag_to_bar(tag)
        self.h_layout.addWidget(self.line_edit)
        self.line_edit.setFocus()


class GDropbox(QComboBox):

    def __init__(self, parent, cast_type, attribute, map=None) -> None:
        super().__init__(parent)
        self.__attr = attribute
        self._cast = cast_type
        self.__map = map
        self.__obj = None

    def focusOutEvent(self, e) -> None:
        if self.__obj is not None:
            value = self.currentText()
            if self.__map is not None:
                value = self.__map[value]
            setattr(self.__obj, self.__attr, value)
        return super().focusOutEvent(e)

    def from_obj(self, obj):
        self.__obj = obj
        self.setCurrentText(str(getattr(obj, self.__attr)))

    def get_attr(self):
        return self.__attr


class GField(QLineEdit):

    def __init__(self, cast_type, attribute) -> None:
        super().__init__()
        self.__attr = attribute
        self._cast = cast_type
        self.__obj = None

    def focusOutEvent(self, e) -> None:
        if self.__obj is not None:
            setattr(self.__obj, self.__attr, self.text())
        return super().focusOutEvent(e)

    def from_obj(self, obj):
        self.__obj = obj
        self.setText(str(getattr(obj, self.__attr)))

    def get_attr(self):
        return self.__attr


class GCheckBox(QCheckBox):

    def __init__(self, parent, text, attribute) -> None:
        super().__init__(text, parent)
        self.__attr = attribute
        self.__obj = None

    def focusOutEvent(self, e) -> None:
        if self.__obj is not None:
            setattr(self.__obj, self.__attr, self.isChecked())
        return super().focusOutEvent(e)

    def from_obj(self, obj):
        self.__obj = obj
        self.setChecked(bool(getattr(obj, self.__attr)))

    def get_attr(self):
        return self.__attr
