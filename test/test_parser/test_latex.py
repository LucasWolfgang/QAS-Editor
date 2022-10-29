"""
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

from io import StringIO
import os
from qas_editor.category import Category
from qas_editor._parsers import latex

TEST_PATH = os.path.dirname(__file__)
SRC_PATH = os.path.abspath(os.path.join(TEST_PATH, '..'))


def test_raw_multargs():
    tmp = StringIO("\\acommand[key1=value1, key2=value2]{a_value}"
                   "{another_value}[opt1]{final_value}[opt2]")
    cat = Category()
    tex = latex.LaTex(cat, tmp, "")
    data = tex._document()
    assert len(data) == 1
    assert data[0].name == "acommand"
    assert data[0].args == ["a_value", "another_value", "final_value"]
    assert data[0].opts == ["key1=value1, key2=value2", "opt1", "opt2"]


def test_latextomoodle_read():
    EXAMPLE = f"{TEST_PATH}/datasets/latex_l2m/read.tex"
    control = Category.read_latex(EXAMPLE)
    control = control["My little category from latex"]
    assert len(control) == 1
    assert control.get_size(False) == 3
    assert control.get_size(True) == 4
    assert control.name == "My little category from latex"
    question = next(control["Simple arithmetic"].questions)
    assert question.question.get() == "The product 6x8 is equal to ... :"
    opts = question.options
    assert len(opts) == 3
    assert opts[0].text == "47"
    assert opts[0].fraction == 0.0


def test_latextomoodle_vs_moodle():
    EXAMPLE = f"{TEST_PATH}/datasets/latex/guillaume_xml.tex"
    data = Category.read_latex(EXAMPLE)
    data.metadata.clear()   # This will always be different
    XML_TEST = f"{TEST_PATH}/datasets/latex/guillaume_xml.xml"
    control = Category.read_moodle(XML_TEST)


def test_amc_read():
    EXAMPLE = f"{TEST_PATH}/datasets/latex/amc_element.tex"
    data = Category.read_latex(EXAMPLE)
    data.metadata.clear()   # This will always be different