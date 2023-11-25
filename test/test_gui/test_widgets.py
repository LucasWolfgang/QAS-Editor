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
from typing import TYPE_CHECKING

from PyQt5.QtWidgets import QApplication

from qas_editor.gui import widget

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


class ContentClass:
    def __init__(self, content):
        self.content = content


def test_gfield_update(qtbot: "QtBot"):
    obj = ContentClass("some text")
    gfield = widget.GField("content", None, str)
    qtbot.addWidget(gfield)
    assert gfield.text() != "some text"    # Initial test is not the new one
    gfield.from_obj(obj)
    assert gfield.text() == "some text"    # Method from_obj set widget text
    obj.content = "other text"
    assert gfield.text() != "other text"   # obj updates dont change widget
    gfield.clear()
    QApplication.setActiveWindow(gfield)
    qtbot.keyClicks(QApplication.focusWidget(), "last one")
    assert gfield.text() == "last one"     # Widget text should update, but it 
    assert obj.content != "last one"       # should not dont change obj content    
    # QApplication.setActiveWindow(other)
    # assert obj.content == "last one"       # Widget should now update
    # TODO - Need to find a way to test last step

def test_gdrag(qtbot: "QtBot"):
    obj = widget.GDrag()