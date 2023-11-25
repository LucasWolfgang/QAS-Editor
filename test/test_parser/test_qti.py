# Question and Answer Sheet Editor <https://github.com/LucasWolfgang/QAS-Editor>
# Copyright (C) 2022  Lucas Wolfgang
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
## Description

"""
import os
import shutil

import pytest

from qas_editor.category import Category
from qas_editor.parsers.ims import IMS, bb, canvas

TEST_PATH = os.path.dirname(os.path.dirname(__file__))

@pytest.fixture(scope="module")
def all_question_types():
    EXAMPLE = f"{TEST_PATH}/datasets/ims/canvas_all.imscc"
    TMP = f"{TEST_PATH}/datasets/ims/canvas_all_tmp"
    shutil.rmtree(TMP, ignore_errors=True)
    yield IMS(EXAMPLE, TMP)
    shutil.rmtree(TMP)


def test_read_manifest(all_question_types: IMS):
    all_question_types.get_manifest()


def test_read_canvas():
    EXAMPLE = f"{TEST_PATH}/datasets/ims/canvas_all.imscc"
    TMP = f"{TEST_PATH}/datasets/ims/canvas_all_tmp"
    cat = Category()
    shutil.rmtree(TMP, ignore_errors=True)
    canvas.read_cc_canvas(cat, EXAMPLE)


def test_read_bb8():
    EXAMPLE = f"{TEST_PATH}/datasets/ims/bb8.imscc"
    TMP = f"{TEST_PATH}/datasets/ims/bb8_tmp"
    cat = Category()
    shutil.rmtree(TMP, ignore_errors=True)
    bb.read_bb8(cat, EXAMPLE)
    

def test_write_bb():
    control = Category.read_moodle(f"{TEST_PATH}/datasets/moodle/multichoice.xml")
    bb.write_blackboard(control, f"{TEST_PATH}/datasets/test.tar")