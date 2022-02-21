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
import sys
import os
test_path = os.path.dirname(__file__)
src_path = os.path.abspath(os.path.join(test_path, '..'))
sys.path.append(src_path)
from qas_editor import quiz
import logging

# ------------------------------------------------------------------------------

log = logging.getLogger()
log.setLevel(logging.DEBUG)
fhandler = logging.FileHandler(filename=f"{test_path}/unittest.log",
                            mode="w", encoding="utf-8")
fhandler.setFormatter(logging.Formatter("%(levelname)s [%(asctime)s]: %(message)s",
                                        "%H:%M:%S,uuu"))
fhandler.setLevel(logging.DEBUG)
log.addHandler(fhandler)
log.debug("Initializing unittest regresion...")

# ------------------------------------------------------------------------------

def gTearDown(self):
    """Unified tearDown that only removed the temporary file if the 
    testcase ran successfully.
    """
    result = self.defaultTestResult()  # These two methods have no side effects
    self._feedErrorsToResult(result, self._outcome.errors)
    if not result.errors and not result.failures:
        pass # Place holder

# ------------------------------------------------------------------------------

class TestIO_XML(unittest.TestCase):

    EXAMPLE = f"{test_path}/datasets/moodle.xml"

    tearDown = gTearDown

    def test_xml(self):
        log.debug("Testing XML read/write.")
        control = quiz.Quiz.read_xml(self.EXAMPLE)
        XML_TEST = f"{self.EXAMPLE}.tmp"
        control.write_xml(XML_TEST, True)
        new_data = quiz.Quiz.read_xml(XML_TEST)
        self.assertTrue(control == new_data)

# ------------------------------------------------------------------------------

class TestIO(unittest.TestCase):

    XML_EXAMPLE = f"{test_path}/datasets/moodle.xml"

    tearDown = gTearDown
        
    def test_aikien(self) -> None:
        log.debug("Testing Aiken read/write.")

    def test_cloze(self) -> None:
        log.debug("Testing Cloze read/write.")

    def test_gift(self) -> None:
        log.debug("Testing GIFT read/write.")

    def test_markdown(self) -> None:
        log.debug("Testing Markdown read/write.")

    def test_latex(self) -> None:
        log.debug("Testing LaTeX read/write.")

    def test_pdf(sef) -> None:
        log.debug("Testing PDF read/write.")

# ------------------------------------------------------------------------------