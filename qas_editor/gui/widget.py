"""
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
import logging
from typing import TYPE_CHECKING
from os.path import splitext
from uuid import uuid4
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QImage, QTextDocument, QKeySequence, QIcon,\
                        QTextCursor
from PyQt5.QtWidgets import QWidget, QActionGroup, QCompleter, QTextEdit,\
                            QToolBar, QFontComboBox, QComboBox, QHBoxLayout,\
                            QFrame, QPushButton, QLabel, QAction, QLineEdit,\
                            QCheckBox, QListWidget, QGridLayout
from .utils import IMG_PATH
from ..question import MARKER_INT
from ..answer import Answer, ACalculated, DragGroup, EmbeddedItem, DropZone,\
                     SelectOption
from ..enums import EmbeddedFormat, TextFormat, TolType, TolFormat, EnhancedEnum
from ..utils import FText, Hint
if TYPE_CHECKING:
    from PyQt5.QtGui import QKeyEvent


LOG = logging.getLogger(__name__)


class _AutoUpdate():
    """ Helper class to abstract interface for auto updatable Widgets.
    """

    _get_data: str = None

    def __init__(self, attribute: str, *args):
        super().__init__(*args)
        self.__obj = None
        self.__attr = attribute

    def get_attr(self):
        """Return attribute updated when focus is lost.
        """
        return self.__attr

    def from_obj(self, obj):
        """Set the target object. The object should have the attribute defined
        during instanciation.

        Args:
            obj (_type_): target object.
        """
        self.__obj = obj
        return getattr(obj, self.__attr)

    def focusOutEvent(self, event):             # pylint: disable=C0103
        """Method overwritten. Updates the data in the target object.
        """
        if self.__obj is not None and self._get_data:
            setattr(self.__obj, self.__attr,
                    getattr(self, self._get_data)) # pylint: disable=E1102
        return super().focusOutEvent(event)        # pylint: disable=E1101


class GDropbox(_AutoUpdate, QComboBox):
    """An auto updatable QComboBox
    """

    _get_data = "currentData"

    def __init__(self, attribute: str, parent: QWidget, group: EnhancedEnum):
        super().__init__(attribute, parent)
        if isinstance(group, EnhancedEnum):
            for item in group:
                self.addItem(item.comment, item)
        elif isinstance(group, list):
            for item in group:
                self.addItem(item)
        self.setFixedHeight(24)

    def from_obj(self, obj):
        data = super().from_obj(obj)
        if isinstance(data, list):
            self.clear()
            for num, item in enumerate(data):
                self.addItem(f"item {num}", item)
        else:
            self.setCurrentText(data.comment)


class GField(_AutoUpdate, QLineEdit):
    """An auto updatable QLineEdit
    """

    _get_data = "text"

    def __init__(self, attribute: str, parent, cast_type):
        super().__init__(attribute, parent)
        self._cast = cast_type

    def from_obj(self, obj):
        value = super().from_obj(obj)
        if value is not None:
            self.setText(str(value))


class GCheckBox(_AutoUpdate, QCheckBox):
    """An auto updatable QCheckBox
    """

    _get_data = "isChecked"

    def from_obj(self, obj):
        self.setChecked(bool(super().from_obj(obj)))


class GList(_AutoUpdate, QListWidget):
    """An auto updatable QListWidget
    """

    def from_obj(self, obj):
        self.clear()
        items = super().from_obj(obj)
        if isinstance(items, list):
            for dataset in items:
                self.addItem(str(dataset))
        else:
            for key, value in items.items():
                self.addItem(f"{key}: {value}")


class GTextEditor(QTextEdit):
    """ Widget for Plain and formatted text.
    """

    def __init__(self, toolbar: "GTextToolbar", attribute: str, is_ftext=False,
                 parent: QWidget = None):
        super().__init__(parent)
        self.toolbar = toolbar
        self.is_ftext = is_ftext
        self.__obj = None
        self.__attr = attribute
        self.__from_drag = False

    @staticmethod
    def __has_marker(text):
        for char in text:
            if ord(char) == MARKER_INT:
                return True
        return False

    def add_marker(self):
        """Add a new marker to the text where the cursor currently is.
        """
        cur = self.textCursor()
        cur.insertText(chr(MARKER_INT))

    def canInsertFromMimeData(self, source) -> bool:  # pylint: disable=C0103
        """[summary]
        Args:
            source ([type]): [description]
        Returns:
            bool: [description]
        """
        return source.hasImage() or super().canInsertFromMimeData(source)

    def contextMenuEvent(self, _):          # pylint: disable=C0103
        """Method overwritten. Disables completely ctx menu
        """
        return None

    def dragEnterEvent(self, event):        # pylint: disable=C0103
        """Method overwritten. Allow moving markers arround
        """
        self.__from_drag = True
        return super().dragEnterEvent(event)

    def focusInEvent(self, event) -> None:  # pylint: disable=C0103
        """Method overwritten. Set itself as the toolbar's target.
        Args:
            event (_type_): _description_
        """
        self.toolbar.update_editor(self)
        return super().focusOutEvent(event)

    def focusOutEvent(self, event) -> None:  # pylint: disable=C0103
        """Method overwritten. Updates the object's field.
        """
        if not self.toolbar.hasFocus():
            self.toolbar.setDisabled(True)
        if self.__obj.formatting == TextFormat.MD:
            self.__obj.text = self.toMarkdown()
        elif self.__obj.formatting == TextFormat.HTML:
            self.__obj.text = self.toHtml()
        else:
            self.__obj.text = self.toPlainText()
        return super().focusOutEvent(event)

    def get_attr(self):
        """Get attribute.
        """
        return self.__attr

    def get_formatting(self):
        """Return the formatting used by the target object
        """
        return self.__obj.formatting.name

    def insertFromMimeData(self, source):   # pylint: disable=C0103
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
        elif source.hasText() and not self.__from_drag and \
                GTextEditor.__has_marker(source.text()):
            return
        self.__from_drag = False
        super().insertFromMimeData(source)

    def keyPressEvent(self, event: QKeyEvent):  # pylint: disable=C0103
        """_summary_
        Args:
            event (QKeyEvent): _description_
        """
        if event.key() == Qt.Key_Backspace:
            cur = self.textCursor()
            pos = cur.position() - event.count()
            cur.setPosition(pos, QTextCursor.KeepAnchor)
        if not (event.key() in [Qt.Key_C, Qt.Key_Z] and event.modifiers() &
                Qt.ControlModifier) and GTextEditor.__has_marker(
                self.textCursor().selectedText()):
            event.ignore()
            return None
        return super().keyPressEvent(event)

    def from_obj(self, obj) -> None:
        """_summary_
        Args:
            obj (FText): Object to get the data from
            standard (bool): If the object passed is a FText (or has the FText
                required data) or is a object that contains the FText
        """
        self.__obj = obj if self.is_ftext else getattr(obj, self.__attr)
        if self.__obj.formatting == TextFormat.MD:
            self.setMarkdown(self.__obj.text)
        elif self.__obj.formatting == TextFormat.HTML:
            self.setHtml(str(self.__obj))
        else:
            self.setPlainText(self.__obj.text)

    def pop_marker(self, index):
        """Pop the last marker found in the text.
        """
        txt = self.toHtml()
        char = chr(MARKER_INT)
        find = txt.find(char)
        i = find != -1
        while find != -1 and i != index:
            find = txt.find(char, find + 1)
            i += 1
        if i == index:
            self.setHtml(txt[:find] + txt[find+len(char):])

    def update_fmt(self, index):
        """ Update the formatting used.
        """
        self.__obj.formatting = list(GTextToolbar.FORMATS.values())[index]


class GTextToolbar(QToolBar):
    """A toolbar for the Editor UI instanciated in a window.
    """

    def __init__(self, parent):
        super().__init__(parent)

        self.editor: GTextEditor = None
        self.setIconSize(QSize(16, 16))

        self._fonts = QFontComboBox(self)
        self.addWidget(self._fonts)

        self._ttype = QComboBox(self)
        self._ttype.addItems([item.comment for item in TextFormat])
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
        self._bold.setShortcut(QKeySequence.Bold)
        self._bold.setCheckable(True)
        self.addAction(self._bold)

        self._italic = QAction(QIcon(f"{IMG_PATH}/italic.png"), "Italic", self)
        self._italic.setShortcut(QKeySequence.Italic)
        self._italic.setCheckable(True)
        self.addAction(self._italic)

        self._underline = QAction(QIcon(f"{IMG_PATH}/underline.png"),
                                  "Underline", self)
        self._underline.setShortcut(QKeySequence.Underline)
        self._underline.setCheckable(True)
        self.addAction(self._underline)
        self.addSeparator()

        self._alignl = QAction(QIcon(f"{IMG_PATH}/alignment.png"),
                               "Align left", self)
        self._alignl.setCheckable(True)
        self.addAction(self._alignl)

        self._alignc = QAction(QIcon(f"{IMG_PATH}/align_center.png"),
                               "Align center", self)
        self._alignc.setCheckable(True)
        self.addAction(self._alignc)

        self._alignr = QAction(QIcon(f"{IMG_PATH}/align_right.png"),
                               "Align right", self)
        self._alignr.setCheckable(True)
        self.addAction(self._alignr)

        self._alignj = QAction(QIcon(f"{IMG_PATH}/align_justify.png"),
                               "Justify", self)
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
        self.addSeparator()

        self._html = QAction(QIcon(f"{IMG_PATH}/html.png"),
                             "Selected text as HTML", self)
        self._html.setCheckable(False)
        self._html.triggered.connect(self.__to_html)
        self.addAction(self._html)

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

    def __to_html(self):
        text = self.editor.textCursor().selectedText()
        self.editor.textCursor().insertHtml(text)

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
            self._fsize.currentIndexChanged.disconnect()
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
            self._ttype.setCurrentText(self.editor.get_formatting())
            for _obj in self._format_actions:
                _obj.blockSignals(False)
            self._ttype.currentIndexChanged.connect(self.editor.update_fmt)
            self._fonts.currentFontChanged.connect(self.editor.setCurrentFont)
            self._underline.toggled.connect(self.editor.setFontUnderline)
            self._italic.toggled.connect(self.editor.setFontItalic)
            self._fsize.currentIndexChanged.connect(
                    lambda s: self.editor.setFontPointSize(float(s)))
            self._bold.toggled.connect(lambda x: self.editor.setFontWeight(
                    QFont.Bold if x else QFont.Normal))
            self._alignl.triggered.connect(self.__align_left)
            self._alignc.triggered.connect(self.__align_center)
            self._alignr.triggered.connect(self.__align_right)
            self._alignj.triggered.connect(self.__align_justf)
            self._wrap.triggered.connect(self.__wrap_text)


class GAnswer(QFrame):
    """An UI representation for QAnswer class.
    """

    def __init__(self, toolbar: GTextToolbar, question: list, option=None):
        super().__init__()
        self._layout = QHBoxLayout(self)
        self._text = GTextEditor(toolbar, "text", True)
        self._text.setToolTip("Answer's text")
        self._text.setFixedHeight(42)
        self._layout.addWidget(self._text, 2)
        self._feedback = GTextEditor(toolbar, "feedback")
        self._feedback.setToolTip("Feedback for this answer")
        self._feedback.setFixedHeight(42)
        self._layout.addWidget(self._feedback, 1)
        self._grade = GField("fraction", self, str)
        self._grade.setMaximumWidth(50)
        self._grade.setToolTip("Grade for this answer")
        self._layout.addWidget(self._grade, 0)
        self._layout.setContentsMargins(5, 5, 5, 5)
        self._layout.setSpacing(2)
        if question is not None:
            if option is None:
                option = Answer()
                question.append(option)
            self.from_obj(option)

    def from_obj(self, obj: Answer) -> None:
        """_summary_
        Args:
            obj (Answer): _description_
        """
        self.option = obj
        self._text.from_obj(obj)
        self._grade.from_obj(obj)
        self._feedback.from_obj(obj)


class GCalculated(GAnswer):
    """An UI representation for QCalculated class.
    """

    def __init__(self, toolbar: GTextToolbar, question: list, option=None):
        super().__init__(toolbar, None)
        self._text.setFixedHeight(30)
        self._feedback.setFixedHeight(30)
        self._tol_type = GDropbox("ttype", self, TolType)
        self._tol_type.setToolTip("The tolerance type")
        self._tol_type.setFixedWidth(105)
        self._layout.addWidget(self._tol_type)
        self._ans_type = GDropbox("aformat", self, TolFormat)
        self._ans_type.setToolTip("Tolerance format")
        self._ans_type.setFixedWidth(110)
        self._layout.addWidget(self._ans_type)
        self._tolerance = GField("tolerance", self, int)
        self._tolerance.setToolTip("The tolerance value")
        self._tolerance.setFixedWidth(45)
        self._layout.addWidget(self._tolerance)
        self._answer_len = GField("alength", self,  int)
        self._answer_len.setToolTip("Number of significant figures/decimals")
        self._answer_len.setFixedWidth(30)
        self._layout.addWidget(self._answer_len)
        if option is None:
            option = ACalculated()
            question.append(option)
        self.from_obj(option)

    def from_obj(self, obj: ACalculated) -> None:
        super().from_obj(obj)
        self._tol_type.from_obj(obj)
        self._tolerance.from_obj(obj)
        self._ans_type.from_obj(obj)
        self._answer_len.from_obj(obj)


class GCloze(QFrame):
    """GUI for QCloze class.
    """

    def __init__(self, _, question: list, option=None):
        super().__init__()
        _layout = QHBoxLayout(self)
        _layout.setSpacing(2)
        self.__obj: EmbeddedItem = None
        self._grade = GField("grade", self, int)
        self._grade.setFixedWidth(30)
        self._grade.setToolTip("Grade for the given answer")
        _layout.addWidget(self._grade, 0)
        self._form = GDropbox("cformat", self, EmbeddedFormat)
        self._form.setToolTip("Cloze format")
        self._form.setMinimumWidth(160)
        _layout.addWidget(self._form, 1)
        _layout.addSpacing(20)
        self._opts = GDropbox("opts", self, None)
        self._opts.currentIndexChanged.connect(self.__changed_opt)
        _layout.addWidget(self._opts, 0)
        self._frac = GField("fraction", self, int)
        self._frac.setFixedWidth(35)
        self._frac.setToolTip("Fraction of the total grade (in percents)")
        _layout.addWidget(self._frac, 0)
        self._text = GField("text", self, str)
        self._text.setToolTip("Answer text")
        _layout.addWidget(self._text, 1)
        self._fdbk = GField("text", self, str)
        self._fdbk.setToolTip("Answer feedback")
        _layout.addWidget(self._fdbk, 1)
        _layout.addSpacing(20)
        self._add = QPushButton("Add")
        self._add.clicked.connect(self.add_opts)
        _layout.addWidget(self._add, 0)
        self._pop = QPushButton("Pop")
        self._pop.clicked.connect(self.pop_opts)
        _layout.addWidget(self._pop, 0)
        _layout.setContentsMargins(2, 2, 2, 2)
        if option is None:
            option = EmbeddedItem(0.0, EmbeddedFormat.MC)
            question.append(option)
        self.from_obj(option)

    def __changed_opt(self, index):
        self._frac.from_obj(self.__obj.opts[index])
        self._text.from_obj(self.__obj.opts[index])
        self._fdbk.from_obj(self.__obj.opts[index].feedback)

    def add_opts(self, stat: bool):
        """_summary_
        Args:
            stat (bool): _description_
        """
        if not stat:
            LOG.debug("Button clicked is not receiving stat False")
        text = self._text.text()
        frac = float(self._frac.text())
        fdbk = FText(self._fdbk.text(), TextFormat.PLAIN)
        self.__obj.opts.append(Answer(frac, text, fdbk, TextFormat.PLAIN))
        self._opts.addItem(text)

    def pop_opts(self, _):
        """_summary_
        Args:
            stat (bool): _description_
        """
        if len(self.__obj.opts) > 1:
            self.__obj.opts.pop()
            self._opts.removeItem(self._opts.count()-1)

    def from_obj(self, obj: EmbeddedItem) -> None:
        """_summary_
        Args:
            obj (ClozeItem): _description_
        """
        self.__obj = obj
        self._form.from_obj(obj)
        self._grade.from_obj(obj)
        self._opts.from_obj(obj)


class GDrag(QWidget):
    """This class works for both DragGroup and DragItem.
    """

    TYPES = ["Image", "Text"]

    def __init__(self, _, question: list, option=None):
        super().__init__()
        self._layout = QGridLayout(self)
        self._layout.addWidget(QLabel("Text"), 0, 0)
        self._text = GField("text", self, str)
        self._layout.addWidget(self._text, 0, 1)
        self._layout.addWidget(QLabel("Group"), 0, 2)
        self._group = GField("group", self, int)
        self._group.setFixedWidth(20)
        self._layout.addWidget(self._group, 0, 3)
        self._layout.addWidget(QLabel("Type"), 0, 4)
        self._itype = GDropbox(None, self, self.TYPES)
        self._itype.setCurrentIndex(1)
        self._itype.setEnabled(False)
        self._itype.setFixedWidth(55)
        self._layout.addWidget(self._itype, 0, 5)
        self._nodrags = GField("no_of_drags", self, int)
        self._layout.addWidget(self._nodrags, 0, 6)
        self.img = None
        if option is None:
            option = EmbeddedItem(0.0, EmbeddedFormat.MC)
            question.append(option)
        self.from_obj(option)

    def from_obj(self, obj: DragGroup):
        """_summary_
        Args:
            obj (_type_): _description_
        """
        self._text.from_obj(obj)
        self._group.from_obj(obj)
        self._nodrags.from_obj(obj)


class GDragImage(GDrag):
    """This class works from both DragText and DragItem.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.imagem = QPushButton("Imagem")
        self._layout.addWidget(self.imagem, 1, 2)
        self._itype.setEnabled(True)


