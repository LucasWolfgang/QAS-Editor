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
import base64
import logging
import xml.etree.ElementTree as et
from urllib import request
from typing import TYPE_CHECKING

from .enums import Format, Status, Distribution
from .utils import Serializable
if TYPE_CHECKING:
    from typing import List
LOG = logging.getLogger(__name__)


class B64File(Serializable):
    """Internal representation for files that uses Base64 encoding.
    """

    def __init__(self, name: str, path: str = None, bfile: str = None) -> None:
        super().__init__()
        self.name = name
        self.path = path
        if bfile is None:
            try:
                with request.urlopen(self.path) as ifile:
                    self.bfile = str(base64.b64encode(ifile.read()), "utf-8")
            except ValueError:
                with open(self.path, "rb") as ifile:
                    self.bfile = str(base64.b64encode(ifile.read()), "utf-8")
        self.bfile = bfile

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        return cls(root.get("name"), root.get("path"), root.text)

    def to_xml(self, strict: bool) -> et.Element:
        bfile = et.Element("file", {"name": self.name, "encoding": "base64"})
        if self.path:
            bfile.set("path", self.path)
        bfile.text = self.bfile
        return bfile


class SelectOption(Serializable):
    """Internal representation
    """

    def __init__(self, text: str, group: int) -> None:
        super().__init__()
        self.text = text
        self.group = group

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags["text"] = (str, "text")
        tags["group"] = (str, "group")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, strict: bool) -> et.Element:
        select_option = et.Element("selectoption")
        text = et.Element("text")
        text.text = self.text
        select_option.append(text)
        group = et.Element("group")
        group.text = str(self.group)
        select_option.append(group)
        return select_option


class Subquestion(Serializable):
    """_summary_
    """

    def __init__(self, formatting: Format, text: str, answer: str):
        super().__init__()
        self.text = text
        self.answer = answer
        self.formatting = formatting

    @classmethod
    def from_json(cls, data: dict):
        data["formatting"] = Format(data["formatting"])
        return cls(**data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        attrs["format"] = (Format, "formatting")
        tags["text"] = (str, "text")
        tags["answer"] = (str, "answer")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, strict: bool) -> et.Element:
        subquestion = et.Element("subquestion",
                                 {"format": self.formatting.value})
        text = et.Element("text")
        text.text = self.text
        subquestion.append(text)
        answer = et.Element("answer")
        subquestion.append(answer)
        text = et.Element("text")
        text.text = self.answer
        answer.append(text)
        return subquestion


class Unit(Serializable):
    """A
    """

    def __init__(self, unit_name: str, multiplier: float) -> None:
        super().__init__()
        self.unit_name = unit_name
        self.multiplier = multiplier

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "Unit":
        tags["unit_name"] = (str, "unit_name")
        tags["multiplier"] = (float, "multiplier")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, strict: bool) -> et.Element:
        unit = et.Element("unit")
        et.SubElement(unit, "unit_name").text = self.unit_name
        et.SubElement(unit, "multiplier").text = self.multiplier
        return unit


class FText(Serializable):
    """A
    """

    def __init__(self, name: str, text="", formatting: Format = None,
                 bfile: List[B64File] = None):
        super().__init__()
        self.name = name
        self.text = text
        self.formatting = Format.AUTO if formatting is None else formatting
        self.bfile = bfile if bfile else []

    @classmethod
    def from_json(cls, data: dict):
        data["formatting"] = Format(data["formatting"])
        for index in range(len(data["bfile"])):
            data["bfile"][index] = B64File.from_json(data["bfile"][index])
        return cls(**data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        tags[True] = "name"
        tags["text"] = (str, "text")
        tags["file"] = (B64File.from_xml, "bfile", True)
        attrs["format"] = (Format, "formatting")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, strict: bool = False) -> None:
        elem = et.Element(self.name, {"format": self.formatting.value})
        txt = et.SubElement(elem, "text")
        txt.text = self.text
        for bfile in self.bfile:
            elem.append(bfile.to_xml(strict))
        return elem


