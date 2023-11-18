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
import re
from typing import Any, Callable, Dict


def mapper(args: Dict[str, dict]):
    """_summary_
    Args:
        input (Dict[Any, float]): _description_
    """
    def default_proc_mapper(dbid):
        output: Dict[str, Any] = {}
        for key, value in args["values"].items():
            if dbid == key:
                output = value
                break
        else:
            output = {"value": 0.0}
        return output
    return default_proc_mapper


def string_process(data: Dict[str, dict]):
    """_summary_
    Args:
        input (Dict[str, float]): _description_
    """
    flag = re.I if data.get("case") else 0
    def default_proc_string(dbid: str):
        output = None
        for key, value in data["values"].items():
            if re.match(key, dbid, flags=flag):
                output = value
                break
        else:
            output = {"value": 0.0}
        return output
    return default_proc_string


def numerical_range(_input: Dict[str, dict]):
    """_summary_
    Args:
        input (Dict[str, float]): _description_
    """
    def default_proc_numerical_range(dbid: float):
        output = None
        for key, value in _input["values"].items():
            if key[0] < dbid < key[1]:
                output = value
                break
        else:
            output = {"value": 0.0}
        return output
    return default_proc_numerical_range


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
        inspect.getsource(self.func)
