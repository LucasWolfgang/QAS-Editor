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

from enum import Enum
from types import DynamicClassAttribute


class EnhancedEnum(Enum):
    """
    """
    def __new__(cls, *values):
        obj = object.__new__(cls)
        obj._value_ = values[0]
        obj._comment_ = values[-1]
        for other_value in values[1:-1]:
            cls._value2member_map_[other_value] = obj
        obj._all_values = values
        return obj

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self._name_}: %s>" % (
                ', '.join([repr(v) for v in self._all_values]))

    @DynamicClassAttribute
    def comment(self):
        return self._comment_


class ClozeFormat(EnhancedEnum):
    """Enumerates Cloze formats
    """
    SA = "SHORTANSWER", "MW", "SA", "Short, Case Insensitive" 
    SAC = "SHORTANSWER_C", "MWC", "SAC", "Short, Case Sensitive"
    NUM = "NUMERICAL", "NM", "Numerical"
    MC = "MULTICHOICE", "MC", "Multichoice, dropdown"
    MVC = "MULTICHOICE_V", "MVC", "Multichoice, vertical column"
    MCH = "MULTICHOICE_H", "MCH", "Multichoice, horizontal row"
    MR = "MULTIRESPONSE", "MR", "Multichoice, vertical row"
    MRH = "MULTIRESPONSE_H", "MRH", "Multichoice, horizontal row"


class Direction(EnhancedEnum):
    """Enumerates the four directions
    """
    UP = 1, "Up"
    DOWN = 2, "Down"
    RIGHT = 3, "Right"
    LEFT = 4, "Left"


class Distribution(EnhancedEnum):
    """Enumerates dataset distribution types.
    """
    UNI = "uniform", "Uniform"
    LOG = "loguniform", "Log"


class Format(EnhancedEnum):
    """Enumerates text format types
    """
    HTML = "html", "HTML"
    AUTO = "moodle_auto_format", "Auto"
    PLAIN = "plain_text", "Plain"
    MD = "markdown", "Markdown"


class Grading(EnhancedEnum):
    """Enumerates Grading patterns
    """
    IGNORE = "0", "Ignore"
    RESPONSE = "1", "Fraction (reponse)"
    QUESTION = "2", "Fraction (question)"


class Numbering(EnhancedEnum):
    """Enumerates Numbering patterns
    """
    NONE = "none", "None"
    ALF_LR = "abc", "abc"
    ALF_UR = "ABCD", "ABCD"
    NUMERIC = "123", "123"
    ROM_LR = "iii", "iii"
    ROM_UR = "IIII", "IIII"


class MathType(Enum):
    """Enumerates ways to represent math function in questions' test
    """
    IGNORE = "Ignore"
    MATHML = "MathML"
    LATEX = "LaTex"


class ShapeType(Enum):
    """Enumerates Shape Types
    """
    CIRCLE = "circle"
    RECT = "rectangle"
    POLY = "polygon"


class ShowUnits(EnhancedEnum):
    """Enumerates way to show Units
    """
    TEXT = "0", "Text input"
    MC = "1", "Multiple choice"
    DROP_DOWN = "2", "Drop-down"
    NONE = "3", "Not visible"


class Status(Enum):
    """Enumerates Status for Datasets
    """
    PRV = "private"
    SHR = "shared"


class Synchronise(EnhancedEnum):
    """
    """
    NO_SYNC = "0", "Do not synchronise"
    SYNC = "1", "Synchronise"
    SYNC_NAME = "2", "Synchronise and add as prefix"


class ResponseFormat(EnhancedEnum):
    """Enumerates Response Formats
    """
    HTML = "editor", "HTML"
    WFILE = "editorfilepicker", "HTML w/ file"
    PLAIN = "plain", "Plain text"
    MONO = "monospaced", "Mono spaced"
    ATCH = "noinline", "No inline"


class ToleranceFormat(EnhancedEnum):
    """Enumerates Tolerance Formats
    """
    DEC = "1", "Decimals"
    SIG = "2", "Significant Figures"


class ToleranceType(EnhancedEnum):
    """Enumerates Tolerance Types
    """
    REL = "1", "Relative"
    NOM = "2", "Nominal"
    GEO = "3", "Geometric"
