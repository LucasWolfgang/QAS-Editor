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
from ..questions import QMultichoice
from typing import TYPE_CHECKING, Callable
if TYPE_CHECKING:
    from ..category import Category
_LOG = logging.getlogger(__name__)

_TIME = [5, 10, 20, 30, 60, 90, 120, 240]

def read(cls, file_path: str, comment=None) -> "Category":
    """
    """
    pass

def write(self, file_path: str):
    """
    """
    def _kwrecursive(cat: "Category", write: Callable):
        for num, qst in enumerate(cat.questions):
            if not isinstance(qst, QMultichoice):
                continue
            qst.check()
            write(f"{num},{qst.question},")
            correct = []
            for pos, ans in enumerate(qst.options[:4]):
                if ans.fraction == 100:
                    correct.append(pos)
                else:
                    write(f"{ans.text},")
            for num in range(4 - len(qst.options)):
                write(",")
            time = qst.time_lim
            if time not in _TIME:       # Rounds question time limit to the
                for val in _TIME:       # next valid value.
                    if val > time:
                        time = val
                        break
                else:
                    time = val
            write(f"{time},\"{','.join(correct)}\"\n")    
        for name in cat:                            # Then add children data
            _kwrecursive(cat[name], write)
    with open(file_path, "w") as ofile:
        ofile.write(",Question,Answer1,Answer2,Answer3,Answer4,Time,Correct\n")
        _kwrecursive(self, ofile.write)
