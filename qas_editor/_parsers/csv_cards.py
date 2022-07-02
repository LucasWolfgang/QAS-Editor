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
import csv
from ..question import QMatching, QMultichoice, QShortAnswer
from typing import TYPE_CHECKING, Callable
if TYPE_CHECKING:
    from ..category import Category


__doc__ = """Applications that provide Card based learning, like the amazing
          Anki and Quizlet, usually give an easy way to export the data in a
          plain text format with some options. Using the correct ones you will
          end up with a comma separated file, with 2 columns and N rows, one
          for each card in your deck. This parser handles this type of files.
          """


def read_cards():
    """Read a comma separated deck.
    """
    pass


# -----------------------------------------------------------------------------


def _write_qmatching(question: QShortAnswer, write):
    question.check()
    for ans in question.options:
        write((question.question.text + ans.text, ans.answer))


def _write_qshortanswer(question: QShortAnswer, write):
    correct = [ans.text for ans in question.options]
    write((question.question.text, "\n".join(correct)))


def _write_multichoice(question: QMultichoice, write):
    question.check()
    for ans in question.options:
        if ans.fraction == 100:
            correct = ans.text
    write((question.question.text, correct))


def write_cards(self, file_path: str):
    """Write a comma separated deck.
    """
    def _kwrecursive(cat: "Category", write: Callable):
        for qst in cat.questions, 1:
            if isinstance(qst, QMultichoice):
                _write_multichoice(qst, write)
            elif isinstance(qst, QShortAnswer):
                _write_qshortanswer(qst, write)
            elif isinstance(qst, QMatching):
                _write_qmatching(qst, write)
        for name in cat:                            # Then add children data
            _kwrecursive(cat[name], write)
    with open(file_path, "w") as ofile:
        ofile.write(",Question,Answer1,Answer2,Answer3,Answer4,Time,Correct\n")
        _kwrecursive(self, csv.writer(ofile).writerow)
