import base64
from typing import List, Dict
from xml.etree import ElementTree as et
from urllib.request import urlopen
from .enums import Format, Status, Distribution, Grading, ShowUnits, ShapeType
from .utils import cdata_str, get_txt

# ----------------------------------------------------------------------------------------

class B64File():

    def __init__(self, name: str, path: str=None, bfile: str=None) -> None:
        self.path = path
        self.name = name
        if bfile:
            self.bfile = bfile
        else:
            try:
                with urlopen(self.path) as response:
                    self.bfile = str(base64.b64encode(response.read()), "utf-8")
            except Exception:
                with open(self.path, "rb") as f:
                    self.bfile = str(base64.b64encode(f.read()), "utf-8")

    @classmethod
    def from_xml(cls, root: et.Element) -> "B64File":
        if root is None:
            return None
        name = root.get("name")
        path = root.get("path")
        bfile = root.text
        return cls(name, path, bfile)

    def to_xml(self) -> et.Element:
        bfile = et.Element("file", {"name": self.name, "encoding" : "base64"})
        if self.path:
            bfile.set("path", self.path)
        bfile.text = self.bfile
        return bfile

# ----------------------------------------------------------------------------------------

class SelectOption:

    def __init__(self, text: str, group: int) -> None:
        self.text = text
        self.group = group

    @classmethod
    def from_xml(cls, root: et.Element) -> "SelectOption":
        data = {x.tag: x for x in root}
        text = data["text"].text
        group = data["group"].text
        return cls(text, group)

    def to_xml(self) -> et.Element:
        select_option = et.Element("selectoption")
        et.SubElement(select_option, "text").text = self.text
        et.SubElement(select_option, "group").text = str(self.group)
        return select_option

# ----------------------------------------------------------------------------------------

class Subquestion:

    def __init__(self, formatting: Format, text: str, answer: str) -> None:
        self.text = text
        self.answer = answer
        self.formatting = formatting

    @classmethod
    def from_xml(cls, root: et.Element) -> "Subquestion":
        data = {x.tag: x for x in root}
        formatting = Format.get(root.get("format"))
        text = data["text"].text
        answer = data["answer"][0].text
        return cls(formatting, text, answer)

    def to_xml(self) -> et.Element:
        subquestion = et.Element("subquestion", {"format": self.formatting.value})
        et.SubElement(subquestion, "text").text = cdata_str(self.text)
        answer = et.SubElement(subquestion, "answer")
        et.SubElement(answer, "text").text = self.answer
        return subquestion

# ----------------------------------------------------------------------------------------

class UnitHandling():

    def __init__(self, grading_type: Grading, penalty: float, show: ShowUnits, left: bool) -> None:
        self.grading_type = grading_type
        self.penalty = penalty
        self.show = show
        self.left = left

    @classmethod
    def from_xml(cls, data: Dict[str, et.Element]) -> "UnitHandling":
        grading_type = Grading.get(get_txt(data, "unitgradingtype"))
        penalty = get_txt(data, "unitpenalty")
        show = ShowUnits.get(get_txt(data, "showunits"))
        left = bool(data.get("unitsleft",False))
        return cls(grading_type, penalty, show, left)

    def to_xml(self, root: et.Element) -> None:
        et.SubElement(root, "unitgradingtype").text = self.grading_type.value
        et.SubElement(root, "unitpenalty").text = str(self.penalty)
        et.SubElement(root, "showunits").text = self.show.value
        et.SubElement(root, "unitsleft").text = str(int(self.left))

# ----------------------------------------------------------------------------------------

class Unit():

    def __init__(self, unit_name: str, multiplier: float) -> None:
        self.unit_name = unit_name
        self.multiplier = multiplier

    @classmethod
    def from_xml(cls, root: et.Element) -> "Unit":
        data = {x.tag: x for x in root}
        unit_name = data["unit_name"].text
        multiplier = data["multiplier"].text
        return cls(unit_name, multiplier)

    def to_xml(self) -> et.Element:
        unit = et.Element("unit")
        et.SubElement(unit, "unit_name").text = self.unit_name
        et.SubElement(unit, "multiplier").text = str(self.multiplier)
        return unit

