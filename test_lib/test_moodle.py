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

import os
from qas_editor import category
from qas_editor._parsers import moodle

TEST_PATH = os.path.dirname(__file__)
SRC_PATH = os.path.abspath(os.path.join(TEST_PATH, '..'))


def test_diff_all():
    EXAMPLE = f"{TEST_PATH}/datasets/moodle/all.xml"
    control = category.Category.read_moodle(EXAMPLE)
    XML_TEST = f"{EXAMPLE}.tmp"
    control.write_moodle(XML_TEST, True)
    new_data = category.Category.read_moodle(XML_TEST)
    assert control.compare(new_data, [])
    os.remove(XML_TEST)


def test_against_json():
    EXAMPLE = f"{TEST_PATH}/datasets/moodle/all.xml"
    data = category.Category.read_moodle(EXAMPLE)
    XML_TEST = f"{TEST_PATH}/datasets/json/all.json"
    #data.write_json(XML_TEST)
    control = category.Category.read_json(XML_TEST)
    assert control.compare(data, [])


def test_diff_calculated():
    EXAMPLE = f"{TEST_PATH}/datasets/moodle/calculated.xml"
    control = category.Category.read_moodle(EXAMPLE)
    XML_TEST = f"{EXAMPLE}.tmp"
    control.write_moodle(XML_TEST, True)
    new_data = category.Category.read_moodle(XML_TEST)
    assert control.compare(new_data, [])
    os.remove(XML_TEST)


def test_sympy():
    from sympy import Symbol, sqrt
    s = ("<text><![CDATA[<p><b>Moodle</b> and <b>fp</b> latex package syntax "
        "is not always equivalent. Here some test for pathological cases.</p>"
        "<p>Let {x} and {y} some real number.<br></p><ul><li>argument of "
        "'pow' function are in a different order {=pow({x},2)}</li><li>"
        "the 'sqrt' function doesn't exist, need 'root(n, x)' in fp, "
        "{=sqrt(({x}-{y})*({x}+{y}))}</li><li>'pi' is a function in moodle,"
        " {=sin(1.5*pi())}</li><li>test with '- unary' expression"
        " {=-{x}+(-{y}+2)}<br></li></ul>]]></text>")
    _vars, _results = moodle.get_sympy(s)
    x = Symbol("x")
    y = Symbol("y")
    assert _vars == {x, y}
    assert _results == ["<text><![CDATA[<p><b>Moodle</b> and <b>fp</b> "
            "latex package syntax is not always equivalent. Here some "
            "test for pathological cases.</p><p>Let ", x, ' and ', y, 
            " some real number.<br></p><ul><li>argument of 'pow' "
            "function are in a different order ", x**2, 
            "</li><li>the 'sqrt' function doesn't exist, need"
            " 'root(n, x)' in fp, ", sqrt((x - y)*(x + y)), 
            "</li><li>'pi' is a function in moodle, ", -1, 
            "</li><li>test with '- unary' expression ", -x - y + 2, 
            '<br></li></ul>]]></text>']
    