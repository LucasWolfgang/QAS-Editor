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
from importlib import resources
from typing import TYPE_CHECKING
from PyQt5.QtCore import Qt, QVariant, QSize
from PyQt5.QtGui import QStandardItemModel, QIcon, QStandardItem
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFrame, QLabel, QGridLayout,\
                            QSplitter, QTreeView, QMainWindow, QStatusBar,\
                            QFileDialog, QMenu, QAction, QAbstractItemView,\
                            QScrollArea, QHBoxLayout, QGroupBox, QShortcut

from .popups import NamePopup, QuestionPopup
from ..quiz import Category
from ..questions import _Question
from ..enums import Numbering, Grading, ShowUnits, ResponseFormat, Synchronise
from .utils import GCollapsible, GTextToolbar, GTextEditor, GTagBar, IMG_PATH,\
                   GField, GCheckBox, GDropbox, GList, action_handler
from .forms import GOptions, GHintsList
if TYPE_CHECKING:
    from typing import List, Callable
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

    SHORTCUTS = {
        "Create file": Qt.CTRL + Qt.Key_N,
        "Read file": Qt.CTRL + Qt.Key_O,
        "Read folder": Qt.CTRL + Qt.SHIFT + Qt.Key_O,
        "Save": Qt.CTRL + Qt.Key_S,
        "Save as": Qt.CTRL + Qt.SHIFT + Qt.Key_S,
        "Add hint in the end": Qt.CTRL + Qt.SHIFT + Qt.Key_H,
        "Remove selected hint": Qt.CTRL + Qt.SHIFT + Qt.Key_J,
        "Add answer": Qt.CTRL + Qt.SHIFT + Qt.Key_A,
        "Remove answer": Qt.CTRL + Qt.SHIFT + Qt.Key_D
    }

    def __init__(self, *args, **kwargs):
        super(Editor, self).__init__(*args, **kwargs)
        self.setWindowTitle("QAS Editor GUI")

        self._items: List[QWidget] = []
        self.path: str = None
        self.top_quiz = Category()
        self.cxt_menu = QMenu(self)
        self.cxt_item: QStandardItem = None
        self.cxt_data: _Question = None
        self.cur_question: _Question = None
        self.set_gtags: Callable = None

        with resources.open_text("qas_editor.gui", "stylesheet.css") as fh:
            self.setStyleSheet(fh.read())

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
        new_file.setShortcut(self.SHORTCUTS["Create file"])
        file_menu.addAction(new_file)
        open_file = QAction("Open file", self)
        open_file.setStatusTip("Open file")
        open_file.triggered.connect(self._read_file)
        open_file.setShortcut(self.SHORTCUTS["Read file"])
        file_menu.addAction(open_file)
        open_folder = QAction("Open folder", self)
        open_folder.setStatusTip("Open folder")
        open_folder.triggered.connect(self._read_folder)
        open_folder.setShortcut(self.SHORTCUTS["Read folder"])
        file_menu.addAction(open_folder)
        save_file = QAction("Save", self)
        save_file.setStatusTip("Save top category to specified file on disk")
        save_file.triggered.connect(lambda: self._write_file(False))
        save_file.setShortcut(self.SHORTCUTS["Save"])
        file_menu.addAction(save_file)
        saveas_file = QAction("Save As...", self)
        saveas_file.setStatusTip("Save top category to specified file on disk")
        saveas_file.triggered.connect(lambda: self._write_file(True))
        saveas_file.setShortcut(self.SHORTCUTS["Save as"])
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
        self._items.append(GOptions(self.toolbar))
        _shortcut = QShortcut(self.SHORTCUTS["Add answer"], self)
        _shortcut.activated.connect(self._items[-1].pop)
        _shortcut = QShortcut(self.SHORTCUTS["Remove answer"], self)
        _shortcut.activated.connect(self._items[-1].add)
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
        frame = GCollapsible(self, title="Question Header")
        self.cframe_vbox.addLayout(frame, 0)

        grid = QVBoxLayout()    # No need of parent. It's inside GCollapsible
        grid.setSpacing(2)

        self._items.append(GTextEditor(self.toolbar, "question"))
        self._items[-1].setToolTip("Question's description text")
        self._items[-1].setMinimumHeight(100)
        grid.addWidget(self._items[-1], 0)
        self._items.append(GTagBar(self))
        self._items[-1].setToolTip("List of tags used by the question.")
        self.set_gtags = self._items[-1].set_gtags
        grid.addWidget(self._items[-1], 1)
        
        others = QHBoxLayout()  # No need of parent. It's inside GCollapsible
        grid.addLayout(others, 0)

        group_box = QGroupBox("General", self)
        _content = QVBoxLayout(group_box)
        _content.setSpacing(5)
        _content.setContentsMargins(5, 3, 5, 3)
        self._items.append(GField(self, int, "dbid"))
        self._items[-1].setToolTip("Optional ID for the question.")
        self._items[-1].setFixedWidth(50)
        _content.addWidget(self._items[-1], 0)
        self._items.append(GField(self, int, "default_grade"))
        self._items[-1].setToolTip("Default grade.")
        self._items[-1].setFixedWidth(50)
        self._items[-1].setText("1.0")
        _content.addWidget(self._items[-1], 0)
        self._items.append(GField(self, str, "penalty"))
        self._items[-1].setToolTip("Penalty")
        self._items[-1].setFixedWidth(50)
        self._items[-1].setText("0.0")
        _content.addWidget(self._items[-1], 0)
        _content.addStretch()

        others.addWidget(group_box, 0)

        group_box = QGroupBox("Unit Handling", self)
        _content = QVBoxLayout(group_box)
        _content.setSpacing(5)
        _content.setContentsMargins(5, 3, 5, 3)
        self._items.append(GDropbox(self, "grading_type", Grading))
        self._items[-1].setToolTip("Grading")
        _content.addWidget(self._items[-1], 0)
        self._items.append(GDropbox(self, "show_units", ShowUnits))
        self._items[-1].setToolTip("Show units")
        _content.addWidget(self._items[-1], 0)
        self._items.append(GField(self, float, "unit_penalty"))
        self._items[-1].setToolTip("Unit Penalty")
        self._items[-1].setText("0.0")
        _content.addWidget(self._items[-1], 0)
        self._items.append(GCheckBox(self, "Put units on the left", "left"))
        _content.addWidget(self._items[-1], 0)
        others.addWidget(group_box, 1)

        group_box = QGroupBox("Multichoices", self)
        _content = QVBoxLayout(group_box)
        _content.setSpacing(5)
        _content.setContentsMargins(5, 3, 5, 3)
        self._items.append(GDropbox(self, "numbering", Numbering))
        self._items[-1].setToolTip("How options will be enumerated")
        _content.addWidget(self._items[-1], 0)
        self._items.append(GCheckBox(self, "Show instructions", "show_instr"))
        self._items[-1].setToolTip("If the structions 'select one (or more "
                                   " options)' should be shown")
        _content.addWidget(self._items[-1], 0)
        self._items.append(GCheckBox(self, "Allow multiple", "single"))
        self._items[-1].setToolTip("If there is just a single or multiple "
                                   "valid answers")
        _content.addWidget(self._items[-1], 0)
        self._items.append(GCheckBox(self, "Shuffle answers", "shuffle"))
        self._items[-1].setToolTip("If answers should be shuffled (e.g. order "
                                   "of options will change each time)")
        _content.addWidget(self._items[-1], 0)
        others.addWidget(group_box, 1)

        group_box = QGroupBox("Documents", self)
        _content = QGridLayout(group_box)
        _content.setSpacing(5)
        _content.setContentsMargins(5, 3, 5, 3)
        self._items.append(GDropbox(self, "rsp_format", ResponseFormat))
        self._items[-1].setToolTip("The format to be used in the reponse.")
        _content.addWidget(self._items[-1], 0, 0)
        self._items.append(GCheckBox(self, "Response required",
                           "rsp_required"))
        self._items[-1].setToolTip("Require the student to enter text.")
        _content.addWidget(self._items[-1], 0, 1, 1, 2)
        self._items.append(GField(self, int, "min_words"))
        self._items[-1].setToolTip("Minimum word limit")
        self._items[-1].setText("0")
        _content.addWidget(self._items[-1], 1, 0)
        self._items.append(GField(self, int, "max_words"))
        self._items[-1].setToolTip("Maximum word limit")
        self._items[-1].setText("10000")
        _content.addWidget(self._items[-1], 2, 0)
        self._items.append(GField(self, int, "attachments"))
        self._items[-1].setToolTip("Number of attachments allowed. 0 is none."
                                   " -1 is unlimited. Should be bigger than "
                                   "field below.")
        self._items[-1].setText("-1")
        _content.addWidget(self._items[-1], 1, 1)
        self._items.append(GField(self, int, "atts_required"))
        self._items[-1].setToolTip("Number of attachments required. 0 is none."
                                   " -1 is unlimited. Should be smaller than "
                                   "field above.")
        self._items[-1].setText("0")
        _content.addWidget(self._items[-1], 2, 1)
        self._items.append(GField(self, int, "lines"))
        self._items[-1].setToolTip("Input box size.")
        self._items[-1].setText("15")
        _content.addWidget(self._items[-1], 1, 2)
        self._items.append(GField(self, int, "max_bytes"))
        self._items[-1].setToolTip("Maximum file size.")
        self._items[-1].setText("1Mb")
        _content.addWidget(self._items[-1], 2, 2)
        self._items.append(GField(self, str, "file_types"))
        self._items[-1].setToolTip("Accepted file types (comma separeted).")
        self._items[-1].setText(".txt, .pdf")
        _content.addWidget(self._items[-1], 3, 0, 1, 3)
        others.addWidget(group_box, 1)

        _wrapper = QVBoxLayout()  # No need of parent. It's inside GCollapsible
        group_box = QGroupBox("Random", self)
        _wrapper.addWidget(group_box)
        _content = QVBoxLayout(group_box)
        _content.setSpacing(5)
        _content.setContentsMargins(5, 3, 5, 3)
        self._items.append(GCheckBox(self, "Include subcats", "subcats"))
        self._items[-1].setToolTip("If questions wshould be choosen from "
                                   "subcategories too.")
        _content.addWidget(self._items[-1])
        self._items.append(GField(self, int, "choose"))
        self._items[-1].setToolTip("Number of questions to select.")
        self._items[-1].setText("5")
        _content.addWidget(self._items[-1])

        group_box = QGroupBox("Fill-in", self)
        _wrapper.addWidget(group_box)
        _content = QVBoxLayout(group_box)
        _content.setContentsMargins(5, 3, 5, 3)
        self._items.append(GCheckBox(self, "Case sensitive", "use_case"))
        self._items[-1].setToolTip("If text is case sensitive.")
        _content.addWidget(self._items[-1])

        others.addLayout(_wrapper, 0)

        group_box = QGroupBox("Datasets", self)
        _content = QVBoxLayout(group_box)
        _content.setSpacing(5)
        _content.setContentsMargins(5, 3, 5, 3)
        self._items.append(GList(self, "datasets"))
        self._items[-1].setFixedHeight(70)
        self._items[-1].setToolTip("List of datasets used by this question.")
        _content.addWidget(self._items[-1], 0)
        self._items.append(GDropbox(self, "synchronize", Synchronise))
        self._items[-1].setToolTip("How should the databases be synchronized.")
        self._items[-1].setMinimumWidth(50)
        _content.addWidget(self._items[-1], 0)
        others.addWidget(group_box, 1)

        others.addStretch()
        frame.setLayout(grid)
        frame.toggle_collapsed()

    def _block_hints(self) -> None:
        frame = GCollapsible(self, title="Hints")
        self.cframe_vbox.addLayout(frame)
        self._items.append(GHintsList(None, self.toolbar))
        _shortcut = QShortcut(self.SHORTCUTS["Add hint in the end"], self)
        _shortcut.activated.connect(self._items[-1].add)
        _shortcut = QShortcut(self.SHORTCUTS["Remove selected hint"], self)
        _shortcut.activated.connect(self._items[-1].pop)
        frame.setLayout(self._items[-1])

    def _block_solution(self) -> None:
        collapsible = GCollapsible(title="Solution and Feedback")
        self.cframe_vbox.addLayout(collapsible)
        layout = QVBoxLayout()
        collapsible.setLayout(layout)
        self._items.append(GTextEditor(self.toolbar, "feedback"))
        self._items[-1].setMinimumHeight(100)
        self._items[-1].setToolTip("General feedback for the question. May "
                                   "also be used to describe solutions.")
        layout.addWidget(self._items[-1])
        sframe = QFrame(self)
        sframe.setStyleSheet(".QFrame{border:1px solid rgb(41, 41, 41);"
                             "background-color: #e4ebb7}")
        layout.addWidget(sframe)
        _content = QGridLayout(sframe)
        self._items.append(GTextEditor(self.toolbar, "if_correct"))
        self._items[-1].setToolTip("Feedback for correct answer")
        _content.addWidget(self._items[-1], 0, 0)
        self._items.append(GTextEditor(self.toolbar, "if_incomplete"))
        self._items[-1].setToolTip("Feedback for incomplete answer")
        _content.addWidget(self._items[-1], 0, 1)
        self._items.append(GTextEditor(self.toolbar, "if_incorrect"))
        self._items[-1].setToolTip("Feedback for incorrect answer")
        _content.addWidget(self._items[-1], 0, 2)
        self._items.append(GCheckBox(self, "Show the number of correct "
                                     "responses once the question has finished"
                                     , "show_num"))
        _content.addWidget(self._items[-1], 2, 0, 1, 3)
        _content.setColumnStretch(3, 1)

    def _block_template(self) -> None:
        collapsible = GCollapsible(title="Templates")
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

    def _block_units(self):
        collapsible = GCollapsible(title="Units")
        self.cframe_vbox.addLayout(collapsible)

    def _block_zones(self):
        collapsible = GCollapsible(title="Background and Zones")
        self.cframe_vbox.addLayout(collapsible)

    @action_handler
    def _create_file(self, *_):
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
    def _delete_item(self, *_):
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
        gtags = {}
        self.top_quiz.get_tags(gtags)
        self.set_gtags(gtags)
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
        gtags = {}
        self.top_quiz.get_tags(gtags)
        self.set_gtags(gtags)
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
        if save_as or path is None:
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