# ----------------------------------------------------------------------------------------

class FText():

    def __init__(self, text: str, formatting: Format) -> None:
        self.text = text
        if formatting is None:
            raise ValueError("Formatting should not be none")
        self.formatting = formatting
        self.bfile: List[B64File] = []

    @classmethod
    def from_xml(cls, root: et.Element) -> "FText":
        if root is None:
            return None
        formatting = Format.get(root.get("format", "html"))
        text = root[0].text
        obj = cls(text, formatting)
        for fls in root.findall("file"):
            obj.bfile.append(B64File.from_xml(fls))
        return obj 

    def to_xml(self, root: et.Element, tag: str) -> et.Element:
        elem = et.SubElement(root, tag, {"format": self.formatting.value})
        et.SubElement(elem, "text").text = cdata_str(self.text)
        for fl in self.bfile:
            elem.append(fl.to_xml())

# ----------------------------------------------------------------------------------------

class Dataset():

    def __init__(self, status: Status, name: str, ctype: str, dist: Distribution, 
                minimum: float,  maximum: float, decimals: int) -> None:
        self.status = status
        self.name = name
        self.type = ctype
        self.distribution = dist
        self.minimum = minimum
        self.maximum =  maximum
        self.decimals = decimals
        self.items: Dict[str, float] = {}

    @classmethod
    def from_xml(cls, root: et.Element) -> "Dataset":
        data = {x.tag: x for x in root}
        status = Status.get(data["status"][0].text)
        name = data["name"][0].text
        ctype = data["type"].text
        distribution = Distribution.get(data["distribution"][0].text)
        minimum = data["minimum"][0].text
        maximum = data["maximum"][0].text
        decimals = data["decimals"][0].text
        qst = cls(status, name, ctype, distribution, minimum, maximum, decimals)
        for i in data["dataset_items"]:
            _tmp = {v.tag: v for v in i}
            qst.items[_tmp["number"].text] = float(_tmp["value"].text)
        return qst

    def to_xml(self) -> et.Element:
        dataset_definition = et.Element("dataset_definition")
        status = et.SubElement(dataset_definition, "status")
        et.SubElement(status, "text").text = self.status.value
        name = et.SubElement(dataset_definition, "name")
        et.SubElement(name, "text").text = self.name
        et.SubElement(dataset_definition, "type").text = self.type
        distribution = et.SubElement(dataset_definition, "distribution")
        et.SubElement(distribution, "text").text = self.distribution.value
        minimum = et.SubElement(dataset_definition, "minimum")
        et.SubElement(minimum, "text").text= self.minimum
        maximum = et.SubElement(dataset_definition, "maximum")
        et.SubElement(maximum, "text").text= self.maximum
        decimals = et.SubElement(dataset_definition, "decimals")
        et.SubElement(decimals, "text").text= self.decimals
        et.SubElement(dataset_definition, "itemcount").text = str(len(self.items)) # TODO ?
        dataset_items = et.SubElement(dataset_definition, "dataset_items")
        for num, item in self.items.items():
            dataset_item = et.SubElement(dataset_items, "dataset_item")
            et.SubElement(dataset_item, "number").text = num
            et.SubElement(dataset_item, "value").text = str(item)
        et.SubElement(dataset_definition, "number_of_items").text = str(len(self.items)) # TODO ?
        return dataset_definition

# ----------------------------------------------------------------------------------------

