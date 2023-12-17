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
from qas_editor.category import Category, TestStatus
from qas_editor.parsers import latex

TEST_PATH = os.path.dirname(os.path.dirname(__file__))


def test_raw_multargs():
    buffer = StringIO("\\acommand[key1=value1, key2=value2]{a_value}"
                   "{another_value}[opt1]{final_value}[opt2]")
    lang = enums.Language.EN_US
    cat = Category()
    tex = latex.LaTexParser(cat, buffer, lang, 2048, "")
    data = [item for item in tex._parse_env()]
    assert len(data) == 1
    assert data[0].tag == "acommand"
    assert data[0].attrs == {0:"a_value", 1:"another_value", 2:"final_value"}
    assert data[0].opts == {"key1":"value1", "key2":"value2", 0:"opt1", 1:"opt2"}


def test_raw_env():
    buffer = StringIO("\\test{arg}\n\\begin{name}{arg2}[opt1] "
                      "A given string\\cmd{}\nAnother string\\end{name}")
    lang = enums.Language.EN_US
    cat = Category()
    tex = latex.LaTexParser(cat, buffer, lang, 2048, "")
    data = [item for item in tex._parse_env()]
    assert len(data) == 2
    assert isinstance(data[1], latex.XItem)
    assert data[1].tag == None
    assert data[1].opts == {0: "opt1"}
    assert data[1].attrs == {0: 'name', 1: 'arg2'}
    assert len(data[1]) == 3
    assert data[1][0] == ' A given string'
    assert isinstance(data[1][1], latex.XItem)
    assert data[1][1].tag == 'cmd'
    assert data[1][1].opts == None
    assert data[1][1].attrs == None

def test_raw_subargs():
    buffer = StringIO("\\test{arg}{\\begin{name}{arg2}[opt1]"
                      "A given string\\end{name}}")
    lang = enums.Language.EN_US
    cat = Category()
    tex = latex.LaTexParser(cat, buffer, lang, 2048, "")
    data = [item for item in tex._parse_env()]
    assert len(data) == 1
    assert isinstance(data[0], latex.XItem)
    assert data[0].tag == "test"
    assert data[0].opts == None
    assert len(data[0].attrs) == 2
    assert data[0].attrs[0] == "arg"
    assert isinstance(data[0].attrs[1], latex.XItem)
    assert data[0].attrs[1].tag == None
    assert data[0].attrs[1].attrs[0] =="name"
    assert data[0].attrs[1].opts[0] =="opt1"
    assert data[0].attrs[1][0] =="A given string"


def test_raw_newlines():
    buffer = StringIO("First string (A)\\\\cmdAfterNl{}\\otherCmd\nSecond "
                      "string\nThird string (that is the second actually)\n\n"
                      "After new line\\newline another new line")
    lang = enums.Language.EN_US
    cat = Category()
    tex = latex.LaTexParser(cat, buffer, lang, 2048, "")
    data = [item for item in tex._parse_env()]
    assert data[0] == ' First string (A)\n'
    assert data[3] == 'Second stringThird string (that is the second actually)\nAfter new line'
    assert data[5] == ' another new line'


def test_latextomoodle_read_essay():
    EXAMPLE = f"{TEST_PATH}/datasets/latex_l2m/essay.tex"
    lang = enums.Language.EN_US
    cat = Category.read_latex_l2m(EXAMPLE, lang)
    assert "latex" in cat.metadata
    assert len(cat.metadata["latex"]) == 2
    assert cat.get_size(False) == 0
    assert len(cat) == 1
    assert "My little category from latex" in cat
    cat = cat["My little category from latex"]
    assert len(cat) == 0
    assert cat.get_size(False) == 2
    assert cat.get_size(True) == 2
    assert cat.name == "My little category from latex"
    qst = next(cat.questions)
    assert len(qst.body[lang].text) == 6
    assert qst.body[lang].text[0] == 'What is the derivative of $f(x) = e^x + 0.5 '
    res = qst.body[lang].text[-1].processor.func(0, TestStatus())
    assert res == {'grade': 1.5, 'penalty': 0.0}


def test_latextomoodle_read_multichoice():
    EXAMPLE = f"{TEST_PATH}/datasets/latex_l2m/multichoice.tex"
    lang = enums.Language.EN_US
    cat = Category.read_latex_l2m(EXAMPLE, lang)
    assert len(cat) == 1
    assert 'Number of roots for a polynomial' in cat
    assert cat.get_size(False) == 0
    assert cat.get_size(True) == 216
    cat = cat['Number of roots for a polynomial']
    assert cat.get_size(False) == 216
    assert cat.get_size(True) == 216
    qst = next(cat.questions)
    assert len(qst.body[lang].text) == 2
    assert qst.body[lang].text[0] == 'The equation $- 3 x^{2} - 3 x - 3=0$ has:\n'
    item = qst.body[lang].text[-1]
    assert len(item.options) == 2
    assert str(item.options[0]) == 'at least a solution'
    assert str(item.options[1]) == 'no real solution'
    assert item.processor.func(0, TestStatus())["value"] == 0
    assert item.processor.func(1, TestStatus())["value"] == 100


def test_latextomoodle_write_essay():
    EXAMPLE = f"{TEST_PATH}/datasets/latex_l2m/essay.tex"
    TMP = f"{EXAMPLE}.tmp"
    lang = enums.Language.EN_US
    ctrl = Category.read_latex_l2m(EXAMPLE, lang)
    ctrl.write_latex_l2m(TMP, lang)
    assert ctrl

def test_amc_read():
    EXAMPLE = f"{TEST_PATH}/datasets/latex_amc/tikz.tex"
    lang = enums.Language.EN_US
    cat = Category()
    with open(EXAMPLE) as ifile:
        tex = latex._AMQReader(cat, ifile, lang, 2048, "")
        data = []
        while tex.line:
            data.extend(item for item in tex._parse_env())
    assert len(data) == 1
    assert data[0].name == "element"
    assert len(data[0].args)== 2
    assert len(data[0].opts)== 0
    assert isinstance(data[0].args[1], latex.Env)
    