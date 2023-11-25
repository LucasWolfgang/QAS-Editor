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
import inspect
import os

from qas_editor.processors import Proc, to_source

TEST_PATH = os.path.dirname(__file__)
SRC_PATH = os.path.abspath(os.path.join(TEST_PATH, '..'))


def test_func_to_string():
    args = {"values":{0:{"value": 0}, 1:{"value": 100}}}
    source = Proc.TEMPLATES["mapper"].format(args=args)
    proc = to_source(source)
    assert proc == """def processor(dbid: Any) -> Dict[(str, Any)]:
    args = {'values': {(0): {'value': 0}, (1): {'value': 100}}}
    output: Dict[(str, Any)] = {}
    for key, value in args['values'].items():
        if dbid == key:
            output = value
            break
    else:
        output = {'value': 0.0}
    return output
"""


def test_string_to_func():
    test = """def processor(dbid):
    output = {}
    for key, value in {0:{"value": 0}, 1:{"value": 100}}.items():
        if dbid == key:
            output = value
            break
    else:
        output = {"value": 0.0}
    return output"""
    proc = Proc.from_str(test)
    res = proc.func(1)
    assert res["value"] == 100
