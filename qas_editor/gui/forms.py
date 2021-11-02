from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QFrame, QComboBox, \
                            QCheckBox, QLineEdit, QPushButton, QLabel, QGridLayout
from ..answer import Answer
from ..enums import Format, Grading, ShowUnits
from ..wrappers import CombinedFeedback, Hint, MultipleTries, UnitHandling
from .utils import GTextEditor

class GAnswer(QFrame):

    def __init__(self, controls, **kwargs) -> None:
        super(GAnswer, self).__init__(**kwargs)
        self.setStyleSheet(".GAnswer{border:1px solid rgb(41, 41, 41); background-color: #e4ebb7}")
        _content = QGridLayout(self)
        _content.addWidget(QLabel("Text"), 0, 0)
        self._text = GTextEditor(controls)
        _content.addWidget(self._text, 0, 1)
        _content.addWidget(QLabel("Grade"), 1, 0)
        self._grade = QLineEdit()
        _content.addWidget(self._grade, 1, 1)
        _content.addWidget(QLabel("Feedback"), 2, 0)
        self._feedback = GTextEditor(controls)
        _content.addWidget(self._feedback, 2, 1)
        _content.setRowStretch(0, 4)
        self.setFixedHeight(140)
        self.setFixedWidth(220)

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

# ----------------------------------------------------------------------------------------

class GChoices(QFrame):

     def __init__(self, controls, **kwargs) -> None:
        super(GAnswer, self).__init__(**kwargs)
        self.setStyleSheet(".GAnswer{border:1px solid rgb(41, 41, 41); background-color: #e4ebb7}")  

# ----------------------------------------------------------------------------------------

class GCFeedback(QFrame):

    def __init__(self, toolbar, **kwargs) -> None:
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

    def __init__(self, toolbar, **kwargs) -> None:
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

    def __init__(self, toolbar, **kwargs) -> None:
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
        

    def from_obj(self, obj: UnitHandling) -> None:
        pass

    def to_obj(self) -> None:
        pass

    def verify(self) -> None:
        """
        Iterate over the object list to verify if it is valid.
        """
        pass

# ----------------------------------------------------------------------------------------


