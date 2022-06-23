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
from io import BytesIO
from importlib import util
from urllib import request
from typing import TYPE_CHECKING
from .enums import TextFormat, Status, Distribution

if TYPE_CHECKING:
    from typing import List

LOG = logging.getLogger(__name__)
EXTRAS_FORMULAE = util.find_spec("sympy") is not None
EXTRAS_GUI = util.find_spec("PyQt5") is not None


def gen_hier(cls, top, category: str):
    """Generates a categorty hierarchy based on the provided string.
    TODO consider putting it in another file.
    """
    cat_list = category.strip().split("/")
    start = 1 if top.name == cat_list[0] else 0
    quiz = top
    for i in cat_list[start:]:
        quiz.add_subcat(cls(i))
        quiz = quiz[i]
    return quiz


def nxt(stt: list, string: str):
    """A help function to parse text char by char.
    
    Args:
        stt (list): 0 - index, 1 - if escaped
        string (str): the string being parsed
    """
    stt[1] = (string[stt[0]] == "\\") and not stt[1]
    stt[0] += 1


def sympy_to_image(s: str, wrap: bool, color='Black', scale=1.0):
    """

    # TODO optimize. It has just too many calls. But at least it works...
    """
    try:
        from matplotlib import figure, font_manager, mathtext
        from matplotlib.backends import backend_agg
        from pyparsing import ParseFatalException  # Part of matplotlib package
    except ImportError:
        return None
    s = s.replace('$$', '$')
    if wrap:
        s = u'${0}$'.format(s)
    try:
        prop = font_manager.FontProperties(size=12)
        dpi = 120 * scale
        buffer = BytesIO()
        parser = mathtext.MathTextParser("path")
        width, height, depth, _, _ = parser.parse(s, dpi=72, prop=prop)
        fig = figure.Figure(figsize=(width / 72, height / 72))
        fig.text(0, depth / height, s, fontproperties=prop, color=color)
        backend_agg.FigureCanvasAgg(fig)  # set the canvas used
        fig.savefig(buffer, dpi=dpi, format="png", transparent=True)
        return str(base64.b64encode(buffer.getvalue()), "utf-8")
    except (ValueError, RuntimeError, ParseFatalException):
        return None



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
            path.append(__a)
            __a.compare(__b, path)
            path.pop()
        elif isinstance(__a, list):
            if len(__a) != len(__b):
                return False
            tmp: list = copy.copy(__b)
            for ita in __a:
                path.append(ita)
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
            cpr = __o.__dict__.get(key)
            if key not in ("_Question__parent", "_Category__parent") and not \
                    Serializable.__itercmp(val, cpr, path):
                raise ValueError(f"In {path} > {key}. Use debugger.")
        return True


class TList(list):
    """Type List (or Datatype list) is a class that restricts the datatype of
    all the items to a single one defined in constructor. It works exactly like
    an list in C++, Java and other high-level compiled languages. Could use an
    array instead if it allowed any time to be used. TODO If there is something
    native we could use instead, it is worthy an PR to update.
    """

    def __init__(self, obj_type: object, iterable=None):
        super().__init__()
        self.__type = obj_type
        if iterable is not None:
            self.extend(iterable)

    @property
    def datatype(self):
        """The datatype of the items in this list.
        """
        return self.__type

    @datatype.setter
    def datatype(self, value):
        if not all(isinstance(obj, value) for obj in self):
            self.clear()
        self.__type = value

    def append(self, __object):
        if isinstance(__object, self.__type):
            super().append(__object)

    def extend(self, __iterable):
        if all(isinstance(obj, self.__type) for obj in __iterable):
            super().extend(__iterable)


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
    """File used in questions. Can be either a local path, an URL, a B64
    encoded string. TODO May add PIL in the future too. Currently is always
    converted into B64 to be embedded. May also change in the future.
    """

    def __init__(self, name: str, path: str = None, bfile: str | bool = True):
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
        if Status.PRV in (self.status, __o.status):
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

    @staticmethod
    def prop(attr: str):
        """Generate get/set/del properties for a Ftext attribute.
        """
        def setter(self, value):
            data = getattr(self, attr)
            if isinstance(value, FText) and value.name == data.name:
                setattr(self, attr, value)
            elif isinstance(value, str):
                data.text = value
            elif value is not None:
                raise ValueError(f"Can't assign {value} to {attr}")

        def getter(self) -> FText:
            return getattr(self, attr)
        return property(getter, setter, doc="")


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


class Equation(Serializable):
    """Represents an equation in a formulary. This is a speciallized way of
    representing a test description (<code>QDescription</code>).
    """

    def __init__(self, name: str, text: FText) -> None:
        self.name = name
        self.text = text


class Table(Serializable):
    """Represents a table in a formulary. This is a speciallized way of
    representing a test description (<code>QDescription</code>).
    """

    def __init__(self, name: str, text: FText) -> None:
        self.name = name
        self.text = text


class Rule(Serializable):
    """Represents a theory, law or other set of sentences that describe a
    given phenomenum. This is a speciallized way of representing a test
    description (<code>QDescription</code>).
    """

    def __init__(self, name: str, text: FText, proof: FText) -> None:
        self.name = name
        self.text = text
        self.proof = proof
