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
from xml.etree import ElementTree as et
from typing import TYPE_CHECKING
from .enums import TolFormat, TextFormat, ShapeType, ClozeFormat, Direction, TolType
from .utils import Serializable, B64File, FText
if TYPE_CHECKING:
    from typing import List
LOG = logging.getLogger(__name__)


class Answer(Serializable):
    """
    This is the basic class used to hold possible answers
    """

    def __init__(self, fraction=0.0, text="", feedback: FText = None,
                 formatting: TextFormat = None):
        self.fraction = fraction
        self.formatting = TextFormat.AUTO if formatting is None else formatting
        self.text = text
        self.feedback = FText("feedback") if feedback is None else feedback


class ANumerical(Answer):
    """
    This class represents a numerical answer.
    This inherits the Answer class and the answer is still
    a string.

    This class additionally includes tolerance, currently only
    the absolute tolerance can be specified via tol method
    when initializing.
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


class ClozeItem(Serializable):
    """This class represents a cloze answer.
    This is not a standard type in the moodle format, once data in a cloze
    questions is held within the question text in this format.
    """

    def __init__(self, grade: int, cformat: ClozeFormat,
                 opts: List[Answer] = None):
        self.cformat = cformat
        self.grade = grade
        self.opts = opts if opts else []

    @classmethod
    def from_cloze(cls, regex):
        """_summary_

        Args:
            regex (_type_): _description_

        Returns:
            ClozeItem: _description_
        """
        opts = []
        for opt in regex[3].split("~"):
            if not opt:
                continue
            tmp = opt.strip("}~").split("#")
            if len(tmp) == 2:
                tmp, fdb = tmp
            else:
                tmp, fdb = tmp[0], ""
            frac = 0.0
            if tmp[0] == "=":
                frac = 100.0
                tmp = tmp[1:]
            elif tmp[0] == "%":
                frac, tmp = tmp[1:].split("%")
                frac = float(frac)
            opts.append(Answer(frac, tmp, FText("feedback", fdb, TextFormat.PLAIN),
                               TextFormat.PLAIN))
        return cls(int(regex[1]), ClozeFormat(regex[2]), opts)

    def to_text(self) -> str:
        """A
        """
        text = ["{", f"{self.grade}:{self.cformat.value}:"]
        opt = self.opts[0]
        text.append(f"{'=' if opt.fraction == 100 else ''}{opt.text}#"
                    f"{opt.feedback.text if opt.feedback else ''}")
        for opt in self.opts[1:]:
            if opt.fraction == 100:
                fraction = "="
            elif opt.fraction == 0:
                fraction = ""
            else:
                fraction = f"%{int(opt.fraction)}%"
            feedback = opt.feedback.text if opt.feedback else ''
            text.append(f"~{fraction}{opt.text}#{feedback}")
        text.append("}")
        return "".join(text)


class DragText(Serializable):
    """[summary]
    """

    def __init__(self, text: str, group=1, unlimited=False):
        self.text = text
        self.group = group
        self.unlimited = unlimited


class DragItem(Serializable):
    """
    Abstract class representing any drag item.
    """

    def __init__(self, number: int, text: str, unlimited: bool = False,
                 group: int = None, no_of_drags: str = None,
                 image: B64File = None):
        if group and no_of_drags:
            raise ValueError("Both group and number of drags can\'t "
                             "be provided to a single obj.")
        self.text = text
        self.group = group
        self.unlimited = unlimited
        self.number = number
        self.no_of_drags = no_of_drags
        self.image = image


class DropZone(Serializable):
    """
    This class represents DropZone for Questions like QDragAndDropImage.
    """

    def __init__(self, coord_x: int, coord_y: int, choice: int,
                 number: int, text: str = None, points: str = None,
                 shape: ShapeType = None):
        """[summary]

        Args:
            x (int): Coordinate X from top left corner.
            y (int): Coordinate Y from top left corner.
            text (str, optional): text contained in the zone. Defaults to None.
            choice ([type], optional): [description]. Defaults to None.
            number ([type], optional): [description]. Defaults to None.
        """
        self.shape = shape
        self.coord_x = coord_x
        self.coord_y = coord_y
        self.points = points
        self.text = text
        self.choice = choice
        self.number = number


class ACrossWord(Serializable):
    """_summary_
    """

    def __init__(self, word: str, coord_x: int, coord_y: int,
                 direction: Direction, clue: str):
        self.word = word
        self.coord_x = coord_x
        self.coord_y = coord_y
        self.direction = direction
        self.clue = clue


class Subquestion(Serializable):
    """_summary_
    """

    def __init__(self, formatting: TextFormat, text: str, answer: str):
        super().__init__()
        self.text = text
        self.answer = answer
        self.formatting = formatting


class SelectOption(Serializable):
    """Internal representation
    """

    def __init__(self, text: str, group: int) -> None:
        super().__init__()
        self.text = text
        self.group = group
