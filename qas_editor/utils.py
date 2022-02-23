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
import logging
LOG = logging.getLogger(__name__)
if TYPE_CHECKING:
    from xml.etree import ElementTree as et

def extract(data: dict, key: str, res: dict, name: str, cast_type) -> None:
    if key in data:
        if cast_type == str:
            res[name] = data[key].text
        elif cast_type in [int, float]:
            res[name] = data[key].text
            if res[name]: res[name] = cast_type(res[name])
        elif cast_type == bool:
            if data[key].text:
                res[name] = data[key].text.lower() in ["true", "1", "t"]
            else:
                res[name] = True
        else: 
            res[name] = cast_type(data[key])
    elif cast_type == bool:
        res[name] = False
    else:
        res[name] = None

# ------------------------------------------------------------------------------

def xtract(root: et.Element, tag_cast: dict, attr_cast: dict) -> None:
    results = {}
    for obj in root:
        key = obj.tag
        if key in tag_cast:
            cast_type, name = tag_cast[key]
            tmp = obj.text
            if cast_type == str: continue
            elif cast_type in [int, float]:
                if results[name]: results[name] = cast_type(tmp)
            elif cast_type == bool:
                tmp = True if not tmp else tmp.lower() in ["true", "1", "t"]
            else: 
                tmp = cast_type(obj)
            if name not in results: results[name] = tmp
            elif isinstance(results[name], list): results[name].append(tmp)
            else: results[name] = [results[name], tmp]
        elif cast_type == bool:
            results[name] = False
        else:
            results[name] = None
    if attr_cast:
        for key in attr_cast:
            results[name] = attr_cast[key](root.get(key))
    return results

# ------------------------------------------------------------------------------

def cdata_str(text: str):
    return f"<![CDATA[{text}]]>" if text else ""

# ------------------------------------------------------------------------------

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

# ------------------------------------------------------------------------------

class Serializable:
    """An abstract class to be used as base for all serializable classes
    """

    def __eq__(self, __o: object) -> bool:
        if not __debug__:
            return self.__dict__ == __o.__dict__
        for item in self.__dict__:
            if self.__dict__[item] != __o.__dict__.get(item):
                msg = (f"{self.__class__.__name__} not equal. "
                       f"{item} ({type(self.__dict__[item])}) differs. ")
                if type(self.__dict__[item]) in (int, float, str):
                    msg += f"Values:\n\t{self.__dict__[item]}\n\t{__o.__dict__[item]}"
                LOG.debug(msg)
                return False
        else:  
            return True

    @classmethod
    def from_cloze(cls, regex) -> "Serializable":
        """_summary_

        Args:
            regex (_type_): _description_

        Returns:
            Serializable: _description_
        """        
        pass

    @classmethod
    def from_json(cls, data: dict) -> "Serializable":
        """_summary_

        Returns:
            Serializable: _description_
        """        
        pass

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict) -> "Serializable":
        """Create a new class using XML data

        Returns:
            Serializable: _description_
        """
        if root is None:
            return None  
        results = {}
        for obj in root:
            if obj.tag in tags:
                cast_type, name = tags[obj.tag]
                tmp = obj.text
                if not tmp:
                    text = obj.find("text")
                    tmp = text.text if text else tmp
                if cast_type == str: continue
                elif cast_type in [int, float]:
                    tmp: results[name] = cast_type(tmp)
                elif cast_type == bool:
                    tmp = True if not tmp else tmp.lower() in ["true", "1", "t"]
                else: 
                    tmp = cast_type(obj, {}, None)
                if name not in results: results[name] = tmp
                elif isinstance(results[name], list): results[name].append(tmp)
                else: results[name] = [results[name], tmp]
            elif cast_type == bool:
                results[name] = False
            else:
                results[name] = None
        if attrs:
            for key in attrs:
                results[name] = attrs[key](root.get(key))
        return results

    def to_cloze(self):
        pass

    def to_xml(self, root: et.Element, tag: str, strict: bool) -> None:
        """_summary_

        Args:
            root (Element): _description_
            tag (str): _description_
            strict (bool): _description_
        """                
        root = None

# ------------------------------------------------------------------------------