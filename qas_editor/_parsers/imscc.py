"""
Question and Answer Sheet Editor <https://github.com/LucasWolfgang/QAS-Editor>
Copyright (C) 2023  Lucas Wolfgang

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
import glob
from typing import TYPE_CHECKING

from ..question import QMultichoice
if TYPE_CHECKING:
    from ..category import Category


# -----------------------------------------------------------------------------


def read_imscc(cls, file_path: str, category: str = "$course$") -> "Category":
    """_summary_
    Args:
        file_path (str): _description_
        category (str, optional): _description_. Defaults to "$".
    Returns:
        Quiz: _description_
    """
    quiz = cls(category)
    cnt = 0

    return quiz


def write_imscc(category: "Category", file_path: str) -> None:
    """_summary_
    Args:
        file_path (str): _description_
    """
    with open(file_path, "w", encoding="utf-8") as ofile:
        pass
