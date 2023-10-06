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
import logging
import csv
from ..answer import Answer
from ..question import QMultichoice
from typing import TYPE_CHECKING, Callable
if TYPE_CHECKING:
    from ..category import Category


_LOG = logging.getLogger(__name__)
_TIME = [5, 10, 20, 30, 60, 90, 120, 240]


def read_kahoot(cls, file_path: str) -> "Category":
    """
    """
    cat = cls()
    with open(file_path, mode='r') as file:
        csvFile = csv.reader(file)
        next(csvFile)  # ignore the header, since is not useful currently.
        for lines in csvFile:
            num, text, ans1, ans2, ans3, ans4, time, resp = lines
            resp = resp.split(",")
            opts = [Answer(100 if "1" in resp else 0, ans1),
                    Answer(100 if "2" in resp else 0, ans2),
                    Answer(100 if "3" in resp else 0, ans3),
                    Answer(100 if "4" in resp else 0, ans4)]
            qst = QMultichoice(len(resp) == 1, name=f"kahoot{num}",
                               question=text, time_lim=int(time), options=opts)
            cat.add_question(qst)
    return cat


def write_kahoot(self, file_path: str):
    """
    """
    def _kwrecursive(cat: "Category", write: Callable):
        for num, qst in enumerate(cat.questions, 1):
            if not isinstance(qst, QMultichoice):
                continue
            qst.check()
            data = [str(num), qst.question.get()]
            correct = []
            if len(qst.options) > 4:
                _LOG.warning("Kahoot: question %s has more than 4 options. "
                             "Before importing to Kahoot you will need to it.",
                             qst.name)
            for pos, ans in enumerate(qst.options, 1):
                if ans.fraction == 100:
                    correct.append(str(pos))
                data.append(ans.text)
            for _ in range(4 - len(qst.options)):
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
