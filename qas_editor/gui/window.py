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
import traceback
from importlib import resources
from typing import TYPE_CHECKING
from PyQt5.QtCore import Qt, QVariant, QSize
from PyQt5.QtGui import QStandardItemModel, QIcon, QStandardItem
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFrame, QLabel, QGridLayout,\
                            QSplitter, QTreeView, QMainWindow, QStatusBar,\
                            QFileDialog, QMenu, QAction, QAbstractItemView,\
                            QScrollArea, QHBoxLayout, QGroupBox, QShortcut,\
                            QPushButton, QLineEdit, QComboBox, QDialog,\
                            QMessageBox, QListWidget, QCheckBox
from ..category import Category, EXTS
from ..question import _Question, QNAME
from ..utils import TList
from ..enums import Numbering, Grading, ShowUnits, RespFormat, Synchronise,\
                    Status, Distribution
from .widget import GTextToolbar, GTextEditor, GTagBar, GField, GCheckBox,\
                    GDropbox, GList
from .layout import GCollapsible, GOptions, GHintsList
if TYPE_CHECKING:
    from typing import List, Callable
    from PyQt5.QtGui import QDropEvent
    from PyQt5.QtCore import QModelIndex
LOG = logging.getLogger(__name__)


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
            LOG.exception(f"Error calling function {function.__name__}")
            self_arg = args[0]      # Needs to exists
            while not isinstance(self_arg, QWidget):
                self_arg = self_arg()
            dlg = QMessageBox(self_arg)
            dlg.setText(traceback.format_exc())
            dlg.setIcon(QMessageBox.Critical)
            dlg.show()
    return wrapper


