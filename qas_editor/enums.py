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


class ClozeFormat(Enum):
    """Enumerates Cloze formats
    """
    SHORTANSWER = "SHORTANSWER", "SA", "MW", "SA"
    SHORTANSWER_C = "SHORTANSWER_C", "SAC", "MWC"
    NUMERICAL = "NUMERICAL", "NM"
    MULTICHOICE = "MULTICHOICE", "MC"
    MULTICHOICE_V = "MULTICHOICE_V", "MVC"
    MULTICHOICE_H = "MULTICHOICE_H", "MCH"
    MULTIRESPONSE = "MULTIRESPONSE", "MR"
    MULTIRESPONSE_H = "MULTIRESPONSE_H", "MRH"

    def __new__(cls, *values):
        obj = object.__new__(cls)
        obj._value_ = values[0]
        for other_value in values[1:]:
            cls._value2member_map_[other_value] = obj
        obj._all_values = values
        return obj

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self._name_}: %s>" % (
                ', '.join([repr(v) for v in self._all_values]))


class Direction(Enum):
    """Enumerates the four directions
    """
    UP = 1
    DOWN = 2
    RIGHT = 3
    LEFT = 4


class Distribution(Enum):
    """Enumerates dataset distribution types.
    """
    UNI = "uniform"
    LOG = "loguniform"


class Format(Enum):
    """Enumerates text format types
    """
    HTML = "html"
    AUTO = "moodle_auto_format"
    PLAIN = "plain_text"
    MD = "markdown"


class Grading(Enum):
    """Enumerates Grading patterns
    """
    IGNORE = "0"        # Ignore
    RESPONSE = "1"      # Fraction of reponse grade
    QUESTION = "2"      # Fraction of question grade


class Numbering(Enum):
    """Enumerates Numbering patterns
    """
    NONE = "none"
    ALF_LR = "abc"
    ALF_UR = "ABCD"
    NUMERIC = "123"
    ROM_LR = "iii"
    ROM_UR = "IIII"


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


class ShowUnits(Enum):
    """Enumerates way to show Units
    """
    TEXT = "0"          # Text input
    MC = "1"            # Multiple choice
    DROP_DOWN = "2"     # Drop-down
    NONE = "3"          # Not visible


class Status(Enum):
    """Enumerates Status for Datasets
    """
    PRV = "private"
    SHR = "shared"


class ResponseFormat(Enum):
    """Enumerates Response Formats
    """
    HTML = "editor"
    WFILE = "editorfilepicker"
    PLAIN = "plain"
    MONO = "monospaced"
    ATCH = "noinline"


class ToleranceFormat(Enum):
    """Enumerates Tolerance Formats
    """
    DEC = "1"           # Decimals
    SIG = "2"           # Significant Figures


class ToleranceType(Enum):
    """Enumerates Tolerance Types
    """
    REL = "1"           # Relative
    NOM = "2"           # Nominal
    GEO = "3"           # Geometric
