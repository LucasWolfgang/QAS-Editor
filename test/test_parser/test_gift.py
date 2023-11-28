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
    assert qst.dbid == 432
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
    lang = enums.Language.EN_US
    assert control.get_size(True) == 2
    qst = control.get_question(0)
    assert qst.dbid == None
    assert len(qst.feedback) == 0
    assert qst.name[lang] == 'match1'
    assert qst.tags == []
    assert len(qst.body[lang].text) == 2
    assert qst.body[lang].text[0][0] == ('Match the cool Moodle features with'
                                ' the version in which they first appeared\:')
    assert len(qst.body[lang].text[1].seta) == 4
    assert len(qst.body[lang].text[1].setb) == 4


def test_read_missing_word():
    EXAMPLE = f"{TEST_PATH}/datasets/gift/missing_words.gift"
    control = category.Category.read_gift(EXAMPLE)
    lang = enums.Language.EN_US
    assert control.get_size(True) == 1
    qst = control.get_question(0)
    assert qst.dbid == None
    assert len(qst.feedback) == 0
    assert qst.name[lang] == 'default'
    assert qst.tags == []
    assert len(qst.body[lang].text) == 3
    assert qst.body[lang].text[2] == ' to download from moodle.org.'
    assert len(qst.body[lang].text[1].options) == 3
    assert qst.body[lang].text[1].processor.func(None)["value"] == 0
    assert qst.body[lang].text[1].processor.func(0)["value"] == 0
    assert qst.body[lang].text[1].processor.func(1)["value"] == 100

def test_read_multichoice():
    EXAMPLE = f"{TEST_PATH}/datasets/gift/multichoice.gift"
    control = category.Category.read_gift(EXAMPLE)
    lang = enums.Language.EN_US
    assert control.get_size(True) == 4
    qst = control.get_question(2)
    assert qst.dbid == 1015
    assert len(qst.feedback) == 1
    assert qst.feedback[lang].text[0][0][0] == 'Remember - the developer docs Release notes are your friend!\xa0'
    assert qst.name[lang] == 'Multichoice3'
    assert qst.tags == []
    assert len(qst.body[lang].text) == 3
    assert qst.body[lang].text[1][0] == 'When was Moodle 3.0 released?'
    assert len(qst.body[lang].text[2].options) == 3
    assert qst.body[lang].text[2].processor.func(None)["value"] == 0
    assert qst.body[lang].text[2].processor.func(1)["value"] == 100
    assert qst.body[lang].text[2].processor.func(2)["value"] == 0
