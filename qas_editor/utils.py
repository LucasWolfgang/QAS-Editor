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

import logging
logger = logging.getLogger(__name__)

def extract(data: dict, key: str, res: dict, name: str, cast_type) -> None:
    if key in data:
        if cast_type == str:
            res[name] = data[key].text
        elif cast_type != bool:
            res[name] = data[key].text
            if res[name]: res[name] = cast_type(res[name])
        else:
            if data[key].text:
                res[name] = data[key].text.lower() in ["true", "1", "t"]
            else:
                res[name] = True
    elif cast_type == bool:
        res[name] = False

# ------------------------------------------------------------------------------

def cdata_str(text: str):
    return f"<![CDATA[{text}]]>" if text else ""

# ------------------------------------------------------------------------------

from PyPDF2.generic import IndirectObject
def quick_print(data, pp):
    """This is a temporary function that I am using to test PDF import/export
    """
    if isinstance(data, dict):
        for i in data:
            print(f"{pp}{i}:")
            quick_print(data[i], pp+"  ")
    elif isinstance(data, list):
        for i in data:
            quick_print(i, pp+"  ")
    elif isinstance(data, IndirectObject):
        quick_print(data.getObject(), pp+"  ")
    else:
        print(pp, data)

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
                logger.debug(msg)
                return False
        else:  
            return True

    @classmethod
    def from_cloze(cls, regex) -> "Serializable":
        pass

    @classmethod
    def from_json(cls, *args, **kwargs) -> "Serializable":
        pass

    @classmethod
    def from_xml(cls, *args, **kwargs) -> "Serializable":
        pass

    def to_cloze(self):
        pass

    def to_xml(self):
        pass