class Editor(QMainWindow):
    """This is the main class.
    """

    SHORTCUTS = {
        "Create file": Qt.CTRL + Qt.Key_N,
        "Find questions": Qt.CTRL + Qt.Key_F,
        "Read file": Qt.CTRL + Qt.Key_O,
        "Read folder": Qt.CTRL + Qt.SHIFT + Qt.Key_O,
        "Save": Qt.CTRL + Qt.Key_S,
        "Save as": Qt.CTRL + Qt.SHIFT + Qt.Key_S,
        "Add hint": Qt.CTRL + Qt.SHIFT + Qt.Key_H,
        "Remove hint": Qt.CTRL + Qt.SHIFT + Qt.Key_Y,
        "Add answer": Qt.CTRL + Qt.SHIFT + Qt.Key_A,
        "Remove answer": Qt.CTRL + Qt.SHIFT + Qt.Key_Q,
        "Open datasets": Qt.CTRL + Qt.SHIFT + Qt.Key_D
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle("QAS Editor GUI")

        self._items: List[QWidget] = []
        self._main_editor = None
        self.path: tuple = None
        self.top_quiz = Category()
        self.cxt_menu = QMenu(self)
        self.cxt_item: QStandardItem = None
        self.cxt_data: _Question | Category = None
        self.cur_question: _Question = None
        self.tagbar: GTagBar = None
        self.main_editor: GTextEditor = None
        self.is_open_find = self.is_open_dataset = False

        with resources.open_text("qas_editor.gui", "stylesheet.css") as ifile:
            self.setStyleSheet(ifile.read())

        self._add_menu_bars()

        self.data_view = QTreeView()
        self.data_view.setIconSize(QSize(18, 18))
        xframe_vbox = self._block_datatree()
        left = QWidget()
        left.setLayout(xframe_vbox)

        self.cframe_vbox = QVBoxLayout()
        self._block_general_data()
        self._block_answer()
        self._block_hints()
        self._block_units()
        self._block_zones()
        self._block_solution()
        self._block_template()
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

        splitter = QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([250, 100])
        self.setCentralWidget(splitter)

        status = QStatusBar()
        self.setStatusBar(status)
        self.cat_name = QLabel()
        status.addWidget(self.cat_name)

        self._update_tree_item(self.top_quiz, self.root_item)
        self.data_view.expandAll()
        self.setGeometry(50, 50, 1200, 650)
        self.show()

    def debug_me(self):
        """TODO Method used for debugg...
        """
        self.path = ("./test/test_parser/datasets/moodle/all.xml", "Moodle")
        #self.path = "./test_lib/datasets/olx/test.olx"
        self.top_quiz = Category.read_moodle(self.path[0], "DEBUG")
        gtags = {}
        self.top_quiz.get_tags(gtags)
        self.tagbar.set_gtags(gtags)
        self.root_item.clear()
        self._update_tree_item(self.top_quiz, self.root_item)
        self.data_view.expandAll()

    def _add_menu_bars(self):
        file_menu = self.menuBar().addMenu("&File")
        tmp = QAction("New file", self)
        tmp.setStatusTip("New file")
        tmp.triggered.connect(self._create_file)
        tmp.setShortcut(self.SHORTCUTS["Create file"])
        file_menu.addAction(tmp)
        tmp = QAction("Open file", self)
        tmp.setStatusTip("Open file")
        tmp.triggered.connect(self._read_file)
        tmp.setShortcut(self.SHORTCUTS["Read file"])
        file_menu.addAction(tmp)
        tmp = QAction("Open folder", self)
        tmp.setStatusTip("Open folder")
        tmp.triggered.connect(self._read_folder)
        tmp.setShortcut(self.SHORTCUTS["Read folder"])
        file_menu.addAction(tmp)
        tmp = QAction("Save", self)
        tmp.setStatusTip("Save top category to specified file on disk")
        tmp.triggered.connect(lambda: self._write_file(False))
        tmp.setShortcut(self.SHORTCUTS["Save"])
        file_menu.addAction(tmp)
        tmp = QAction("Save As...", self)
        tmp.setStatusTip("Save top category to specified file on disk")
        tmp.triggered.connect(lambda: self._write_file(True))
        tmp.setShortcut(self.SHORTCUTS["Save as"])
        file_menu.addAction(tmp)

        file_menu = self.menuBar().addMenu("&Edit")
        tmp = QAction("Shortcuts", self)
        # TODO add a popup to list the shortcuts
        file_menu.addAction(tmp)
        tmp = QAction("Datasets", self)
        tmp.triggered.connect(self._open_dataset_popup)
        tmp.setShortcut(self.SHORTCUTS["Open datasets"])
        file_menu.addAction(tmp)
        tmp = QAction("Find Question", self)
        tmp.triggered.connect(self._open_find_popup)
        tmp.setShortcut(self.SHORTCUTS["Find questions"])
        file_menu.addAction(tmp)

        file_menu = self.menuBar().addMenu("&Options")
        tmp = QAction("Import", self)
        tmp.triggered.connect(self._open_dataset_popup)
        file_menu.addAction(tmp)

        file_menu = self.menuBar().addMenu("&Help")

        self.toolbar = GTextToolbar(self)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)

    def _add_new_category(self):
        popup = PopupName(self, True)
        popup.show()
        if not popup.exec():
            return
        self.cxt_data.add_subcat(popup.data)
        self._new_item(popup.data, self.cxt_item)

    def _add_new_question(self):
        popup = PopupQuestion(self, self.cxt_data)
        popup.show()
        if not popup.exec():
            return
        self._new_item(popup.question, self.cxt_item)

    @action_handler
    def _append_category(self):
        path, key = QFileDialog.getOpenFileName(self, "Open file", "", EXTS)
        if not path:
            return
        quiz = Category.read_files([path], path.rsplit("/", 1)[-1])
        self.cxt_data[quiz.name] = quiz
        self._update_tree_item(quiz, self.cxt_item)

    def _block_answer(self) -> None:
        frame = GCollapsible(self, "Answers")
        self.cframe_vbox.addLayout(frame)
        self._items.append(GOptions(self, self.toolbar, self.main_editor))
        _shortcut = QShortcut(self.SHORTCUTS["Add answer"], self)
        _shortcut.activated.connect(self._items[-1].add)
        _shortcut = QShortcut(self.SHORTCUTS["Remove answer"], self)
        _shortcut.activated.connect(self._items[-1].pop)
        frame.setLayout(self._items[-1])

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
        clayout = GCollapsible(self, "Question Header")
        self.cframe_vbox.addLayout(clayout, 1)
        grid = QVBoxLayout()    # No need of parent. It's inside GCollapsible
        grid.setSpacing(2)
        self.main_editor = GTextEditor(self.toolbar, "question")
        self._items.append(self.main_editor)
        self._items[-1].setToolTip("Question's description text")
        self._items[-1].setMinimumHeight(200)
        grid.addWidget(self._items[-1], 1)
        self.tagbar = GTagBar(self)
        self.tagbar.setToolTip("List of tags used by the question.")
        self._items.append(self.tagbar)
        grid.addWidget(self._items[-1], 0)
        others = QHBoxLayout()  # No need of parent. It's inside GCollapsible
        grid.addLayout(others, 0)
        others.addWidget(self._block_general_data_general(), 0)
        others.addWidget(self._block_general_data_unit_handling(), 1)
        others.addWidget(self._block_general_data_multichoice(), 1)
        others.addWidget(self._block_general_data_documents(), 1)
        others.addLayout(self._block_general_data_random(), 0)
        others.addWidget(self._block_general_data_datasets(), 2)
        others.addStretch()
        clayout.setLayout(grid)
        clayout.toggle()

    def _block_general_data_general(self):
        group_box = QGroupBox("General", self)
        _content = QVBoxLayout(group_box)
        _content.setSpacing(5)
        _content.setContentsMargins(5, 3, 5, 3)
        self._items.append(GField("dbid", self, int))
        self._items[-1].setToolTip("Optional ID for the question.")
        self._items[-1].setFixedWidth(50)
        _content.addWidget(self._items[-1], 0)
        self._items.append(GField("default_grade", self, int))
        self._items[-1].setToolTip("Default grade.")
        self._items[-1].setFixedWidth(50)
        self._items[-1].setText("1.0")
        _content.addWidget(self._items[-1], 0)
        self._items.append(GField("max_tries", self, str))
        self._items[-1].setToolTip("Max tries")
        self._items[-1].setFixedWidth(50)
        _content.addWidget(self._items[-1], 0)
        self._items.append(GField("time_lim", self, str))
        self._items[-1].setToolTip("Time limit (s)")
        self._items[-1].setFixedWidth(50)
        _content.addWidget(self._items[-1], 0)
        _content.addStretch()
        return group_box

    def _block_general_data_unit_handling(self):
        group_box = QGroupBox("Unit Handling", self)
        _content = QVBoxLayout(group_box)
        _content.setSpacing(5)
        _content.setContentsMargins(5, 3, 5, 3)
        self._items.append(GDropbox("grading_type", self, Grading))
        self._items[-1].setToolTip("Grading")
        self._items[-1].setMinimumWidth(80)
        _content.addWidget(self._items[-1], 0)
        self._items.append(GDropbox("show_units", self, ShowUnits))
        self._items[-1].setToolTip("Show units")
        _content.addWidget(self._items[-1], 0)
        self._items.append(GField("unit_penalty", self, float))
        self._items[-1].setToolTip("Unit Penalty")
        self._items[-1].setText("0.0")
        _content.addWidget(self._items[-1], 0)
        self._items.append(GCheckBox("left", "Left side", self))
        _content.addWidget(self._items[-1], 0)
        return group_box

    def _block_general_data_multichoice(self):
        group_box = QGroupBox("Multichoices", self)
        _content = QVBoxLayout(group_box)
        _content.setSpacing(5)
        _content.setContentsMargins(5, 3, 5, 3)
        self._items.append(GDropbox("numbering", self, Numbering))
        self._items[-1].setToolTip("How options will be enumerated")
        _content.addWidget(self._items[-1], 0)
        self._items.append(GCheckBox("show_instr", "Instructions", self))
        self._items[-1].setToolTip("If the structions 'select one (or more "
                                   " options)' should be shown")
        _content.addWidget(self._items[-1], 0)
        self._items.append(GCheckBox("single", "Multi answer", self))
        self._items[-1].setToolTip("If there is just a single or multiple "
                                   "valid answers")
        _content.addWidget(self._items[-1], 0)
        self._items.append(GCheckBox("shuffle", "Shuffle", self))
        self._items[-1].setToolTip("If answers should be shuffled (e.g. order "
                                   "of options will change each time)")
        _content.addWidget(self._items[-1], 0)
        return group_box

    def _block_general_data_documents(self):
        group_box = QGroupBox("Documents", self)
        _content = QGridLayout(group_box)
        _content.setSpacing(5)
        _content.setContentsMargins(5, 3, 5, 3)
        self._items.append(GDropbox("rsp_format", self, RespFormat))
        self._items[-1].setToolTip("The format to be used in the reponse.")
        _content.addWidget(self._items[-1], 0, 0, 1, 2)
        self._items.append(GCheckBox("rsp_required",
                                     "Required", self))
        self._items[-1].setToolTip("Require the student to enter some text.")
        _content.addWidget(self._items[-1], 0, 2)
        self._items.append(GField("min_words", self, int))
        self._items[-1].setToolTip("Minimum word limit")
        self._items[-1].setText("0")
        _content.addWidget(self._items[-1], 1, 0)
        self._items.append(GField("max_words", self, int))
        self._items[-1].setToolTip("Maximum word limit")
        self._items[-1].setText("10000")
        _content.addWidget(self._items[-1], 2, 0)
        self._items.append(GField("attachments", self, int))
        self._items[-1].setToolTip("Number of attachments required. 0 is none."
                                   " -1 is unlimited.")
        self._items[-1].setText("-1")
        _content.addWidget(self._items[-1], 1, 1)
        self._items.append(GCheckBox("atts_required", "Required", self))
        self._items[-1].setToolTip("If attachments are allowed.")
        _content.addWidget(self._items[-1], 1, 2)
        self._items.append(GField("lines", self, int))
        self._items[-1].setToolTip("Input box lines size.")
        self._items[-1].setText("15")
        _content.addWidget(self._items[-1], 2, 1)
        self._items.append(GField("max_bytes", self, int))
        self._items[-1].setToolTip("Maximum file size.")
        self._items[-1].setText("1Mb")
        _content.addWidget(self._items[-1], 2, 2)
        self._items.append(GField("file_types", self, str))
        self._items[-1].setToolTip("Accepted file types (comma separeted).")
        self._items[-1].setText(".txt, .pdf")
        _content.addWidget(self._items[-1], 3, 0, 1, 3)
        return group_box

    def _block_general_data_random(self):
        _wrapper = QVBoxLayout()  # No need of parent. It's inside GCollapsible
        group_box = QGroupBox("Random", self)
        _wrapper.addWidget(group_box)
        _content = QVBoxLayout(group_box)
        _content.setSpacing(5)
        _content.setContentsMargins(5, 3, 5, 3)
        self._items.append(GCheckBox("subcats", "Subcats", self))
        self._items[-1].setToolTip("If questions wshould be choosen from "
                                   "subcategories too.")
        _content.addWidget(self._items[-1])
        self._items.append(GField("choose", self, int))
        self._items[-1].setToolTip("Number of questions to select.")
        self._items[-1].setText("5")
        self._items[-1].setFixedWidth(85)
        _content.addWidget(self._items[-1])
        group_box = QGroupBox("Fill-in", self)
        _wrapper.addWidget(group_box)
        _content = QVBoxLayout(group_box)
        _content.setContentsMargins(5, 3, 5, 3)
        self._items.append(GCheckBox("use_case", "Match case", self))
        self._items[-1].setToolTip("If text is case sensitive.")
        _content.addWidget(self._items[-1])
        return _wrapper

    def _block_general_data_datasets(self):
        group_box = QGroupBox("Datasets", self)
        _content = QGridLayout(group_box)
        _content.setSpacing(5)
        _content.setContentsMargins(5, 3, 5, 3)
        self._items.append(GList("datasets", self))
        self._items[-1].setFixedHeight(70)
        self._items[-1].setToolTip("List of datasets used by this question.")
        _content.addWidget(self._items[-1], 0, 0, 1, 2)
        self._items.append(GDropbox("synchronize", self, Synchronise))
        self._items[-1].setToolTip("How should the databases be synchronized.")
        self._items[-1].setMinimumWidth(70)
        _content.addWidget(self._items[-1], 1, 0)
        _gen = QPushButton("Gen", self)
        _gen.setToolTip("Generate new items based on the max, min and decimal "
                        "values of the datasets, and the current solution.")
        _gen.clicked.connect(self._gen_items)
        _content.addWidget(_gen, 1, 1)
        return group_box

    def _block_hints(self):
        clayout = GCollapsible(self, "Hints")
        self.cframe_vbox.addLayout(clayout)
        self._items.append(GHintsList(None, self.toolbar))
        _shortcut = QShortcut(self.SHORTCUTS["Add hint"], self)
        _shortcut.activated.connect(self._items[-1].add)
        _shortcut = QShortcut(self.SHORTCUTS["Remove hint"], self)
        _shortcut.activated.connect(self._items[-1].pop)
        clayout.setLayout(self._items[-1])

    def _block_solution(self) -> None:
        collapsible = GCollapsible(self, "Solution and Feedback")
        self.cframe_vbox.addLayout(collapsible)
        layout = QVBoxLayout()
        collapsible.setLayout(layout)
        self._items.append(GTextEditor(self.toolbar, "remarks"))
        self._items[-1].setMinimumHeight(100)
        self._items[-1].setToolTip("General feedback for the question. May "
                                   "also be used to describe solutions.")
        layout.addWidget(self._items[-1])
        self._items.append(GCheckBox("show_num", "Show the number of correct r"
                                     "esponses once the question has finished",
                                      self))
        layout.addWidget(self._items[-1])
        _content = GOptions(self, self.toolbar, None)
        layout.addLayout(_content)

    def _block_template(self) -> None:
        collapsible = GCollapsible(self, "Templates")
        self.cframe_vbox.addLayout(collapsible)
        layout = QVBoxLayout()
        collapsible.setLayout(layout)
        self._items.append(GTextEditor(self.toolbar, "template"))
        self._items[-1].setMinimumHeight(70)
        self._items[-1].setToolTip("Text displayed in the response input box "
                                   "when a new attempet is started.")
        layout.addWidget(self._items[-1])
        self._items.append(GTextEditor(self.toolbar, "grader_info"))
        self._items[-1].setMinimumHeight(50)
        self._items[-1].setToolTip("Information for graders.")
        layout.addWidget(self._items[-1])
        self._items.append(GField("notes", self.toolbar, str))
        self._items[-1].setMinimumHeight(50)
        self._items[-1].setToolTip("Notes about the question.")
        layout.addWidget(self._items[-1])

    def _block_units(self):
        collapsible = GCollapsible(self, "Units")
        self.cframe_vbox.addLayout(collapsible)

    def _block_zones(self):
        collapsible = GCollapsible(self, "Background and Zones")
        self.cframe_vbox.addLayout(collapsible)

    @action_handler
    def _clone_shallow(self) -> None:
        new_data = copy.copy(self.cxt_data)
        self._new_item(new_data, self.cxt_item.parent())

    @action_handler
    def _clone_deep(self) -> None:
        new_data = copy.deepcopy(self.cxt_data)
        self._new_item(new_data, self.cxt_itemparent())

    @action_handler
    def _create_file(self, *_):
        self.top_quiz = Category()
        self.path = None
        self.root_item.clear()
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
            tmp = QAction("Delete", self)
            tmp.triggered.connect(self._delete_item)
            self.cxt_menu.addAction(tmp)
            tmp = QAction("Clone (Shallow)", self)
            tmp.triggered.connect(self._clone_shallow)
            self.cxt_menu.addAction(tmp)
            tmp = QAction("Clone (Deep)", self)
            tmp.triggered.connect(self._clone_deep)
            self.cxt_menu.addAction(tmp)
        if isinstance(self.cxt_data, Category):
            tmp = QAction("Save as", self)
            conn = tmp.triggered.connect
            conn(lambda: self._write_quiz(self.cxt_data, True))
            self.cxt_menu.addAction(tmp)
            tmp = QAction("Append", self)
            tmp.triggered.connect(self._append_category)
            self.cxt_menu.addAction(tmp)
            tmp = QAction("Sort", self)
            # TODO add sorting for the Category and Questions
            self.cxt_menu.addAction(tmp)
            tmp = QAction("New Question", self)
            tmp.triggered.connect(self._add_new_question)
            self.cxt_menu.addAction(tmp)
            tmp = QAction("New Category", self)
            tmp.triggered.connect(self._add_new_category)
            self.cxt_menu.addAction(tmp)
        self.cxt_menu.popup(self.data_view.mapToGlobal(event))

    @action_handler
    def _delete_item(self, *_):
        self.cxt_item.parent().removeRow(self.cxt_item.index().row())
        cat = self.cxt_data.parent
        if isinstance(self.cxt_data, _Question):
            cat.pop_question(self.cxt_data)
        elif isinstance(self.cxt_data, Category):
            cat.pop_subcat(self.cxt_data)

    @action_handler
    def _gen_items(self, _):
        pass

    @staticmethod
    def _new_item(data: Category | _Question, parent: QStandardItem):
        name = f"{data.__class__.__name__}_icon.png".lower()
        item = None
        with resources.path("qas_editor.images", name) as path:
            item = QStandardItem(QIcon(path.as_posix()), data.name)
            item.setEditable(False)
            item.setData(QVariant(data))
            parent.appendRow(item)
        return item

    @action_handler
    def _open_dataset_popup(self, _):
        if not self.is_open_dataset:
            popup = PopupDataset(self, self.top_quiz)
            popup.show()
            self.is_open_dataset = True

    @action_handler
    def _open_find_popup(self, _):
        if not self.is_open_find:
            popup = PopupFind(self, self.top_quiz, self.tagbar.cat_tags)
            popup.show()
            self.is_open_find = True

    @action_handler
    def _read_file(self, _):
        files, key = QFileDialog.getOpenFileNames(self, "Open file", "", EXTS)
        if not files:
            return
        # if len(files) == 1:
        #     self.path = files[0]
        # self.top_quiz = Category.read_files(files)
        # gtags = {}
        # self.top_quiz.get_tags(gtags)
        # self.tagbar.set_gtags(gtags)
        # self.root_item.clear()
        # self._update_tree_item(self.top_quiz, self.root_item)
        # self.data_view.expandAll()

    @action_handler
    def _read_folder(self, _):
        dialog = QFileDialog(self)
        dir_mode = QFileDialog.FileMode.Directory  # pylint: disable=E1101
        dialog.setFileMode(dir_mode)
        if not dialog.exec():
            return
        self.top_quiz = Category()
        self.path = None
        for folder in dialog.selectedFiles():
            cat = folder.rsplit("/", 1)[-1]
            quiz = Category.read_files(glob.glob(f"{folder}/*"), cat)
            self.top_quiz.add_subcat(quiz)
        gtags = {}
        self.top_quiz.get_tags(gtags)
        self.tagbar.set_gtags(gtags)
        self.root_item.clear()
        self._update_tree_item(self.top_quiz, self.root_item)
        self.data_view.expandAll()

    @action_handler
    def _rename_category(self, *_):
        popup = PopupName(self, False)
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
                if attr in item.__dict__ or attr in dir(item):
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
        item = self._new_item(data, parent)
        for k in data.questions:
            self._new_item(k, item)
        for k in data:
            self._update_tree_item(data[k], item)

    @action_handler
    def _write_quiz(self, quiz: Category, save_as: bool):
        if save_as or self.path is None:
            path, ext = QFileDialog.getSaveFileName(self, "Save file", "", EXTS)
            if not path:
                return (None, None)
        else:
            path, ext = self.path
        quiz.write(ext.strip(), path)
        return path, ext

    @action_handler
    def _write_file(self, save_as: bool) -> None:
        data = self._write_quiz(self.top_quiz, save_as)
        if data and data[0]:
            self.path = data


