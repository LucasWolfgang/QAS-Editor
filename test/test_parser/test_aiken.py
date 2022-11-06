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
from qas_editor import category

TEST_PATH = os.path.dirname(os.path.dirname(__file__))


def test_read():
    EXAMPLE = f"{TEST_PATH}/datasets/aiken/aiken_1.txt"
    control = category.Category.read_aiken(EXAMPLE)
    assert control.get_size() == 5
    question = control.get_question(1)
    assert question.QNAME == 'Multichoice'
    assert question.default_grade == 1.0
    assert question.name == 'aiken_1'
    assert question.question.get() == ("During the month of September 2013, "
                            "Moodle ran a successful MOOC for teachers new " 
                            "to Moodle. What was the name of the course?")
    assert len(question.options) == 3
    assert question.options[0].text == 'Teaching with Moodle'
    assert question.options[0].fraction == 100
    assert question.options[1].fraction == 0
    assert question.options[2].fraction == 0


def test_diff_simple():
    EXAMPLE = f"{TEST_PATH}/datasets/aiken/aiken_1.txt"
    control = category.Category.read_aiken(EXAMPLE)
    XML_TEST = f"{EXAMPLE}.tmp"
    control.write_aiken(XML_TEST)
    new_data = category.Category.read_aiken(XML_TEST)
    assert control.compare(new_data, [])
    os.remove(XML_TEST)
    