class Tags(list):

    def append(self, __object: str) -> None:
        if isinstance(__object, str):
            super().append(__object)

    @classmethod
    def from_xml(cls, root: et.Element) -> "Tags":
        tags = cls()
        if root is None:
            return None
        for x in root:
            tags.append(x[0].text)
        return tags

    def to_xml(self) -> et.Element:
        tags = et.Element("tags")
        for item in self.__iter__():
            tag = et.SubElement(tags, "tag")
            et.SubElement(tag, "text").text = item
        return tags

# ----------------------------------------------------------------------------------------

class Hint():

    def __init__(self, formatting: Format, text: str, show_correct: bool, 
                clear_wrong: bool, state_incorrect: bool=False) -> None:
        self.formatting = formatting
        self.text = text
        self.show_correct = show_correct
        self.clear_wrong = clear_wrong
        self.state_incorrect = state_incorrect

    @classmethod
    def from_xml(cls, root: et.Element) -> "Hint":
        data = {x.tag: x for x in root}
        formatting = Format.get(root.get("format"))
        text = data["text"].text
        state_incorrect = "options" in data
        show_correct = "shownumcorrect" in data
        clear_wrong = "clearwrong" in data
        return cls(formatting, text, show_correct, clear_wrong, state_incorrect)

    def to_xml(self) -> et.Element:
        hint = et.Element("hint", {"format": self.formatting.value})
        et.SubElement(hint, "text").text = cdata_str(self.text)
        if self.show_correct:
            et.SubElement(hint, "shownumcorrect")
        if self.state_incorrect:
            et.SubElement(hint, "options").text = "1"
        if self.clear_wrong:
            et.SubElement(hint, "clearwrong")
        return hint

# ----------------------------------------------------------------------------------------

class CombinedFeedback():
    """
    Class tp wrap combined feeback variables.
    """

    def __init__(self, correct: FText, incomplete: FText, incorrect: FText, show_num: bool) -> None:
        self.correct = correct
        self.incomplete = incomplete
        self.incorrect = incorrect
        self.show_num = show_num

    @classmethod
    def from_xml(cls, root: et.Element) -> "CombinedFeedback":
        data = {x.tag: x for x in root}
        correct = FText.from_xml(data["correctfeedback"])
        incomplete = FText.from_xml(data["partiallycorrectfeedback"])
        incorrect = FText.from_xml(data["incorrectfeedback"])
        show_num = True if "shownumcorrect" in data else False
        return cls(correct, incomplete, incorrect, show_num)

    def to_xml(self, root: et.Element) -> None:
        self.correct.to_xml(root, "correctfeedback")
        self.incomplete.to_xml(root, "partiallycorrectfeedback")
        self.incorrect.to_xml(root, "incorrectfeedback")
        if self.show_num:
            et.SubElement(root, "shownumcorrect")

# ----------------------------------------------------------------------------------------

class DragItem():
    """
    Abstract class representing any drag item.
    """

    def __init__(self, number: int, text: str, unlimited: bool=False, group: int=None, 
                 no_of_drags: str=None, image: B64File=None) -> None:
        if group and no_of_drags:
            return ValueError("Both group and number of drags can\'t be provided to a single obj.")
        self.number = number
        self.text = text
        self.unlimited = unlimited
        self.group = group
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

class DropZone():
    """
    This class represents DropZone for Questions like QDragAndDropImage.
    """

    def __init__(self, shape: ShapeType, x: int, y: int, points: str, text: str, 
                choice: int, number: int) -> None:
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
        if "coords" in data and "shape" in data:
            shape = ShapeType.get(data["shape"].text)
            coords = data["coords"].text.split(";", 1)
            x, y = coords[0].split(",")
            points = coords[1]
        elif "xleft" in data and "ytop" in data:
            x = data["xleft"].text
            y = data["ytop"].text
            points = shape = None
        else:
            raise AttributeError("One or more coordenates are missing for the DropZone")
        choice = data["choice"].text
        number = data["no"].text
        text = get_txt(data, "text")
        return cls(shape, x, y, points, text, choice, number)

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