class PopupDataset(QWidget):
    """UI for the data listed in <code>Dataset</code> class.
    """

    def __init__(self, parent, top: Category):
        super().__init__(parent)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Datasets")
        datasets = {}
        top.get_datasets(datasets)
        self.__datasets = datasets
        self.__cur_data = None
        _content = QGridLayout(self)
        _list = QListWidget(self)
        _list.addItems(datasets)
        _list.blockSignals(True)
        _list.currentItemChanged.connect(self.__changed_dataset)
        _list.blockSignals(False)
        _content.addWidget(_list, 0, 0, 4, 2)
        _add = QPushButton("Add", self)
        _add.setToolTip("")
        _content.addWidget(_add, 4, 0)
        _new = QPushButton("New", self)
        _new.setToolTip("If the dataset if private or public")
        _content.addWidget(_new, 4, 1)
        self._status = GDropbox("status", self, Status)
        self._status.setToolTip("")
        self._status.setFixedWidth(120)
        _content.addWidget(self._status, 0, 2)
        self._name = GField("name", self, str)
        self._name.setToolTip("Name of the dataset")
        _content.addWidget(self._name, 0, 3)
        self._ctype = GField("ctype", self, str)
        self._ctype.setToolTip("")
        _content.addWidget(self._ctype, 0, 4, 1, 2)
        self._dist = GDropbox("distribution", self, Distribution)
        self._dist.setToolTip("How the values are distributed in the dataset")
        self._dist.setFixedWidth(120)
        _content.addWidget(self._dist, 1, 2)
        self._min = GField("minimum", self, float)
        self._min.setToolTip("Minimum value in the dataset")
        _content.addWidget(self._min, 1, 3)
        self._max = GField("maximum", self, float)
        self._max.setToolTip("Maximum value in the dataset")
        _content.addWidget(self._max, 1, 4)
        self._dec = GField("decimals", self, int)
        self._dec.setToolTip("Number of decimals used in the dataset items")
        _content.addWidget(self._dec, 1, 5)
        self._items = GList("items", self)
        self._items.setToolTip("Dataset items")
        self._items.setFixedWidth(110)
        _content.addWidget(self._items, 2, 2, 3, 1)
        self._classes = QListWidget(self)
        self._classes.setToolTip("Instances that uses the current dataset")
        _content.addWidget(self._classes, 2, 3, 2, 3)
        self._key = QLineEdit(self)
        self._key.setToolTip("Item that will be updated (key value)")
        _content.addWidget(self._key, 4, 3)
        self._value = QLineEdit(self)
        self._value.setToolTip("Value to be used in the dataset's item update")
        _content.addWidget(self._value, 4, 4)
        _update = QPushButton("Update", self)
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


