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
import base64
import copy
import logging
from urllib import request
from xml.etree import ElementTree as et
from .enums import TextFormat, Status, Distribution
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import List

LOG = logging.getLogger(__name__)


def gen_hier(cls, top, category: str):
    cat_list = category.strip().split("/")
    start = 1 if top.name == cat_list[0] else 0
    quiz = top
    for i in cat_list[start:]:
        quiz.add_subcat(cls(i))
        quiz = quiz[i]
    return quiz


class Serializable:
    """An abstract class to be used as base for all serializable classes
    """

    def __str__(self) -> str:
        return f"{self.__class__} @{hex(id(self))}"

    @staticmethod
    def __itercmp(__a, __b, path: list):
        if not isinstance(__b, __a.__class__):
            return False
        if hasattr(__a, "compare"):
            path.append(str(__a))
            __a.compare(__b, path)
            path.pop()
        elif isinstance(__a, list):
            if len(__a) != len(__b):
                return False
            tmp: list = copy.copy(__b)
            for ita in __a:
                path.append(str(ita))
                idx = 0
                for idx, itb in enumerate(tmp):
                    if Serializable.__itercmp(ita, itb, path):
                        break
                else:
                    return False
                tmp.pop(idx)
                path.pop()
        elif isinstance(__a, dict):
            for key, value in __a.items():
                if not Serializable.__itercmp(value, __b.get(key), path):
                    return False
        elif __a != __b:
            return False
        return True

    def compare(self, __o: object, path: list) -> bool:
        """A
        """
        if not isinstance(__o, self.__class__):
            return False
        for key, val in self.__dict__.items():
            if key not in ("_Question__parent", "_Category__parent") and not \
                    Serializable.__itercmp(val, __o.__dict__.get(key), path):
                cpr = __o.__dict__.get(key)
                path = ", ".join(path[:-1])
                if isinstance(val, list) and cpr:
                    val = ", ".join(map(str, val))
                    cpr = ", ".join(map(str, cpr))
                if isinstance(val, str) and len(val) > 20:
                    with open("raw1.tmp", "w") as ofile:
                        ofile.write(val)
                    with open("raw2.tmp", "w") as ofile:
                        ofile.write(cpr)
                    output = f"Items differs [{path}, {key}]. See diff files."
                else:
                    output = f"Items differs [{path}, {key}]\n\t{val}\n\t{cpr}"
                raise ValueError(output)
        return True

    def to_xml(self, strict: bool) -> et.Element:
        """Create a XML representation of the object instance following the
        moodle standard. This function if first implemented as "virtual" in
        the Serializable class, raising an exception if not overriden.

        Args:
            root (et.Element): where the new tags will be added to
            strict (bool): if the tags added should only be the ones correctly
                interpreted by moodle.

        Returns:
            et.Element: The instance root element. In a organized XML, this
            should be always different from the "root" argument, but since
            Moodle uses tags, like the ones in CombinedFeedback, that can or
            not be valid, we end-up in this mess.
        """
        raise NotImplementedError(f"XML not implemented in {self}")


class LineBuffer:
    """Helps parsing text files that uses lines (\\n) as part of the standard
    somehow.
    """

    def __init__(self, stream) -> None:
        self.last = ""
        self.cur = ""
        self.eof = False
        self._stream = stream

    def read(self, until: str = None) -> str:
        """_summary_

        Args:
            inext (bool, optional): _description_. Defaults to False.

        Returns:
            _type_: _description_
        """
        _buffer = [self.cur]
        self.last = self.cur
        self.cur = self._stream.readline()
        while (self.cur and self.cur == "\n" and 
                    (until is None or self.cur != until)):
            self.cur = self._stream.readline()
            _buffer.append(self.cur.strip())
        self.eof = not bool(self.cur)
        self.cur = self.cur.strip()
        return self.cur if until is None else "".join(_buffer)


# -----------------------------------------------------------------------------


class ParseError(Exception):
    """Exception used when a parsing fails.
    """


class MarkerError(Exception):
    """Exception used when there is a Marker related error
    """


class AnswerError(Exception):
    """Exception used when a parsing fails.
    """


# -----------------------------------------------------------------------------


class B64File(Serializable):
    """Internal representation for files that uses Base64 encoding.
    """

    def __init__(self, name: str, path: str = None, bfile: str|bool = True):
        super().__init__()
        self.name = name
        self.path = path
        self.bfile = bfile
        if bfile is True:
            try:
                with request.urlopen(self.path) as ifile:
                    self.bfile = str(base64.b64encode(ifile.read()), "utf-8")
            except ValueError:
                with open(self.path, "rb") as ifile:
                    self.bfile = str(base64.b64encode(ifile.read()), "utf-8")


class Dataset(Serializable):
    """A
    """

    def __init__(self, status: Status, name: str, ctype: str,
                 distribution: Distribution, minimum: float, maximum: float,
                 decimals: int, items: dict = None) -> None:
        super().__init__()
        self.status = status
        self.name = name
        self.ctype = ctype
        self.distribution = distribution
        self.minimum = minimum
        self.maximum = maximum
        self.decimals = decimals
        self.items = items if items else {}

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, self.__class__):
            return False
        if self.status == Status.PRV or __o.status == Status.PRV:
            return False
        return self.__dict__ == __o.__dict__

    def __str__(self) -> str:
        return f"{self.status.name} > {self.name} ({hex(id(self))})"


class FText(Serializable):
    """A
    """

    def __init__(self, name: str, text="", formatting: TextFormat = None,
                 bfile: List[B64File] = None):
        super().__init__()
        self.name = name
        self.text = text
        self.formatting = TextFormat.AUTO if formatting is None else formatting
        self.bfile = bfile if bfile else []


class Hint(Serializable):
    """Represents a hint to be displayed when a wrong answer is provided
    to a "multiple tries" question. The hints are give in the listed order.
    """

    def __init__(self, formatting: TextFormat, text: str, show_correct: bool,
                 clear_wrong: bool, state_incorrect: bool = False) -> None:
        self.formatting = formatting
        self.text = text
        self.show_correct = show_correct
        self.clear_wrong = clear_wrong
        self.state_incorrect = state_incorrect


class Unit(Serializable):
    """A
    """

    def __init__(self, unit_name: str, multiplier: float) -> None:
        super().__init__()
        self.unit_name = unit_name
        self.multiplier = multiplier


class Tags(Serializable, list):
    """A
    """

    def __init__(self, tags=None) -> None:
        super().__init__(tags) if tags is not None else super().__init__()


class Equation(Serializable):
    """Represents an equation in a formulary. This is a speciallized way of 
    representing a test description (<code>QDescription</code>).
    """

    def __init__(self, name: str, text: FText) -> None:
        self.__name = name
        self.__text = text

    def to_description(self):
        pass


class Table(Serializable):
    """Represents a table in a formulary. This is a speciallized way of 
    representing a test description (<code>QDescription</code>).
    """

    def __init__(self, name: str, text: FText) -> None:
        self.__name = name
        self.__text = text

    def to_description(self):
        pass


class Rule(Serializable):
    """Represents a theory, law or other set of sentences that describe a
    given phenomenum. This is a speciallized way of representing a test
    description (<code>QDescription</code>).
    """

    def __init__(self, name: str, text: FText, proof: FText) -> None:
        self.__name = name
        self.__text = text
        self.__proof = proof

    def to_description(self):
        pass