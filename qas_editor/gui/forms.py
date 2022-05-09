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
import logging
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QFrame,\
                            QPushButton,QLabel, QGridLayout, QApplication
from ..answer import Answer, CalculatedAnswer, DragItem, ClozeItem
from ..enums import ClozeFormat, Format, ToleranceType
from ..wrappers import FText, Hint, Subquestion, SelectOption
from ..questions import QCalculatedMultichoice, QCalculatedSimple, QCloze,\
                        QDragAndDropImage, QDragAndDropText, QMatching, \
                        QMissingWord, QMultichoice, QCalculated, QNumerical,\
                        QRandomMatching, QDragAndDropMarker
from .utils import GCheckBox, GDropbox, GField, GTextEditor, action_handler
if TYPE_CHECKING:
    from .utils import GTextToolbar
LOG = logging.getLogger(__name__)


class GAnswer(QWidget):
    """GUI for QAnswer class.
    """

    def __init__(self, **kwargs):
        super().__init__()
        _layout = QHBoxLayout(self)
        self._text = GTextEditor(kwargs.get("toolbar"), "text")
        self._text.setToolTip("Answer's text")
        _layout.addWidget(self._text, 0)
        self._feedback = GTextEditor(kwargs.get("toolbar"), "feedback")
        self._feedback.setToolTip("Feedback for this answer")
        _layout.addWidget(self._feedback, 1)
        self._grade = GField(self, str, "fraction")
        self._grade.setMaximumWidth(50)
        self._grade.setToolTip("Grade for this answer")
        _layout.addWidget(self._grade, 2)
        _layout.setStretch(0, 0)
        _layout.setStretch(0, 1)
        _layout.setContentsMargins(0,0,0,0)

    def from_obj(self, obj: Answer) -> None:
        """_summary_

        Args:
            obj (Answer): _description_
        """
        self._text.from_obj(obj, True)
        self._grade.from_obj(obj)
        self._feedback.from_obj(obj)


class GCalculated(QWidget):

    def __init__(self, toolbar: GTextToolbar, **kwargs):
        super().__init__(**kwargs)
        _layout = QGridLayout(self)
        self._text = GTextEditor(toolbar, "text", parent=self)
        self._text.setToolTip("Answer's formula")
        _layout.addWidget(self._text, 0, 0)
        self._grade = GField(self, int, "fraction")
        self._grade.setMaximumWidth(50)
        self._grade.setToolTip("Grade for this answer")
        _layout.addWidget(self._grade, 0, 1)
        self._feedback = GTextEditor(toolbar, "feedback", parent=self)
        self._feedback.setToolTip("Feedback for this answer")
        _layout.addWidget(self._feedback, 0, 2, 1, 3)
        self._tol_type = GDropbox(self, "tolerance_type", ToleranceType)
        _layout.addWidget(self._tol_type, 1, 0)
        self._tolerance = GField(self, int, "tolerance")
        _layout.addWidget(self._tolerance, 1, 1)
        self._ans_type = GCheckBox(self, "Test123", "answer_format")
        _layout.addWidget(self._ans_type, 2, 0)
        self._answer_len = GField(self, int, "answer_length")
        _layout.addWidget(self._answer_len, 2, 1)

    def from_obj(self, obj: CalculatedAnswer) -> None:
        self._text.from_obj(obj, False)
        self._grade.from_obj(obj)
        self._feedback.from_obj(obj)
        self._tol_type.from_obj(obj)
        self._tolerance.from_obj(obj)
        self._ans_type.from_obj(obj)
        self._answer_len.from_obj(obj)


