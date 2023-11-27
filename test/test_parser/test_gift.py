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

from qas_editor import category, enums

TEST_PATH = os.path.dirname(os.path.dirname(__file__))

def test_read_all():
    EXAMPLE = f"{TEST_PATH}/datasets/gift/all.gift"
    control = category.Category.read_gift(EXAMPLE)
    control = control["qas editor"]
    assert len(control) == 9
    assert control.get_size() == 0
    assert control.get_size(True) == 22
    mq = control["Multichoice"]
    question = mq.get_question(2)
    assert question.remarks.get() == ("<p><span style\\=\"font-size\: 14px;\">"
            "Remember - the developer docs Release notes are your friend!"
            "&nbsp;</span><a href\\=\"http\://docs.moodle.org/dev/Releases\""
            " style\\=\"font-size\\: 14px;\">http\\://docs.moodle.org/dev/"
            "Releases</a><br></p>")
    assert len(question.options) == 3
    assert question.options[1].text == ('<p><span style\\="font-size\\: 14px;'
                                        '">November 2015</span><br></p>')


def test_read_essay():
    EXAMPLE = f"{TEST_PATH}/datasets/gift/essay.gift"
    control = category.Category.read_gift(EXAMPLE)
    lang = enums.Language.EN_US
    assert control.get_size(True) == 2
    qst = control.get_question(0)
    assert qst.dbid == "432"
    assert len(qst.feedback) == 0
    assert qst.name[lang] == 'Essay 1'
    assert qst.tags == ['Advanced', 'ad']
    assert len(qst.body[lang].text) == 6
    assert qst.body[lang].text[2][0] == ('In 50 words, explain which question'
            ' type you think you will use the most \xa0-and why - and then '
            'which question type you will use the least - and why?')

def test_read_matching():
    EXAMPLE = f"{TEST_PATH}/datasets/gift/matching.gift"
    control = category.Category.read_gift(EXAMPLE)
    control = control["qas editor"]
    