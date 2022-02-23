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
import base64
import logging
import xml.etree.ElementTree as et
from urllib import request
from typing import TYPE_CHECKING
from .enums import Format, Status, Distribution, Grading, ShowUnits
from .utils import cdata_str, Serializable, xtract
if TYPE_CHECKING:
    from typing import List, Dict
LOG = logging.getLogger(__name__)

# ------------------------------------------------------------------------------

class B64File(Serializable):
    """Internal representation for files that uses Base64 encoding.
    """

    def __init__(self, name: str, path: str = None, bfile: str = None) -> None:
        super().__init__()
        self.path = path
        self.name = name
        if bfile is None:
            try:
                with request.urlopen(self.path) as ifile:
                    self.bfile = str(base64.b64encode(ifile.read()), "utf-8")
            except ValueError:
                with open(self.path, "rb") as ifile:
                    self.bfile = str(base64.b64encode(ifile.read()), "utf-8")
        self.bfile = bfile

    @classmethod
    def from_json(cls, data: dict) -> "B64File":
        return cls(**data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "B64File":
        return cls(root.get("name"), root.get("path"), root.text)

    def to_xml(self, root: et.Element, tag: str, strict: bool = False) -> None:
        bfile = et.Element("file", {"name": self.name, "encoding" : "base64"})
        if self.path:
            bfile.set("path", self.path)
        bfile.text = self.bfile
        root.append(bfile)

# ------------------------------------------------------------------------------

class SelectOption(Serializable):
    """Internal representation
    """

    def __init__(self, text: str, group: int) -> None:
        super().__init__()
        self.text = text
        self.group = group

    @classmethod
    def from_json(cls, data: dict) -> "SelectOption":
        return cls(**data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "SelectOption":
        tags["text"] = (str, "text")
        tags["group"] = (str, "group")
        return cls(**xtract(root, tags, attrs))

    def to_xml(self, root: et.Element, tag: str, strict: bool = False) -> None:
        select_option = et.Element("selectoption")
        text = et.Element("text")
        text.text = self.text
        select_option.append(text)
        group = et.Element("group")
        group.text = str(self.group)
        select_option.append(group)
        root.append(select_option)

# ------------------------------------------------------------------------------

class Subquestion(Serializable):
    """_summary_
    """

    def __init__(self, formatting: Format, text: str, answer: str) -> None:
        super().__init__()
        self.text = text
        self.answer = answer
        self.formatting = formatting

    @classmethod
    def from_json(cls, data: dict) -> "Subquestion":
        data["formatting"] = Format(data["formatting"])
        return cls(**data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "Subquestion":
        tags["format"] = (Format, "formatting")
        tags["text"] = (str, "text")
        tags["answer"] = (str, "answer")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, tag: str, strict: bool = False) -> None:
        subquestion = et.Element("subquestion", {"format": self.formatting.value})
        text = et.Element("text")
        text.text = cdata_str(self.text)
        subquestion.append(text)
        answer = et.Element("answer")
        subquestion.append(answer)
        text = et.Element("text")
        text.text = self.answer
        answer.append(text)
        root.append(subquestion)

# ------------------------------------------------------------------------------

class UnitHandling(Serializable):
    """A
    """

    def __init__(self, grading_type: Grading, penalty: float, show: ShowUnits,
                 left: bool) -> None:
        super().__init__()
        self.grading_type = grading_type
        self.penalty = penalty
        self.show = show
        self.left = left

    @classmethod
    def from_json(cls, data: dict) -> "UnitHandling":
        data["grading_type"] = Grading(data["grading_type"])
        data["show"] = ShowUnits(data["show"])
        return cls(**data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "UnitHandling":
        tags["unitgradingtype"] = (Grading, "grading_type")
        tags["unitpenalty"] = (str, "penalty")
        tags["unitsleft"] = (bool, "left")
        tags["showunits"] = (ShowUnits, "show")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, tag: str, strict: bool = False) -> None:
        unitgradingtype = et.Element("unitgradingtype")
        unitgradingtype.text = self.grading_type.value
        root.append(unitgradingtype)
        unitpenalty = et.Element("unitpenalty")
        unitpenalty.text = str(self.penalty)
        root.append(unitpenalty)
        showunits = et.Element("showunits")
        showunits.text = self.show.value
        root.append(showunits)
        unitsleft = et.Element("unitsleft")
        unitsleft.text = str(self.left)
        root.append(unitsleft)

# ----------------------------------------------------------------------------------------

class Unit(Serializable):
    """A
    """

    def __init__(self, unit_name: str, multiplier: float) -> None:
        super().__init__()
        self.unit_name = unit_name
        self.multiplier = multiplier

    @classmethod
    def from_json(cls, data: dict) -> "Unit":
        return cls(**data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "Unit":
        tags["unit_name"] = (str, "unit_name")
        tags["multiplier"] = (float, "multiplier")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, tag: str, strict: bool = False) -> None:
        unit = et.Element("unit")
        unit_name = et.Element("unit_name")
        unit_name.text = self.unit_name
        unit.append(unit_name)
        multiplier = et.Element("multiplier")
        multiplier.text = str(self.multiplier)
        unit.append(multiplier)
        root.append(unit)

# ------------------------------------------------------------------------------

class FText(Serializable):
    """A
    """

    def __init__(self, text: str, formatting: Format, bfile: List[B64File]) -> None:
        super().__init__()
        self.text = text
        if not isinstance(formatting, Format):
            raise TypeError("Formatting type is not valid")
        self.formatting = formatting
        self.bfile = bfile if bfile else []

    @classmethod
    def from_json(cls, data: dict) -> "FText":
        data["formatting"] = Format(data["formatting"])
        return cls(**data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "FText":
        tags["text"] = (str, "text")
        tags["file"] = (B64File.from_xml, "bfile")
        if attrs is None:
            attrs = {}
        attrs["format"] = (Format, "formatting")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, tag: str, strict: bool = False) -> None:
        elem = et.Element(tag, {"format": self.formatting.value})
        text = et.Element("text")
        text.text = cdata_str(self.text)
        elem.append(text)
        for bfile in self.bfile:
            elem.append(bfile.to_xml())
        root.append(elem)

# ------------------------------------------------------------------------------

class Dataset(Serializable):
    """A
    """

    def __init__(self, status: Status, name: str, ctype: str,
                 distribution: Distribution, minimum: float, maximum: float,
                 decimals: int, items: Dict[str, float] = None) -> None:
        super().__init__()
        self.status = status
        self.name = name
        self.ctype = ctype
        self.distribution = distribution
        self.minimum = minimum
        self.maximum = maximum
        self.decimals = decimals
        self.items = items if items else {}

    @classmethod
    def from_json(cls, data: dict) -> "Dataset":
        data["status"] = Status(data["status"])
        data["distribution"] = Distribution(data["distribution"])
        return cls(**data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "Dataset":
        tags["status"] = (Status, "status")
        tags["name"] = (str, "name")
        tags["type"] = (str, "ctype")
        tags["distribution"] = (Distribution, "distribution")
        tags["minimum"] = (str, "minimum")
        tags["maximum"] = (str, "maximum")
        tags["decimals"] = (str, "decimals")
        tags["dataset_items"] = (DatasetItem.from_xml, "dataset_items")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, tag: str, strict: bool = False) -> None:
        dataset_def = et.Element("dataset_definition")
        status = et.SubElement(dataset_def, "status")
        et.SubElement(status, "text").text = self.status.value
        name = et.SubElement(dataset_def, "name")
        et.SubElement(name, "text").text = self.name
        et.SubElement(dataset_def, "type").text = self.ctype
        distribution = et.SubElement(dataset_def, "distribution")
        et.SubElement(distribution, "text").text = self.distribution.value
        minimum = et.SubElement(dataset_def, "minimum")
        et.SubElement(minimum, "text").text = self.minimum
        maximum = et.SubElement(dataset_def, "maximum")
        et.SubElement(maximum, "text").text = self.maximum
        decimals = et.SubElement(dataset_def, "decimals")
        et.SubElement(decimals, "text").text = self.decimals
        et.SubElement(dataset_def, "itemcount").text = str(len(self.items))
        dataset_items = et.SubElement(dataset_def, "dataset_items")
        for num, item in self.items.items():
            dataset_item = et.SubElement(dataset_items, "dataset_item")
            et.SubElement(dataset_item, "number").text = num
            et.SubElement(dataset_item, "value").text = str(item)
        et.SubElement(dataset_def, "number_of_items").text = str(len(self.items))
        root.append(dataset_def)

# ------------------------------------------------------------------------------

class DatasetItem(Serializable):
    """A
    """

    def __init__(self, number: int, value: float) -> None:
        super().__init__()
        self.number = number
        self.value = value

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "DatasetItem":
        tags["number"] = (int, "number")
        tags["value"] = (float, "value")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, tag: str, strict: bool = False) -> None:
        dataset_item = et.Element("dataset_item")
        number = et.Element("number")
        number.text = str(self.number)
        dataset_item.append(number)
        value = et.Element("value")
        value.text = str(self.value)
        dataset_item.append(value)
        root.append(dataset_item)

# ------------------------------------------------------------------------------

class Tags(Serializable):
    """A
    """
    def __init__(self, tags: list):
        self.__tags = tags

    def __iter__(self):
        return self.__tags.__iter__()

    def append(self, __object: str) -> None:
        """_summary_

        Args:
            __object (str): _description_
        """
        if isinstance(__object, str):
            self.__tags = __object

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "Tags":
        tags["tag"] = (str, "tags")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, tag: str, strict: bool = False) -> None:
        tags = et.Element("tags")
        for item in self.__iter__():
            _tag = et.SubElement(tags, "tag")
            et.SubElement(_tag, "text").text = item
        root.append(tags)