class PopupFind(QWidget):
    """A find window.
    """

    def __init__(self, parent, top: Category, gtags: dict):
        super().__init__(parent)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Find")
        _content = QGridLayout(self)
        self._by_title = QCheckBox("By title", self)
        _content.addWidget(self._by_title, 0, 0)
        self._title = QLineEdit(self)
        _content.addWidget(self._title, 0, 1)
        self._by_tags = QCheckBox("By tags", self)
        _content.addWidget(self._by_tags, 1, 0)
        self._tags = TList(str)
        _tagbar = GTagBar(self)
        _tagbar.from_list(self._tags)
        _tagbar.set_gtags(gtags)
        _content.addWidget(_tagbar, 1, 1)
        self._by_text = QCheckBox("By text", self)
        _content.addWidget(self._by_text, 2, 0)
        self._text = QLineEdit(self)
        _content.addWidget(self._text, 2, 1)
        self._by_qtype = QCheckBox("By type", self)
        _content.addWidget(self._by_qtype, 3, 0)
        self._qtype = QComboBox(self)
        self._qtype.addItems(QNAME)
        _content.addWidget(self._qtype, 3, 1)
        self._by_dbid = QCheckBox("By dbid", self)
        _content.addWidget(self._by_dbid, 4, 0)
        self._dbid = QLineEdit(self)
        _content.addWidget(self._dbid, 4, 1)
        _find = QPushButton("Find", self)
        _find.clicked.connect(self._find_me)
        _content.addWidget(_find, 5, 0, 1, 2)
        self._reslist = QListWidget(self)
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


