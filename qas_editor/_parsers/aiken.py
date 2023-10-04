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
import re
import logging
import glob
from typing import TYPE_CHECKING
from ..question import QMultichoice
from ..utils import FText
from ..enums import TextFormat
from ..answer import Answer
if TYPE_CHECKING:
    from ..category import Category

LOG = logging.getLogger(__name__)
_PATTERN = re.compile(r"[A-Z]+\) (.+)")


def _from_question(buffer, line: str, name: str):
    header = line
    answers = []
    match = None
    for _line in buffer:
        match = _PATTERN.match(_line)
        if match:
            answers.append(Answer(0.0, match[1], None, TextFormat.PLAIN))
            break
        header += _line
    for _line in buffer:
        match = _PATTERN.match(_line)
        if not match:
            answers[ord(_line[8].upper())-65].fraction = 100.0
            break
        answers.append(Answer(0.0, match[1], None, TextFormat.PLAIN))
    question = FText(header.strip(), TextFormat.PLAIN)
    return QMultichoice(name=name, options=answers, question=question)


# -----------------------------------------------------------------------------


def read_aiken(cls: "Category", file_path: str, category: str = "$course$") -> "Category":
    """_summary_

    Args:
        file_path (str): _description_
        category (str, optional): _description_. Defaults to "$".

    Returns:
        Quiz: _description_
    """
    quiz = cls(category)
    cnt = 0
    for _path in glob.glob(file_path):
        with open(_path, encoding="utf-8") as ifile:
            for line in ifile:
                if line == "\n":
                    continue
                quiz.add_question(_from_question(ifile, line, f"aiken_{cnt}"))
                cnt += 1
    return quiz


def write_aiken(category: "Category", file_path: str) -> None:
    """_summary_

    Args:
        file_path (str): _description_
    """
    def _to_aiken(cat: "Category", writer) -> str:
        for question in cat.questions:
            if isinstance(question, QMultichoice):
                writer(f"{question.question.get()}\n")
                correct = "ANSWER: None\n\n"
                for num, ans in enumerate(question.options):
                    writer(f"{chr(num+65)}) {ans.text}\n")
                    if ans.fraction == 100.0:
                        correct = f"ANSWER: {chr(num+65)}\n\n"
                writer(correct)
        for name in cat:
            _to_aiken(cat[name], writer)
    with open(file_path, "w", encoding="utf-8") as ofile:
        _to_aiken(category, ofile.write)
