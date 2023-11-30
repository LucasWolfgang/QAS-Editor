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

import logging
from typing import Callable, Dict, List

from .enums import (Direction, EmbeddedFormat, Orientation, ShapeType,
                    TextFormat, TolFormat, TolType)
from .parsers.text import FText
from .processors import Proc
from .utils import File

_LOG = logging.getLogger(__name__)


class Item:
    """This is an abstract class Question used as a parent for specific
    types of Questions.
    """
    MARKER_INT = 9635

    def __init__(self, feedbacks: List[FText] = None, proc: Proc = None):
        """
        Args:
            feedback (str, optional): General feedback.
        """
        self._proc = proc
        self._feedbacks = [] if feedbacks is None else feedbacks
        self._meta = {}

    @property
    def feedbacks(self) -> List[FText]:
        """_summary_
        """
        return self._feedbacks

    @property
    def meta(self) -> Dict[str, str]:
        """_summary_
        """
        return self._meta

    @property
    def processor(self) -> Proc:
        """Function that does the processing part (define grades, when hints
            will be shown, etc). Stored in text format.
        """
        return self._proc

    @processor.setter
    def processor(self, value):
        if isinstance(value, Proc):
            self._proc = value

    def check(self):
        """_summary_
        """
        return True


class ChoiceOption:
    """This is the basic class used to hold possible answers.Represents
    qti-simple-choice. 
    Attributes:
    """

    def __init__(self, text: FText):
        self._text = text
        self.template_id = None
        self.fixed = False
        self.show = False

    def __str__(self) -> str:
        return self._text.get()


class GapOption:
    """qti-simple-associable-choice"""

    def __init__(self, text: FText) -> None:
        self.text = text
        self.template_id = None
        self.show = True
        self.match_group = None	
        self.match_max: int = None	
        self.match_min: int = 0


class MatchOption(GapOption):
    """qti-simple-associable-choice"""

    def __init__(self, text: FText) -> None:
        super().__init__(text)
        self.fixed = False


class InlineChoiceItem(Item):
    """qti-inline-choice"""

    def __init__(self, feedbacks: List[FText] = None, proc: Proc = None):
        super().__init__(feedbacks, proc)
        self._options: List[ChoiceOption] = []
        self.shuffle: bool = False
        self.required: bool = False

    @property
    def options(self) -> List[ChoiceOption]:
        """_summary_
        Returns:
            List[Choice]: _description_
        """
        return self._options

    def check(self):
        return True


class ChoiceItem(Item):
    """Basic class used to represent a multichoice item. Represents
    qti-choice-interaction. 
    """

    def __init__(self, feedbacks: List[FText] = None, proc: Proc = None):
        super().__init__(feedbacks, proc)
        self._options: List[ChoiceOption] = []
        self.shuffle: bool = False
        self.max_choices: int = 1
        self.min_choices: int = 0
        self.orientation: Orientation = Orientation.VER
        self.min_smsg = "Not enough options selected"
        self.max_smsg = "Selected options exceed maximum"

    @property
    def options(self) -> List[ChoiceOption]:
        """_summary_
        """
        return self._options

    def check(self):
        return True


class EntryItem(Item):
    """Represent an input entry item. Represents qti-text-entry-interaction.
    """

    def __init__(self, feedbacks: List[FText] = None, proc: Proc = None):
        super().__init__(feedbacks, proc)
        self.patternmask: str = None
        """Pattern mask"""
        self.patternmask_msg: str = None
        self.place_holder: str = None
        self.format: str = TextFormat.PLAIN
        self.length: int = 10
        

class TextItem(EntryItem):
    """Represent an input entry. Represents a qti-extended-text-interaction.
    """

    def __init__(self, feedbacks: List[FText] = None, proc: Proc = None):
        super().__init__(feedbacks, proc)
        self.max_strings = ""
        self.min_strings = ""


class GapItem(Item):
    """qti-gap-match-interaction"""
    
    def __init__(self, feedbacks: List[FText] = None, proc: Proc = None):
        super().__init__(feedbacks, proc)
        self.max_assoc = 1
        self.min_assoc = None
        self.shuffle = False
        self.set: List[MatchOption] = []


class MatchItem(Item):
    """qti-match-interaction"""

    def __init__(self, feedbacks: List[FText] = None, proc: Proc = None):
        super().__init__(feedbacks, proc)
        self.max_assoc = 1
        self.min_assoc = None
        self.shuffle = False
        self.set_from: List[MatchOption] = []
        self.set_to: List[MatchOption] = []


class Answer:
    """
    This is the basic class used to hold possible answers
    """

    def __init__(self, fraction=0.0, text="", feedback: FText = None,
                 formatting: TextFormat = None):
        self.fraction = fraction
        self.formatting = TextFormat.AUTO if formatting is None else formatting
        self.text = text
        self._feedback = FText()
        self._feedback.parse(feedback, None)


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


class EmbeddedItem:
    """A cloze item. It is embedded in parts of the question text marked by
    the <code>MARKER_INT</code> from the questions.py file. This item defile
    a question, which possible types are enumerated in <code>ClozeFormat</code>
    """
    MARKER_INT = 9635

    def __init__(self, grade: int, cformat: EmbeddedFormat,
                 opts: List[Answer] = None):
        self.cformat = cformat
        self.grade = grade
        self.opts: List[Answer] = opts

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


class DragItem:
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


class DropZone:
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


class Subquestion:
    """_summary_
    """

    def __init__(self, text: str, answer: str, formatting: TextFormat = None):
        super().__init__()
        self.text = text
        self.answer = answer
        self.formatting = formatting if formatting else TextFormat.AUTO


class SelectOption:
    """Internal representation
    """

    def __init__(self, text: str, group: int) -> None:
        super().__init__()
        self.text = text
        self.group = group
