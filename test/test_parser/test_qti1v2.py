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
from qas_editor._parsers import qti1v2, bb
from qas_editor.category import Category

TEST_PATH = os.path.dirname(os.path.dirname(__file__))


def test_read():
    EXAMPLE = f"{TEST_PATH}/datasets/qti1v2/item.zip"
    parser = qti1v2.QTIParser1_2()
    

def test_write_bb():
    control = Category.read_moodle(f"{TEST_PATH}/datasets/moodle/multichoice.xml")
    bb.write_blackboard(control, f"{TEST_PATH}/datasets/test.tar")