class GCloze(QWidget):
    """GUI for QCloze class.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        _layout = QHBoxLayout(self)
        _layout.setSpacing(3)
        self.__obj: ClozeItem = None
        self._pos = GField(self, int , "start")
        self._pos.setFixedWidth(40)
        self._pos.setToolTip("Position in the plain text")
        _layout.addWidget(self._pos)
        self._grade = GField(self, int, "grade")
        self._grade.setFixedWidth(20)
        self._grade.setToolTip("Grade for the given answer")
        _layout.addWidget(self._grade)
        self._form = GDropbox(self, "cformat", ClozeFormat)
        self._form.setToolTip("Cloze format")
        _layout.addWidget(self._form)
        _layout.addSpacing(25)
        self._opts = GDropbox(self, "opts", Answer)
        self._opts.setFixedWidth(140)
        self._opts.currentIndexChanged.connect(self.__changed_opt)
        _layout.addWidget(self._opts)
        self._frac = GField(self, int, "fraction")
        self._frac.setFixedWidth(35)
        self._frac.setToolTip("Fraction of the total grade (in percents)")
        _layout.addWidget(self._frac)
        self._text = GTextEditor(self, str, "text")
        self._text.setToolTip("Answer text")
        _layout.addWidget(self._text)
        self._fdbk = GTextEditor(self, str, "feedback")
        self._fdbk.setToolTip("Answer feedback")
        _layout.addWidget(self._fdbk)
        _layout.addSpacing(20)
        self._add = QPushButton("Add")
        self._add.setMinimumWidth(20)
        self._add.clicked.connect(self.add_opts)
        _layout.addWidget(self._add)
        self._pop = QPushButton("Pop")
        self._pop.setMinimumWidth(20)
        self._pop.clicked.connect(self.pop_opts)
        _layout.addWidget(self._pop)

    def __changed_opt(self, index):
        self._frac.from_obj(self.opts[index])
        self._text.from_obj(self.opts[index], False)
        self._fdbk.from_obj(self.opts[index], True)

    @action_handler
    def add_opts(self, stat: bool):
        """_summary_

        Args:
            stat (bool): _description_
        """
        if not stat:
            LOG.debug("Button clicked is not receiving stat False")
        text = self._text.text()
        frac = float(self._frac.text())
        fdbk = FText(self._fdbk.text(), Format.PLAIN)
        self.__obj.opts.append(Answer(frac, text, fdbk, Format.PLAIN))
        self._opts.addItem(text)

    @action_handler
    def pop_opts(self, stat: bool):
        """_summary_

        Args:
            stat (bool): _description_
        """
        if not stat:
            LOG.debug("Button clicked is not receiving stat False")
        self.__obj.opts.pop()
        self._opts.removeItem(self._opts.count()-1)

    def from_obj(self, obj: ClozeItem) -> None:
        """_summary_

        Args:
            obj (ClozeItem): _description_
        """
        self.__obj = obj
        self._pos.from_obj(obj)
        self._form.from_obj(obj)
        self._grade.from_obj(obj)
        self._opts.from_obj(obj)


class GDrag(QWidget):
    """This class works from both DragText and DragItem.
    I hope someday people from moodle unify these 2.

    Args:
        QGridLayout ([type]): [description]
    """

    TYPES = ["Image", "Text"]

    def __init__(self, only_text: bool, **kwargs) -> None:
        super().__init__(**kwargs)
        _layout = QGridLayout(self)
        _layout.addWidget(QLabel("Text"), 0, 0)
        self.text = GField(self, str, "text")
        _layout.addWidget(self.text, 0, 1)
        _layout.addWidget(QLabel("Group"), 0, 2)
        self.group = GField(self, int, "group")
        self.group.setFixedWidth(20)
        _layout.addWidget(self.group, 0, 3)
        _layout.addWidget(QLabel("Type"), 0, 4)
        self.itype = GDropbox(self, None, self.TYPES)
        self.itype.setFixedWidth(55)
        _layout.addWidget(self.itype, 0, 5)
        self.unlimited = GCheckBox(self, "Unlimited", "unlimited")
        _layout.addWidget(self.unlimited, 0, 6)
        if only_text:
            self.itype.setCurrentIndex(1)
            self.itype.setEnabled(False)
        else:
            self.imagem = QPushButton("Imagem")
            _layout.addWidget(self.imagem, 1, 2)
        self.img = None
        self.obj = None

    def __del__(self):
        try:
            for i in range(self.count()):
                self.itemAt(i).widget().deleteLater()
        except RuntimeError:
            pass

    def from_obj(self, obj):
        """_summary_

        Args:
            obj (_type_): _description_
        """
        self.text.setText(obj.text)
        self.group.setText(str(obj.group))
        self.unlimited.setChecked(obj.unlimited)
        self.obj = obj

    def setVisible(self, visible: bool) -> None:    # pylint: disable=C0103
        """_summary_

        Args:
            visible (bool): _description_
        """
        for child in self.children():
            child.setVisible(visible)


class GDropZone(QWidget):
    """GUI for QDropZone class.
    """

    TYPES = ["Image", "Text"]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        _layout = QHBoxLayout(self)
        self.__obj = None
        _layout.addWidget(QLabel("Type", self), 0)
        self.itype = GDropbox(self, None, self.TYPES)
        self.itype.addItem(self.TYPES)
        _layout.addWidget(self.itype, 1)
        self.group = GField(self)
        _layout.addWidget(QLabel("Group"), 2)
        _layout.addWidget(self.group, 3)
        self.text = GField(self)
        _layout.addWidget(QLabel("Text"), 4)
        _layout.addWidget(self.text, 5)
        self._ndrags = GField(self)
        _layout.addWidget(QLabel("No Drags"), 4)
        _layout.addWidget(self._ndrags, 5)

    def from_obj(self, obj: DragItem):
        """_summary_

        Args:
            obj (DragItem): _description_
        """
        self.__obj = obj
        #self.itype.setCurrentText(obj.)
        self.group.setText(obj.group)
        self.text.setText(obj.text)
        self._ndrags.setText(obj.no_of_drags)


class GSelectOption(QWidget):
    """GUI for QDropZone class.
    """

    def __init__(self):
        super().__init__()
        self.__obj = None
        _layout = QHBoxLayout(self)
        self._group = GField(self, int, "group")
        _layout.addWidget(QLabel("Group"), 0)
        _layout.addWidget(self._group, 1)
        self._text = GField(self, str, "text")
        _layout.addWidget(QLabel("Text"), 2)
        _layout.addWidget(self._text, 3)
        self._pop = QPushButton("Pop", self)
        _layout.addWidget(self._text, 4)

    def from_obj(self, obj: SelectOption):
        """_summary_

        Args:
            obj (_type_): _description_
        """
        self.__obj = obj
        self._text.setText(obj.text)
        self._group.setText(str(obj.group))


class GOptions(QVBoxLayout):
    """GUI for GOptions class.
    """
    _TYPES = {
        QCalculated: (GCalculated, False),
        QCalculatedSimple: (GCalculated, False),
        QCalculatedMultichoice: (GCalculated, False),
        QCloze: (GCloze, False),
        QDragAndDropText: (GDrag, True),
        QDragAndDropMarker: (GDrag, False),
        QDragAndDropImage: (GDrag, False),
        QMatching: (Subquestion, False),
        QRandomMatching: (),
        QMultichoice: (GAnswer, False),
        QNumerical: (GAnswer, False),
        QMissingWord: (SelectOption, False)
    }

    def __init__(self, toolbar, **kwargs) -> None:
        super().__init__(**kwargs)
        self.visible = True
        self.toolbar = toolbar
        self.__ctype = None
        self.__obj: list = None

    def add(self):
        """_summary_

        Raises:
            TypeError: _description_

        Returns:
            _type_: _description_
        """
        cls, only_text = self._TYPES[self.__ctype]
        item = cls(toolbar=self.toolbar, only_text=only_text)
        self.addWidget(item)
        return item

    def from_obj(self, obj) -> None:
        """_summary_

        Args:
            objs (list): _description_
        """
        ctype = self.__ctype
        self.__ctype = type(obj)
        self.__obj = obj.options
        new_size = len(self.__obj)
        if len(self.children()) != 0:
            to_rem = 0
            if self._TYPES[ctype][0] != self._TYPES[self.__ctype][0]:
                to_rem = self.count()
            elif self.count() > new_size:
                to_rem = self.count() - new_size
            for i in reversed(range(to_rem)):
                self.itemAt(i).layout().deleteLater()
            for obj, child in zip(self.__obj, self.children()):
                child.from_obj(obj)
        if self.count() < new_size:
            for obj in self.__obj[self.count():]:
                item = self.add()
                item.from_obj(obj)

    def get_attr(self):
        return "options"

    def pop(self) -> None:
        """_summary_
        """
        widget = QApplication.focusWidget().parent()
        for idx in range(self.count()):
            if self.itemAt(idx).widget() == widget:
                self.removeWidget(widget)
                widget.deleteLater()

    def setVisible(self, visible: bool) -> None:    # pylint: disable=C0103
        """_summary_

        Args:
            visible (bool): _description_
        """
        if self.visible == visible:
            return
        for child in self.children():
            child.setVisible(visible)


class GHint(QFrame):
    """GUI class for the Hint wrapper.
    """

    def __init__(self, toolbar: GTextToolbar, hint: Hint = None):
        super().__init__()
        self.__obj = None
        self._text = GTextEditor(toolbar, "text")
        self._show = GCheckBox(self, "Show the number of correct responses",
                               "show_correct")
        self._state = GCheckBox(self, "State which markers are incorrectly placed",
                                "state_incorrect")
        self._clear = GCheckBox(self, "Move incorrectly placed markers back to "
                                "default start position", "clear_wrong")
        _content = QGridLayout(self)
        _content.addWidget(self._text, 0, 0, 3, 1)
        _content.addWidget(self._show, 0, 1)
        _content.addWidget(self._state, 1, 1)
        _content.addWidget(self._clear, 2, 1)
        if hint is None:
            hint = Hint(Format.AUTO, "", True, True)
        self.from_obj(hint)

    def from_obj(self, obj: Hint) -> None:
        """_summary_

        Args:
            obj (Hint): _description_
        """
        self.__obj = obj
        self._show.setChecked(self.__obj.show_correct)
        self._clear.setChecked(self.__obj.clear_wrong)
        self._state.setChecked(self.__obj.state_incorrect)
        if self.__obj.formatting == Format.MD:
            self._text.setMarkdown(self.__obj.text)
        elif self.__obj.formatting == Format.HTML:
            self._text.setHtml(self.__obj.text)
        elif self.__obj.formatting == Format.PLAIN:
            self._text.setPlainText(self.__obj.text)

    def get_attr(self):
        return "hint"

    @property
    def obj(self):
        return self.__obj


class GHintsList(QVBoxLayout):
    """GUI class for the MultipleTries wrapper
    """

    def __init__(self, parent: QWidget, toolbar: GTextToolbar) -> None:
        super().__init__(parent)
        self.__obj: list = None
        self._toolbar = toolbar

    def add(self):
        """
        """
        ui = GHint(self._toolbar)
        self.__obj.append(ui.obj)
        super().addWidget(ui)

    def from_obj(self, obj) -> None:
        """_summary_

        Args:
            obj (MultipleTries): _description_
        """
        self.__obj = obj.hints
        new_size = len(self.__obj)
        if len(self.children()) != 0:
            to_rem = 0
            if self.count() > new_size:
                to_rem = self.count() - new_size
            for i in reversed(range(to_rem)):
                self.itemAt(i).layout().deleteLater()
            for obj, child in zip(self.__obj, self.children()):
                child.from_obj(obj)
        if self.count() < new_size:
            for obj in self.__obj[self.count():]:
                item = self.add()
                item.from_obj(obj)

    def get_attr(self):
        return "hints"

    def pop(self) -> None:
        """_summary_
        """
        if not self.count():
            return
        self.itemAt(self.count()-1).widget().deleteLater()


class GCrossWord(QWidget):
    """GUI class for the CrossWord question class.
    """

    def from_obj(self, _) -> None:
        """_summary_

        Args:
            obj (QCrossWord): _description_
        """
        LOG.debug(f"Function <from_obj> not implemented in {self}")


class GUnits(QVBoxLayout):

    def __init__(self):
        pass

    def get_attr(self):
        return "units"

class GZones(QVBoxLayout):

    def __init__(self, parent):
        _row = QHBoxLayout()
        self._background = QPushButton("Background")
        _row.addLayout(self._background)
        self._highlight = GCheckBox(parent, "Highlight dropzones with incorre"
                                    "ct correct markers placed", "highlight")

    def from_obj(self, obj) -> None:
        """_summary_

        Args:
            obj (MultipleTries): _description_
        """
        self.__obj = obj.hints
        new_size = len(self.__obj)
        if len(self.children()) != 0:
            to_rem = 0
            if self.count() > new_size:
                to_rem = self.count() - new_size
            for i in reversed(range(to_rem)):
                self.itemAt(i).layout().deleteLater()
            for obj, child in zip(self.__obj, self.children()):
                child.from_obj(obj)
        if self.count() < new_size:
            for obj in self.__obj[self.count():]:
                item = self.add()
                item.from_obj(obj)

    def get_attr(self):
        return "zones"

                                
