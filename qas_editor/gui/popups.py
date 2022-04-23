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

from PyQt5.QtWidgets import QDialog, QPushButton, QLineEdit, QVBoxLayout,\
                            QComboBox
from .utils import action_handler
from ..questions import QNAME
from ..quiz import Quiz


class NamePopup(QDialog):

    def __init__(self, new_cat, suggestion="") -> None:
        super().__init__()
        self.setWindowTitle("Create" if new_cat else "Rename")
        category_create = QPushButton("Ok")
        action = self._create_category if new_cat else self._update_name
        category_create.clicked.connect(action)
        self._category_name = QLineEdit()
        self._category_name.setFocus()
        self._category_name.setText(suggestion)
        vbox = QVBoxLayout()
        vbox.addWidget(self._category_name)
        vbox.addWidget(category_create)
        self.setLayout(vbox)
        self.data = None

    @action_handler
    def _create_category(self, status) -> None:
        name = self._category_name.text()
        if not name:
            self.reject()
        self.data = Quiz(name)
        self.accept()

    @action_handler
    def _update_name(self, status) -> None:
        name = self._category_name.text()
        if not name:
            self.reject()
        self.data = name
        self.accept()


class QuestionPopup(QDialog):

    def __init__(self, quiz: Quiz) -> None:
        super().__init__()
        self.setWindowTitle("Create Question")
        self.__quiz = quiz
        question_create = QPushButton("Create")
        question_create.clicked.connect(self._create_question)
        self.__type = QComboBox()
        self.__type.addItems(QNAME)
        vbox = QVBoxLayout()
        vbox.addWidget(self.__type)
        vbox.addWidget(question_create)
        self.setLayout(vbox)
        self.question = None

    @action_handler
    def _create_question(self, status) -> None:
        self.question = QNAME[self.__type.currentText()](name="New Question")
        if self.__quiz.add_question(self.question):
            self.accept()
        else:
            self.reject()
