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
test_path = os.path.dirname(__file__)
src_path = os.path.abspath(os.path.join(test_path, '..'))
sys.path.append(src_path)
from qas_editor import quiz


def test_file_xml():
    EXAMPLE = f"{test_path}/datasets/moodle.xml"
    control = quiz.Category.read_xml(EXAMPLE)
    XML_TEST = f"{EXAMPLE}.tmp"
    control.write_xml(XML_TEST, True)
    new_data = quiz.Category.read_xml(XML_TEST)
    # os.remove(XML_TEST)
    assert control.compare(new_data, [])


def test_aikien() -> None:
    EXAMPLE = f"{test_path}/datasets/aiken/aiken_1.txt"
    control = quiz.Category.read_aiken(EXAMPLE)
    XML_TEST = f"{EXAMPLE}_tmp"
    control.write_aiken(XML_TEST)
    new_data = quiz.Category.read_aiken(XML_TEST)
    os.remove(XML_TEST)
    assert control.compare(new_data, [])


def test_cloze() -> None:
    pass


def test_gift() -> None:
    pass


def test_markdown() -> None:
    pass


def test_latex() -> None:
    pass


def test_pdf() -> None:
    pass

# ------------------------------------------------------------------------------
