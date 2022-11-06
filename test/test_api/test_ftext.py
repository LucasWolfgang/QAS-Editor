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
import os
from qas_editor import utils
from sympy import Symbol, sqrt

from qas_editor.enums import MathType
from qas_editor.utils import File

TEST_PATH = os.path.dirname(__file__)
SRC_PATH = os.path.abspath(os.path.join(TEST_PATH, '..'))
X = Symbol("x")
Y = Symbol("y")

def test_sympy_all():
    s = ("<text><![CDATA[<p><b>Moodle</b> and <b>fp</b> latex package syntax "
        "is not always equivalent. Here some test for pathological cases.</p>"
        "<p>Let {x} and {y} some real number.<br/></p><ul><li>argument of "
        "'pow' function are in a different order {=pow({x},2)}</li><li>"
        "the 'sqrt' function doesn't exist, need 'root(n, x)' in fp, "
        "{=sqrt(({x}-{y})*({x}+{y}))}</li><li>'pi' is a function in moodle,"
        " {=sin(1.5*pi())}</li><li>test with '- unary' expression"
        " {=-{x}+(-{y}+2)}<br/></li></ul>]]></text>")
    _vars, _results = utils.FText.from_string(s)
    assert _vars == {X, Y}
    assert _results.text == ["<text><![CDATA[<p><b>Moodle</b> and <b>fp</b> "
            "latex package syntax is not always equivalent. Here some "
            "test for pathological cases.</p><p>Let ", X, ' and ', Y, 
            " some real number.<br/></p><ul><li>argument of 'pow' "
            "function are in a different order ", X**2, 
            "</li><li>the 'sqrt' function doesn't exist, need"
            " 'root(n, x)' in fp, ", sqrt((X - Y)*(X + Y)), 
            "</li><li>'pi' is a function in moodle, ", -1, 
            "</li><li>test with '- unary' expression ", -X - Y + 2, 
            '<br/></li></ul>]]></text>']


def test_empty():
    s, ref  = ('nothing', ['nothing'])
    _, _ftext = utils.FText.from_string(s)
    assert _ftext.text == ref


def test_var_ascii():
    _vars, _results = utils.FText.from_string('var {x}')
    _results = _results.get(MathType.ASCII)
    assert _results == "var x"
    assert _vars == {X}


def test_var_latex():
    _vars, _results = utils.FText.from_string('var {x}')
    _results = _results.get(MathType.LATEX)
    assert _results == "var $$x$$"
    assert _vars == {X}


def test_file_img():
    dt = ("<file encoding=\"base64\" name=\"4.png\" path="/">iVBORw0KGgoAAAANSUh"
            "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</file>")
    utils.FText.from_string(text)


def test_file_img_ref():
    text = ("""and<p style="text-align: left;">file <img src="@@PLUGINFILE@@"""
        """/dessin.svg" alt="escargot" style="vertical-align: text-bottom;"""
        """class="img-responsive" width="100" height="141"/> is close.</p>""")
    _vars, _results = utils.FText.from_string(text)
    tmp = _results.get()
    assert _vars == set()
    assert tmp == text
    assert isinstance(_results.text[1], File)


def test_file_video_ref():
    text = ("""and<p style="text-align: left;">file <img src="@@PLUGINFILE@@"""
        """/dessin.svg" alt="escargot" style="vertical-align: text-bottom;"""
        """class="img-responsive" width="100" height="141"/> is close.</p>""")
    _vars, _results = utils.FText.from_string(text)
    tmp = _results.get()
    assert _vars == set()
    assert tmp == text
    assert isinstance(_results.text[1], File)

