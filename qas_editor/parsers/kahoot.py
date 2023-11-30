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
import logging
from typing import TYPE_CHECKING, Callable, Type

from ..answer import ChoiceItem, ChoiceOption
from ..enums import Language, OutFormat, TextFormat
from ..processors import Proc
from ..question import QQuestion
from .text import FText

if TYPE_CHECKING:
    from ..category import Category


_LOG = logging.getLogger(__name__)
_TIME = [5, 10, 20, 30, 60, 90, 120, 240]


def read_kahoot(cls: Type[Category], file_path: str, lang: Language) -> "Category":
    """
    """
    cat = cls()
    with open(file_path, mode='r') as file:
        csvFile = csv.reader(file)
        next(csvFile)  # ignore the header, since is not useful currently.
        for lines in csvFile:
            args = {"values": {}}
            num, text, ans1, ans2, ans3, ans4, time, resp = lines
            resp = list(map(int, resp.split(",")))
            item = ChoiceItem()
            item.max_choices = len(resp)
            for idx, ans in enumerate((ans1, ans2, ans3, ans4)):
                item.options.append(ChoiceOption(FText(ans)))
                args["values"][idx] = {"value": 100 if idx+1 in resp else 0}
            item.processor = Proc.from_template("mapper", args)
            qst = QQuestion({lang: f"kahoot{num}"}, int(num))
            qst.time_lim = int(time)
            qst.body[lang].text.append(text)
            qst.body[lang].text.append(item)
            cat.add_question(qst)
    return cat


def write_kahoot(self: Category, file_path: str, lang: Language):
    """
    """
    def _kwrecursive(cat: Category, write: Callable):
        for qst in cat.questions:
            if not (len(qst.body[lang]) == 2 or isinstance(qst.body[lang][1], ChoiceItem)):
                continue
            qst.check()
            data = [str(qst.dbid), FText.to_string(qst.body[lang][0], None, 
                                                   OutFormat.TEXT, TextFormat.PLAIN)]
            correct = []
            if len(qst.body[lang][1].options) > 4:
                _LOG.warning("Kahoot: question %s has more than 4 options. "
                             "Before importing to Kahoot you will need to it.",
                             qst.name)
            item = qst.body[lang][1]
            for pos, ans in enumerate(item.options):
                if item.processor.func(pos)["value"] == 100:
                    correct.append(str(pos+1))
                data.append(str(ans))
            for _ in range(4 - len(item.options)):
                data.append(None)
            time = qst.time_lim
            if time not in _TIME:       # Rounds question time limit to the
                for val in _TIME:       # next valid value.
                    if val > time:
                        time = val
                        break
                else:
                    time = val
            data.append(time)
            data.append(','.join(correct))
            write(data)
        for name in cat:                            # Then add children data
            _kwrecursive(cat[name], write)
    with open(file_path, "w") as ofile:
        ofile.write(",Question,Answer1,Answer2,Answer3,Answer4,Time,Correct\n")
        _kwrecursive(self, csv.writer(ofile).writerow)
