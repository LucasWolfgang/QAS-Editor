from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .utils import GTextToolbar

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QFrame, QComboBox, \
                            QCheckBox, QLineEdit, QPushButton, QLabel, QGridLayout
from ..answer import Answer, DragItem, DragText
from ..enums import Format, Grading, ShowUnits
from ..wrappers import CombinedFeedback, Hint, MultipleTries, UnitHandling
from .utils import GTextEditor
from ..questions import QCrossWord

class GAnswer(QGridLayout):

    def __init__(self, toolbar: GTextToolbar, **kwargs) -> None:
        super(QGridLayout, self).__init__(**kwargs)
        self.addWidget(QLabel("Text"), 0, 0)
        self._text = GTextEditor(toolbar)
        self._text.setFixedHeight(40)
        self.addWidget(self._text, 0, 1)
        self.addWidget(QLabel("Grade"), 0, 2)
        self._grade = QLineEdit()
        self.addWidget(self._grade, 0, 3)
        self.addWidget(QLabel("Feedback"), 1, 2)
        self._feedback = GTextEditor(toolbar)
        self._text.setFixedHeight(25)
        self.addWidget(self._feedback, 1, 2)
        self.setRowStretch(0, 4)

    def from_obj(self, obj: Answer) -> None:
        self._grade.setText(str(obj.fraction))
        self._text.text_format = obj.formatting
        if obj.formatting == Format.MD:
            self._text.setMarkdown(obj.text)
        elif obj.formatting == Format.HTML:
            self._text.setHtml(obj.text)
        elif obj.formatting == Format.PLAIN:
            self._text.setPlainText(obj.text)

    def to_obj(self) -> None:
        """[summary]

        Args:
            items (dict): [description]
        """
        fraction = float(self._grade.text())
        tp = self._text.toolbar.text_type.currentIndex()
        if tp == 0:
            text = self._text.toMarkdown()
            formatting = Format.MD
        elif tp == 1:
            text = self._text.toHtml()
            formatting = Format.HTML
        else:
            text = self._text.toPlainText()
            formatting = Format.PLAIN
        feedback = self._feedback.getFText()
        return Answer(fraction, text, feedback, formatting)

    def setVisible(self, visible: bool) -> None:
        for child in self.children():
            child.setVisible(visible)

# ----------------------------------------------------------------------------------------

class GDrag(QGridLayout):
    """This class works from both DragText and DragItem.
    I hope someday people from moodle unify these 2.

    Args:
        QGridLayout ([type]): [description]
    """

    TYPES = ["Image", "Text"]

    def __init__(self, only_text: bool, **kwargs) -> None:
        super(QGridLayout, self).__init__(**kwargs)
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

    def from_obj(self, obj):
        self.text.setText(obj.text)
        self.group.setText(str(obj.group))
        self.unlimited = self.unlimited.isChecked()
        self.obj = obj

    def setVisible(self, visible: bool) -> None:
        for child in self.children():
            child.setVisible(visible)

    def to_obj(self) -> DragItem:
        if self.only_text:
            return DragText(self.text.text(), self.group.text(), self.unlimited.isChecked())
        else:
            return DragItem(0, self.text.text(), self.unlimited.isChecked(),
                                self.group.text(), self.img)

# ----------------------------------------------------------------------------------------

class GDropZone(QGridLayout):

    TYPES = ["Image", "Text"]

    def __init__(self, **kwargs) -> None:
        super(GAnswer, self).__init__(**kwargs)
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

    def from_obj(self, obj: DragItem):
        pass

    def setVisible(self, visible: bool) -> None:
        for child in self.children():
            child.setVisible(visible)

    def to_obj(self) -> DragItem:
        pass

# ----------------------------------------------------------------------------------------

