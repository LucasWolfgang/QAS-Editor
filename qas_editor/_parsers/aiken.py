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

from ..questions import QMultichoice
from ..utils import FText, LineBuffer
from ..enums import TextFormat
from ..answer import Answer
if TYPE_CHECKING:
    from ..category import Category

LOG = logging.getLogger(__name__)


def _from_QMultichoice(buffer: LineBuffer, name: str):
    header = ""
    answers = []
    match = None
    while not buffer.eof and match is None:
        header += buffer.cur
        match = re.match(r"[A-Z]+\) (.+)", buffer.read())
    while not buffer.eof and match is not None:
        answers.append(Answer(0.0, match[1], None, TextFormat.PLAIN))
        match = re.match(r"[A-Z]+\) (.+)", buffer.read())
    try:
        answers[ord(buffer.cur[8].upper())-65].fraction = 100.0
    except IndexError:
        LOG.exception(f"Failed to set correct answer in question {name}.")
    return QMultichoice(name=name, options=answers,
                question=FText("questiontext", header, TextFormat.PLAIN, None))


# -----------------------------------------------------------------------------


def read_aiken(cls, file_path: str, category: str = "$course$") -> "Category":
    """_summary_

    Args:
        file_path (str): _description_
        category (str, optional): _description_. Defaults to "$".

    Returns:
        Quiz: _description_
    """
    quiz = cls(category)
    name = file_path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    cnt = 0
    for _path in glob.glob(file_path):
        with open(_path, encoding="utf-8") as ifile:
            buffer = LineBuffer(ifile)
            buffer.read()
            while not buffer.eof:
                quiz.add_question(_from_QMultichoice(buffer, f"aiken_{cnt}"))
                buffer.read()
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
                writer(f"{question.question.text}\n")
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
