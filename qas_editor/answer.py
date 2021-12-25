from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .enums import Direction
    from typing import List
from .utils import cdata_str, extract
from .enums import Format, ShapeType, ClozeFormat
from xml.etree import ElementTree as et
from .wrappers import B64File, FText

class Answer:
    """
    This is the basic class used to hold possible answers
    """

    def __init__(self, fraction: float, text: str, feedback: FText=None, 
                formatting: Format=None) -> None:
        self.fraction = fraction
        self.formatting = formatting
        self.text = text
        self.feedback = feedback

    @classmethod
    def from_xml(cls, root: et.Element, *args) -> "Answer":
        data = {x.tag: x for x in root}
        fraction = root.get("fraction")
        text = data["text"].text
        feedback = FText.from_xml(data.get("feedback"))
        formatting = Format(root.get("format", "html"))
        return cls(*args, fraction, text, feedback, formatting)

    def to_xml(self) -> et.Element:
        answer = et.Element("answer", {"fraction": str(self.fraction)})  
        if self.formatting:
            answer.set("format", self.formatting.value)
        answer.set("fraction", str(self.fraction))
        et.SubElement(answer, "text").text = cdata_str(self.text)
        if self.feedback:
            self.feedback.to_xml(answer, "feedback")
        return answer

# ----------------------------------------------------------------------------------------

