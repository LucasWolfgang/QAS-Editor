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
from __future__ import annotations
from typing import TYPE_CHECKING
from PyQt5 import QtWidgets, Qt, QtGui, QtCore
from .utils import action_handler, HOTKEYS, key_name
from ..enums import Distribution, Status
from ..utils import TList
from ..question import QNAME
from ..category import Category
from .. import __author__, __version__, __doc__
if TYPE_CHECKING:
    from .window import Editor


class PDataset(QtWidgets.QWidget):
    """UI for the data listed in <code>Dataset</code> class.
    """

    def __init__(self, parent, top: Category):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Datasets")
        datasets = {}
        top.get_datasets(datasets)
        self.__datasets = datasets
        self.__cur_data = None
        _content = QtWidgets.QGridLayout(self)
        _list = QtWidgets.QListWidget(self)
        _list.addItems(datasets)
        _list.blockSignals(True)
        _list.currentItemChanged.connect(self.__changed_dataset)
        _list.blockSignals(False)
        _content.addWidget(_list, 0, 0, 4, 2)
        _add = QtWidgets.QPushButton("Add", self)
        _add.setToolTip("")
        _content.addWidget(_add, 4, 0)
        _new = QtWidgets.QPushButton("New", self)
        _new.setToolTip("If the dataset if private or public")
        _content.addWidget(_new, 4, 1)
        self._status = QtWidgets.GDropbox("status", self, Status)
        self._status.setToolTip("")
        self._status.setFixedWidth(120)
        _content.addWidget(self._status, 0, 2)
        self._name = QtWidgets.GField("name", self, str)
        self._name.setToolTip("Name of the dataset")
        _content.addWidget(self._name, 0, 3)
        self._ctype = QtWidgets.GField("ctype", self, str)
        self._ctype.setToolTip("")
        _content.addWidget(self._ctype, 0, 4, 1, 2)
        self._dist = QtWidgets.GDropbox("distribution", self, Distribution)
        self._dist.setToolTip("How the values are distributed in the dataset")
        self._dist.setFixedWidth(120)
        _content.addWidget(self._dist, 1, 2)
        self._min = QtWidgets.GField("minimum", self, float)
        self._min.setToolTip("Minimum value in the dataset")
        _content.addWidget(self._min, 1, 3)
        self._max = QtWidgets.GField("maximum", self, float)
        self._max.setToolTip("Maximum value in the dataset")
        _content.addWidget(self._max, 1, 4)
        self._dec = QtWidgets.GField("decimals", self, int)
        self._dec.setToolTip("Number of decimals used in the dataset items")
        _content.addWidget(self._dec, 1, 5)
        self._items = QtWidgets.GList("items", self)
        self._items.setToolTip("Dataset items")
        self._items.setFixedWidth(110)
        _content.addWidget(self._items, 2, 2, 3, 1)
        self._classes = QtWidgets.QListWidget(self)
        self._classes.setToolTip("Instances that uses the current dataset")
        _content.addWidget(self._classes, 2, 3, 2, 3)
        self._key = QtWidgets.QLineEdit(self)
        self._key.setToolTip("Item that will be updated (key value)")
        _content.addWidget(self._key, 4, 3)
        self._value = QtWidgets.QLineEdit(self)
        self._value.setToolTip("Value to be used in the dataset's item update")
        _content.addWidget(self._value, 4, 4)
        _update = QtWidgets.QPushButton("Update", self)
        _update.setToolTip("Update one item in the dataset using the "
                           "values provided in the field on the left")
        _update.clicked.connect(self.__update_items)
        _content.addWidget(_update, 4, 5)
        self.setGeometry(100, 100, 600, 400)

    def __changed_dataset(self, current, _):
        self.__cur_data, classes = self.__datasets[current.text()]
        self._status.from_obj(self.__cur_data)
        self._name.from_obj(self.__cur_data)
        self._ctype.from_obj(self.__cur_data)
        self._dec.from_obj(self.__cur_data)
        self._dist.from_obj(self.__cur_data)
        self._min .from_obj(self.__cur_data)
        self._max.from_obj(self.__cur_data)
        self._items.from_obj(self.__cur_data)
        self._classes.clear()
        for _cls in classes:
            self._classes.addItem(str(_cls))

    @action_handler
    def __update_items(self, _):
        key = int(self._key.text())
        value = float(self._value.text())
        self.__cur_data.items[key] = value
        self._items.from_obj(self.__cur_data)

    def closeEvent(self, _):  # pylint: disable=C0103
        """ Closing event
        """
        self.parent().is_open_dataset = False


