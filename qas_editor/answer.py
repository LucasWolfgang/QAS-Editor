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
import logging
from typing import TYPE_CHECKING, Dict, List, Callable
from .enums import TolFormat, TextFormat, ShapeType, EmbeddedFormat, Direction,\
                   TolType
from .parsers.text import FText
from .utils import Serializable, File, TList
_LOG = logging.getLogger(__name__)


class Item:
    """This is an abstract class Question used as a parent for specific
    types of Questions.
    """

    def __init__(self, feedbacks: List[FText] = None, 
                 hints: List[FText] = None):
        """[summary]
        Args:
            feedback (str, optional): general feedback.
            hints (Dict[str, FText], optional): hints.
        """
        self._proc = None
        self._feedbacks = feedbacks
        self._hints = hints

    @property
    def feedbacks(self) -> List[FText]:
        return self._feedbacks

    @property
    def hints(self) -> List[FText]:
        return self._hints

    @property
    def processor(self) -> str:
        """Function that does the processing part (define grades, when hints
            will be shown, etc). Stored in text format.
        """
        return self._proc
    
    @processor.setter
    def processor(self, value):
        if isinstance(value, str):
            exec(value)  # Ignore the result. What we want is no Exception here
            self._value = value

    def check(self):
        return True


class ChoicesItem(Item):
    """This is the basic class used to hold possible answers
    """
    MARKER_INT = 9635

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._options = TList[Choice]()

    @property
    def options(self) -> TList[Choice]:
        """_summary_
        Returns:
            TList[Choice]: _description_
        """
        return self._options

    def check(self):
        return True


class Choice:
    """This is the basic class used to hold possible answers
    Attributes:

    """

    def __init__(self, text, parser: Callable = None):
        self._text = FText()
        self._text.parse(text, parser)
        self.fixed = False
        self.show = False


class Answer(Serializable):
    """
    This is the basic class used to hold possible answers
    """

    def __init__(self, fraction=0.0, text="", feedback: FText = None,
                 formatting: TextFormat = None):
        self.fraction = fraction
        self.formatting = TextFormat.AUTO if formatting is None else formatting
        self.text = text
        self._feedback = FText()
        self._feedback.parse(feedback)



class ANumerical(Answer):
    """This class represents a numerical answer. It inherits the Answerclass
    and additionally includes tolerance, currently only the absolute tolerance
    can be specified via tol method when initializing.
    """

    def __init__(self, tolerance=0.1, **kwargs):
        super().__init__(**kwargs)
        self.tolerance = tolerance


class ACalculated(ANumerical):
    """[summary]
    """

    def __init__(self, alength=2, ttype: TolType = None,
                 aformat: TolFormat = None, **kwargs):
        super().__init__(**kwargs)
        self.ttype = TolType.NOM if ttype is None else ttype
        self.aformat = TolFormat.DEC if aformat is None else aformat
        self.alength = alength


class EmbeddedItem(Serializable):
    """A cloze item. It is embedded in parts of the question text marked by
    the <code>MARKER_INT</code> from the questions.py file. This item defile
    a question, which possible types are enumerated in <code>ClozeFormat</code>
    """
    MARKER_INT = 9635

    def __init__(self, grade: int, cformat: EmbeddedFormat,
                 opts: List[Answer] = None):
        self.cformat = cformat
        self.grade = grade
        self.opts = TList[Answer](opts)

    def to_cloze(self) -> str:
        """A
        """
        text = ["{", f"{self.grade}:{self.cformat.value}:"]
        opt: Answer = self.opts[0]
        text.append(f"{'=' if opt.fraction == 100 else ''}{opt.text}#"
                    f"{'?' if opt.feedback is None else opt.feedback.get()}")
        for opt in self.opts[1:]:
            if opt.fraction == 100:
                fraction = "="
            elif opt.fraction == 0:
                fraction = ""
            else:
                fraction = f"%{int(opt.fraction)}%"
            feedback = opt.feedback.get() if opt.feedback else ''
            text.append(f"~{fraction}{opt.text}#{feedback}")
        text.append("}")
        return "".join(text)


class DragItem(Serializable):
    """A dragable item. Use it as base for other "Drag" classes.
    All dragable objects have a text parameter, which may be showed in the
    canvas, or just used to identify the item.
    """

    def __init__(self, number=0, text="", no_of_drags=1):
        self.number = number
        self.text = text
        self.no_of_drags = no_of_drags


class DragGroup(DragItem):
    """A dragable item that belong to a group of dragable items.
    """

    def __init__(self, group=1, **kwargs):
        super().__init__(**kwargs)
        self.group = group


class DragImage(DragGroup):
    """A dragable and groupable item that can use an image to represent the
    item in a canvas.
    """

    def __init__(self, image: File = None, **kwargs):
        super().__init__(**kwargs)
        self.image = image


class DropZone(Serializable):
    """A zone where dragable items can be placed. They are related to the
    items matching the item number to the zone choise. Zone number is used
    only to enumerate the zone.
    """

    def __init__(self, coord_x: int, coord_y: float, choice: float,
                 number: int, text: str = None, points: List[float] = None,
                 shape: ShapeType = None):
        self.shape = shape if shape else ShapeType.RECT
        self.coord_x = coord_x
        self.coord_y = coord_y
        self.points = points
        self.text = text
        self.choice = choice
        self.number = number


class ACrossWord(Serializable):
    """_summary_
    """

    def __init__(self, word: str, coord_x: int, coord_y: int, clue: str,
                 direction: Direction):
        self.word = word
        self.coord_x = coord_x
        self.coord_y = coord_y
        self.direction = direction
        self.clue = clue


class Subquestion(Serializable):
    """_summary_
    """

    def __init__(self, text: str, answer: str, formatting: TextFormat = None):
        super().__init__()
        self.text = text
        self.answer = answer
        self.formatting = formatting if formatting else TextFormat.AUTO


class SelectOption(Serializable):
    """Internal representation
    """

    def __init__(self, text: str, group: int) -> None:
        super().__init__()
        self.text = text
        self.group = group
