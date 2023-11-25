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

from qas_editor.gui import popup

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


def test_gfield_update(qtbot: "QtBot"):
    app = QApplication([])
    tmp = popup.PHotkey(None)
    tmp.show()
    app.exec()