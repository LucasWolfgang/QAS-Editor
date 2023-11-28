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

from qas_editor import category, enums, utils

TEST_PATH = os.path.dirname(os.path.dirname(__file__))


def test_read_all():
    """_summary_
    """
    file_name = f"{TEST_PATH}/datasets/anki/math.txt"
    lang = enums.Language.EN_US
    control = category.Category.read_csvcard(file_name, lang)
    assert control.get_size(False) == 91
    assert control.get_size(True) == 91
    qst = control.get_question(10)
    assert qst.body[lang][0] == '2 x 1 ='


def test_diff_simple():
    """_summary_
    """
    file_name = f"{TEST_PATH}/datasets/anki/math.txt"
    tmp_test = f"{file_name}.tmp"
    lang = enums.Language.EN_US
    control = category.Category.read_csvcard(file_name, lang)
    control.write_csvcard(tmp_test, lang)
    new_data = category.Category.read_csvcard(tmp_test, lang)
    assert utils.Compare.compare(new_data, control)
    os.remove(tmp_test)
    return control
