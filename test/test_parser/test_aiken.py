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

from qas_editor import category, utils

TEST_PATH = os.path.dirname(os.path.dirname(__file__))


def test_read():
    """Tests the read process.
    """
    example = f"{TEST_PATH}/datasets/aiken/aiken_1.txt"
    control = category.Category.read_aiken(example)
    assert control.get_size() == 5
    question = control.get_question(1)
    assert question.tags == []
    assert question.name == 'aiken_1'
    assert question.body.text[0] == ("During the month of September 2013, "
                            "Moodle ran a successful MOOC for teachers new " 
                            "to Moodle. What was the name of the course?")
    assert len(question.body.text) == 2
    tmp = question.body.text[1]
    assert str(tmp.options[0]) == 'Teaching with Moodle'
    assert str(tmp.options[1]) == 'Moodle MOOC'
    assert str(tmp.options[2]) == 'Moodle for Teachers'
    exec(tmp.processor, globals())
    assert processor(0) == 100   # pylint: disable=E0602
    assert processor(1) == 0     # pylint: disable=E0602
    assert processor(2) == 0     # pylint: disable=E0602


def test_diff_simple():
    """Test differences between a files that was read, writen and read again
    """
    example = f"{TEST_PATH}/datasets/aiken/aiken_1.txt"
    control = category.Category.read_aiken(example)
    test = f"{example}.tmp"
    control.write_aiken(test)
    new_data = category.Category.read_aiken(test)
    os.remove(test)
    assert utils.Compare.compare(new_data, control)
    