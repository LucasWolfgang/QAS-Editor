import os
import base64
from typing import List, Dict
from xml.etree import ElementTree as et
from urllib.request import urlopen
from qas_enums import Format, Status, Distribution, Grading, ShowUnits

def get_txt(data: dict, key: str, default=None) -> str:
    if key not in data:
        return default
    return data[key].text

def cdata_str(text: str):
    return f"<![CDATA[{text if text else ''}]]>"

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
        text = cdata_str(self.text) if self.formatting == Format.HTML else self.text
        et.SubElement(subquestion, "text").text = text
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
        show = ShowUnits.get(data.get("showunits"))
        left = True if data.get("unitsleft") else False
        return cls(grading_type, penalty, show, left)

    def to_xml(self, root: et.Element) -> None:
        et.SubElement(root, "unitgradingtype").text = self.grading_type.value
        et.SubElement(root, "unitpenalty").text = str(self.penalty)
        et.SubElement(root, "showunits").text = self.show.value
        et.SubElement(root, "unitsleft").text = self.left

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
        self.formatting = formatting

    @classmethod
    def from_xml(cls, root: et.Element) -> "FText":
        if not root:
            return None
        formatting = Format.get(root.get("format"))
        text = root[0].text
        return cls(text, formatting)

    def to_xml(self, root: et.Element, tag: str) -> et.Element:
        elem = et.SubElement(root, tag, {"format": self.formatting.value})
        text = cdata_str(self.text) if self.formatting == Format.HTML else self.text
        et.SubElement(elem, "text").text = text

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
        self.items: List[float] = []

    @classmethod
    def from_xml(cls, root: et.Element) -> "Dataset":
        data = {x.tag: x for x in root}
        status = Status.get(data["status"].text)
        name = data["name"].text
        ctype = data["type"].text
        distribution = Distribution.get(data["distribution"].text)
        minimum = data["minimum"].text
        maximum = data["maximum"].text
        decimals = data["decimals"].text
        qst = cls(status, name, ctype, distribution, minimum, maximum, decimals)
        for i in data["dataset_items"]:
            for v in i:
                if v.tag == "value":
                    qst.items.append(v.text)
                    break
        return qst

    def to_xml(self) -> et.Element:
        dataset_definition = et.Element("dataset_definition")
        et.SubElement(dataset_definition, "status").text = self.status
        et.SubElement(dataset_definition, "name").text = self.name
        et.SubElement(dataset_definition, "type").text = self.type
        et.SubElement(dataset_definition, "distribution").text = self.distribution
        et.SubElement(dataset_definition, "minimum").text = self.minimum
        et.SubElement(dataset_definition, "maximum").text = self.maximum
        et.SubElement(dataset_definition, "decimals").text = self.decimals
        et.SubElement(dataset_definition, "itemcount").text = len(self.items) # TODO ?
        dataset_items = et.SubElement(dataset_definition, "dataset_items")
        for num, item in enumerate(self.items):
            dataset_item = et.SubElement(dataset_definition, "dataset_item")
            et.SubElement(dataset_item, "number").text = num
            et.SubElement(dataset_item, "value").text = item
            dataset_items.append(dataset_item)
        et.SubElement(dataset_definition, "number_of_items").text = len(self.items) # TODO ?
        return dataset_definition

# ----------------------------------------------------------------------------------------

class Tags(list):

    def append(self, __object: str) -> None:
        if isinstance(__object, str):
            super().append(__object)

    @classmethod
    def from_xml(cls, root: et.Element) -> "Tags":
        tags = cls()
        if not root:
            return tags
        for x in root:
            tags.append(x[0].text)
        return tags

    def to_xml(self) -> et.Element:
        tags = et.Element("tags")
        for item in self.__iter__:
            tag = et.SubElement(tags, "tag")
            et.SubElement(tag, "text").text = item

# ----------------------------------------------------------------------------------------

class Hint():

    def __init__(self, formatting: Format, text: str, show_correct: bool, 
                clear_wrong: bool) -> None:
        self.formatting = formatting
        self.text = text
        self.show_correct = show_correct
        self.clear_wrong = clear_wrong

    @classmethod
    def from_xml(cls, root: et.Element) -> "Hint":
        data = {x.tag: x for x in root}
        formatting = Format.get(root.get("format"))
        text = data["text"].text
        show_correct = True if data.get("shownumcorrect") else False
        clear_wrong = True if data.get("clearwrong") else False
        return cls(formatting, text, show_correct, clear_wrong)

    def to_xml(self) -> et.Element:
        hint = et.Element("hint", {"format": self.formatting.value})
        text = cdata_str(self.text) if self.formatting == Format.HTML else self.text
        et.SubElement(hint, "text").text = text
        if self.show_correct:
            et.SubElement(hint, "shownumcorrect")
        if self.clear_wrong:
            et.SubElement(hint, "clearwrong")

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
        show_num = True if data.get("shownumcorrect", None) else False
        return cls(correct, incomplete, incorrect, show_num)

    def to_xml(self, root: et.Element) -> et.Element:
        self.correct.to_xml(root, "correctfeedback")
        self.incomplete.to_xml(root, "partiallycorrectfeedback")
        self.incorrect.to_xml(root, "incorrectfeedback")
        if self.show_num:
            et.SubElement(root, "shownumcorrect")

    def to_json(self) -> dict:
        pass

