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

from .answer import Answer, CalculatedAnswer, DragText, NumericalAnswer
from .enums import *
from .questions import (QCalculated, QCalculatedMultichoice, QCalculatedSimple,
                        QCloze, QDescription, QDragAndDropImage,
                        QDragAndDropMarker, QDragAndDropText, QEssay,
                        QMatching, QMissingWord, QMultichoice, QNumerical,
                        QRandomMatching, QShortAnswer, QTrueFalse)

__author__ = "Lucas Wolfgang"
__version__ = "0.0.1"
__all__ = ["GUI", "main", "Answer", "DragText", "NumericalAnswer", "CalculatedAnswer",
        "QDescription", "QCalculated", "QCalculatedSimple",
        "QCalculatedMultichoice", "QCloze", "QDragAndDropText",
        "QDragAndDropImage", "QDragAndDropMarker", "QEssay",
        "QMatching", "QRandomMatching", "QMissingWord", "QMultichoice",
        "QNumerical", "QShortAnswer", "QTrueFalse"]
