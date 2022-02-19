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

import unittest
from .quiz import Quiz

class TestIO(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.XML_EXAMPLE = "./testcases/moodle.xml"
        cls.XML_TEST = "./testcases/moodle_2.xml"
        
    def test_aikien(self) -> None:
        pass

    def test_cloze(self) -> None:
        pass

    def test_gift(self) -> None:
        pass

    def test_markdown(self) -> None:
        pass

    def test_latex(self) -> None:
        pass

    def test_pdf(sef) -> None:
        pass

    def test_xml(self):
        data = Quiz.read_xml(self.XML_EXAMPLE)
        data.write_xml(self.XML_TEST, True)
        with open(self.XML_EXAMPLE, 'r') as infile:
            control = infile.read()
        with open(self.XML_TEST, 'r') as infile:
            data = infile.read()
        self.assertTrue(control == data)

        
        
def run_tests() -> None:
    unittest.main()