class GDropZone(QWidget):
    """GUI for QDropZone class.
    """

    TYPES = ["Image", "Text"]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        _layout = QHBoxLayout(self)
        _layout.addWidget(QLabel("Type", self), 0)
        self._itype = GDropbox(None, self, self.TYPES)
        self._itype.addItem(self.TYPES)
        _layout.addWidget(self._itype, 1)
        self._group = GField("group", self, int)
        _layout.addWidget(QLabel("Group"), 2)
        _layout.addWidget(self._group, 3)
        self._text = GField("text", self, str)
        _layout.addWidget(QLabel("Text"), 4)
        _layout.addWidget(self._text, 5)
        self._ndrags = GField("no_of_drags", self, int)
        _layout.addWidget(QLabel("No Drags"), 4)
        _layout.addWidget(self._ndrags, 5)

    def from_obj(self, obj: DropZone):
        """_summary_

        Args:
            obj (DragItem): _description_
        """
        self._group.from_obj(obj)
        self._text.from_obj(obj)
        self._ndrags.from_obj(obj)


class GSelectOption(QWidget):
    """GUI for QDropZone class.
    """

    def __init__(self):
        super().__init__()
        _layout = QHBoxLayout(self)
        self._group = GField("group", self, int)
        _layout.addWidget(QLabel("Group"), 0)
        _layout.addWidget(self._group, 1)
        self._text = GField("text", self, str)
        _layout.addWidget(QLabel("Text"), 2)
        _layout.addWidget(self._text, 3)
        self._pop = QPushButton("Pop", self)
        _layout.addWidget(self._text, 4)

    def from_obj(self, obj: SelectOption):
        """_summary_

        Args:
            obj (_type_): _description_
        """
        self._text.from_obj(obj)
        self._group.from_obj(obj)


