import base64
from typing import List, Dict
from xml.etree import ElementTree as et
from urllib.request import urlopen
from .enums import Format, Status, Distribution, Grading, ShowUnits
from .utils import cdata_str, extract

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
        formatting = Format(root.get("format"))
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
        res = {}
        res["grading_type"] = Grading(data["unitgradingtype"].text)
        res["penalty"] = data["unitpenalty"].text
        res["show"] = ShowUnits(data["showunits"].text)        
        extract(data, "unitsleft", res, "left", bool)
        return cls(**res)

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
        if not isinstance(formatting, Format):
            raise TypeError("Formatting type is not valid")
        self.formatting = formatting
        self.bfile: List[B64File] = []

    @classmethod
    def from_xml(cls, root: et.Element) -> "FText":
        if root is None:
            return None
        formatting = Format(root.get("format", "html"))
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
        status = Status(data["status"][0].text)
        name = data["name"][0].text
        ctype = data["type"].text
        distribution = Distribution(data["distribution"][0].text)
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
        formatting = Format(root.get("format"))
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

class MultipleTries():

    def __init__(self, penalty: float=0.5, hints: List[Hint]=None) -> None:
        self.penalty = penalty
        self.hints = hints if hints is not None else []

    @classmethod
    def from_xml(cls, data: dict, root: et.Element) -> "MultipleTries":
        hints = []
        for h in root.findall("hint"):
            hints.append(Hint.from_xml(h))
        return cls(float(data["penalty"].text), hints)

    def to_xml(self, question: et.Element) -> None:
        for h in self.hints:
            question.append(h.to_xml())
        et.SubElement(question, "penalty").text = str(self.penalty)

# ----------------------------------------------------------------------------------------
