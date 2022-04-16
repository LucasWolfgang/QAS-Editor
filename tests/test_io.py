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

import sys
import os
import logging

# ------------------------------------------------------------------------------

test_path = os.path.dirname(__file__)
src_path = os.path.abspath(os.path.join(test_path, '..'))
sys.path.append(src_path)
from qas_editor import quiz
log = logging.getLogger()
log.setLevel(logging.DEBUG)
fhandler = logging.FileHandler(filename=f"{test_path}/unittest.log",
                            mode="w", encoding="utf-8")
fhandler.setFormatter(logging.Formatter("%(levelname)s [%(asctime)s]: %(message)s",
                                        "%H:%M:%S"))
fhandler.setLevel(logging.DEBUG)
log.addHandler(fhandler)
log.debug("Initializing pytest regression...")

# ------------------------------------------------------------------------------

def test_file_xml():
    EXAMPLE = f"{test_path}/datasets/moodle.xml"
    control = quiz.Quiz.read_xml(EXAMPLE)
    XML_TEST = f"{EXAMPLE}.tmp"
    control.write_xml(XML_TEST, True)
    new_data = quiz.Quiz.read_xml(XML_TEST)
    os.remove(XML_TEST)
    assert control == new_data


def test_aikien() -> None:
    log.debug("Testing Aiken read/write.")


def test_cloze() -> None:
    log.debug("Testing Cloze read/write.")


def test_gift() -> None:
    log.debug("Testing GIFT read/write.")


def test_markdown() -> None:
    log.debug("Testing Markdown read/write.")


def test_latex() -> None:
    log.debug("Testing LaTeX read/write.")


def test_pdf() -> None:
    log.debug("Testing PDF read/write.")

# ------------------------------------------------------------------------------
