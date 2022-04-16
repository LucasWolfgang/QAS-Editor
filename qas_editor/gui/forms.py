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
from ..answer import Answer, CalculatedAnswer, DragItem, DragText, ClozeItem
from ..enums import ClozeFormat, Format, Grading, ShowUnits
from ..wrappers import CombinedFeedback, FText, Hint, MultipleTries, UnitHandling
from ..questions import QCrossWord
from .utils import GTextEditor, action_handler
if TYPE_CHECKING:
    from .utils import GTextToolbar
LOG = logging.getLogger(__name__)

class GAnswer(QHBoxLayout):
    """GUI for QAnswer class.
    """

    def __init__(self, toolbar: GTextToolbar, **kwargs) -> None:
        super().__init__(**kwargs)
        self.obj = None
        self._text = GTextEditor(toolbar, "")
        self._text.setToolTip("Use this field to define the answer text")
        self.addWidget(self._text, 0)
        self._feedback = GTextEditor(toolbar, "feedback")
        self._feedback.setToolTip("Use this field to define the answer feedback")
        self.addWidget(self._feedback, 1)
        self._grade = QLineEdit()
        self._grade.setMaximumWidth(50)
        self._grade.setToolTip("Use this field to define the answer grade")
        self.addWidget(self._grade, 2)
        self.setStretch(0, 0)
        self.setStretch(0, 1)

    def __del__(self):
        try:
            for i in range(self.count()):
                self.itemAt(i).widget().deleteLater()
        except RuntimeError: pass

    def from_obj(self, obj: Answer) -> None:
        """_summary_

        Args:
            obj (Answer): _description_
        """
        self._grade.setText(str(obj.fraction))
        self._text.text_format = obj.formatting
        if obj.formatting == Format.MD:
            self._text.setMarkdown(obj.text)
        elif obj.formatting == Format.HTML:
            self._text.setHtml(obj.text)
        elif obj.formatting == Format.PLAIN:
            self._text.setPlainText(obj.text)
        self.obj = obj

    def to_obj(self) -> Answer:
        """_summary_

        Returns:
            Answer: _description_
        """
        fraction = float(self._grade.text())
        formatting = self._text.text_format
        if formatting == Format.MD:
            text = self._text.toMarkdown()
        elif formatting == Format.HTML:
            text = self._text.toHtml()
        else:
            text = self._text.toPlainText()
        feedback = self._feedback.get_ftext()
        if self.obj is not None:
            self.obj.fraction = fraction
            self.obj.text = text
            self.obj.feedback = feedback
            self.obj.formatting = formatting
        else:
            self.obj = Answer(fraction, text, feedback, formatting)
        return self.obj

    def setVisible(self, visible: bool) -> None: # pylint: disable=C0103
        """_summary_

        Args:
            visible (bool): _description_
        """
        for child in self.children():
            child.setVisible(visible)

# ------------------------------------------------------------------------------

class GCalculated(QFrame):

    def __init__(self, toolbar: GTextToolbar, **kwargs) -> None:
        super().__init__(**kwargs)
        self.__obj = None
        grid = QGridLayout(self)
        self.setLayout(grid)
        self._text = GTextEditor(toolbar, "", parent=self)
        self._text.setToolTip("Use this field to define the answer formula")
        grid.addWidget(self._text, 0, 0)
        self._grade = QLineEdit(self)
        self._grade.setMaximumWidth(50)
        self._grade.setToolTip("Use this field to define the answer grade")
        grid.addWidget(self._grade, 0, 1)
        self._feedback = GTextEditor(toolbar, "feedback", parent=self)
        self._feedback.setToolTip("Use this field to define the answer feedback")
        grid.addWidget(self._feedback, 0, 2, 1, 3)
        self._tol_type = QComboBox(self)
        grid.addWidget(self._tol_type, 1, 0)
        self._tolerance = QLineEdit(self)
        grid.addWidget(self._tolerance, 1, 1)
        self._ans_type = QCheckBox(self)
        grid.addWidget(self._ans_type, 2, 0)
        self._answer_disp = QLineEdit(self)
        grid.addWidget(self._answer_disp, 2, 1)

    def from_obj(self, obj: Answer) -> None:
        self.__obj = obj

    def to_obj(self) -> CalculatedAnswer:
        pass

