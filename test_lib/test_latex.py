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
from qas_editor.category import Category


TEST_PATH = os.path.dirname(__file__)
SRC_PATH = os.path.abspath(os.path.join(TEST_PATH, '..'))


def test_guillaume_read():
    EXAMPLE = f"{TEST_PATH}/datasets/latex/guillaume_read.tex"
    control = Category.read_latex(EXAMPLE)
    control = control["My little catgory from latex"]
    assert len(control) == 1
    assert control.get_size(False) == 3
    assert control.get_size(True) == 4
    assert control.name == "My little catgory from latex"
    question = next(control["Simple arithmetic"].questions)
    assert question.question.text == "The product 6x8 is equal to ... :"
    opts = question.options
    assert len(opts) == 3
    assert opts[0].text == "47"
    assert opts[0].fraction == 0.0

def test_guillaume_vs_moodle():
    EXAMPLE = f"{TEST_PATH}/datasets/latex/guillaume_xml.tex"
    data = Category.read_latex(EXAMPLE)
    data.metadata.clear()   # This will always be different
    XML_TEST = f"{TEST_PATH}/datasets/latex/guillaume_xml.xml"
    control = Category.read_moodle(XML_TEST)
    assert data.compare(control, [])

_EXPR =[['nothing', 'nothing', ''],  # variable
    ['var {x}', r'var \FPprint{\x }', ''],  # variable
    ['var {x_y}', r'var \FPprint{\xy }', ''],  # variable with '_'
    ['var {x1}', r'var \FPprint{\x1 }', 'Warning'],  # variable with '_'
    ['var {x} and {y} end.', r'var \FPprint{\x } and \FPprint{\y } end.', ''],  # 2 variables
    ['Embedded Eq. {=1+1} = 2', r'Embedded Eq. \FPprint{\FPeval{\out}{clip(1+1)}\out} = 2', ''],  # eq inside text
    ['{=sqrt(3)}', r'\FPprint{\FPeval{\out}{clip(root(2, 3))}\out}', ''],  # sqrt -> root(2,...)
    ['{=(1.0 + pow(2, 3)/2)}', r'\FPprint{\FPeval{\out}{clip((1.0+pow(3,2)/2))}\out}', ''],  # pow -> pow(2,...)
    ['{=pow(2, 0.5)}', r'\FPprint{\FPeval{\out}{clip(pow(0.5,2))}\out}', ''],  # pow for roots 1.414213562373095042
    ['{=pow(0.5+1.5, 0.5)}', r'\FPprint{\FPeval{\out}{clip(pow(0.5,0.5+1.5))}\out}', ''],  # test expr in swap 1.414213562373095042
    ['{=-({x}-{y})}', r'\FPprint{\FPeval{\out}{clip(neg((\x -\y )))}\out}', ''],  # - unary
    ['{=-1.2e-3}', r'\FPprint{\FPeval{\out}{clip(-0.0012)}\out}', ''],  # float
    ['{=2*(((1-2)*(1+2))/(1+pi()))}', r'\FPprint{\FPeval{\out}{clip(2*(((1-2)*(1+2))/(1+\FPpi)))}\out}', ''],  # nested + pi()
    ['{=max(3, 2) + 2*2}', r'\FPprint{\FPeval{\out}{clip(max(3,2)+2*2)}\out}', ''],  # function of 2 variables 7
    ['{=log(log(2) + 2)}', r'\FPprint{\FPeval{\out}{clip(ln(ln(2)+2))}\out}', ''],  # nested log function 0.990710465347531441
    ['{=log(log(2) + 2}', r'{=log(log(2) + 2}', ''],  # Miss formed, parser skip
    ['{=xyz(2)}', r'\FPprint{\FPeval{\out}{clip(xyz(2))}\out}', 'Unsupported'],  # Miss formed, parser skip
    ['{=expm1(2)}', r'\FPprint{\FPeval{\out}{clip(expm1(2))}\out}', 'Unsupported'],  # Miss formed, parser skip
    # Embedded LaTeX equation in XML may leads to problems (because of braces)
    # Remove standard mathjax delimiters from 'variable' parsing,
    # In mathjax equation environnement inside delimiters is correct
    [r'$$\begin{equation}\int x dx =3\end{equation}$$ {=sin({x}+1)}',
        r'$$\begin{equation}\int x dx =3\end{equation}$$ \FPprint{\FPeval{\out}{clip(sin(\x +1))}\out}',''], # $$ ... $$
    [r'\(\begin{equation}\int x dx =3\end{equation}\) {=sin({x}+1)}',
        r'\(\begin{equation}\int x dx =3\end{equation}\) \FPprint{\FPeval{\out}{clip(sin(\x +1))}\out}',''], #\( ... \)
    [r'\[\begin{equation}\int x dx =3\end{equation}\] {=sin({x}+1)}',
        r'\[\begin{equation}\int x dx =3\end{equation}\] \FPprint{\FPeval{\out}{clip(sin(\x +1))}\out}',''], #\[ ... \[)]
    [r'\[\begin{equation}\int x dx =3\end{equation}\] {x}',
        r'\[\begin{equation}\int x dx =3\end{equation}\] \FPprint{\x }',''] #\[ ... \[)] + var
    ]


def test_render():
    """ Tests if input XML file yields reference LaTeX file and warning are
    printed.
    """
    print('\n> Tests of' , self.__class__.__name__)
    # Create the parser
    parser = CreateCalculatedParser('xml2fp')
    for e, ref, expectedwarn in _EXPR:
        print("Expr = {} -> {}".format(e, ref))
        # mock out std ouput for testing
        with patch('sys.stdout', new=StringIO()) as fake_out:
            # parse answer
            out = parser.render(e)
            # check for the expected conversion
            self.assertEqual(out, ref)
            # check for expected warnings
            # As '' belong to all strings
            warn = fake_out.getvalue()
            if warn:
                self.assertIn(expectedwarn, warn)


def test_name_Qmult_Aucune(self):
    """ Check specific element for question 'Qmult:Aucune'.
    """
    # question name
    qname = 'Qmult:Aucune'

    # Test shuffleanswers, should be 'false', ie keep order
    # Test local scoring, ie local scoring \bareme{e=-0.5,b=1,m=-1.,p=-0.5}
    # Test question multiple ie target_single='false'
    ok = self.question_fields(qname=qname,
                                target_ans_sum=0,
                                target_shuffleanswers='false',
                                target_single='false')

    # the test is ok if ok==0
    self.assertEqual(ok, 0)