class GHint(QFrame):
    """GUI class for the Hint wrapper.
    """

    def __init__(self, toolbar: GTextToolbar, question: list, option=None):
        super().__init__()
        self.__obj = None
        self._text = GTextEditor(toolbar, "text")
        self._show = GCheckBox("show_correct", "Show the number of"
                               " correct responses", self)
        self._state = GCheckBox("state_incorrect", "State which markers "
                                "are incorrectly placed", self)
        self._clear = GCheckBox("clear_wrong", "Move incorrectly placed "
                                "markers back to default start position", self)
        _content = QGridLayout(self)
        _content.addWidget(self._text, 0, 0, 3, 1)
        _content.addWidget(self._show, 0, 1)
        _content.addWidget(self._state, 1, 1)
        _content.addWidget(self._clear, 2, 1)
        if option is None:
            option = Hint(TextFormat.AUTO, "", True, True)
            question.append(option)
        self.from_obj(option)

    def from_obj(self, obj: Hint) -> None:
        """_summary_

        Args:
            obj (Hint): _description_
        """
        self.__obj = obj
        self._show.setChecked(self.__obj.show_correct)
        self._clear.setChecked(self.__obj.clear_wrong)
        self._state.setChecked(self.__obj.state_incorrect)
        if self.__obj.formatting == TextFormat.MD:
            self._text.setMarkdown(self.__obj.text)
        elif self.__obj.formatting == TextFormat.HTML:
            self._text.setHtml(self.__obj.text)
        elif self.__obj.formatting == TextFormat.PLAIN:
            self._text.setPlainText(self.__obj.text)

    def get_attr(self):
        """Get attribute
        """
        return "hint"

    @property
    def obj(self):
        """Object
        """
        return self.__obj


