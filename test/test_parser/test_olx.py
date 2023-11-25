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

from qas_editor.category import Category
from qas_editor.parsers import olx

TEST_PATH = os.path.dirname(os.path.dirname(__file__))

# This is just a temporary way to test the input/outputs while validation that
# the tests are actually working.
# https://github.com/mitodl/openedx-course-test
DOCKER = "docker run -i -t -v \"/path/to/course_dir\":\"/course\" -w /test_course mitodl/openedx-course-test bash -e test_course"

def test_read_course():
    EXAMPLE = f"{TEST_PATH}/datasets/olx/course.tar.xz"
    tmp = olx.read_olx(Category, EXAMPLE)
    raise tmp