# ------------------------------------------------------------------------------

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
        except RuntimeError: pass

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

    def from_obj(self, obj: ClozeItem) -> None:
        """_summary_

        Args:
            obj (ClozeItem): _description_
        """
        self._pos.setText(str(obj.start))
        self._form.setCurrentText(str(obj.cformat.value))
        self._grade.setText(str(obj.grade))
        self.opts = obj.opts
        self._opts.addItems([a.text for a in self.opts])

    def to_obj(self) -> None:
        """_summary_

        Returns:
            _type_: _description_
        """
        pos = int(self._pos.text())
        grade = float(self._grade.text())
        cform = ClozeFormat(self._form.currentText())
        if self.obj is not None:
            self.obj.start = pos
            self.obj.grade = grade
            self.obj.cformat = cform
            # Self opts and obj opts are already the same list
        else:
            self.obj = ClozeItem(pos, grade, cform, self.opts)
        return self.obj

    def setVisible(self, visible: bool) -> None:    # pylint: disable=C0103
        """_summary_

        Args:
            visible (bool): _description_
        """
        for child in self.children():
            child.setVisible(visible)

# ------------------------------------------------------------------------------

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
        except RuntimeError: pass

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

    def to_obj(self) -> DragItem:
        """_summary_

        Returns:
            DragItem: _description_
        """
        if self.obj is not None:
            self.obj.text = self.text.text()
            self.obj.group = self.group.text()
            self.obj.unlimited = self.unlimited.isChecked()
            if not self.only_text:
                self.obj.image = self.img
        else:
            if self.only_text:
                self.obj = DragText(self.text.text(), self.group.text(),
                                    self.unlimited.isChecked())
            else:
                self.obj = DragItem(0, self.text.text(), self.unlimited.isChecked(),
                                    self.group.text(), self.img)
        return self.obj

# ----------------------------------------------------------------------------------------

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
        except RuntimeError: pass

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

    def to_obj(self) -> DragItem:
        """_summary_

        Returns:
            DragItem: _description_
        """
        LOG.debug(f"Function <to_obj> not implemented in {self}")

# ----------------------------------------------------------------------------------------

class GOptions(QVBoxLayout):
    """GUI for GOptions class.
    """

    def __init__(self, toolbar, **kwargs) -> None:
        super().__init__(**kwargs)
        self.visible = True
        self.toolbar = toolbar
        self.__ctype = None
        #self.setSpacing(0)
        self.setContentsMargins(0, 0, 0, 0)

    def _soft_clear(self, new_size=0, new_type=None):
        if len(self.children()) == 0:
            return
        to_rem = 0
        if new_type and new_type != self.__ctype:
            to_rem = self.count()
        elif self.count() > new_size:
            to_rem = self.count() - new_size
        for i in reversed(range(to_rem)):
            self.itemAt(i).layout().deleteLater()

    def add(self, obj):
        """_summary_

        Args:
            obj (_type_): _description_

        Raises:
            ValueError: _description_
        """
        if not isinstance(obj, self.__ctype):
            raise ValueError(f"Objects in this Layout can only be of type {self.__ctype}.")
        item = self.add_default()
        item.from_obj(obj)

    def add_default(self):
        """_summary_

        Raises:
            TypeError: _description_

        Returns:
            _type_: _description_
        """
        if   self.__ctype is Answer:
            item = GAnswer(self.toolbar)
        elif self.__ctype is DragText:
            item = GDrag(True)
        elif self.__ctype is DragItem:
            item = GDrag(False)
        elif self.__ctype is ClozeItem:
            item = GCloze()
        elif self.__ctype is CalculatedAnswer:
            item = GCloze()
        else: raise TypeError(f"Type {self.__ctype} is not implemented")
        self.addLayout(item)
        return item

    def addLayout(self, layout, stretch: int = 0) -> None:  # pylint: disable=C0103
        """_summary_

        Args:
            layout (_type_): _description_
            stretch (int, optional): _description_. Defaults to 0.

        Returns:
            _type_: _description_
        """
        if not isinstance(layout, GAnswer) and not isinstance(layout, GDrag):
            LOG.warning(f"Attempted adding non-valid layout {type(layout)} to GOptions.")
        return super().addLayout(layout, stretch=stretch)

    def from_obj(self, objs: list) -> None:
        """_summary_

        Args:
            objs (list): _description_
        """
        self._soft_clear(len(objs), None if not objs else type(objs[0]))
        if not objs:
            return
        self.__ctype = type(objs[0])
        for obj, child in zip(objs, self.children()):
            if hasattr(child, "from_obj"):
                child.from_obj(obj)
        if self.count() < len(objs):
            for obj in objs[self.count():]:
                self.add(obj)

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

    def to_obj(self):
        """_summary_

        Returns:
            _type_: _description_
        """
        return [child.to_obj() for child in self.children()]