# ------------------------------------------------------------------------------

class Hint(Serializable):
    """A
    """

    def __init__(self, formatting: Format, text: str, show_correct: bool,
                 clear_wrong: bool, state_incorrect: bool = False) -> None:
        self.formatting = formatting
        self.text = text
        self.show_correct = show_correct
        self.clear_wrong = clear_wrong
        self.state_incorrect = state_incorrect

    @classmethod
    def from_json(cls, data: dict) -> "Hint":
        data["formatting"] = Format(data["formatting"])
        return cls(**data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "Hint":
        tags["text"] = (str, "text")
        tags["options"] = (str, "state_incorrect")
        tags["shownumcorrect"] = (str, "show_correct")
        tags["clearwrong"] = (str, "clear_wrong")
        if attrs is None:
            attrs = {}
        attrs["format"] = (Format, "formatting")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, tag: str, strict: bool = False) -> None:
        hint = et.Element("hint", {"format": self.formatting.value})
        et.SubElement(hint, "text").text = cdata_str(self.text)
        if self.show_correct:
            et.SubElement(hint, "shownumcorrect")
        if self.state_incorrect:
            et.SubElement(hint, "options").text = "1"
        if self.clear_wrong:
            et.SubElement(hint, "clearwrong")
        root.append(hint)

