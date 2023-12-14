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

import os
from io import StringIO

from qas_editor import enums
from qas_editor.category import Category
from qas_editor.parsers import latex

TEST_PATH = os.path.dirname(os.path.dirname(__file__))


def test_raw_multargs():
    tmp = StringIO("\\acommand[key1=value1, key2=value2]{a_value}"
                   "{another_value}[opt1]{final_value}[opt2]")
    cat = Category()
    tex = latex.LaTex(cat, tmp, "")
    data = [item for item in tex._parse()]
    assert len(data) == 1
    assert data[0].name == "acommand"
    assert data[0].args == ["a_value", "another_value", "final_value"]
    assert data[0].opts == ["key1=value1, key2=value2", "opt1", "opt2"]


def test_raw_subitems():
    tmp = StringIO("\\element{tikz}{\\begin{name}{arg2}[opt1]"
                   "A given string\\end{name}}")
    cat = Category()
    tex = latex.LaTex(cat, tmp, "")
    data = [item for item in tex._parse()]
    assert len(data) == 1
    assert isinstance(data[0], latex.Cmd)
    assert data[0].name == "element"
    assert data[0].opts == []
    assert len(data[0].args) == 2
    assert data[0].args[0] == "tikz"
    assert isinstance(data[0].args[1], latex.Env)
    assert data[0].args[1].name =="name"
    assert data[0].args[1].args[0] =="arg2"
    assert data[0].args[1].opts[0] =="opt1"
    assert data[0].args[1].subitems[0] =="A given string"


def test_latextomoodle_read():
    EXAMPLE = f"{TEST_PATH}/datasets/latex_l2m/read.tex"
    lang = enums.Language.EN_US
    control = Category.read_latex_l2m(EXAMPLE, lang)
    control = control["My little category from latex"]
    assert len(control) == 1
    assert control.get_size(False) == 3
    assert control.get_size(True) == 4
    assert control.name == "My little category from latex"
    question = next(control["Simple arithmetic"].questions)
    assert question.question.get() == "The product 6x8 is equal to ... :\n"
    opts = question.options
    assert len(opts) == 3
    assert opts[0].text == "47"
    assert opts[0].fraction == 0.0


def test_latextomoodle_vs_moodle():
    EXAMPLE = f"{TEST_PATH}/datasets/latex_l2m/multichoice.tex"
    lang = enums.Language.EN_US
    data = Category.read_latex(EXAMPLE, lang)

def test_amc_element():
    EXAMPLE = f"{TEST_PATH}/datasets/latex_amc/tikz.tex"
    lang = enums.Language.EN_US
    cat = Category()
    with open(EXAMPLE) as ifile:
        tex = latex._PkgAMQ(cat, ifile, "", lang)
        data = []
        while tex.line:
            data.extend(item for item in tex._parse())
    assert len(data) == 1
    assert data[0].name == "element"
    assert len(data[0].args)== 2
    assert len(data[0].opts)== 0
    assert isinstance(data[0].args[1], latex.Env)
    