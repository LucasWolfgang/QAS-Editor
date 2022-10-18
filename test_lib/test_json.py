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


def test_read_essay():
    EXAMPLE = f"{TEST_PATH}/datasets/json/essay.json"
    control = Category.read_json(EXAMPLE)
    qst = control.get_question(0)
    assert qst.default_grade == 1.1
    assert qst.lines == 3
    assert qst.question.get() == 'Explain in few words the aim of this course.<br>' 
    assert qst.atts_required == False


def test_diff_all():
    _EXAMPLE = f"{TEST_PATH}/datasets/json/all.json"
    control = Category.read_json(_EXAMPLE)
    _TEST = f"{_EXAMPLE}.tmp"
    control.write_json(_TEST, True)
    new_data = Category.read_json(_TEST)
    assert control.compare(new_data, [])
    os.remove(_TEST)