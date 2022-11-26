"""
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
import traceback
import logging
from typing import Callable
from PyQt5 import QtWidgets, QtCore


IMG_PATH = __file__.replace('\\', '/').rsplit('/', 2)[0] + "/images"

_LOG = logging.getLogger(__name__)

HOTKEYS = {
    "Open hotkeys": QtCore.Qt.CTRL + QtCore.Qt.ALT + QtCore.Qt.Key_H,
    "Create file": QtCore.Qt.CTRL + QtCore.Qt.Key_N,
    "Find questions": QtCore.Qt.CTRL + QtCore.Qt.Key_F,
    "Read file": QtCore.Qt.CTRL + QtCore.Qt.Key_O,
    "Read folder": QtCore.Qt.CTRL + QtCore.Qt.SHIFT + QtCore.Qt.Key_O,
    "Save file": QtCore.Qt.CTRL + QtCore.Qt.Key_S,
    "Save file as": QtCore.Qt.CTRL + QtCore.Qt.SHIFT + QtCore.Qt.Key_S,
    "Add hint": QtCore.Qt.CTRL + QtCore.Qt.SHIFT + QtCore.Qt.Key_H,
    "Remove hint": QtCore.Qt.CTRL + QtCore.Qt.SHIFT + QtCore.Qt.Key_Y,
    "Add answer": QtCore.Qt.CTRL + QtCore.Qt.SHIFT + QtCore.Qt.Key_A,
    "Remove answer": QtCore.Qt.CTRL + QtCore.Qt.SHIFT + QtCore.Qt.Key_Q,
    "Open datasets": QtCore.Qt.CTRL + QtCore.Qt.SHIFT + QtCore.Qt.Key_D
}


def action_handler(function: Callable) -> Callable:
    """_summary_
    Args:
        function (Callable): _description_
    Returns:
        Callable: _description_
    """
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception:   # pylint: disable=W0703
            _LOG.exception(f"Error calling function {function.__name__}")
            self_arg = args[0]      # Needs to exists
            while not isinstance(self_arg, QtWidgets.QWidget):
                self_arg = self_arg()
            dlg = QtWidgets.QMessageBox(self_arg)
            dlg.setText(traceback.format_exc())
            dlg = QtWidgets.QMessageBox(self_arg)
            dlg.setIcon(QtWidgets.QMessageBox.Critical)
            dlg.show()
    return wrapper


def key_name(value: int):
    text = ""
    if value & 0x1000000 or 0x20 > value & 0x7f > 0x7f:
        return text
    if value & QtCore.Qt.CTRL:
        text += "CTRL + "
    if value & QtCore.Qt.ALT:
        text += "ALT + "
    if value & QtCore.Qt.SHIFT:
        text += "SHIFT + "
    text += chr(value & 0x7f)
    return text