class GOptions(QVBoxLayout):

    def __init__(self, toolbar, **kwargs) -> None:
        super(QVBoxLayout, self).__init__(**kwargs)
        self.visible = True
        self.toolbar = toolbar

    def add(self, obj):
        if isinstance(obj, Answer): item = GAnswer(self.toolbar)
        elif isinstance(obj, DragText): item = GDrag(True)
        elif isinstance(obj, DragItem): item = GDrag(False)
        item.from_obj(obj)
        self.addLayout(item)

    def from_obj(self, objs:list) -> None:
        children = self.children()
        if len(children) > len(objs):
            self.replaceWidget(children[0], children[len(objs)])
        for obj, child in zip(objs, children):
            if isinstance(obj, Answer):     child.from_obj(obj)
            elif isinstance(obj, DragText): child.from_obj(obj)
            elif isinstance(obj, DragItem): child.from_obj(obj)
        for obj in objs[len(children):]: self.add(obj)

    def setVisible(self, visible: bool) -> None:
        if self.visible == visible: return
        for child in self.children():
            child.setVisible(visible)

    def to_obj(self):
        return [child.to_obj() for child in self.children]

# ----------------------------------------------------------------------------------------

class GCFeedback(QFrame):

    def __init__(self, toolbar: GTextToolbar, **kwargs) -> None:
        super().__init__(**kwargs)
        self.setStyleSheet(".GCFeedback{border:1px solid rgb(41, 41, 41); background-color: #e4ebb7}")
        self._correct = GTextEditor(toolbar)
        self._incomplete = GTextEditor(toolbar)
        self._incorrect  = GTextEditor(toolbar)
        self._show = QCheckBox("Show the number of correct responses once the question has finished")
        _content = QGridLayout(self)
        _content.addWidget(QLabel("Feedback for correct answer"), 0, 0)
        _content.addWidget(self._correct, 1, 0)
        _content.addWidget(QLabel("Feedback for incomplete answer"), 0, 1)
        _content.addWidget(self._incomplete, 1, 1)
        _content.addWidget(QLabel("Feedback for incorrect answer"), 0, 2)
        _content.addWidget(self._incorrect, 1, 2)
        _content.addWidget(self._show, 2, 0, 1, 3)
        
    def from_obj(self, obj: CombinedFeedback) -> None:
        self._correct.setFText(obj.correct)
        self._incomplete.setFText(obj.incomplete)
        self._incorrect.setFText(obj.incorrect)

    def to_obj(self) -> None:
        correct = self._correct.getFText()
        incomplete = self._incomplete.getFText()
        incorrect = self._incorrect.getFText()
        return CombinedFeedback(correct, incomplete, incorrect, self._show.isChecked())

# ----------------------------------------------------------------------------------------

class GHint(QFrame):

    def __init__(self, toolbar: GTextToolbar, **kwargs) -> None:
        super().__init__(**kwargs)
        self.setStyleSheet(".GHint{border:1px solid rgb(41, 41, 41); background-color: #e4ebb7}")
        self._text = GTextEditor(toolbar)
        self._show = QCheckBox("Show the number of correct responses")
        self._state = QCheckBox("State which markers are incorrectly placed")
        self._clear = QCheckBox("Move incorrectly placed markers back to default start position")
        _content = QVBoxLayout(self)
        _content.addWidget(self._text)
        _content.addWidget(self._show)
        _content.addWidget(self._state)
        _content.addWidget(self._clear)

    def from_obj(self, obj: Hint) -> None:
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
        tp = self._text.toolbar.text_type.currentIndex()
        if tp == 0:
            text = self._text.toMarkdown()
            formatting = Format.MD
        elif tp == 1:
            text = self._text.toHtml()
            formatting = Format.HTML
        else:
            text = self._text.toPlainText()
            formatting = Format.PLAIN
        return Hint(formatting, text, self._show.isChecked(), 
                    self._clear.isChecked(), self._state.isChecked())

# ----------------------------------------------------------------------------------------

