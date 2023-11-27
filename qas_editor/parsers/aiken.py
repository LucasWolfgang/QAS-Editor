# Question and Answer Sheet Editor <https://github.com/LucasWolfgang/QAS-Editor>
# Copyright (C) 2022  Lucas Wolfgang
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
## Description

"""
from __future__ import annotations

import glob
import logging
import re
from typing import TYPE_CHECKING, Type

from .. import processors as pcsr
from ..answer import ChoicesItem, Option
from ..enums import Language
from ..question import QQuestion
from .text import FText, PlainParser

if TYPE_CHECKING:
    from ..category import Category

LOG = logging.getLogger(__name__)
_PATTERN = re.compile(r"[A-Z]+\) (.+)")


def _from_question(buffer, line: str, name: str, language: Language):
    question = QQuestion({language: name}, None, None)
    simple_choice = ChoicesItem()
    header = line
    match = None
    for _line in buffer:
        match = _PATTERN.match(_line)
        if match:
            parser = PlainParser()
            parser.parse(match[1])
            simple_choice.options.append(Option(FText(parser)))
            break
        header += _line
    target = 0
    for _line in buffer:
        match = _PATTERN.match(_line)
        if not match:
            target = ord(_line[8].upper())-65
            break
        parser = PlainParser()
        parser.parse(match[1])
        simple_choice.options.append(Option(FText(parser)))
    question.body[language].text.append(header.strip())
    question.body[language].text.append(simple_choice)
    args = {"values": {target: {"value": 100}}}
    simple_choice.processor = pcsr.Proc.from_default("mapper", args)
    return question


# -----------------------------------------------------------------------------
processor = print

def read_aiken(cls: Type[Category], file_path: str, category: str, 
               language: Language) -> Category:
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
                question = _from_question(ifile, line, f"aiken_{cnt}", language)
                quiz.add_question(question)
                cnt += 1
    return quiz


def write_aiken(category: Category, language: Language, file_path: str) -> None:
    """_summary_

    Args:
        file_path (str): _description_
    """
    def _to_aiken(cat: Category, writer):
        for question in cat.questions:
            if (len(question.body[language]) == 2 and
                        isinstance(question.body[language][1], ChoicesItem)):
                writer(f"{question.body[language].text[0]}\n")
                correct = "ANSWER: None\n\n"
                proc = question.body[language].text[1].processor
                opts = question.body[language].text[1].options
                for num, ans in enumerate(opts):
                    writer(f"{chr(num+65)}) {ans}\n")
                    if proc.func(num)["value"] == 100.0:
                        correct = f"ANSWER: {chr(num+65)}\n\n"
                writer(correct)
        for name in cat:
            _to_aiken(cat[name], writer)
    with open(file_path, "w", encoding="utf-8") as ofile:
        _to_aiken(category, ofile.write)
