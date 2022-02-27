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
from .enums import Format, ShapeType, ClozeFormat, Direction
from .utils import cdata_str, Serializable
from .wrappers import B64File, FText
if TYPE_CHECKING:
    from typing import List
LOG = logging.getLogger(__name__)

class Answer(Serializable):
    """
    This is the basic class used to hold possible answers
    """

    def __init__(self, fraction: float, text: str, feedback: FText,
                 formatting: Format) -> None:
        self.fraction = fraction
        self.formatting = formatting
        self.text = text
        self.feedback = feedback

    @classmethod
    def from_json(cls, data: dict) -> "Answer":
        data["formatting"] = Format(data["formatting"])
        data["feedback"] = FText.from_json(data["feedback"])
        return cls(**data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "Answer":
        tags["fraction"] = (float, "fraction")
        tags["text"] = (str, "text")
        tags["feedback"] = (FText.from_xml, "feedback")
        attrs["format"] = (Format, "format")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, strict: bool) -> et.Element:
        answer = et.SubElement(root, "answer", {"fraction": str(self.fraction)})
        if self.formatting:
            answer.set("format", self.formatting.value)
        et.SubElement(answer, "text").text = cdata_str(self.text)
        if self.feedback:
            self.feedback.to_xml(answer)
        return answer

# ------------------------------------------------------------------------------

class NumericalAnswer(Answer):
    """
    This class represents a numerical answer.
    This inherits the Answer class and the answer is still
    a string.

    This class additionally includes tolerance, currently only
    the absolute tolerance can be specified via tol method
    when initializing.
    """

    def __init__(self, tolerance: float = 0.1, **kwargs) -> None:
        super().__init__(**kwargs)
        self.tolerance = tolerance

    @classmethod
    def from_json(cls, data: dict) -> "NumericalAnswer":
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "NumericalAnswer":
        tags["tolerance"] = float
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, strict: bool) -> et.Element:
        answer = super().to_xml(root, strict)
        et.SubElement(answer, "tolerance").text = str(self.tolerance)
        return answer

# ------------------------------------------------------------------------------

class CalculatedAnswer(NumericalAnswer):
    """[summary]
    """

    def __init__(self, tolerance_type: int, answer_format: int,
                 answer_length: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self.tolerance_type = tolerance_type
        self.answer_format = answer_format
        self.answer_length = answer_length

    @classmethod
    def from_json(cls, data: dict) -> "CalculatedAnswer":
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "CalculatedAnswer":
        tags["tolerancetype"] = (int, "tolerance_type")
        tags["correctanswerformat"] = (int, "answer_length")
        tags["correctanswerlength"] = (int, "answer_length")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, strict: bool) -> et.Element:
        answer = super().to_xml(root, strict)
        et.SubElement(answer, "tolerancetype").text = str(self.tolerance_type)
        et.SubElement(answer, "correctanswerformat").text = str(self.answer_format)
        et.SubElement(answer, "correctanswerlength").text = str(self.answer_length)
        return answer

# ------------------------------------------------------------------------------

class ClozeItem(Serializable):
    """This class represents a cloze answer.
    This is not a standard type in the moodle format, once data in a cloze
    questions is held within the question text in this format.
    """

    def __init__(self, start: int, grade: int, cformat: ClozeFormat,
                 options: List[Answer] = None) -> None:
        self.start: int = start
        self.cformat: ClozeFormat = cformat
        self.grade = grade
        self.opts: List[Answer] = options if options else []

    def __str__(self) -> str:
        text = ["{", f"{self.grade}:{self.cformat.value}:"]
        opt = self.opts[0]
        text.append(f"{'=' if opt.fraction == 100 else ''}{opt.text}# \
                    {opt.feedback.text if opt.feedback else ''}")
        for opt in self.opts[1:]:
            text.append(f"~{'=' if opt.fraction == 100 else ''}{opt.text}# \
                        {opt.feedback.text if opt.feedback else ''}")
        text.append("}")
        return "".join(text)

    @classmethod
    def from_json(cls, data: dict) -> "ClozeItem":
        data["cformat"] = ClozeFormat(data["cformat"])
        for i in range(len(data["opts"])):
            data["opts"][i] = Answer.from_json(data["opts"])
        return cls(**data)

    @classmethod
    def from_cloze(cls, regex) -> "ClozeItem":
        """_summary_

        Args:
            regex (_type_): _description_

        Returns:
            ClozeItem: _description_
        """
        options = []
        for opt in regex[3].split("~"):
            if not opt:
                continue
            tmp = opt.strip("}~").split("#")
            if len(tmp) == 2:
                tmp, fdb = tmp
            else: tmp, fdb = tmp[0], ""
            frac = 0.0
            if tmp[0] == "=":
                frac = 100.0
                tmp = tmp[1:]
            elif tmp[0] == "%":
                frac, tmp = tmp[1:].split("%")
                frac = float(frac)
            options.append(Answer(frac, tmp,
                                  FText("feedback", fdb, Format.PLAIN, None),
                                  Format.PLAIN))
        return cls(regex.start(), int(regex[1]), ClozeFormat(regex[2]), options)

    def to_xml(self, root: et.Element, strict: bool):
        LOG.debug(f"Function <to_xml> is not used in {self}")