class DatasetItems(Serializable):
    """A
    """

    def __init__(self, items: dict = None) -> None:
        super().__init__()
        self.__items = {} if items is None else items

    def __len__(self):
        return self.__items.__len__()

    def __iter__(self):
        return self.__items.__iter__()

    @classmethod
    def from_json(cls, data: dict) -> "Serializable":
        data["items"] = {}
        for key in data["_DatasetItems__items"]:
            data["items"][int(key)] = data["_DatasetItems__items"][key]
        data.pop("_DatasetItems__items")
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        data = {}
        for item in root:
            number = int(item.find("number").text)
            value = float(item.find("value").text)
            data[number] = value
        return cls(data)

    def to_xml(self, strict: bool) -> et.Element:
        dataset_items = et.Element("dataset_items")
        for key, val in self.__items.items():
            item = et.Element("dataset_item")
            number = et.Element("number")
            number.text = key
            item.append(number)
            value = et.Element("value")
            value.text = val
            item.append(value)
            dataset_items.append(item)
        return dataset_items


class Dataset(Serializable):
    """A
    """

    def __init__(self, status: Status, name: str, ctype: str,
                 distribution: Distribution, minimum: float, maximum: float,
                 decimals: int, items: DatasetItems = None) -> None:
        super().__init__()
        self.status = status
        self.name = name
        self.ctype = ctype
        self.distribution = distribution
        self.minimum = minimum
        self.maximum = maximum
        self.decimals = decimals
        self.items = items if items else DatasetItems()

    @classmethod
    def from_json(cls, data: dict) -> "Dataset":
        data["status"] = Status(data["status"])
        data["distribution"] = Distribution(data["distribution"])
        data["items"] = DatasetItems.from_json(data["items"])
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
        tags["dataset_items"] = (DatasetItems.from_xml, "items")
        return super().from_xml(root, tags, attrs)

    @staticmethod
    def from_xml_list(root: et.Element, *_) -> List["Dataset"]:
        """A
        """
        return [Dataset.from_xml(obj, {}, {}) for obj in root]

    def to_xml(self, strict: bool) -> et.Element:
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
        et.SubElement(dataset_def, "itemcount").text = len(self.items)
        dataset_def.append(self.items.to_xml(strict))
        et.SubElement(dataset_def, "number_of_items").text = len(self.items)
        return dataset_def


class Tags(Serializable):
    """A
    """
    def __init__(self, tags: List[str] = None):
        self.__tags = tags if tags is not None else []

    def __iter__(self):
        return self.__tags.__iter__()

    def append(self, __obj: str) -> None:
        """_summary_

        Args:
            __object (str): _description_
        """
        if isinstance(__obj, str) and __obj not in self.__tags:
            self.__tags = __obj

    def extend(self, __obj: list):
        self.__tags.extend(__obj)

    def index(self, __obj: str):
        return self.__tags.index(__obj)

    def remove(self, __obj):
        return self.__tags.remove(__obj)

    @classmethod
    def from_json(cls, data: dict) -> "Serializable":
        data["tags"] = data.pop("_Tags__tags")
        return super().from_json(data)

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "Tags":
        tags["tag"] = (str, "tags", True)
        return super().from_xml(root, tags, attrs)

    def to_xml(self, strict: bool) -> et.Element:
        tags = et.Element("tags")
        for item in self.__iter__():
            _tag = et.SubElement(tags, "tag")
            et.SubElement(_tag, "text").text = item
        return tags


class Hint(Serializable):
    """Represents a hint to be displayed when a wrong answer is provided
    to a "multiple tries" question. The hints are give in the listed order.
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
        tags["options"] = (bool, "state_incorrect")
        tags["shownumcorrect"] = (bool, "show_correct")
        tags["clearwrong"] = (bool, "clear_wrong")
        attrs["format"] = (Format, "formatting")
        return super().from_xml(root, tags, attrs)

    def to_xml(self, strict: bool) -> et.Element:
        hint = et.Element("hint", {"format": self.formatting.value})
        txt = et.SubElement(hint, "text")
        txt.text = self.text
        if self.show_correct:
            et.SubElement(hint, "shownumcorrect")
        if self.state_incorrect:
            et.SubElement(hint, "options")
        if self.clear_wrong:
            et.SubElement(hint, "clearwrong")
        return hint