class NumericalAnswer(Answer):
    """
    This class represents a numerical answer.
    This inherits the Answer class and the answer is still
    a string.

    This class additionally includes tolerance, currently only
    the absolute tolerance can be specified via tol method 
    when initializing.
    """

    def __init__(self, tol: float=0.1, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.tolerance = tol

    @classmethod
    def from_xml(cls, root: et.Element, *args) -> "NumericalAnswer":
        data = {x.tag: x for x in root}
        tolerance = data["tolerance"].text
        answer = super().from_xml(root, *args, tolerance)
        return answer

    def to_xml(self) -> et.Element:
        answer = super().to_xml()
        tolerance = et.SubElement(answer, "tolerance")
        tolerance.text = str(self.tolerance)
        return answer

# ----------------------------------------------------------------------------------------

class CalculatedAnswer(NumericalAnswer):
    """[summary]
    """
    
    def __init__(self, tolerance_type: int=1, correct_answer_format: int=1, 
                correct_answer_length: int=1, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.tolerance_type = tolerance_type
        self.correct_answer_format = correct_answer_format
        self.correct_answer_length = correct_answer_length

    @classmethod
    def from_xml(cls, root: et.Element) -> "CalculatedAnswer":
        data = {x.tag: x for x in root}
        tolerance_type = data["tolerancetype"].text
        correct_answer_format = data["correctanswerformat"].text
        correct_answer_length = data["correctanswerlength"].text
        answer: "CalculatedAnswer" = super().from_xml(root, tolerance_type, 
                                                    correct_answer_format, 
                                                    correct_answer_length)
        return answer

    def to_xml(self) -> et.Element:
        answer = super().to_xml()
        et.SubElement(answer, "tolerancetype").text = str(self.tolerance_type)
        et.SubElement(answer, "correctanswerformat").text = str(self.correct_answer_format)
        et.SubElement(answer, "correctanswerlength").text = str(self.correct_answer_length)
        return answer

# ----------------------------------------------------------------------------------------

class ClozeItem():
    """This class represents a cloze answer.
    This is not a standard type in the moodle format, once data in a cloze questions is
    held within the question text in this format.
    """

    def __init__(self, start: int, grade: int, cformat: ClozeFormat, 
                options: List[Answer]=None) -> None:
        self.start: int = start
        self.cformat: ClozeFormat = cformat
        self.grade = grade
        self.opts: List[Answer] = options if options else []

    def __str__(self) -> str:
        text = ["{", f"{self.grade}:{self.cformat.value}:"]
        o = self.opts[0]
        text.append(f"{'=' if o.fraction == 100 else ''}{o.text}# \
                    {o.feedback.text if o.feedback else ''}" )
        for o in self.opts[1:]:
            text.append(f"~{'=' if o.fraction == 100 else ''}{o.text}# \
                        {o.feedback.text if o.feedback else ''}" )
        text.append("}")
        return "".join(text)

    @classmethod
    def from_cloze(cls, regex) -> "ClozeItem":
        options = []
        for opt in regex[3].split("~"):
            if not opt: continue
            tmp = opt.strip("}~").split("#")
            if len(tmp) == 2: tmp, fdb = tmp
            else: tmp, fdb = tmp[0], ""
            frac = 0.0
            if tmp[0] == "=":
                frac = 100.0
                tmp = tmp[1:]
            elif tmp[0] == "%":
                frac, tmp = tmp[1:].split("%")
                frac = float(frac)    
            options.append(Answer(frac, tmp, FText(fdb, Format.PLAIN), Format.PLAIN))
        return cls(regex.start(), int(regex[1]), ClozeFormat(regex[2]), options)

# ----------------------------------------------------------------------------------------

class DragText:
    """[summary]
    """

    def __init__(self, text: str, group: int=1, unlimited: bool=False) -> None:
        self.text = text
        self.group = group
        self.unlimited = unlimited

    @classmethod
    def from_xml(cls, root: et.Element) -> "DragText":
        data = {x.tag: x for x in root}
        text = data["text"].text
        group = int(data["group"].text)
        unlimited = True if data.get("infinite") else False
        return cls(text, group, unlimited)

    def to_xml(self) -> et.Element:
        dragbox = et.Element("dragbox")
        et.SubElement(dragbox, "text").text = self.text
        et.SubElement(dragbox, "group").text = str(self.group)
        if self.unlimited:
           et.SubElement(dragbox, "infinite")
        return dragbox

# ----------------------------------------------------------------------------------------

class DragItem:
    """
    Abstract class representing any drag item.
    """

    def __init__(self, number: int, text: str, unlimited: bool=False, group: int=None, 
                 no_of_drags: str=None, image: B64File=None) -> None:
        if group and no_of_drags:
            return ValueError("Both group and number of drags can\'t be provided to a single obj.")
        self.text = text
        self.group = group
        self.unlimited = unlimited
        self.number = number
        self.no_of_drags = no_of_drags
        self.image = image

    @classmethod
    def from_xml(cls, root: et.Element) -> "DragItem":
        data = {x.tag: x for x in root}
        number = data["no"].text
        text = data["text"].text
        unlimited = "infinite" in data
        group = data.get("draggroup").text if "draggroup" in data else None
        no_of_drags = data.get("noofdrags").text if "noofdrags" in data else None
        image = B64File.from_xml(data.get("file"))
        return cls(number, text, unlimited, group, no_of_drags, image)

    def to_xml(self) -> et.Element:
        dragitem = et.Element("drag")
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

# ----------------------------------------------------------------------------------------

class DropZone:
    """
    This class represents DropZone for Questions like QDragAndDropImage.
    """

    def __init__(self, x: int, y: int, choice: int, number: int, text: str=None, 
                 points: str=None, shape: ShapeType=None) -> None:
        """[summary]

        Args:
            x (int): Coordinate X from top left corner.
            y (int): Coordinate Y from top left corner.
            text (str, optional): text contained in the drop zone. Defaults to None.
            choice ([type], optional): [description]. Defaults to None.
            number ([type], optional): [description]. Defaults to None.
        """
        self.shape = shape
        self.x = x
        self.y = y
        self.points = points
        self.text = text
        self.choice = choice
        self.number = number

    @classmethod
    def from_xml(cls, root: et.Element) -> "DropZone":
        data = {x.tag: x for x in root}
        res = {}
        if "coords" in data and "shape" in data:
            res["shape"] = ShapeType(data["shape"].text)
            coords = data["coords"].text.split(";", 1)
            res["x"], res["y"] = map(int, coords[0].split(","))
            res["points"] = coords[1]
        elif "xleft" in data and "ytop" in data:
            extract(data, "xleft", res, "x", int)
            extract(data, "ytop", res, "y", int)
        else:
            raise AttributeError("One or more coordenates are missing for the DropZone")
        extract(data, "choice", res, "choice", int)
        extract(data, "no", res, "number", int)
        extract(data, "text", res, "text", str)
        return cls(**res)

    def to_xml(self) -> et.Element:
        dropzone = et.Element("drop")
        if self.text:
            et.SubElement(dropzone, "text").text = self.text
        et.SubElement(dropzone, "no").text = str(self.number)
        et.SubElement(dropzone, "choice").text = str(self.choice)
        if self.shape:
            et.SubElement(dropzone, "shape").text = self.shape.value
        if not self.points:
            et.SubElement(dropzone, "xleft").text = str(self.x)
            et.SubElement(dropzone, "ytop").text = str(self.y)
        else:
            et.SubElement(dropzone, "coords").text = f"{self.x},{self.y};{self.points}"
        return dropzone

# ----------------------------------------------------------------------------------------

class CrossWord():

    def __init__(self, word: str, x: int, y: int, direction: Direction, clue: str) -> None:
        self.word = word
        self.x = x
        self.y = y
        self.direction = direction
        self.clue = clue

    @classmethod
    def from_xml(cls, root: et.Element, *args) -> "NumericalAnswer":
        raise NotImplementedError("This Class is not avaiable in a Moodle XML")

    def to_xml(self) -> et.Element:
        raise NotImplementedError("This Class is not avaiable in a Moodle XML")