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
                            QComboBox, QCheckBox, QLineEdit, QPushButton,\
                            QLabel, QGridLayout
from ..answer import Answer, CalculatedAnswer, DragItem, ClozeItem
from ..enums import ClozeFormat, Format
from ..wrappers import FText, Hint, Subquestion
from ..questions import QCalculatedMultichoice, QCalculatedSimple, QCloze,\
                        QDragAndDropImage, QDragAndDropText, QMatching,\
                        QMultichoice, QCalculated, QNumerical, QRandomMatching
from .utils import GField, GTextEditor, action_handler
if TYPE_CHECKING:
    from .utils import GTextToolbar
LOG = logging.getLogger(__name__)


class GAnswer(QHBoxLayout):
    """GUI for QAnswer class.
    """

    def __init__(self, **kwargs):
        super().__init__()
        self._text = GTextEditor(kwargs.get("toolbar"), "text")
        self._text.setToolTip("Answer's text")
        self.addWidget(self._text, 0)
        self._feedback = GTextEditor(kwargs.get("toolbar"), "feedback")
        self._feedback.setToolTip("Feedback for this answer")
        self.addWidget(self._feedback, 1)
        self._grade = GField(str, "fraction")
        self._grade.setMaximumWidth(50)
        self._grade.setToolTip("Grade for this answer")
        self.addWidget(self._grade, 2)
        self.setStretch(0, 0)
        self.setStretch(0, 1)

    def __del__(self):
        try:
            for i in range(self.count()):
                self.itemAt(i).widget().deleteLater()
        except RuntimeError:
            pass

    def from_obj(self, obj: Answer) -> None:
        """_summary_

        Args:
            obj (Answer): _description_
        """
        self._text.from_obj(obj)
        self._grade.from_obj(obj)
        self._feedback.from_obj(obj)

    def setVisible(self, visible: bool) -> None:  # pylint: disable=C0103
        """_summary_

        Args:
            visible (bool): _description_
        """
        for child in self.children():
            child.setVisible(visible)


class GCalculated(QFrame):

    def __init__(self, toolbar: GTextToolbar, **kwargs):
        super().__init__(**kwargs)
        self.__obj = None
        grid = QGridLayout(self)
        self.setLayout(grid)
        self._text = GTextEditor(toolbar, "", parent=self)
        self._text.setToolTip("Answer's formula")
        grid.addWidget(self._text, 0, 0)
        self._grade = QLineEdit(self)
        self._grade.setMaximumWidth(50)
        self._grade.setToolTip("Grade for this answer")
        grid.addWidget(self._grade, 0, 1)
        self._feedback = GTextEditor(toolbar, "feedback", parent=self)
        self._feedback.setToolTip("Feedback for this answer")
        grid.addWidget(self._feedback, 0, 2, 1, 3)
        self._tol_type = QComboBox(self)
        grid.addWidget(self._tol_type, 1, 0)
        self._tolerance = QLineEdit(self)
        grid.addWidget(self._tolerance, 1, 1)
        self._ans_type = QCheckBox(self)
        grid.addWidget(self._ans_type, 2, 0)
        self._answer_disp = QLineEdit(self)
        grid.addWidget(self._answer_disp, 2, 1)

    def from_obj(self, obj: CalculatedAnswer) -> None:
        self.__obj = obj


