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
import csv
from ..question import QMatching, QMultichoice, QShortAnswer
from ..answer import Answer
from typing import TYPE_CHECKING, Callable
if TYPE_CHECKING:
    from ..category import Category


__doc__ = """Applications that provide Card based learning, like the amazing
          Anki and Quizlet, usually give an easy way to export the data in a
          plain text format with some options. Using the correct ones you will
          end up with a comma separated file, with 2 columns and N rows, one
          for each card in your deck. This parser handles this type of files.
          """


def read_cards(cls, file_path: str) -> Category:
    """Read a comma separated deck.
    """
    cls: Category = cls()
    with open(file_path) as ifile:
        for num, items in enumerate(csv.reader(ifile, delimiter="\t")):
            if len(items) == 2:
                header, answer = items
                ans = Answer(100, answer)
                qst = QShortAnswer(True, name=num, options=[ans], question=header)
                cls.add_question(qst)
            else:
                NotImplementedError("Flow not implemented")
    return cls


# -----------------------------------------------------------------------------


def _write_qmatching(question: QMatching, write):
    for ans in question.options:
        write((question.question.get() + ans.text, ans.answer))


def _write_qsa_qmc(question: QShortAnswer|QMultichoice, write):
    for ans in question.options:
        if ans.fraction == 100:
            correct = ans.text
            break
    write((question.question.get(), correct))


def write_cards(self, file_path: str):
    """Write a comma separated deck.
    """
    def _kwrecursive(cat: "Category", write: Callable):
        for qst in cat.questions:
            qst.check()
            if isinstance(qst, (QMultichoice, QShortAnswer)):
                _write_qsa_qmc(qst, write)
            elif isinstance(qst, QMatching):
                _write_qmatching(qst, write)
        for name in cat:                            # Then add children data
            _kwrecursive(cat[name], write)
    with open(file_path, "w") as ofile:
        _kwrecursive(self, csv.writer(ofile, delimiter="\t").writerow)