class PExportOpt(QtWidgets.QWidget):
    """A popup to list options used while exporting databases.
    """

    def __init__(self, parent: Editor):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Export Options")


class PFind(QtWidgets.QWidget):
    """A find window.
    """

    def __init__(self, parent, top: Category, gtags: dict):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Find")
        _content = QtWidgets.QGridLayout(self)
        self._by_title = QtWidgets.QCheckBox("By title", self)
        _content.addWidget(self._by_title, 0, 0)
        self._title = QtWidgets.QLineEdit(self)
        _content.addWidget(self._title, 0, 1)
        self._by_tags = QtWidgets.QCheckBox("By tags", self)
        _content.addWidget(self._by_tags, 1, 0)
        self._tags = TList[str]()
        _tagbar = QtWidgets.GTagBar(self)
        _tagbar.from_list(self._tags)
        _tagbar.set_gtags(gtags)
        _content.addWidget(_tagbar, 1, 1)
        self._by_text = QtWidgets.QCheckBox("By text", self)
        _content.addWidget(self._by_text, 2, 0)
        self._text = QtWidgets.QLineEdit(self)
        _content.addWidget(self._text, 2, 1)
        self._by_qtype = QtWidgets.QCheckBox("By type", self)
        _content.addWidget(self._by_qtype, 3, 0)
        self._qtype = QtWidgets.QComboBox(self)
        self._qtype.addItems(QNAME)
        _content.addWidget(self._qtype, 3, 1)
        self._by_dbid = QtWidgets.QCheckBox("By dbid", self)
        _content.addWidget(self._by_dbid, 4, 0)
        self._dbid = QtWidgets.QLineEdit(self)
        _content.addWidget(self._dbid, 4, 1)
        _find = QtWidgets.QPushButton("Find", self)
        _find.clicked.connect(self._find_me)
        _content.addWidget(_find, 5, 0, 1, 2)
        self._reslist = QtWidgets.QListWidget(self)
        _content.addWidget(self._reslist, 0, 2, 7, 1)
        _content.setVerticalSpacing(2)
        _content.setColumnStretch(1, 1)
        _content.setColumnStretch(2, 2)
        self._res = []
        self._category = top

    @action_handler
    def _find_me(self, _):
        title = self._title.text() if self._by_title.isChecked() else None
        tags = list(self._tags) if self._by_tags.isChecked() else None
        text = self._text.text() if self._by_text.isChecked() else None
        qtype = QNAME[self._qtype.currentText()] if \
            self._by_qtype.isChecked() else None
        dbid = int(self._dbid.text()) if self._by_dbid.isChecked() else None
        if all(item is None for item in [title, tags, text, qtype, dbid]):
            return
        self._res.clear()
        self._reslist.clear()
        self._category.find(self._res, title, tags, text, qtype, dbid)
        name = []
        for data in self._res:
            name.clear()
            parent = data
            while parent.parent is not None:
                name.append(parent.name)
                parent = parent.parent
            name.reverse()
            self._reslist.addItem(" > ".join(name))

    def closeEvent(self, _):   # pylint: disable=C0103
        """ Closing event
        """
        self.parent().is_open_find = False


class PAbout(QtWidgets.QWidget):

    def __init__(self, parent: Editor):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Help")
        _content = QtWidgets.QGridLayout(self)
        _content.setSpacing(5)
        _content.addWidget(QtWidgets.QLabel("Name:", self), 0, 0)
        item = QtWidgets.QLabel("Question and Answer Sheet editor", self)
        _content.addWidget(item, 0, 1)
        _content.addWidget(QtWidgets.QLabel("Author:", self), 1, 0)
        _content.addWidget(QtWidgets.QLabel(__author__, self), 1, 1)
        _content.addWidget(QtWidgets.QLabel("Version:", self), 2, 0)
        _content.addWidget(QtWidgets.QLabel(__version__, self), 2, 1)
        _content.setSizeConstraint(3) # Fixed sized based on sizeHint


class PTips(QtWidgets.QWidget):

    text = """\n\nUsage tips:\n
        * The structure of the module is based on the Moodle XML, but has already
    a considerable number of modifications to handle other formats. 

        * The GUI is heavily based on Hotkeys and Tooltips to make the GUI as fast
    and as clean as possible. Hostkeys are listed in Edit > Hotkeys.

        * The GUI also uses a lot of Popups and Context Menus. If there is no
    hotkey for what you need it is because you will be able to access it on one
    of these 2 other ways. For instance, to create a new category, right click
    an existing category and select "New Category".

        * Most of the common hotkeys also work as expected (ctrl+c, ctrl+v, etc)
    but you can't change them.
        
        * To see the types of questions that can be currently created, right-click
    any category and select "New Category".
    """

    def __init__(self, parent: Editor):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Help")
        _content = QtWidgets.QGridLayout(self)
        _content.setSpacing(5)
        _content.setContentsMargins(20, 20, 20, 20)
        _content.addWidget(QtWidgets.QLabel(__doc__ + self.text, self), 0, 0)
        _content.setSizeConstraint(3) # Fixed sized based on sizeHint


