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
from qas_editor import category


def test_xml_all():
    EXAMPLE = f"{test_path}/datasets/moodle/all.xml"
    control = category.Category.read_xml(EXAMPLE)
    XML_TEST = f"{EXAMPLE}.tmp"
    control.write_xml(XML_TEST, True)
    new_data = category.Category.read_xml(XML_TEST)
    os.remove(XML_TEST)
    assert control.compare(new_data, [])


def test_xml_vs_json():
    EXAMPLE = f"{test_path}/datasets/moodle/all.xml"
    data = category.Category.read_xml(EXAMPLE)
    XML_TEST = f"{test_path}/datasets/moodle/all.json"
    # data.write_json(XML_TEST)
    control = category.Category.read_json(XML_TEST)
    assert control.compare(data, [])


def test_xml_calculated():
    EXAMPLE = f"{test_path}/datasets/moodle/calculated.xml"
    control = category.Category.read_xml(EXAMPLE)
    XML_TEST = f"{EXAMPLE}.tmp"
    control.write_xml(XML_TEST, True)
    new_data = category.Category.read_xml(XML_TEST)
    os.remove(XML_TEST)
    assert control.compare(new_data, [])

def test_xml_hello():
    pass