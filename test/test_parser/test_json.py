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


TEST_PATH = os.path.dirname(os.path.dirname(__file__))


def _diff_file(file_name):
    control = Category.read_json(file_name)
    XML_TEST = f"{file_name}.tmp"
    control.write_json(XML_TEST, True)
    new_data = Category.read_json(XML_TEST)
    assert control.compare(new_data, [])
    os.remove(XML_TEST)
    return control


def test_read_qcalculated():
    cat = _diff_file(f"{TEST_PATH}/datasets/json/qcalculated.json")


def test_read_qcalculatedmc():
    cat = _diff_file(f"{TEST_PATH}/datasets/json/qcalculatedmc.json")


def test_read_qembedded():
    cat = _diff_file(f"{TEST_PATH}/datasets/json/qembedded.json")


def test_read_qessay():
    cat = _diff_file(f"{TEST_PATH}/datasets/json/qessay.json")
    qst = cat.get_question(0)
    assert qst.default_grade == 1.1
    assert qst.lines == 3
    assert qst.question.get() == 'Explain in few words the aim of this course.<br>' 
    assert qst.atts_required == False


def test_read_qdadimage():
    cat = _diff_file(f"{TEST_PATH}/datasets/json/qdadimage.json")


def test_read_qdadmarker():
    cat = _diff_file(f"{TEST_PATH}/datasets/json/qdadmarker.json")


def test_read_qdadtext():
    EXAMPLE = f"{TEST_PATH}/datasets/json/qdadtext.json"
    control = Category.read_json(EXAMPLE)
    qst = control.get_question(0)
    assert qst.max_tries == 3
    assert len(qst.options) == 7


def test_read_qmissingword():
    cat = _diff_file(f"{TEST_PATH}/datasets/json/qmissingword.json")


def test_read_qmatching():
    cat = _diff_file(f"{TEST_PATH}/datasets/json/qmatching.json")


def test_read_qmultichoice():
    cat = _diff_file(f"{TEST_PATH}/datasets/json/qmultichoice.json")


def test_read_qnumerical():
    cat = _diff_file(f"{TEST_PATH}/datasets/json/qnumerical.json")


def test_read_qshortanswer():
    cat = _diff_file(f"{TEST_PATH}/datasets/json/qshortanswer.json")


def test_read_qtruefalse():
    cat = _diff_file(f"{TEST_PATH}/datasets/json/qtruefalse.json")


def test_diff_all():
    _EXAMPLE = f"{TEST_PATH}/datasets/json/all.json"
    control = Category.read_json(_EXAMPLE)
    _TEST = f"{_EXAMPLE}.tmp"
    control.write_json(_TEST, True)
    new_data = Category.read_json(_TEST)
    assert control.compare(new_data, [])
    os.remove(_TEST)