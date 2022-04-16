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
from typing import TYPE_CHECKING
import copy
import logging

LOG = logging.getLogger(__name__)
if TYPE_CHECKING:
    from xml.etree import ElementTree as et


def cdata_str(text: str):
    """_summary_

    Args:
        text (str): _description_

    Returns:
        _type_: _description_
    """
    return f"<![CDATA[{text}]]>" if text else ""


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


class Serializable:
    """An abstract class to be used as base for all serializable classes
    """

    @staticmethod
    def __itercmp(__a, __b):
        if not isinstance(__b, __a.__class__):
            return False
        if hasattr(__a, "compare"):
            __a.compare(__b)
        elif isinstance(__a, list):
            if len(__a) != len(__b):
                return False
            tmp = copy.copy(__b)
            for ita in __a:
                for idx, itb in enumerate(tmp):
                    if Serializable.__itercmp(ita, itb):
                        break
                else:
                    return False
                tmp.pop(idx)
        elif isinstance(__a, dict):
            for key, value in __a.items():
                if not Serializable.__itercmp(value, __b.get(key)):
                    return False
        elif __a != __b:
            return False
        return True

    def compare(self, __o: object) -> bool:
        if not isinstance(__o, self.__class__):
            return False
        for key, value in self.__dict__.items():
            if key in ("_Question__parent", "_Quiz__parent"):
                continue
            if not Serializable.__itercmp(value, __o.__dict__.get(key)):
                raise ValueError(f"Items differs:\n\t{value}\n\t{__o.__dict__[key]}")
        return True

    @classmethod
    def from_json(cls, data: dict) -> "Serializable":
        """_summary_

        Returns:
            Serializable: _description_
        """
        raise NotImplementedError("JSON not implemented")

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):  # pylint: disable=R0912
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
                a_list = len(tags[obj.tag]) == 3
                tmp = obj.text.strip() if obj.text else None
                if not tmp:
                    text = obj.find("text")
                    if text is not None:
                        tmp = text.text
                if cast_type == bool:
                    tmp = True if not tmp else tmp.lower() in ["true", "1", "t"]
                elif not tmp:
                    continue
                elif isinstance(cast_type, type):
                    tmp = cast_type(tmp)
                else:   # Call back to the from_xml defined for that class
                    tmp = cast_type(obj, {}, {})
                if a_list:
                    if name not in results:
                        results[name] = []
                    results[name].append(tmp)
                else:
                    results[name] = tmp
        for key in tags:
            cast_type, name, *_ = tags[key]
            if name in results:
                continue
            if cast_type == bool: # Some tags act like False when missing
                results[name] = False
            elif isinstance(key, type):
                tmp = {}
                for k in cast_type:
                    tmp[k] = results.pop(k)
                results[name] = key(**tmp)
            else:   # Otherwise, set to None to show that the tag is missing
                results[name] = None
        if attrs:
            for key in attrs:
                cast_type, name = attrs[key]
                results[name] = cast_type(root.get(key)) if key in root.attrib else None
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
            Moodle uses tags, like the ones in CombinedFeedback, that can or not
            be valid, we end-up in this mess.
        """
        raise NotImplementedError("XML not implemented")

# ------------------------------------------------------------------------------