class GCloze(QHBoxLayout):
    """GUI for QCloze class.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.setSpacing(3)
        self.obj: ClozeItem = None
        self.opts = []
        self._pos = QLineEdit()
        self._pos.setFixedWidth(40)
        self._pos.setToolTip("Position in the plain text")
        self.addWidget(self._pos)
        self._grade = QLineEdit()
        self._grade.setFixedWidth(20)
        self._grade.setToolTip("Grade for the given answer")
        self.addWidget(self._grade)
        self._form = QComboBox()
        self._form.addItems([a.value for a in ClozeFormat])
        self._form.setToolTip("Cloze format")
        self.addWidget(self._form)
        self.addSpacing(25)
        self._opts = QComboBox()
        self._opts.setFixedWidth(140)
        self._opts.currentIndexChanged.connect(self.__changed_opt)
        self.addWidget(self._opts)
        self._frac = QLineEdit()
        self._frac.setFixedWidth(35)
        self._frac.setToolTip("Fraction of the total grade (in percents)")
        self.addWidget(self._frac)
        self._text = QLineEdit()
        self._text.setToolTip("Answer text")
        self.addWidget(self._text)
        self._fdbk = QLineEdit()
        self._fdbk.setToolTip("Answer feedback")
        self.addWidget(self._fdbk)
        self.addSpacing(20)
        self._add = QPushButton("Add")
        self._add.setMinimumWidth(20)
        self._add.clicked.connect(self.add_opts)
        self.addWidget(self._add)
        self._pop = QPushButton("Pop")
        self._pop.setMinimumWidth(20)
        self._pop.clicked.connect(self.pop_opts)
        self.addWidget(self._pop)

    def __del__(self):
        try:
            for i in range(self.count()):
                self.itemAt(i).widget().deleteLater()
        except RuntimeError:
            pass

    def __changed_opt(self, index):
        self._frac.setText(str(self.opts[index].fraction))
        self._text.setText(self.opts[index].text)
        self._fdbk.setText(self.opts[index].feedback.text)

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
        self.opts.append(Answer(frac, text, fdbk, Format.PLAIN))
        self._opts.addItem(text)

    @action_handler
    def pop_opts(self, stat: bool):
        """_summary_

        Args:
            stat (bool): _description_
        """
        if not stat:
            LOG.debug("Button clicked is not receiving stat False")
        self.opts.pop()
        self._opts.removeItem(self._opts.count()-1)

    def from_obj(self, obj: Answer) -> None:
        """_summary_

        Args:
            obj (ClozeItem): _description_
        """
        self._pos.setText(str(obj.start))
        self._form.setCurrentText(str(obj.cformat.value))
        self._grade.setText(str(obj.grade))
        self.opts = obj.opts
        self._opts.addItems([a.text for a in self.opts])

    def setVisible(self, visible: bool) -> None:    # pylint: disable=C0103
        """_summary_

        Args:
            visible (bool): _description_
        """
        for child in self.children():
            child.setVisible(visible)


class GDrag(QGridLayout):
    """This class works from both DragText and DragItem.
    I hope someday people from moodle unify these 2.

    Args:
        QGridLayout ([type]): [description]
    """

    TYPES = ["Image", "Text"]

    def __init__(self, only_text: bool, **kwargs) -> None:
        super().__init__(**kwargs)
        self.addWidget(QLabel("Text"), 0, 0)
        self.text = QLineEdit()
        self.addWidget(self.text, 0, 1)
        self.addWidget(QLabel("Group"), 0, 2)
        self.group = QLineEdit()
        self.group.setFixedWidth(20)
        self.addWidget(self.group, 0, 3)
        self.addWidget(QLabel("Type"), 0, 4)
        self.itype = QComboBox()
        self.itype.addItems(self.TYPES)
        self.itype.setFixedWidth(55)
        self.addWidget(self.itype, 0, 5)
        self.unlimited = QCheckBox("Unlimited")
        self.addWidget(self.unlimited, 0, 6)
        if only_text:
            self.itype.setCurrentIndex(1)
            self.itype.setEnabled(False)
        else:
            self.imagem = QPushButton("Imagem")
            self.addWidget(self.imagem, 1, 2)
        self.only_text = only_text
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


class GDropZone(QGridLayout):
    """GUI for QDropZone class.
    """

    TYPES = ["Image", "Text"]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.addWidget(QLabel("Type"), 0, 0)
        self.itype = QComboBox()
        self.itype.addItem(self.TYPES)
        self.addWidget(self.itype, 0, 1)
        self.group = QLineEdit()
        self.addWidget(QLabel("Group"), 0, 2)
        self.addWidget(self.group, 0, 3)
        self.text = QLineEdit()
        self.addWidget(QLabel("Text"), 0, 4)
        self.addWidget(self.text, 0, 5)

    def __del__(self):
        try:
            for i in range(self.count()):
                self.itemAt(i).widget().deleteLater()
        except RuntimeError:
            pass

    def from_obj(self, _: DragItem):
        """_summary_

        Args:
            obj (DragItem): _description_
        """
        LOG.debug(f"Function <from_obj> not implemented in {self}")

    def setVisible(self, visible: bool) -> None:    # pylint: disable=C0103
        """_summary_

        Args:
            visible (bool): _description_
        """
        for child in self.children():
            child.setVisible(visible)


class GOptions(QVBoxLayout):
    """GUI for GOptions class.
    """
    _TYPES = {
        QCalculated: (GCalculated, False),
        QCalculatedSimple: (GCalculated, False),
        QCalculatedMultichoice: (GCalculated, False),
        QCloze: (GCloze, False),
        QDragAndDropText: (GDrag, True),
        QDragAndDropImage: (GDrag, False),
        QMatching: (Subquestion, False),
        QRandomMatching: (),
        QMultichoice: (GAnswer, False),
        QNumerical: (GAnswer, False)
    }

    def __init__(self, toolbar, **kwargs) -> None:
        super().__init__(**kwargs)
        self.visible = True
        self.toolbar = toolbar
        self.__ctype = None
        self.__obj: list = None
        self.setContentsMargins(0, 0, 0, 0)

    def add_default(self):
        """_summary_

        Raises:
            TypeError: _description_

        Returns:
            _type_: _description_
        """
        cls, only_text = self._TYPES[self.__ctype]
        item = cls(toolbar=self.toolbar, only_text=only_text)
        self.addLayout(item)
        return item

    def addLayout(self, layout, stretch: int = 0):  # pylint: disable=C0103
        """_summary_

        Args:
            layout (_type_): _description_
            stretch (int, optional): _description_. Defaults to 0.

        Returns:
            _type_: _description_
        """
        if not isinstance(layout, self.__ctype):
            LOG.warning(f"Attempted adding {type(layout)} to GOptions.")
        return super().addLayout(layout, stretch=stretch)

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
                item = self.add_default()
                item.from_obj(obj)
                self.add(obj)

    def get_attr(self):
        return "options"

    def pop(self) -> None:
        """_summary_
        """
        if not self.count():
            return
        self.itemAt(self.count()-1).layout().deleteLater()

    def setVisible(self, visible: bool) -> None:    # pylint: disable=C0103
        """_summary_

        Args:
            visible (bool): _description_
        """
        if self.visible == visible:
            return
        for child in self.children():
            child.setVisible(visible)


class GCFeedback(QFrame):
    """GUI class for the CombinedFeedback wrapper
    """

    def __init__(self, toolbar: GTextToolbar, **kwargs) -> None:
        super().__init__(**kwargs)
        self.__obj = None
        self.setStyleSheet(".GCFeedback{border:1px solid rgb(41, 41, 41);"
                           "background-color: #e4ebb7}")
        self._correct = GTextEditor(toolbar, "correct")
        self._incomplete = GTextEditor(toolbar, "incomplete")
        self._incorrect = GTextEditor(toolbar, "incorrect")
        self._show = QCheckBox("Show the number of correct responses once "
                               "the question has finished")
        _content = QGridLayout(self)
        _content.addWidget(QLabel("Feedback for correct answer"), 0, 0)
        _content.addWidget(self._correct, 1, 0)
        _content.addWidget(QLabel("Feedback for incomplete answer"), 0, 1)
        _content.addWidget(self._incomplete, 1, 1)
        _content.addWidget(QLabel("Feedback for incorrect answer"), 0, 2)
        _content.addWidget(self._incorrect, 1, 2)
        _content.addWidget(self._show, 2, 0, 1, 3)
        _content.setColumnStretch(3, 1)

    def from_obj(self, obj) -> None:
        """_summary_

        Args:
            obj (CombinedFeedback): _description_
        """
        self.__obj = obj
        self._correct.from_obj(self.__obj)
        self._incomplete.from_obj(self.__obj)
        self._incorrect.from_obj(self.__obj)

    def get_attr(self):
        return "combined_feedback"


class GHint(QFrame):
    """GUI class for the Hint wrapper.
    """

    def __init__(self, toolbar: GTextToolbar, **kwargs) -> None:
        super().__init__(**kwargs)
        self.__obj = None
        self.setStyleSheet(".GHint {border:1px solid rgb(41, 41, 41); "
                           " background-color: #e4ebb7}")
        self._text = GTextEditor(toolbar, "")
        self._show = QCheckBox("Show the number of correct responses")
        self._state = QCheckBox("State which markers are incorrectly placed")
        self._clear = QCheckBox("Move incorrectly placed markers back to "
                                "default start position")
        _content = QGridLayout(self)
        _content.addWidget(self._text, 0, 0, 3, 1)
        _content.addWidget(self._show, 0, 1)
        _content.addWidget(self._state, 1, 1)
        _content.addWidget(self._clear, 2, 1)

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


# TODO - Change to HintsList
class GMultipleTries(QVBoxLayout):
    """GUI class for the MultipleTries wrapper
    """

    def __init__(self, parent: QWidget, toolbar: GTextToolbar) -> None:
        super().__init__(parent)
        self.__obj = None
        _header = QHBoxLayout()
        self._penalty = GField(str, "penalty")
        self._penalty.setText("0")
        _header.addWidget(QLabel("Penalty for each try"))
        _header.addWidget(self._penalty)
        add = QPushButton("Add Hint")
        add.clicked.connect(self._add_hint)
        _header.addWidget(add)
        rem = QPushButton("Remove Last")
        rem.clicked.connect(self.pop)
        _header.addWidget(rem)
        _header.setStretch(1, 1)
        self.addLayout(_header)
        self._toolbar = toolbar

    def _add_hint(self):
        ui = GHint(self._toolbar)
        hint = Hint(Format.AUTO, "", True, True)
        ui.from_obj(hint)
        self.__obj.hints.append()
        super().addWidget(ui)

    def from_obj(self, obj) -> None:
        """_summary_

        Args:
            obj (MultipleTries): _description_
        """
        self.__obj = obj.multiple_tries
        self._penalty.from_obj(self.__obj)
        if len(self.__obj.hints) > self.count()-1:
            for _ in range(len(self.__obj.hints)-self.count()):
                self.addWidget(GHint(self._toolbar))
        elif len(self.__obj.hints)+1 < self.count():
            for i in reversed(range(self.count()-len(self.__obj.hints))):
                self.itemAt(i).layout().deleteLater()
        for num in range(len(self.__obj.hints)):
            self.itemAt(num+2).from_obj(self.__obj.hints[num])

    def get_attr(self):
        return "multiple_tries"

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
