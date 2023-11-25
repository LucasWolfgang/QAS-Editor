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

from qas_editor import answer, category, enums, utils

TEST_PATH = os.path.dirname(os.path.dirname(__file__))

def test_read_all():
    """_summary_
    """
    example = f"{TEST_PATH}/datasets/cloze/cloze.cloze"
    lang = enums.Language.EN_US
    tmp = category.Category.read_cloze(example, lang)
    assert tmp.get_size(True) == 1
    question = tmp.get_question(0)
    assert len(question.body[lang].text) == 17
    item = question.body[lang].text[3]
    assert isinstance(item, answer.EntryItem)
    assert len(item.feedbacks) == 3
    assert item.feedbacks[1].text == ['Feedback for correct answer']
    assert item.processor.func("Correct answer")["value"] == 1
    assert item.processor.func("Answer that gives half the credit")["value"] == 0.5
    assert item.processor.func("Wrong answer")["value"] == 0
    assert item.processor.func("Random Stuff")["value"] == 0


def test_diff_simple():
    """_summary_
    """
    example = f"{TEST_PATH}/datasets/cloze/cloze.cloze"
    lang = enums.Language.EN_US
    control = category.Category.read_cloze(example, lang)
    cloze_test = f"{TEST_PATH}/datasets/cloze/cloze_0.cloze"
    control.write_cloze(cloze_test, lang, "\n\n")
    new_data = category.Category.read_cloze(cloze_test, lang)
    assert utils.Compare.compare(new_data, control)
    os.remove(cloze_test)
