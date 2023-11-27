# Question and Answer Sheet Editor <https://github.com/LucasWolfgang/QAS-Editor>
# Copyright (C) 2022  Lucas Wolfgang
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
## Description

"""

from enum import Enum, auto
from types import DynamicClassAttribute


class EnhancedEnum(Enum):
    """An enhanced <code>Enum</code> that included allow multiple values to
    be used, and adds a new comment field.
    """

    def __new__(cls, *values):
        obj = object.__new__(cls)
        obj._value_ = values[0]
        obj._comment_ = values[-1]
        for other_value in values[1:]:
            cls._value2member_map_[other_value] = obj  # pylint: disable=E1101
        obj._all_values = values
        return obj

    def __repr__(self):
        values = ', '.join([repr(v) for v in self._all_values])
        return (f"<{self.__class__.__name__}."         # pylint: disable=E1101
                f"{self._name_}: {values}>")           # pylint: disable=E1101

    @DynamicClassAttribute
    def comment(self):
        """Description/commentary for the given item
        """
        return self._comment_
    
    @DynamicClassAttribute
    def values(self) -> list:
        return self._all_values


class EmbeddedFormat(EnhancedEnum):
    """Enumerates Cloze formats
    """
    MC = "MULTICHOICE", "MC", "MCV", "MULTICHOICE_V", "Multichoice, dropdown"
    MCH = "MULTICHOICE_H", "MCH", "Multichoice, horizontal row"
    MR = "MULTIRESPONSE", "MR", "Multichoice, vertical column"
    MRH = "MULTIRESPONSE_H", "MRH", "Multichoice, horizontal row"
    NUM = "NUMERICAL", "NM", "Numerical"
    SA = "SHORTANSWER", "MW", "SA", "Short, Case Insensitive"
    SAC = "SHORTANSWER_C", "MWC", "SAC", "Short, Case Sensitive"


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


class FileAddr(Enum):
    """Define how to intepret the File's path.
    """
    LOCAL = "Local"
    EMBEDDED = "Embedded"
    URL = "URL"


class Grading(EnhancedEnum):
    """Enumerates Grading patterns
    """
    IGNORE = "0", "Ignore"
    RESPONSE = "1", "Fraction (reponse)"
    QUESTION = "2", "Fraction (question)"


class Language(Enum):
    """Languages that can be attributes to a FText section (TODO)
    """
    EN_US = "us english"
    PT_BR = "brazilian portuguese"
    ANY = "any"
    """When the language is universaly understood, like math."""


class MathType(Enum):
    """Enumerates ways to represent math function in questions' test
    """
    MATHML = "MathML"
    LATEX = "LaTex"
    MATHJAX = "MathJax"
    ASCII = "ASCII"
    MOODLE = "moodle"
    FILE = "File"


class Numbering(EnhancedEnum):
    """Enumerates Numbering patterns
    """
    NONE = "none", "None"
    ALF_LR = "abc", "abc"
    ALF_UR = "ABCD", "ABCD"
    NUMERIC = "123", "123"
    ROM_LR = "iii", "iii"
    ROM_UR = "IIII", "IIII"


class OutFormat(Enum):
    """_summary_
    """
    TEXT = auto()
    MOODLE = auto()
    OLX = auto()
    QTI = auto()
    GIFT = auto()


class Orientation(Enum):
    """_summary_
    """
    HOR = auto()
    VER = auto()


class ShapeType(Enum):
    """Enumerates Shape Types
    """
    CIRCLE = "circle"
    RECT = "rectangle"
    POLY = "polygon"


class ShowAnswer(EnhancedEnum):
    """
    """
    ALWAYS = True, "always"
    ANSWERED = "answered"
    ATTEMPTED = "attempted"
    CLOSED = "closed"
    COR_PAST = "correct_or_past_due"
    FINISHED = "finished"
    PAST_DUE = "past_due"
    NEVER = False, "never"


class ShowUnits(EnhancedEnum):
    """Enumerates way to show Units
    """
    TEXT = "0", "Text input"
    MC = "1", "Multiple choice"
    DROP_DOWN = "2", "Drop-down"
    NONE = "3", "Not visible"


class ShuffleType(EnhancedEnum):
    """
    """
    ALWAYS = True, "always"
    RESET = "on_reset"
    NEVER = False, "never"
    STUDENT = "per_student"


class Status(EnhancedEnum):
    """Enumerates Status for Datasets
    """
    PRV = "private"
    SHR = "shared"


class Synchronise(EnhancedEnum):
    """Synchronise types
    """
    NO_SYNC = "0", "Do not synchronise"
    SYNC = "1", "Synchronise"
    SYNC_NAME = "2", "Synchronise and add as prefix"


class RespFormat(EnhancedEnum):
    """Enumerates Response Formats
    """
    HTML = "editor", "HTML"
    WFILE = "editorfilepicker", "HTML w/ file"
    PLAIN = "plain", "Plain text"
    MONO = "monospaced", "Mono spaced"
    ATCH = "noinline", "No inline"


class TextFormat(EnhancedEnum):
    """Enumerates text format types
    """
    HTML = "html", "HTML"
    AUTO = "auto", "moodle_auto_format", "Auto"
    PLAIN = "plain_text", "Plain"
    MD = "markdown", "Markdown"
    LATEX = "latex", "LaTEX"


class TolType(EnhancedEnum):
    """Enumerates Tolerance Types
    """
    REL = "1", "Relative"
    NOM = "2", "Nominal"
    GEO = "3", "Geometric"


class TolFormat(EnhancedEnum):
    """Tolerance Format types
    """
    DEC = "1", "Decimals"
    FIG = "2", "Significant figures"