# ----------------------------------------------------------------------------------------

class DragItem():
    """
    Abstract class representing any drag item.
    """

    def __init__(self, number: int, text: str, unlimited: bool=False, group: int=None, 
                 no_of_drags: str=None, image_path: str=None, image: str=None) -> None:
        if self.group and self.no_of_drags:
            return ValueError("Both group and number of drags can\'t be provided to a single obj.")
        self.number = number
        self.text = text
        self.unlimited = unlimited
        self.group = group
        self.no_of_drags = no_of_drags
        self.image_path = image_path
        if image:
            self.image = image
        else:
            try:
                with urlopen(image_path) as response:
                    self.image = str(base64.b64encode(response.read()), "utf-8")
            except Exception:
                with open(image_path, "rb") as f:
                    self.image = str(base64.b64encode(f.read()), "utf-8")

    @classmethod
    def from_xml(cls, root: et.Element) -> "DragItem":
        data = {x.tag: x for x in root}
        number = data["no"].text
        text = data["text"].text
        unlimited = True if data.get("infinite", None) else False
        group = data.get("draggroup").text if data.get("draggroup") else None
        no_of_drags = data.get("draggroup").text if data.get("draggroup") else None
        file_path = data.get("file").get("path", "") + data.get("file").get("name")
        image = data.get("file").text
        return cls(number, text, unlimited, group, no_of_drags, file_path, image)

    def to_xml(self) -> et.Element:
        dragitem = et.Element("drag")
        et.SubElement(dragitem, "no").text = str(self.number)
        et.SubElement(dragitem, "text").text = self.text
        if self.unlimited:
            et.SubElement(dragitem, "infinite")
        if self.group:
            et.SubElement(dragitem, "draggroup").text = str(self.group)
        if self.no_of_drags:
            et.SubElement(dragitem, "noofdrags").text = str(self.no_of_drags)
        if self.file_path:
            et.SubElement(dragitem, "file", {
                    "name": os.path.basename(self.image_path), 
                    "encoding": "base64"})
        return dragitem

# ----------------------------------------------------------------------------------------

class DropZone():
    """
    This class represents DropZone for Questions like DragAndDropOntoImageQuestion.
    """

    def __init__(self, x: int, y: int, text: str, choice: int, number: int):
        """[summary]

        Args:
            x (int): Coordinate X from top left corner.
            y (int): Coordinate Y from top left corner.
            text (str, optional): text contained in the drop zone. Defaults to None.
            choice ([type], optional): [description]. Defaults to None.
            number ([type], optional): [description]. Defaults to None.
        """
        self.x = x
        self.y = y
        self.text = text
        self.choice = choice
        self.number = number

    @classmethod
    def from_xml(cls, root: et.Element) -> "DropZone":
        data = {x.tag: x for x in root}
        x = data["xleft"]
        y = data["ytop"]
        text = data["text"]
        choice = data["choice"]
        number = data["no"]
        return cls(x, y, text, choice, number)

    def to_xml(self) -> et.Element:
        dropzone = et.Element("drop")
        et.SubElement(dropzone, "text").text = self.text
        et.SubElement(dropzone, "no").text = str(self.number)
        et.SubElement(dropzone, "choice").text = str(self.choice)
        et.SubElement(dropzone, "xleft").text = str(self.x)
        et.SubElement(dropzone, "ytop").text = str(self.y)
        return dropzone

# ----------------------------------------------------------------------------------------

def build_image_tag(root: et.Element, file_path: str) -> None:
    """[summary]

    Args:
        root (et.Element): [description]
        name (str): [description]
        file_name (str): [description]
    """
    file = et.SubElement(root, "file", {"name": os.path.basename(file_path), "encoding": "base64"})
    try:
        file.text = urlopen(file_path).read()
    except Exception:
        with open(file_path, "rb") as f:
            file.text = str(base64.b64encode(f.read()), "utf-8")