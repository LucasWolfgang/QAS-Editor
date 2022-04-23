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
import copy
import logging
from xml.etree import ElementTree as et

LOG = logging.getLogger(__name__)


# from PyPDF2.generic import IndirectObject
# def quick_print(data, pp):
#     """This is a temporary function that I am using to test PDF import/export
#     """
#     if isinstance(data, dict):
#         for i in data:
#             print(f"{pp}{i}:")
#             quick_print(data[i], pp+"  ")
#     elif isinstance(data, list):
#         for i in data:
#             quick_print(i, pp+"  ")
#     elif isinstance(data, IndirectObject):
#         quick_print(data.getObject(), pp+"  ")
#     else:
#         print(pp, data)

def serialize_fxml(write, elem, short_empty, pretty, level=0):
    """_summary_

    Args:
        write (_type_): _description_
        elem (_type_): _description_
        short_empty (_type_): _description_
        pretty (_type_): _description_
        level (int, optional): _description_. Defaults to 0.

    Raises:
        ValueError: _description_
        NotImplementedError: _description_
        ParseError: _description_
    """
    tag = elem.tag
    text = elem.text
    if pretty:
        write(level * "  ")
    write(f"<{tag}")
    for key, value in elem.attrib.items():
        value = _escape_attrib_html(value)
        write(f" {key}=\"{value}\"")
    if (isinstance(text, str) and text) or text is not None or \
            len(elem) or not short_empty:
        if len(elem) and pretty:
            write(">\n")
        else:
            write(">")
        write(_escape_cdata(text))
        for child in elem:
            serialize_fxml(write, child, short_empty, pretty, level+1)
        if len(elem) and pretty:
            write(level * "  ")
        write(f"</{tag}>")
    else:
        write(" />")
    if pretty:
        write("\n")
    if elem.tail:
        write(_escape_cdata(elem.tail))


def _escape_cdata(data):
    if data is None:
        return ""
    if isinstance(data, (int, float)):
        return str(data)
    if ("&" in data or "<" in data or ">" in data) and not\
            (str.startswith(data, "<![CDATA[") and str.endswith(data, "]]>")):
        return f"<![CDATA[{data}]]>"
    return data


def _escape_attrib_html(data):
    if data is None:
        return ""
    if isinstance(data, (int, float)):
        return str(data)
    if "&" in data:
        data = data.replace("&", "&amp;")
    if ">" in data:
        data = data.replace(">", "&gt;")
    if "\"" in data:
        data = data.replace("\"", "&quot;")
    return data


class Serializable:
    """An abstract class to be used as base for all serializable classes
    """

    @staticmethod
    def __itercmp(__a, __b, path: list):
        if not isinstance(__b, __a.__class__):
            return False
        if hasattr(__a, "compare"):
            __a.compare(__b, path)
        elif isinstance(__a, list):
            if len(__a) != len(__b):
                return False
            tmp: list = copy.copy(__b)
            for ita in __a:
                path.append(str(ita))
                idx = 0
                for idx, itb in enumerate(tmp):
                    if Serializable.__itercmp(ita, itb, path):
                        break
                else:
                    return False
                tmp.pop(idx)
                path.remove(str(ita))
        elif isinstance(__a, dict):
            for key, value in __a.items():
                path.append(key)
                if not Serializable.__itercmp(value, __b.get(key), path):
                    return False
                path.remove(key)
        elif __a != __b:
            return False
        return True

    def compare(self, __o: object, path: list) -> bool:
        """A
        """
        if not isinstance(__o, self.__class__):
            return False
        for key, value in self.__dict__.items():
            path.append(key)
            if key in ("_Question__parent", "_Quiz__parent"):
                continue
            if not Serializable.__itercmp(value, __o.__dict__.get(key), path):
                raise ValueError(f"Items differs in {'/'.join(path)}:"
                                 f"\n\t{value}\n\t{__o.__dict__[key]}")
            path.remove(key)
        return True

    @classmethod
    def from_gift(cls, header: list, answer: list):
        """_summary_

        Args:
            header (list): _description_
            answer (list): _description_

        Returns:
            QMatching: _description_
        """
        raise NotImplementedError("GIFT not implemented")

    @classmethod
    def from_json(cls, data: dict) -> "Serializable":
        """_summary_

        Returns:
            Serializable: _description_
        """
        raise NotImplementedError("JSON not implemented")

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        """Create a new class using XML data

        Args:
            root (et.Element): _description_
            tags (dict): _description_
            attrs (dict): _description_

        Returns:
            Serializable: _description_
        """
        if root is None:
            return None
        results = {}
        name = tags.pop(True, None) # True is used as a key to ask for the tag
        if name:                    # If it is present, tag is mapped to <name>
            results[name] = root.tag
        for obj in root:
            if obj.tag in tags:
                cast_type, name, *_ = tags[obj.tag]
                if not isinstance(cast_type, type):
                    tmp = cast_type(obj, {}, {})
                else:
                    tmp = obj.text.strip() if obj.text else ""
                    if not tmp:
                        text = obj.find("text")
                        if text is not None:
                            tmp = text.text
                    if cast_type == bool:
                        tmp = tmp.lower() in ["true", "1", "t", ""]
                    elif tmp or cast_type == str:
                        tmp = cast_type(tmp)
                if len(tags[obj.tag]) == 3:
                    if name not in results:
                        results[name] = []
                    results[name].append(tmp)
                else:
                    results[name] = tmp
                    tags.pop(obj.tag)
        for key in tags:
            cast_type, name, *_ = tags[key]
            if cast_type == bool: # Some tags act like False when missing
                results[name] = False
            else:   # Otherwise, set to None to show that the tag is missing
                results[name] = None
        if attrs:
            for key in attrs:
                cast_type, name = attrs[key]
                results[name] = root.get(key, None)
                if results[name] is not None:
                    results[name] = cast_type(results[name])
        return cls(**results)

    def to_xml(self, root: et.Element, strict: bool) -> et.Element:
        """Create a XML representation of the object instance following the
        moodle standard. This function if first implemented as "virtual" in
        the Serializable class, raising an exception if not overriden.

        Args:
            root (et.Element): where the new tags will be added to
            strict (bool): if the tags added should only be the ones correctly
                interpreted by moodle.

        Returns:
            et.Element: The instance root element. In a organized XML, this
            should be always different from the "root" argument, but since
            Moodle uses tags, like the ones in CombinedFeedback, that can or
            not be valid, we end-up in this mess.
        """
        raise NotImplementedError("XML not implemented")


class ParseError(Exception):
    """Exception used when a parsing fails.
    """


class LineBuffer:
    """Helps parsing text files that uses lines (\\n) as part of the standard
    somehow.
    """

    def __init__(self, buffer) -> None:
        self.last = buffer.readline()
        self.__bfr = buffer

    def read(self, inext: bool = False):
        """_summary_

        Args:
            inext (bool, optional): _description_. Defaults to False.

        Raises:
            ParseError: _description_

        Returns:
            _type_: _description_
        """
        if not self.last and inext:
            raise ParseError()
        tmp = self.last
        if inext:
            self.last = self.__bfr.readline()
            while self.last and self.last == "\n":
                self.last = self.__bfr.readline()
        return tmp
