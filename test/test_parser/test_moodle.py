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
from qas_editor.parsers import moodle

TEST_PATH = os.path.dirname(os.path.dirname(__file__))


def _diff_file(file_name):
    control = category.Category.read_moodle(file_name)
    XML_TEST = f"{file_name}.tmp"
    control.write_moodle(XML_TEST, True)
    new_data = category.Category.read_moodle(XML_TEST)
    assert control.compare(new_data, [])
    os.remove(XML_TEST)
    return control


def test_diff_calculated():
    _diff_file(f"{TEST_PATH}/datasets/moodle/calculated.xml")


def test_diff_calculatedsimple():
    _diff_file(f"{TEST_PATH}/datasets/moodle/calculatedsimple.xml")


def test_diff_calculatedmulti():
    _diff_file(f"{TEST_PATH}/datasets/moodle/calculatedmulti.xml")


def test_diff_cloze():
    _diff_file(f"{TEST_PATH}/datasets/moodle/cloze.xml")


def test_diff_ddwtos():
    _diff_file(f"{TEST_PATH}/datasets/moodle/ddwtos.xml")


def test_diff_ddmarker():
    _diff_file(f"{TEST_PATH}/datasets/moodle/ddmarker.xml")


def test_diff_ddimageortext():
    _diff_file(f"{TEST_PATH}/datasets/moodle/ddimageortext.xml")


def test_diff_essay():
    _diff_file(f"{TEST_PATH}/datasets/moodle/essay.xml")


def test_diff_gapselect():
    _diff_file(f"{TEST_PATH}/datasets/moodle/gapselect.xml")


def test_diff_multichoice():
    _diff_file(f"{TEST_PATH}/datasets/moodle/multichoice.xml")


def test_diff_description():
    """TODO - This testcase will soon change when QDescription class is removed
    and we start using the QProblem to define subquestions that has a macro
    description. The testcase may be the same, but the internal behavior will
    change and the test name too.
    """
    _diff_file(f"{TEST_PATH}/datasets/moodle/description.xml")


def test_diff_numerical():
    _diff_file(f"{TEST_PATH}/datasets/moodle/numerical.xml")


def test_diff_matching():
    _diff_file(f"{TEST_PATH}/datasets/moodle/matching.xml")


def test_diff_randomsamatch():
    """TODO - This testcase will soon changed, since this question is a just an
    easier way to randoming generated bigger matching questions. We may create
    an random class or something like that tha can hold the same values
    provided in a moodle's randomsamatch.
    """
    _diff_file(f"{TEST_PATH}/datasets/moodle/randomsamatch.xml")


def test_diff_shortanswer():
    _diff_file(f"{TEST_PATH}/datasets/moodle/shortanswer.xml")


def test_diff_truefalse():
    _diff_file(f"{TEST_PATH}/datasets/moodle/truefalse.xml")


def test_diff_all():
    _diff_file(f"{TEST_PATH}/datasets/moodle/all.xml")


def test_diff_backup():
    """TODO
    """
    pass