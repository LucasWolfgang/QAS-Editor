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
from .enums import CalculatedFormat, Format, ShapeType, ClozeFormat, Direction, ToleranceType
from .utils import Serializable
from .wrappers import B64File, FText
if TYPE_CHECKING:
    from typing import List
LOG = logging.getLogger(__name__)


class Answer(Serializable):
    """
    This is the basic class used to hold possible answers
    """

    def __init__(self, fraction=0.0, text="", feedback: FText = None,
                 formatting: Format = None):
        self.fraction = fraction
        self.formatting = Format.AUTO if formatting is None else formatting
        self.text = text
        self.feedback = FText("feedback") if feedback is None else feedback

    @classmethod
    def from_json(cls, data: dict):
        data["formatting"] = Format(data["formatting"])
        data["feedback"] = FText.from_json(data["feedback"])
        return cls(**data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["text"] = (str, "text")
        tags["feedback"] = (FText.from_xml, "feedback")
        attrs["format"] = (Format, "formatting")
        attrs["fraction"] = (float, "fraction")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, strict: bool) -> et.Element:
        answer = et.Element("answer", {"fraction": self.fraction})
        if self.formatting:
            answer.set("format", self.formatting.value)
        et.SubElement(answer, "text").text = self.text
        if self.feedback:
            answer.append(self.feedback.to_xml(strict))
        return answer


class NumericalAnswer(Answer):
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

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["tolerance"] = (float, "tolerance")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, strict: bool) -> et.Element:
        answer = super().to_xml(strict)
        et.SubElement(answer, "tolerance").text = self.tolerance
        return answer


class CalculatedAnswer(NumericalAnswer):
    """[summary]
    """

    def __init__(self, alength=2, ttype: ToleranceType = None,
                 aformat: CalculatedFormat = None, **kwargs):
        super().__init__(**kwargs)
        self.ttype = ToleranceType.NOM if ttype is None else ttype
        self.aformat = CalculatedFormat.DEC if aformat is None else aformat
        self.alength = alength

    @classmethod
    def from_json(cls, data: dict):
        data["ttype"] = ToleranceType(data["ttype"])
        data["aformat"] = CalculatedFormat(data["aformat"])
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["tolerancetype"] = (ToleranceType, "ttype")
        tags["correctanswerformat"] = (CalculatedFormat, "aformat")
        tags["correctanswerlength"] = (int, "alength")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, strict: bool) -> et.Element:
        answer = super().to_xml(strict)
        et.SubElement(answer, "tolerancetype").text = self.ttype.value
        et.SubElement(answer, "correctanswerformat").text = self.aformat.value
        et.SubElement(answer, "correctanswerlength").text = self.alength
        return answer


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
    def from_json(cls, data: dict):
        data["cformat"] = ClozeFormat(data["cformat"])
        for i in range(len(data["opts"])):
            data["opts"][i] = Answer.from_json(data["opts"][i])
        return cls(**data)

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
            opts.append(Answer(frac, tmp, FText("feedback", fdb, Format.PLAIN),
                               Format.PLAIN))
        return cls(int(regex[1]), ClozeFormat(regex[2]), opts)

    def to_text(self) -> str:
        """A
        """
        text = ["{", f"{self.grade}:{self.cformat.value}:"]
        opt = self.opts[0]
        text.append(f"{'=' if opt.fraction == 100 else ''}{opt.text}#"
                    f"{opt.feedback.text if opt.feedback else ''}")
        for opt in self.opts[1:]:
            text.append(f"~{'=' if opt.fraction == 100 else ''}{opt.text}#"
                        f"{opt.feedback.text if opt.feedback else ''}")
        text.append("}")
        return "".join(text)

    def to_xml(self, strict: bool):
        LOG.debug("Function <to_xml> always ignored for ClozeItem instances.")


class DragText(Serializable):
    """[summary]
    """

    def __init__(self, text: str, group=1, unlimited=False):
        self.text = text
        self.group = group
        self.unlimited = unlimited

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["text"] = (str, "text")
        tags["group"] = (str, "group")
        tags["unlimited"] = (bool, "unlimited")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, strict: bool) -> et.Element:
        dragbox = et.Element("dragbox")
        et.SubElement(dragbox, "text").text = self.text
        et.SubElement(dragbox, "group").text = str(self.group)
        if self.unlimited:
            et.SubElement(dragbox, "infinite")
        return dragbox


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

    @classmethod
    def from_json(cls, data: dict):
        data["image"] = B64File.from_json(data["image"])
        return cls(**data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["no"] = (int, "number")
        tags["text"] = (str, "text")
        tags["infinite"] = (bool, "unlimited")
        tags["draggroup"] = (int, "group")
        tags["noofdrags"] = (bool, "no_of_drags")
        tags["file"] = (B64File.from_xml, "image")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, strict: bool) -> et.Element:
        dragitem = et.Element("drag")
        et.SubElement(dragitem, "no").text = self.number
        et.SubElement(dragitem, "text").text = self.text
        if self.group:
            et.SubElement(dragitem, "draggroup").text = self.group
        if self.unlimited:
            et.SubElement(dragitem, "infinite")
        if self.no_of_drags:
            et.SubElement(dragitem, "noofdrags").text = self.no_of_drags
        if self.image:
            dragitem.append(self.image.to_xml(strict))
        return dragitem


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

    @classmethod
    def from_json(cls, data: dict):
        if data["shape"] is not None:
            data["shape"] = ShapeType(data["shape"])
        return cls(**data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        data = {a.tag: a for a in root}
        res = {}
        if "coords" in data and "shape" in data:
            res["shape"] = ShapeType(data["shape"].text)
            coords = data["coords"].text.split(";", 1)
            res["coord_x"], res["coord_y"] = map(int, coords[0].split(","))
            res["points"] = coords[1]
        elif "xleft" in data and "ytop" in data:
            res["coord_x"] = int(data["xleft"].text)
            res["coord_y"] = int(data["ytop"].text)
        else:
            raise AttributeError("One or more coordenates are missing")
        res["choice"] = int(data["choice"].text)
        res["number"] = int(data["no"].text)
        res["text"] = data["text"].text if "text" in data else None
        return cls(**res)

    def to_xml(self, strict: bool) -> et.Element:
        dropzone = et.Element("drop")
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


class CrossWord(Serializable):
    """_summary_
    """

    def __init__(self, word: str, coord_x: int, coord_y: int,
                 direction: Direction, clue: str):
        self.word = word
        self.coord_x = coord_x
        self.coord_y = coord_y
        self.direction = direction
        self.clue = clue

    @classmethod
    def from_json(cls, data: dict):
        data["direction"] = Direction(data["direction"])
        return cls(**data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        raise NotImplementedError("This Class is not avaiable in a Moodle XML")