# ----------------------------------------------------------------------------------------

class CombinedFeedback(Serializable):
    """
    Class tp wrap combined feeback variables.
    """

    def __init__(self, correct: FText, incomplete: FText, incorrect: FText,
                 show_num: bool = False) -> None:
        self.correct = correct
        self.incomplete = incomplete
        self.incorrect = incorrect
        self.show_num = show_num

    @classmethod
    def from_json(cls, data: dict) -> "CombinedFeedback":
        data["correct"] = FText.from_json(data["correct"])
        data["incomplete"] = FText.from_json(data["incomplete"])
        data["incorrect"] = FText.from_json(data["incorrect"])
        return cls(**data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "CombinedFeedback":
        tags["correctfeedback"] = (FText.from_xml, "correct")
        tags["partiallycorrectfeedback"] = (FText.from_xml, "incorrect")
        tags["incorrectfeedback"] = (FText.from_xml, "incorrect")
        tags["shownumcorrect"] = (bool, "show_num")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, tag: str, strict: bool = False) -> None:
        self.correct.to_xml(root, "correctfeedback")
        self.incomplete.to_xml(root, "partiallycorrectfeedback")
        self.incorrect.to_xml(root, "incorrectfeedback")
        if self.show_num:
            et.SubElement(root, "shownumcorrect")

# ------------------------------------------------------------------------------

class MultipleTries(Serializable):
    """A
    """

    def __init__(self, penalty: float = 0.5, hints: List[Hint] = None) -> None:
        self.penalty = penalty
        self.hints = hints if hints is not None else []

    @classmethod
    def from_json(cls, data: dict) -> "MultipleTries":
        for i in range(len(data["hints"])):
            data["hints"][i] = Hint.from_json(data["hints"][i])
        return cls(**data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "MultipleTries":
        tags["hint"] = (Hint.from_xml, "hints")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, root: et.Element, tag: str, strict: bool = False) -> None:
        for hint in self.hints:
            root.append(hint.to_xml())
        et.SubElement(root, "penalty").text = str(self.penalty)

# ------------------------------------------------------------------------------