# ------------------------------------------------------------------------------

class DragText(Serializable):
    """[summary]
    """

    def __init__(self, text: str, group: int = 1, unlimited: bool = False) -> None:
        self.text = text
        self.group = group
        self.unlimited = unlimited

    @classmethod
    def from_json(cls, data: dict) -> "DragText":
        return cls(**data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "DragText":
        tags["text"] = (str, "text")
        tags["group"] = (str, "group")
        tags["unlimited"] = (bool, "unlimited")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, strict: bool) -> et.Element:
        dragbox = et.SubElement(root, "dragbox")
        et.SubElement(dragbox, "text").text = self.text
        et.SubElement(dragbox, "group").text = str(self.group)
        if self.unlimited:
            et.SubElement(dragbox, "infinite")
        return dragbox

# ------------------------------------------------------------------------------

class DragItem(Serializable):
    """
    Abstract class representing any drag item.
    """

    def __init__(self, number: int, text: str, unlimited: bool = False,
                 group: int = None, no_of_drags: str = None,
                 image: B64File = None) -> None:
        if group and no_of_drags:
            raise ValueError("Both group and number of drags can\'t "+
                             "be provided to a single obj.")
        self.text = text
        self.group = group
        self.unlimited = unlimited
        self.number = number
        self.no_of_drags = no_of_drags
        self.image = image

    @classmethod
    def from_json(cls, data: dict) -> "DragItem":
        data["image"] = B64File.from_json(data["image"])
        return cls(**data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "DragItem":
        tags["number"] = (int, "number")
        tags["text"] = (str, "text")
        tags["infinite"] = (bool, "unlimited")
        tags["draggroup"] = (int, "group")
        tags["noofdrags"] = (bool, "no_of_drags")
        tags["file"] = (B64File.from_xml, "image")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, strict: bool) -> et.Element:
        dragitem = et.SubElement(root, "drag")
        et.SubElement(dragitem, "no").text = str(self.number)
        et.SubElement(dragitem, "text").text = self.text
        if self.group:
            et.SubElement(dragitem, "draggroup").text = str(self.group)
        if self.unlimited:
            et.SubElement(dragitem, "infinite")
        if self.no_of_drags:
            et.SubElement(dragitem, "noofdrags").text = str(self.no_of_drags)
        if self.image:
            dragitem.append(self.image.to_xml())
        return dragitem

# ------------------------------------------------------------------------------

class DropZone(Serializable):
    """
    This class represents DropZone for Questions like QDragAndDropImage.
    """

    def __init__(self, coord_x: int, coord_y: int, choice: int,
                 number: int, text: str = None, points: str = None,
                 shape: ShapeType = None) -> None:
        """[summary]

        Args:
            x (int): Coordinate X from top left corner.
            y (int): Coordinate Y from top left corner.
            text (str, optional): text contained in the drop zone. Defaults to None.
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

    @classmethod
    def from_json(cls, data: dict) -> "DropZone":
        if data["shape"] is not None:
            data["shape"] = ShapeType(data["shape"])
        return cls(**data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "DropZone":
        data = {a.tag: a for a in root}
        res = {}
        if "coords" in data and "shape" in data:
            res["shape"] = ShapeType(data["shape"].text)
            coords = data["coords"].text.split(";", 1)
            res["coord_x"], res["coord_y"] = map(int, coords[0].split(","))
            res["points"] = coords[1]
        elif "xleft" in data and "ytop" in data:
            res["xleft"] = int(data["coord_x"])
            res["ytop"] = int(data["coord_y"])
        else:
            raise AttributeError("One or more coordenates are missing for the DropZone")
        res["choice"] = int(data["choice"])
        res["no"] = int(data["number"])
        res["text"] = data["text"]
        return cls(**res)

    def to_xml(self, root: et.Element, strict: bool) -> et.Element:
        dropzone = et.SubElement(root, "drop")
        if self.text:
            et.SubElement(dropzone, "text").text = self.text
        et.SubElement(dropzone, "no").text = str(self.number)
        et.SubElement(dropzone, "choice").text = str(self.choice)
        if self.shape:
            et.SubElement(dropzone, "shape").text = self.shape.value
        if not self.points:
            et.SubElement(dropzone, "xleft").text = str(self.coord_x)
            et.SubElement(dropzone, "ytop").text = str(self.coord_y)
        else:
            _tmp = et.SubElement(dropzone, "coords")
            _tmp.text = f"{self.coord_x},{self.coord_y};{self.points}"
        return dropzone

# ------------------------------------------------------------------------------

class CrossWord(Serializable):
    """_summary_
    """

    def __init__(self, word: str, coord_x: int, coord_y: int,
                 direction: Direction, clue: str) -> None:
        self.word = word
        self.coord_x = coord_x
        self.coord_y = coord_y
        self.direction = direction
        self.clue = clue

    @classmethod
    def from_json(cls, data: dict) -> "CrossWord":
        data["direction"] = Direction(data["direction"])
        return cls(**data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "CrossWord":
        raise NotImplementedError("This Class is not avaiable in a Moodle XML")

# ------------------------------------------------------------------------------