class PImportOpt(QtWidgets.QWidget):
    """A popup to list options used while importing databases.
    """

    def __init__(self, parent: Editor):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Import Options")


class PQuestion(QtWidgets.QDialog):
    """ Popup to create a new Question instance.
    """

    def __init__(self, parent, quiz: Category):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Create Question")
        self.__quiz = quiz
        question_create = QtWidgets.QPushButton("Create", self)
        question_create.clicked.connect(self._create_question)
        self.__type = QtWidgets.QComboBox(self)
        self.__type.addItems(QNAME)
        self.__name = QtWidgets.QLineEdit(self)
        vbox = QtWidgets.QVBoxLayout(self)
        vbox.addWidget(self.__type)
        vbox.addWidget(self.__name)
        vbox.addWidget(question_create)
        self.question = None
        vbox.setSizeConstraint(3) # Fixed sized based on sizeHint

    @action_handler
    def _create_question(self, _):
        name = self.__name.text()
        self.question = QNAME[self.__type.currentText()](name=name)
        if self.__quiz.add_question(self.question):
            self.accept()
        else:
            self.reject()


class PName(QtWidgets.QDialog):
    """ Popup to name or rename instances, eiter Category or Question.
    """

    def __init__(self, parent, new_cat, suggestion=""):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Create" if new_cat else "Rename")
        category_create = QtWidgets.QPushButton("Ok", self)
        action = self._create_category if new_cat else self._update_name
        category_create.clicked.connect(action)
        self._category_name = QtWidgets.QLineEdit(self)
        self._category_name.setFocus()
        self._category_name.setText(suggestion)
        vbox = QtWidgets.QVBoxLayout(self)
        vbox.addWidget(self._category_name)
        vbox.addWidget(category_create)
        self.data = None

    @action_handler
    def _create_category(self, _) -> None:
        name = self._category_name.text()
        if not name:
            self.reject()
        self.data = Category(name)
        self.accept()

    @action_handler
    def _update_name(self, _) -> None:
        name = self._category_name.text()
        if not name:
            self.reject()
        self.data = name
        self.accept()


class PHotkey(QtWidgets.QWidget):
    """A popup to list the hotkey options.
    """

    def __init__(self, parent: Editor):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Hotkeys")
        self.items = {}
        _content = QtWidgets.QGridLayout(self)
        _content.setSpacing(5)
        _content.setContentsMargins(20, 20, 20, 20)
        row = 1
        col = 0
        self.lkey = (0, "")
        self.klabel = QtWidgets.QLabel(self)
        self.klabel.setText("Current key: ")
        self.klabel.setStyleSheet('background: silver; padding: 5; margin: 0 0 10 0')
        _content.setVerticalSpacing(0)
        for key, value in HOTKEYS.items():
            item = QtWidgets.QPushButton(key_name(value), self)
            item.clicked.connect(self.connected)
            #item.setStyleSheet('padding: 1 0 1 0; solid white')
            _content.addWidget(item, row, col)
            item = QtWidgets.QLabel(self)
            item.setText(key)
            item.setStyleSheet('padding: 5 10 5 0 solid white')
            _content.addWidget(item, row, col + 1)
            self.items[key] = item
            row +=1
            if row > 10:
                row = 1
                col += 3
        _content.setColumnStretch(2, 1)
        _content.addWidget(self.klabel, 0, 0, 1, col+2)
        _content.setSizeConstraint(3) # Fixed sized based on sizeHint

    def connected(self):
        key, text = self.lkey
        if not key:
            return
        button = self.sender()
        for value in HOTKEYS.values():
            if value == key:
                return
        HOTKEYS[button.text()] = key
        button.setText(text)

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        key = event.key()
        print(hex(key), hex(QtWidgets.QApplication.keyboardModifiers()))
        key += int(QtWidgets.QApplication.keyboardModifiers())
        text = key_name(key)
        if text:
            self.klabel.setText(f"Current key: '{text}'")
            self.lkey = (key, text)
        return super().keyPressEvent(event)