class GMultipleTries(QWidget): 

    def __init__(self, toolbar: GTextToolbar, **kwargs) -> None:
        super().__init__(**kwargs)
        self._penalty = QLineEdit()
        self._penalty.setText("0")
        add = QPushButton("Add Hint")
        add.clicked.connect(lambda x: self._content.addWidget(GHint(toolbar)))
        rem = QPushButton("Remove Last")
        _header = QHBoxLayout()
        _header.addWidget(QLabel("Penalty for each try"))
        _header.addWidget(self._penalty)
        _header.addWidget(add)
        _header.addWidget(rem)
        self._content = QVBoxLayout(self)
        self._content.addLayout(_header)
        self._toolbar = toolbar

    def from_obj(self, obj: MultipleTries) -> None:
        self._penalty.setText(str(obj.penalty))
        if len(obj.hints) > self._content.count()-1:
            for _ in range(len(obj.hints)-self._content.count()):
                self._content.addWidget(GHint(self._toolbar))
        elif len(obj.hints)+1 < self._content.count():
            for num in range(self._content.count()-len(obj.hints)):
                self._content.removeWidget(self._content.itemAt(self._content.count()-1))
        for num in range(len(obj.hints)):
            self._content.itemAt(num+2).from_obj(obj.hints[num])

    def to_obj(self) -> None:
        penalty = float(self._penalty.text())
        hints = []
        for num in range(self._content.count()-1):
            hints.append(self._content.itemAt(num+1).to_obj())
        return MultipleTries(penalty, hints)

# ----------------------------------------------------------------------------------------

class GUnitHadling(QWidget):

    GRADE = {"Ignore": "IGNORE", "Fraction of reponse": "RESPONSE", 
                "Fraction of question": "QUESTION"}
    SHOW_UNITS = {"Text input": "TEXT", "Multiple choice": "MC", 
                "Drop-down": "DROP_DOWN", "Not visible": "NONE"}

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.setStyleSheet(".GWidget{border:1px solid rgb(41, 41, 41); background-color: #e4ebb7}")
        self._grading = QComboBox()   
        self._grading.addItems(["Ignore", "Fraction of reponse", "Fraction of question"])
        self._penalty = QLineEdit()
        self._penalty.setText("0")
        self._show = QComboBox()
        self._show.addItems(["Text input", "Multiple choice", "Drop-down", "Not visible"])
        self._left = QCheckBox("Put units on the left")
        _content = QHBoxLayout(self)
        _content.addWidget(QLabel("Grading"))
        _content.addWidget(self._grading)
        _content.addWidget(QLabel("Penalty"))
        _content.addWidget(self._penalty)
        _content.addWidget(QLabel("Show units"))
        _content.addWidget(self._show)
        _content.addWidget(self._left)

    def from_obj(self, obj: UnitHandling) -> None:
        for k, v in self.GRADE:
            if obj.grading_type.value == v:
                self._grading.setCurrentText(k)
        for k, v in self.SHOW_UNITS:
            if obj.show.value == v:
                self._show.setCurrentIndex(k)
        self._penalty.setText(str(obj.penalty))

    def to_obj(self) -> UnitHandling:
        grade = Grading[self.GRADE[self._grading.currentText()]]
        penalty = float(self._penalty.text())
        show = ShowUnits[self.SHOW_UNITS[self._show.currentText()]]
        return UnitHandling(grade, penalty, show, self._left.isChecked())

# ----------------------------------------------------------------------------------------

class GCrossWord(QWidget):

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        
    def setAnswerString(self, x, y, direction, value):
        """
        Set answered string.
        """
        if not self.active():
            raise ValueError("puzzle is inactive")
        self._puzzle.setAnswerString(x, y, direction, value)

    def from_obj(self, obj: QCrossWord) -> None:
        pass

    def to_obj(self) -> None:
        pass

    def verify(self) -> None:
        """
        Iterate over the object list to verify if it is valid.
        """
        pass

# ----------------------------------------------------------------------------------------