# ------------------------------------------------------------------------------

class GCFeedback(QFrame):
    """GUI class for the CombinedFeedback wrapper
    """

    def __init__(self, toolbar: GTextToolbar, **kwargs) -> None:
        super().__init__(**kwargs)
        self.setStyleSheet(".GCFeedback{border:1px solid rgb(41, 41, 41);"+
                           "background-color: #e4ebb7}")
        self._correct = GTextEditor(toolbar, "correctfeedback")
        self._incomplete = GTextEditor(toolbar, "partiallycorrectfeedback")
        self._incorrect = GTextEditor(toolbar, "incorrectfeedback")
        self._show = QCheckBox("Show the number of correct responses once"+
                               " the question has finished")
        _content = QGridLayout(self)
        _content.addWidget(QLabel("Feedback for correct answer"), 0, 0)
        _content.addWidget(self._correct, 1, 0)
        _content.addWidget(QLabel("Feedback for incomplete answer"), 0, 1)
        _content.addWidget(self._incomplete, 1, 1)
        _content.addWidget(QLabel("Feedback for incorrect answer"), 0, 2)
        _content.addWidget(self._incorrect, 1, 2)
        _content.addWidget(self._show, 2, 0, 1, 3)
        _content.setColumnStretch(3, 1)

    def from_obj(self, obj: CombinedFeedback) -> None:
        """_summary_

        Args:
            obj (CombinedFeedback): _description_
        """
        self._correct.set_ftext(obj.correct)
        self._incomplete.set_ftext(obj.incomplete)
        self._incorrect.set_ftext(obj.incorrect)

    def to_obj(self) -> None:
        """_summary_

        Returns:
            _type_: _description_
        """
        correct = self._correct.get_ftext()
        incomplete = self._incomplete.get_ftext()
        incorrect = self._incorrect.get_ftext()
        return CombinedFeedback(correct, incomplete, incorrect, self._show.isChecked())

# ----------------------------------------------------------------------------------------

class GHint(QFrame):
    """GUI class for the Hint wrapper.
    """

    def __init__(self, toolbar: GTextToolbar, **kwargs) -> None:
        super().__init__(**kwargs)
        self.setStyleSheet(".GHint{border:1px solid rgb(41, 41, 41); background-color: #e4ebb7}")
        self._text = GTextEditor(toolbar, "")
        self._show = QCheckBox("Show the number of correct responses")
        self._state = QCheckBox("State which markers are incorrectly placed")
        self._clear = QCheckBox("Move incorrectly placed markers back to default start position")
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
        self._show.setChecked(obj.show_correct)
        self._clear.setChecked(obj.clear_wrong)
        self._state.setChecked(obj.state_incorrect)
        self._text.text_format = obj.formatting
        if obj.formatting == Format.MD:
            self._text.setMarkdown(obj.text)
        elif obj.formatting == Format.HTML:
            self._text.setHtml(obj.text)
        elif obj.formatting == Format.PLAIN:
            self._text.setPlainText(obj.text)

    def to_obj(self):
        """_summary_

        Returns:
            _type_: _description_
        """
        formatting = self._text.text_format
        if formatting == Format.MD:
            text = self._text.toMarkdown()
        elif formatting == Format.HTML:
            text = self._text.toHtml()
        else:
            text = self._text.toPlainText()
        return Hint(formatting, text, self._show.isChecked(),
                    self._clear.isChecked(), self._state.isChecked())

# ----------------------------------------------------------------------------------------