class GCrossWord(QWidget):
    """GUI class for the CrossWord question class.
    """

    def from_obj(self, _) -> None:
        """_summary_

        Args:
            obj (QCrossWord): _description_
        """
        LOG.debug(f"Function <from_obj> not implemented in {self}")


class GTagBar(QFrame):
    """Custom widget that allows the user to enter tags and provides a
    interface to later get these tags as a list.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self._tags: list = None
        self.cat_tags: dict = None
        self._h_layout = QHBoxLayout(self)
        self._h_layout.setContentsMargins(0, 0, 0, 0)
        self._h_layout.setSpacing(1)
        self._line_edit = QLineEdit(self)
        self._line_edit.returnPressed.connect(self.__create_tags)
        self._line_edit.textChanged.connect(self.__on_text_change)
        self._h_layout.addWidget(self._line_edit, 1)
        completer = QCompleter(["easy"], self)
        self._line_edit.setCompleter(completer)
        self._model_item = completer.model()

    def __create_tags(self):
        new_tags = self._line_edit.text().split(',')
        self._line_edit.setText('')
        for tag in new_tags:
            if tag not in self._tags:
                self._tags.append(tag)
                self.cat_tags[tag] = self.cat_tags.setdefault(tag, 0) + 1
        self._tags.sort(key=lambda x: x.lower())
        self.__refresh()

    def __on_text_change(self):
        text = self._line_edit.text().lower()
        if self.cat_tags is None or not text:
            return
        tmp = []
        for item in self.cat_tags:
            if text in item.lower():
                tmp.append(item)
        self._model_item.setStringList(tmp)

    def __delete(self, tag_name):
        index = self._tags.index(tag_name)
        self._tags.remove(tag_name)
        self._h_layout.itemAt(index + 1).widget().setParent(None)
        self._line_edit.setFocus()

    def __refresh(self):
        for i in reversed(range(1, self._h_layout.count())):
            self._h_layout.itemAt(i).widget().setParent(None)
        if self._tags:
            for tag in self._tags:
                label = QLabel(tag + "    ", self)
                hbox = QHBoxLayout(label)
                hbox.setContentsMargins(0, 0, 0, 5)
                x_button = QPushButton('x', label)
                x_button.setFixedSize(16, 16)
                x_button.clicked.connect(lambda _, _tg=tag: self.__delete(_tg))
                hbox.addWidget(x_button, 0, Qt.AlignRight)
                self._h_layout.addWidget(label)
        self._line_edit.setFocus()

    def from_list(self, obj):
        """Update the list of tags based on a iterable object.
        """
        self._tags = obj
        self.__refresh()

    def from_obj(self, obj):
        """_summary_

        Args:
            obj (_Question): _description_
        """
        self.from_list(obj.tags)

    def get_attr(self):
        """ Return attribute updated when new tag is added.
        """
        return "tags"

    def set_gtags(self, tags: dict):
        """Set the complete list of tags using in the project. Tags may be
        duplicate, so a dict is used to count how many times it is used.
        """
        self._model_item.setStringList(set(tags))
        self.cat_tags = tags
