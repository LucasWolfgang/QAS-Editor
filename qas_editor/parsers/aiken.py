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
import re
import logging
import glob
from typing import TYPE_CHECKING, Type
from qas_editor.question import QMultichoice, QQuestion
from qas_editor.processors import PROCESSORS
from qas_editor.answer import Choice, ChoicesItem
if TYPE_CHECKING:
    from ..category import Category

LOG = logging.getLogger(__name__)
_PATTERN = re.compile(r"[A-Z]+\) (.+)")


def _from_question(buffer, line: str, name: str):
    question = QQuestion(name)
    simple_choice = ChoicesItem()
    header = line
    match = None
    for _line in buffer:
        match = _PATTERN.match(_line)
        if match:
            simple_choice.options.append(Choice(match[1]))
            break
        header += _line
    target = 0
    for _line in buffer:
        match = _PATTERN.match(_line)
        if not match:
            target = ord(_line[8].upper())-65
            break
        simple_choice.options.append(Choice(match[1]))
    question.body.text.append(header.strip())
    question.body.text.append(simple_choice)
    simple_choice.processor = PROCESSORS["multichoice"].format(index=target)
    return question


# -----------------------------------------------------------------------------


def read_aiken(cls: Type[Category], file_path: str, category: str = "$course$") -> Category:
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


def write_aiken(category: Type[Category], file_path: str) -> None:
    """_summary_

    Args:
        file_path (str): _description_
    """
    def _to_aiken(cat: Type[Category], writer) -> str:
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
        return None
    with open(file_path, "w", encoding="utf-8") as ofile:
        _to_aiken(category, ofile.write)
