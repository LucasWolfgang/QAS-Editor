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
    s = ("<p><b>Moodle</b> and <b>fp</b> latex package syntax "
        "is not always equivalent. Here some test for pathological cases.</p>"
        "<p>Let {x} and {y} some real number.<br/></p><ul><li>argument of "
        "'pow' function are in a different order {=pow({x},2)}</li><li>"
        "the 'sqrt' function doesn't exist, need 'root(n, x)' in fp, "
        "{=sqrt(({x}-{y})*({x}+{y}))}</li><li>'pi' is a function in moodle,"
        " {=sin(1.5*pi())}</li><li>test with '- unary' expression"
        " {=-{x}+(-{y}+2)}<br/></li></ul>")
    _results = utils.FText.from_string(s)
    assert _results.text == ["<p><b>Moodle</b> and <b>fp</b> "
            "latex package syntax is not always equivalent. Here some "
            "test for pathological cases.</p><p>Let ", X, ' and ', Y, 
            " some real number.<br/></p><ul><li>argument of 'pow' "
            "function are in a different order ", X**2, 
            "</li><li>the 'sqrt' function doesn't exist, need"
            " 'root(n, x)' in fp, ", sqrt((X - Y)*(X + Y)), 
            "</li><li>'pi' is a function in moodle, ", -1, 
            "</li><li>test with '- unary' expression ", -X - Y + 2, 
            '<br/></li></ul>']


def test_empty():
    _ftext = utils.FText.from_string('nothing')
    assert _ftext.text == ['nothing']


def test_var_ascii():
    _results = utils.FText.from_string('var {x}')
    assert _results.get(MathType.ASCII) == "var x"


def test_var_latex():
    _results = utils.FText.from_string('var {x}')
    assert _results.get(MathType.LATEX) == "var $$x$$"


def test_img_ref():
    text = ("""and<p style="text-align: left;">file <img src="@@PLUGINFILE@@"""
        """/dessin.svg" alt="escargot" style="vertical-align: text-bottom;" """
        """class="img-responsive" width="100" height="141"/> is close.</p>""")
    _results = utils.FText.from_string(text)
    assert len(_results.text) == 6
    assert isinstance(_results.text[3], utils.FileRef)
    assert len(_results.files) == 1
    assert _results.files[0] == utils.File("/dessin.svg","")
    assert _results.files[0] == _results.text[3].file
    assert _results.text[3].metadata == {'alt': 'escargot',
            'style': 'vertical-align: text-bottom;', 'class': 'img-responsive',
            'width': '100', 'height': '141'}


def test_img_ref_base64():
    text = ("""and<p style="text-align: left;">file <img src="data:image/png;"""
        """base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4"""
        """//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==" alt="Red"""
        """ dot" width="100" height="141"/> is close.</p>""")
    _results = utils.FText.from_string(text)
    assert len(_results.text) == 6
    assert isinstance(_results.text[3], utils.FileRef)
    assert len(_results.files) == 1
    assert _results.files[0] == utils.File("/0.png","")
    assert _results.files[0] == _results.text[3].file
    assert _results.text[3].metadata == {'alt': 'Red dot', 'width': '100', 'height': '141'}



