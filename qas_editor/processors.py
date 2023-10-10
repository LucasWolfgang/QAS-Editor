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

import inspect
from typing import TYPE_CHECKING, Any, Callable, Dict, Tuple

if TYPE_CHECKING:
    from .parsers.text import FText


def mapper(_input: Dict[Any, dict]):
    """_summary_
    Args:
        input (Dict[Any, float]): _description_
    """
    def processor(dbid):
        output: Dict[str, Any] = {}
        for key, value in _input.items():
            if dbid == key:
                output = value
                break
        else:
            output = {"value": 0.0}
        return output
    return processor


def mapper_nocase(_input: Dict[str, dict]):
    """_summary_
    Args:
        input (Dict[str, float]): _description_
    """
    def processor(dbid: str):
        output = None
        for key, value in _input.items():
            if dbid.lower() == key.lower():
                output = value
                break
        else:
            output = {"value": 0.0}
        return output
    return processor


def numerical_range(_input: Dict[Tuple[float, float], dict]):
    """_summary_
    Args:
        input (Dict[str, float]): _description_
    """
    def processor(dbid: float):
        output = None
        for key, value in _input.items():
            if key[0] < dbid < key[1]:
                output = value
                break
        else:
            output = {"value": 0.0}
        return output
    return processor


class Proc:
    """_summary_
    """

    def __init__(self, func: Callable, args: dict = None, std=True) -> None:
        self.func = func(args) if args else func
        self.args = args
        self.std = std

    def to_string(self):
        """_summary_
        """
        return inspect.getsource(self.func)

    def to_xml(self):
        """_summary_
        """
