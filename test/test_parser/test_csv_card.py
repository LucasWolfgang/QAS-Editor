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
from qas_editor.category import Category

TEST_PATH = os.path.dirname(os.path.dirname(__file__))


def _diff_file(file_name: str):
    control = Category.read_csvcard(file_name)
    XML_TEST = f"{file_name}.tmp"
    control.write_csvcard(XML_TEST)
    new_data = Category.read_csvcard(XML_TEST)
    assert control.compare(new_data, [])
    os.remove(XML_TEST)
    return control


def test_read_anki():
    cat = _diff_file(f"{TEST_PATH}/datasets/anki/math.txt")
    assert cat.get_size(False) == 91
    assert cat.get_size(True) == 91
    qst = cat.get_question(10)
    assert qst.question.get() == '2 x 1 ='