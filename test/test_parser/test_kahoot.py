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


def test_diff_all():
    EXAMPLE = f"{TEST_PATH}/datasets/kahoot/kahoot.csv"
    lang = enums.Language.EN_US
    control = category.Category.read_kahoot(EXAMPLE, lang)
    _TEST = f"{EXAMPLE}.tmp"
    control.write_kahoot(_TEST, lang)
    data = category.Category.read_kahoot(_TEST, lang)
    assert utils.Compare.compare(data, control)
    os.remove(_TEST)