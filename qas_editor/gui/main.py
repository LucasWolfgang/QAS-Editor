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

from __future__ import annotations
import glob
import logging
import copy
import os
from typing import TYPE_CHECKING
from PyQt5.QtCore import Qt, QVariant, QSize
from PyQt5.QtGui import QStandardItemModel, QIcon, QStandardItem
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFrame, QLabel, QGridLayout,\
                            QSplitter, QTreeView, QMainWindow, QStatusBar,\
                            QFileDialog, QMenu, QAction, QAbstractItemView,\
                            QPushButton, QScrollArea, QHBoxLayout, QGroupBox

from .popups import NamePopup, QuestionPopup
from ..quiz import Category
from ..questions import _Question
from ..enums import Numbering, Grading, ShowUnits
from .utils import GCollapsible, GTextToolbar, GTextEditor, GTagBar, IMG_PATH,\
                   GField, GCheckBox, GDropbox, action_handler
from .forms import GOptions
if TYPE_CHECKING:
    from typing import Dict
    from PyQt5.QtGui import QDropEvent
    from PyQt5.QtCore import QModelIndex
LOG = logging.getLogger(__name__)


class Editor(QMainWindow):
    """This is the main class.
    """

    FORMATS = ("Aiken (*.txt);;Cloze (*.cloze);;GIFT (*.gift);;JSON (*.json)"
               ";;LaTex (*.tex);;Markdown (*.md);;PDF (*.pdf);;XML (*.xml)")

    SERIALIZER = {"cloze":  ("write_cloze"),
                  "json":   ("write_json"),
                  "gift":   ("write_gift"),
                  "md":     ("write_markdown"),
                  "pdf":    ("write_pdf"),
                  "tex":    ("write_latex"),
                  "txt":    ("write_aiken"),
                  "xml":    ("write_xml")}

    GRADE = {"Ignore": "IGNORE", "Fraction of reponse": "RESPONSE",
             "Fraction of question": "QUESTION"}

    SHOW_UNITS = {"Text input": "TEXT", "Multiple choice": "MC",
                  "Drop-down": "DROP_DOWN", "Not visible": "NONE"}

    def __init__(self, *args, **kwargs):
        super(Editor, self).__init__(*args, **kwargs)
        self.setWindowTitle("QAS Editor GUI")

        self._items = []
        self.path: str = None
        self.top_quiz = Category()
        self.cxt_menu = QMenu(self)
        self.cxt_item: QStandardItem = None
        self.cxt_data: _Question = None
        self.cur_question: _Question = None

        self._add_menu_bars()

        # Left side
        self.data_view = QTreeView()
        self.data_view.setIconSize(QSize(18, 18))
        xframe_vbox = self._block_datatree()
        left = QWidget()
        left.setLayout(xframe_vbox)

        # Right side
        self.cframe_vbox = QVBoxLayout()
        self._block_general_data()
        self._block_answer()
        self._block_multiple_tries()
        self._block_solution()
        # self._block_database()
        self.cframe_vbox.addStretch()
        self.cframe_vbox.setSpacing(5)
        for value in self._items:
            value.setEnabled(False)

        frame = QFrame()
        frame.setLineWidth(2)
        frame.setLayout(self.cframe_vbox)
        right = QScrollArea()
        right.setWidget(frame)
        right.setWidgetResizable(True)

        # Create main window divider for the splitter
        splitter = QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([250, 100])
        self.setCentralWidget(splitter)

        # Create lower status bar.
        status = QStatusBar()
        self.setStatusBar(status)
        self.cat_name = QLabel()
        status.addWidget(self.cat_name)

        self._update_tree_item(self.top_quiz, self.root_item)
        self.data_view.expandAll()
        self.setGeometry(300, 300, 1000, 600)
        self.show()

    def _add_menu_bars(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        new_file = QAction("New file", self)
        new_file.setStatusTip("New file")
        new_file.triggered.connect(self._create_file)
        file_menu.addAction(new_file)
        open_file = QAction("Open file", self)
        open_file.setStatusTip("Open file")
        open_file.triggered.connect(self._read_file)
        file_menu.addAction(open_file)
        open_folder = QAction("Open folder", self)
        open_folder.setStatusTip("Open folder")
        open_folder.triggered.connect(self._read_folder)
        file_menu.addAction(open_folder)
        save_file = QAction("Save", self)
        save_file.setStatusTip("Save top category to specified file on disk")
        save_file.triggered.connect(lambda: self._write_file(False))
        file_menu.addAction(save_file)
        saveas_file = QAction("Save As...", self)
        saveas_file.setStatusTip("Save top category to specified file on disk")
        saveas_file.triggered.connect(lambda: self._write_file(True))
        file_menu.addAction(saveas_file)
        self.toolbar = GTextToolbar()
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)

    def _add_new_category(self):
        popup = NamePopup(True)
        popup.show()
        if not popup.exec():
            return
        self.cxt_data[popup.data.name] = popup.data
        self._new_item(popup.data, self.cxt_item, "question")

    def _add_new_question(self):
        popup = QuestionPopup(self.cxt_data)
        popup.show()
        if not popup.exec():
            return
        self._new_item(popup.question, self.cxt_item, "question")

    @action_handler
    def _append_category(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open file", "",
                                              self.FORMATS)
        if not path:
            return None
        quiz = Category.read_files([path], path.rsplit("/", 1)[-1])
        self.cxt_data[quiz.name] = quiz
        self._update_tree_item(quiz, self.cxt_item)

    def _block_answer(self) -> None:
        frame = GCollapsible(title="Answers")
        self.cframe_vbox.addLayout(frame)

        group_box = QGroupBox("Unit Handling", self)
        _content = QGridLayout(group_box)
        _content.addWidget(QLabel("Grading"), 0, 0,  Qt.AlignmentFlag.AlignRight)
        self._items.append(GDropbox(self, Grading, "grading_type", self.GRADE))
        self._items[-1].addItems(self.GRADE.__iter__())
        _content.addWidget(self._items[-1], 0, 1)
        _content.addWidget(QLabel("Penalty"), 0, 2, Qt.AlignmentFlag.AlignLeft)
        self._items.append(GField(float, "penalty"))
        self._items[-1].setText("0")
        _content.addWidget(self._items[-1], 0, 3)
        _content.addWidget(QLabel("Show units"), 1, 0)
        self._items.append(GDropbox(self, ShowUnits, "show_units"))
        self._items[-1].addItems(self.SHOW_UNITS.__iter__())
        _content.addWidget(self._items[-1], 1, 1)
        self._items.append(GCheckBox(self, "Put units on the left", "left"))
        _content.addWidget(self._items[-1], 1, 2, 1, 2)
        _content.setContentsMargins(5, 3, 5, 3)
        _content.setVerticalSpacing(0)

        grid = QGridLayout()
        frame.setLayout(grid)
        self._items.append(GDropbox(self, str, "numbering"))
        self._items[-1].addItems([c.value for c in Numbering])
        self._items[-1].setToolTip("")
        grid.addWidget(self._items[-1], 0, 0)

        self._items.append(GCheckBox(self, "Show instructions", "show_instr"))
        grid.addWidget(self._items[-1], 1, 0)
        self._items.append(GCheckBox(self, "Single answer", "single"))
        self._items[-1].setContentsMargins(10, 0, 0, 0)
        grid.addWidget(self._items[-1], 0, 2)
        self._items.append(GCheckBox(self, "Shuffle answers", "shuffle"))
        grid.addWidget(self._items[-1], 1, 2)
        grid.addWidget(group_box, 0, 3, 2, 1)
        self._items.append(GOptions(self.toolbar))
        aabutton = QPushButton("Add Answer")
        aabutton.clicked.connect(self._items[-1].add_default)
        ppbutton = QPushButton("Pop Answer")
        ppbutton.clicked.connect(self._items[-1].pop)
        grid.addWidget(aabutton, 0, 4)
        grid.addWidget(ppbutton, 1, 4)
        grid.addLayout(self._items[-1], 2, 0, 1, 5)
        grid.setColumnStretch(4, 1)
        grid.setVerticalSpacing(0)

    def _block_database(self) -> None:
        frame = GCollapsible(title="Database")
        self.cframe_vbox.addLayout(frame)

    def _block_datatree(self) -> QVBoxLayout:
        self.data_view.setStyleSheet("margin: 5px 5px 0px 5px")
        self.data_view.setHeaderHidden(True)
        self.data_view.doubleClicked.connect(self._update_item)
        self.data_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.data_view.customContextMenuRequested.connect(self._data_view_cxt)
        self.data_view.setDragEnabled(True)
        self.data_view.setAcceptDrops(True)
        self.data_view.setDropIndicatorShown(True)
        self.data_view.setDragDropMode(QAbstractItemView.InternalMove)
        self.data_view.original_dropEvent = self.data_view.dropEvent
        self.data_view.dropEvent = self._dataview_dropevent
        self.root_item = QStandardItemModel(0, 1)
        self.root_item.setHeaderData(0, Qt.Horizontal, "Classification")
        self.data_view.setModel(self.root_item)

        xframe_vbox = QVBoxLayout()
        xframe_vbox.addWidget(self.data_view)
        return xframe_vbox

    def _block_general_data(self) -> None:
        frame = GCollapsible(self, title="General Data")
        self.cframe_vbox.addLayout(frame)

        grid = QGridLayout()
        grid.addWidget(QLabel("Tags"), 0, 0)
        self._items.append(GTagBar(self))
        self._items[-1].setToolTip("List of tags used by the question.")
        grid.addWidget(self._items[-1], 0, 1)
        grid.setColumnStretch(1, 1)
        tmp = QLabel("Default grade")
        tmp.setContentsMargins(10, 0, 0, 0)
        grid.addWidget(tmp, 0, 2)
        self._items.append(GField(int, "default_grade"))
        self._items[-1].setFixedWidth(30)
        self._items[-1].setToolTip("Default grade.")
        grid.addWidget(self._items[-1], 0, 3)
        tmp = QLabel("ID")
        tmp.setContentsMargins(10, 0, 0, 0)
        grid.addWidget(tmp, 0, 4)
        self._items.append(GField(int, "dbid"))
        self._items[-1].setFixedWidth(40)
        self._items[-1].setToolTip("Optional ID for the question.")
        grid.addWidget(self._items[-1], 0, 5)
        self._items.append(GTextEditor(self.toolbar, "question"))
        self._items[-1].setMinimumHeight(100)
        self._items[-1].setToolTip("Tags used to ")
        grid.addWidget(self._items[-1], 1, 0, 1, 6)
        frame.setLayout(grid)
        frame.toggle_collapsed()

    def _block_multiple_tries(self) -> None:
        frame = GCollapsible(self, title="Multiple Tries")
        self.cframe_vbox.addLayout(frame)
        _header = QHBoxLayout()
        _header.addWidget(QLabel("Penalty", self))
        self._items.append(GField(str, "penalty"))
        self._items[-1].setText("0")
        _header.addWidget(self._items[-1])
        add = QPushButton("Add Hint", self)
        # add.clicked.connect(self._add_hint)
        _header.addWidget(add)
        rem = QPushButton("Remove Last", self)
        # rem.clicked.connect(self.pop)
        _header.addWidget(rem)
        _header.setStretch(1, 1)
        frame.setLayout(_header)

    def _block_solution(self) -> None:
        collapsible = GCollapsible(title="Solution and Feedback")
        self.cframe_vbox.addLayout(collapsible)
        layout = QVBoxLayout()
        collapsible.setLayout(layout)
        self._items.append(GTextEditor(self.toolbar, "feedback"))
        self._items[-1].setFixedHeight(50)
        self._items[-1].setToolTip("General feedback for the question. May "
                                   "also be used to describe solutions.")
        layout.addWidget(self._items[-1])
        sframe = QFrame(self)
        sframe.setStyleSheet(".QFrame{border:1px solid rgb(41, 41, 41);"
                             "background-color: #e4ebb7}")
        layout.addWidget(sframe)
        _content = QGridLayout(self)
        _content.addWidget(QLabel("Feedback for correct answer"), 0, 0)
        self._items.append(GTextEditor(self.toolbar, "if_correct"))
        _content.addWidget(self._items[-1], 1, 0)
        _content.addWidget(QLabel("Feedback for incomplete answer"), 0, 1)
        self._items.append(GTextEditor(self.toolbar, "if_incomplete"))
        _content.addWidget(self._items[-1], 1, 1)
        _content.addWidget(QLabel("Feedback for incorrect answer"), 0, 2)
        self._items.append(GTextEditor(self.toolbar, "if_incorrect"))
        _content.addWidget(self._items[-1], 1, 2)
        self._items.append(GCheckBox(self, "Show the number of correct "
                                     "responses once the question has finished"
                                     , "show_num"))
        _content.addWidget(self._items[-1], 2, 0, 1, 3)
        _content.setColumnStretch(3, 1)
        sframe.setLayout(_content)

    @action_handler
    def _create_file(self):
        self.top_quiz = Category()
        self.path = None
        self._update_tree_item(self.top_quiz, self.root_item)

    @action_handler
    def _dataview_dropevent(self, event: QDropEvent):
        from_obj = self.data_view.selectedIndexes()[0].data(257)
        to_obj = self.data_view.indexAt(event.pos()).data(257)
        if isinstance(to_obj, Category):
            if isinstance(from_obj, _Question):
                to_obj.add_subcat(from_obj)
            else:
                to_obj.add_question(from_obj)
        else:
            event.ignore()
        self.data_view.original_dropEvent(event)

    def _data_view_cxt(self, event):
        model_idx = self.data_view.indexAt(event)
        self.cxt_item = self.root_item.itemFromIndex(model_idx)
        self.cxt_data = model_idx.data(257)
        self.cxt_menu.clear()
        rename = QAction("Rename", self)
        rename.triggered.connect(self._rename_category)
        self.cxt_menu.addAction(rename)
        if self.cxt_item != self.root_item.item(0):
            delete = QAction("Delete", self)
            delete.triggered.connect(self._delete_item)
            self.cxt_menu.addAction(delete)
            clone = QAction("Clone (Shallow)", self)
            clone.triggered.connect(self._clone_shallow)
            self.cxt_menu.addAction(clone)
            clone = QAction("Clone (Deep)", self)
            clone.triggered.connect(self._clone_deep)
            self.cxt_menu.addAction(clone)
        if isinstance(self.cxt_data, Category):
            save_as = QAction("Save as", self)
            save_as.triggered.connect(lambda: self._write_quiz(self.cxt_data,
                                                               True))
            self.cxt_menu.addAction(save_as)
            append = QAction("Append", self)
            append.triggered.connect(self._append_category)
            self.cxt_menu.addAction(append)
            rename = QAction("New Question", self)
            rename.triggered.connect(self._add_new_question)
            self.cxt_menu.addAction(rename)
            append = QAction("New Category", self)
            append.triggered.connect(self._add_new_category)
            self.cxt_menu.addAction(append)
        self.cxt_menu.popup(self.data_view.mapToGlobal(event))

    @action_handler
    def _delete_item(self):
        self.cxt_item.parent().removeRow(self.cxt_item.index().row())
        cat = self.cxt_data.parent
        if isinstance(self.cxt_data, _Question):
            cat.pop_question(self.cxt_data)
        elif isinstance(self.cxt_data, Category):
            cat.pop_subcat(self.cxt_data)

    @action_handler
    def _clone_shallow(self) -> None:
        new_data = copy.copy(self.cxt_data)
        self._new_item(new_data, self.cxt_item.parent(), "question")

    @action_handler
    def _clone_deep(self) -> None:
        new_data = copy.deepcopy(self.cxt_data)
        self._new_item(new_data, self.cxt_itemparent(), "question")

    def _new_item(self, data: Category, parent: QStandardItem, title: str):
        path = f"{IMG_PATH}/{data.__class__.__name__}_icon.png".lower()
        if not os.path.isfile(path):
            path = f"{IMG_PATH}/{title}_icon.png"
        item = QStandardItem(QIcon(path), data.name)
        item.setEditable(False)
        item.setData(QVariant(data))
        parent.appendRow(item)
        return item

    @action_handler
    def _read_file(self, *args):
        files, _ = QFileDialog.getOpenFileNames(self, "Open file", "",
                                                self.FORMATS)
        if not files:
            return None
        if len(files) == 1:
            self.path = files[0]
        self.top_quiz = Category.read_files(files)
        self.root_item.clear()
        self._update_tree_item(self.top_quiz, self.root_item)
        self.data_view.expandAll()

    @action_handler
    def _read_folder(self, *args):
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        if not dialog.exec():
            return None
        self.top_quiz = Category()
        self.path = None
        for folder in dialog.selectedFiles():
            cat = folder.rsplit("/", 1)[-1]
            quiz = Category.read_files(glob.glob(f"{folder}/*"), cat)
            self.top_quiz.add_subcat(quiz)
        self.root_item.clear()
        self._update_tree_item(self.top_quiz, self.root_item)
        self.data_view.expandAll()

    @action_handler
    def _rename_category(self):
        popup = NamePopup(False)
        popup.show()
        if not popup.exec():
            return
        self.cxt_data.name = popup.data
        self.cxt_item.setText(popup.data)

    @action_handler
    def _update_item(self, model_index: QModelIndex) -> None:
        item = model_index.data(257)
        if isinstance(item, _Question):
            for key in self._items:
                attr = key.get_attr()
                if attr in item.__dict__:
                    key.setEnabled(True)
                    key.from_obj(item)
                else:
                    key.setEnabled(False)
            self.cur_question = item
        path = [f" ({item.__class__.__name__})"]
        while item.parent:
            path.append(item.name)
            item = item.parent
        path.append(item.name)
        path.reverse()
        self.cat_name.setText(" > ".join(path[:-1]) + path[-1])

    def _update_tree_item(self, data: Category, parent: QStandardItem) -> None:
        item = self._new_item(data, parent, "category")
        for k in data.questions:
            self._new_item(k, item, "question")
        for k in data:
            self._update_tree_item(data[k], item)

    def _write_quiz(self, quiz: Category, save_as: bool):
        if save_as:
            path, _ = QFileDialog.getSaveFileName(self, "Save file", "",
                                                  self.FORMATS)
            if not path:
                return None
        else:
            path = self.path
        ext = path.rsplit('.', 1)[-1]
        quiz.__getattribute__(self.SERIALIZER[ext][0])(path)
        return path

    @action_handler
    def _write_file(self, save_as: bool) -> None:
        path = self._write_quiz(self.top_quiz, save_as)
        if path:
            self.path = path