class GMultipleTries(QVBoxLayout):
    """GUI class for the MultipleTries wrapper
    """

    def __init__(self, toolbar: GTextToolbar, **kwargs) -> None:
        super().__init__(**kwargs)
        _header = QHBoxLayout()
        self._penalty = QLineEdit()
        self._penalty.setText("0")
        _header.addWidget(QLabel("Penalty for each try"))
        _header.addWidget(self._penalty)
        add = QPushButton("Add Hint")
        add.clicked.connect(lambda: self.addWidget(GHint(toolbar)))
        _header.addWidget(add)
        rem = QPushButton("Remove Last")
        rem.clicked.connect(self.pop)
        _header.addWidget(rem)
        _header.setStretch(1, 1)
        self.addLayout(_header)
        self._toolbar = toolbar

    def from_obj(self, obj: MultipleTries) -> None:
        """_summary_

        Args:
            obj (MultipleTries): _description_
        """
        self._penalty.setText(str(obj.penalty))
        if len(obj.hints) > self.count()-1:
            for _ in range(len(obj.hints)-self.count()):
                self.addWidget(GHint(self._toolbar))
        elif len(obj.hints)+1 < self.count():
            for i in reversed(range(self.count()-len(obj.hints))):
                self.itemAt(i).layout().deleteLater()
        for num in range(len(obj.hints)):
            self.itemAt(num+2).from_obj(obj.hints[num])

    def pop(self) -> None:
        """_summary_
        """
        if not self.count():
            return
        self.itemAt(self.count()-1).widget().deleteLater()

    def to_obj(self) -> None:
        """_summary_

        Returns:
            _type_: _description_
        """
        penalty = float(self._penalty.text())
        hints = []
        for num in range(self.count()-1):
            hints.append(self.itemAt(num+1).to_obj())
        return MultipleTries(penalty, hints)

# ----------------------------------------------------------------------------------------

class GUnitHadling(QFrame):
    """GUi class for the UnitHandling wrapper.
    """

    GRADE = {"Ignore": "IGNORE", "Fraction of reponse": "RESPONSE",
             "Fraction of question": "QUESTION"}
    SHOW_UNITS = {"Text input": "TEXT", "Multiple choice": "MC",
                  "Drop-down": "DROP_DOWN", "Not visible": "NONE"}

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.setStyleSheet(".GUnitHadling{border:1px solid; background-color: #e4ebb7}")
        self._grading = QComboBox()
        self._grading.addItems(["Ignore", "Fraction of reponse", "Fraction of question"])
        self._penalty = QLineEdit()
        self._penalty.setFixedWidth(70)
        self._penalty.setText("0")
        self._show = QComboBox()
        self._show.addItems(["Text input", "Multiple choice", "Drop-down", "Not visible"])
        self._left = QCheckBox("Put units on the left")
        _content = QGridLayout(self)
        _content.addWidget(QLabel("Grading"), 0, 0)
        _content.addWidget(self._grading, 0, 1)
        _content.addWidget(QLabel("Penalty"), 0, 2)
        _content.addWidget(self._penalty, 0, 3)
        _content.addWidget(QLabel("Show units"), 1, 0)
        _content.addWidget(self._show, 1, 1)
        _content.addWidget(self._left, 1, 2, 1, 2)
        _content.setContentsMargins(5, 2, 5, 1)
        self.setFixedSize(300, 55)

    def from_obj(self, obj: UnitHandling) -> None:
        """_summary_

        Args:
            obj (UnitHandling): _description_
        """
        for key, value in self.GRADE.items():
            if obj.grading_type.value == value:
                self._grading.setCurrentText(key)
        for key, value in self.SHOW_UNITS.items():
            if obj.show.value == value:
                self._show.setCurrentIndex(key)
        self._penalty.setText(str(obj.penalty))

    def to_obj(self) -> UnitHandling:
        """_summary_

        Returns:
            UnitHandling: _description_
        """
        grade = Grading[self.GRADE[self._grading.currentText()]]
        penalty = float(self._penalty.text())
        show = ShowUnits[self.SHOW_UNITS[self._show.currentText()]]
        return UnitHandling(grade, penalty, show, self._left.isChecked())

# ------------------------------------------------------------------------------

class GCrossWord(QWidget):
    """GUI class for the CrossWord question class.
    """

    def from_obj(self, _: QCrossWord) -> None:
        """_summary_

        Args:
            obj (QCrossWord): _description_
        """
        LOG.debug(f"Function <from_obj> not implemented in {self}")

    def to_obj(self) -> None:
        """_summary_
        """
        LOG.debug(f"Function <to_obj> not implemented in {self}")

# ------------------------------------------------------------------------------
