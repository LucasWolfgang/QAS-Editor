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
Applications that provide Card based learning, like the amazing
Anki and Quizlet, usually give an easy way to export the data in a
plain text format with some options. Using the correct ones you will
end up with a comma separated file, with 2 columns and N rows, one
for each card in your deck. This parser handles this type of files.
"""
from __future__ import annotations

import csv
import os
from typing import TYPE_CHECKING, Callable

from qas_editor.enums import Platform, TextFormat

from ..answer import EntryItem
from ..processors import Proc
from ..question import QQuestion
from .text import FText

if TYPE_CHECKING:
    from ..category import Category
    from ..enums import Language


def read_cards(cls, file_path: str, lang: Language) -> Category:
    """Read a comma separated deck.
    """
    cls: Category = cls()
    with open(file_path, encoding="utf-8") as ifile:
        for num, items in enumerate(csv.reader(ifile, delimiter="\t")):
            if len(items) == 2:
                header, answer = items
                ans = EntryItem()
                args = {"values":{answer:{"value":100}}}
                ans.processor = Proc.from_template("string_process", args)
                qst = QQuestion({lang: num}, None, None)
                qst.body[lang].text.append(header)
                qst.body[lang].text.append(ans)
                cls.add_question(qst)
            else:
                raise NotImplementedError("Flow not implemented")
    return cls


def read_anki(cls, file_path: str, lang: Language):
    read_cards(cls, file_path, lang)


def read_quizlet(cls, file_path: str, lang: Language):
    read_cards(cls, file_path, lang)


# -----------------------------------------------------------------------------


def write_cards(self, file_path: str, lang: Language, plat: Platform):
    """Write a comma separated deck.
    """
    path = os.path.dirname(file_path)
    def _kwrecursive(cat: "Category", write: Callable):
        for qst in cat.questions:
            qst.check()
            text = qst.body[lang].text
            if len(text) == 2 and isinstance(text[1], EntryItem):
                head, resp = text
                for key, val in resp.processor.args["values"].items():
                    if val["value"] == 100:
                        break
                else:
                    continue
                head = FText.to_string(head, path, plat, TextFormat.PLAIN)
                write((head, key))
        for name in cat:                            # Then add children data
            _kwrecursive(cat[name], write)
    with open(file_path, "w", encoding="utf-8") as ofile:
        _kwrecursive(self, csv.writer(ofile, delimiter="\t").writerow)


def write_anki(self, file_path: str, lang: Language):
    write_cards(self, file_path, lang, Platform.ANKI)


def write_quizlet(self, file_path: str, lang: Language):
    write_cards(self, file_path, lang, Platform.QUIZLET)