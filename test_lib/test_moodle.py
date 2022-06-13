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

import os
from qas_editor import category

TEST_PATH = os.path.dirname(__file__)
SRC_PATH = os.path.abspath(os.path.join(TEST_PATH, '..'))


def test_diff_all():
    EXAMPLE = f"{TEST_PATH}/datasets/moodle/all.xml"
    control = category.Category.read_moodle(EXAMPLE)
    XML_TEST = f"{EXAMPLE}.tmp"
    control.write_moodle(XML_TEST, True)
    new_data = category.Category.read_moodle(XML_TEST)
    assert control.compare(new_data, [])
    os.remove(XML_TEST)


def test_against_json():
    EXAMPLE = f"{TEST_PATH}/datasets/moodle/all.xml"
    data = category.Category.read_moodle(EXAMPLE)
    XML_TEST = f"{TEST_PATH}/datasets/json/all.json"
    # data.write_json(XML_TEST)
    control = category.Category.read_json(XML_TEST)
    assert control.compare(data, [])


def test_diff_calculated():
    EXAMPLE = f"{TEST_PATH}/datasets/moodle/calculated.xml"
    control = category.Category.read_moodle(EXAMPLE)
    XML_TEST = f"{EXAMPLE}.tmp"
    control.write_moodle(XML_TEST, True)
    new_data = category.Category.read_moodle(XML_TEST)
    assert control.compare(new_data, [])
    os.remove(XML_TEST)