class PopupQuestion(QDialog):
    """ Popup to create a new Question instance.
    """

    def __init__(self, parent, quiz: Category):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Create Question")
        self.__quiz = quiz
        question_create = QPushButton("Create", self)
        question_create.clicked.connect(self._create_question)
        self.__type = QComboBox(self)
        self.__type.addItems(QNAME)
        self.__name = QLineEdit(self)
        vbox = QVBoxLayout(self)
        vbox.addWidget(self.__type)
        vbox.addWidget(self.__name)
        vbox.addWidget(question_create)
        self.question = None

    @action_handler
    def _create_question(self, _):
        name = self.__name.text()
        self.question = QNAME[self.__type.currentText()](name=name)
        if self.__quiz.add_question(self.question):
            self.accept()
        else:
            self.reject()


class PopupName(QDialog):
    """ Popup to name or rename instances, eiter Category or Question.
    """

    def __init__(self, parent, new_cat, suggestion=""):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Create" if new_cat else "Rename")
        category_create = QPushButton("Ok", self)
        action = self._create_category if new_cat else self._update_name
        category_create.clicked.connect(action)
        self._category_name = QLineEdit(self)
        self._category_name.setFocus()
        self._category_name.setText(suggestion)
        vbox = QVBoxLayout(self)
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


class PopupImportOpt(QWidget):
    """A popup to list options used while importing databases.
    """

    def __init__(self, parent: Editor):
        super().__init__(parent)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Import Options")


class PopupExportOpt(QWidget):
    """A popup to list options used while exporting databases.
    """

    def __init__(self, parent: Editor):
        super().__init__(parent)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Export Options")
