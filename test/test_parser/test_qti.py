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
import shutil
import pytest
from qas_editor._parsers.ims import qti1v2, bb, IMS, canvas
from qas_editor.category import Category

TEST_PATH = os.path.dirname(os.path.dirname(__file__))

@pytest.fixture(scope="module")
def all_question_types():
    EXAMPLE = f"{TEST_PATH}/datasets/ims/canvas_all_question_types.imscc"
    TMP = f"{TEST_PATH}/datasets/ims/canvas_all_question_types_tmp"
    shutil.rmtree(TMP, ignore_errors=True)
    yield IMS(EXAMPLE, TMP)
    shutil.rmtree(TMP)

def test_read_manifest(all_question_types: IMS):
    all_question_types.get_manifest()


def test_read_canvas():
    EXAMPLE = f"{TEST_PATH}/datasets/ims/canvas_all_question_types.imscc"
    TMP = f"{TEST_PATH}/datasets/ims/canvas_all_question_types_tmp"
    cat = Category()
    shutil.rmtree(TMP, ignore_errors=True)
    canvas.read_cc_canvas(cat, EXAMPLE)

def test_read():
    EXAMPLE = f"{TEST_PATH}/datasets/qti1v2/item.zip"
    parser = qti1v2.QTIParser1v2()
    parser.read(EXAMPLE)
    

def test_write_bb():
    control = Category.read_moodle(f"{TEST_PATH}/datasets/moodle/multichoice.xml")
    bb.write_blackboard(control, f"{TEST_PATH}/datasets/test.tar")