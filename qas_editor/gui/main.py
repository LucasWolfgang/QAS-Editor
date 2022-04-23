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
                            QPushButton, QScrollArea

from .popups import NamePopup, QuestionPopup
from ..quiz import Quiz
from ..questions import _Question
from ..enums import Numbering
from .utils import GFrameLayout, GTextToolbar, GTextEditor, GTagBar, IMG_PATH,\
                   GField, GCheckBox, GDropbox, action_handler
from .forms import GOptions, GUnitHadling, GCFeedback, GMultipleTries
if TYPE_CHECKING:
    from typing import Dict
    from PyQt5.QtGui import QDropEvent
    from PyQt5.QtCore import QModelIndex
LOG = logging.getLogger(__name__)


class Editor(QMainWindow):
    """This is the main class.
    """

    FORMATS = "Aiken (*.txt);;Cloze (*.cloze);;GIFT (*.gift);;JSON (*.json)"+\
              ";;LaTex (*.tex);;Markdown (*.md);;PDF (*.pdf);;XML (*.xml)"

    SERIALIZER = { "cloze":  ("write_cloze"),
                   "json":   ("write_json"),
                   "gift":   ("write_gift"),
                   "md":     ("write_markdown"),
                   "pdf":    ("write_pdf"),
                   "tex":    ("write_latex"),
                   "txt":    ("write_aiken"),
                   "xml":    ("write_xml")
    }

    def __init__(self, *args, **kwargs):
        super(Editor, self).__init__(*args, **kwargs)
        self.setWindowTitle("QAS Editor GUI")

        self._items: Dict[str, QWidget] = {}
        self.path: str = None
        self.top_quiz = Quiz()
        self._cur_question = None
        self.context_menu = QMenu(self)

        self._add_menu_bars()

        # Left side
        self.data_view = QTreeView()
        self.data_view.setIconSize(QSize(18,18))
        xframe_vbox = self._add_datatree_viewer()
        left = QWidget()
        left.setLayout(xframe_vbox)

        # Right side
        self.cframe_vbox = QVBoxLayout()
        self._add_general_data_block()
        self._add_answer_block()
        self._add_multiple_tries_block()
        self._add_solution_block()
        self._add_database_block()
        self.cframe_vbox.addStretch()
        self.cframe_vbox.setSpacing(5)
        # self.cframe_vbox.setContentsMargins(0,0,0,0)
        for value in self._items.values():
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

    def _add_answer_block(self) -> None:
        frame = GFrameLayout(title="Answers")
        self.cframe_vbox.addLayout(frame)
        self._items["shuffle"] = GCheckBox(self, "Shuffle the answers", "shuffle")
        self._items["show_instruction"] = GCheckBox(self, "Show instructions",
                                                    "show_instruction")
        self._items["single"] = GCheckBox(self, "Single answer", "single")
        self._items["single"].setContentsMargins(10, 0, 0, 0)
        self._items["answer_numbering"] = GDropbox(self, str, "answer_numbering")
        self._items["answer_numbering"].addItems([c.value for c in Numbering])
        self._items["unit_handling"] = GUnitHadling()
        self._items["answers"] = GOptions(self.toolbar)
        aabutton = QPushButton("Add Answer")
        aabutton.clicked.connect(self._items["answers"].add_default)
        ppbutton = QPushButton("Pop Answer")
        ppbutton.clicked.connect(self._items["answers"].pop)

        grid = QGridLayout()
        grid.addWidget(QLabel("Numbering"), 0, 0)
        grid.addWidget(self._items["answer_numbering"], 0, 1, Qt.AlignLeft)
        grid.addWidget(self._items["show_instruction"], 1, 0, 1, 2)
        grid.addWidget(self._items["single"], 0, 2)
        grid.addWidget(self._items["shuffle"], 1, 2)
        grid.addWidget(self._items["unit_handling"], 0, 3, 2, 1)
        grid.addWidget(aabutton, 0, 4)
        grid.addWidget(ppbutton, 1, 4)
        grid.addLayout(self._items["answers"], 2, 0, 1, 5)
        grid.setColumnStretch(4, 1)
        frame.setLayout(grid)

    def _add_database_block(self) -> None:
        frame = GFrameLayout(title="Database")
        self.cframe_vbox.addLayout(frame)

    def _add_datatree_viewer(self) -> QVBoxLayout:
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

    def _add_general_data_block(self) -> None:
        frame = GFrameLayout(self, title="General Data")
        self.cframe_vbox.addLayout(frame)

        self._items["default_grade"] = GField(self, int, "default_grade")
        self._items["default_grade"].setFixedWidth(30)
        self._items["default_grade"].setToolTip("Default grade.")
        self._items["id_number"] = GField(self, int, "id_number")
        self._items["id_number"].setFixedWidth(40)
        self._items["id_number"].setToolTip("Provides a second way of "
                                            "finding a question.")
        self._items["tags"] = GTagBar(self)
        self._items["tags"].setToolTip("List of tags used by the question.")
        self._items["question"] = GTextEditor(self.toolbar, "question")
        self._items["question"].setMinimumHeight(100)
        self._items["question"].setToolTip("Tags used to ")
        grid = QGridLayout()
        grid.addWidget(QLabel("Tags"), 0, 0)
        grid.addWidget(self._items["tags"], 0, 1)
        grid.setColumnStretch(1, 1)
        tmp = QLabel("Default grade")
        tmp.setContentsMargins(10, 0, 0, 0)
        grid.addWidget(tmp, 0, 2)
        grid.addWidget(self._items["default_grade"], 0, 3)
        tmp = QLabel("ID")
        tmp.setContentsMargins(10, 0, 0, 0)
        grid.addWidget(tmp, 0, 4)
        grid.addWidget(self._items["id_number"], 0, 5)
        grid.addWidget(self._items["question"], 1, 0, 1, 6)
        frame.setLayout(grid)
        frame.toggle_collapsed()

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

    def _add_multiple_tries_block(self) -> None:
        frame = GFrameLayout(self, title="Multiple Tries")
        self.cframe_vbox.addLayout(frame)
        self._items["multiple_tries"] = GMultipleTries(self, self.toolbar)
        frame.setLayout(self._items["multiple_tries"])

    def _add_solution_block(self) -> None:
        frame = GFrameLayout(title="Solution and Feedback")
        self.cframe_vbox.addLayout(frame)
        self._items["general_feedback"] = GTextEditor(self.toolbar,
                                                      "general_feedback")
        self._items["general_feedback"].setFixedHeight(50)
        self._items["combined_feedback"] = GCFeedback(self.toolbar)
        self._items["combined_feedback"].setFixedHeight(110)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("General feedback"))
        layout.addWidget(self._items["general_feedback"])
        layout.addWidget(self._items["combined_feedback"])
        frame.setLayout(layout)

    def _add_new_category(self, quiz: Quiz, parent: QStandardItem):
        popup = NamePopup(True)
        popup.show()
        if not popup.exec():
            return
        quiz[popup.data.name] = popup.data
        self._new_item(popup.data, parent, "question")

    def _add_new_question(self, quiz: Quiz, parent: QStandardItem):
        popup = QuestionPopup(quiz)
        popup.show()
        if not popup.exec():
            return
        self._new_item(popup.question, parent, "question")

    @action_handler
    def _append_category(self, parent: Quiz, item: QStandardItem):
        path, _ = QFileDialog.getOpenFileName(self, "Open file", "",
                                              self.FORMATS)
        if not path:
            return None
        quiz = Quiz.read_files([path], path.rsplit("/", 1)[-1])
        parent[quiz.name] = quiz
        self._update_tree_item(quiz, item)

    @action_handler
    def _create_file(self):
        self.top_quiz = Quiz()
        self.path = None
        self._update_tree_item(self.top_quiz, self.root_item)

    @action_handler
    def _dataview_dropevent(self, event: QDropEvent):
        from_obj = self.data_view.selectedIndexes()[0].data(257)
        to_obj = self.data_view.indexAt(event.pos()).data(257)
        if isinstance(to_obj, _Question):
            event.ignore()
            raise TypeError()
        from_obj.parent = to_obj    # This already does all the magic
        self.data_view.original_dropEvent(event)

    def _data_view_cxt(self, event):
        model_idx = self.data_view.indexAt(event)
        item = self.root_item.itemFromIndex(model_idx)
        data = model_idx.data(257)
        self.context_menu.clear()
        rename = QAction("Rename", self)
        rename.triggered.connect(lambda: self._rename_category(data, item))
        self.context_menu.addAction(rename)
        if item != self.root_item.item(0):
            delete = QAction("Delete", self)
            delete.triggered.connect(lambda: self._delete_item(data, item))
            self.context_menu.addAction(delete)
            clone = QAction("Clone (Shallow)", self)
            clone.triggered.connect(lambda: self._clone_shallow(data, item))
            self.context_menu.addAction(clone)
            clone = QAction("Clone (Deep)", self)
            clone.triggered.connect(lambda: self._clone_deep(data, item))
            self.context_menu.addAction(clone)
        if isinstance(data, Quiz):
            save_as = QAction("Save as", self)
            save_as.triggered.connect(lambda: self._write_quiz(data, True))
            self.context_menu.addAction(save_as)
            append = QAction("Append", self)
            append.triggered.connect(lambda: self._append_category(data, item))
            self.context_menu.addAction(append)
            rename = QAction("New Question", self)
            rename.triggered.connect(lambda: self._add_new_question(data, item))
            self.context_menu.addAction(rename)
            append = QAction("New Category", self)
            append.triggered.connect(lambda: self._add_new_category(data, item))
            self.context_menu.addAction(append)
        self.context_menu.popup(self.data_view.mapToGlobal(event))

    @action_handler
    def _delete_item(self, item, parent: QStandardItem) -> None:
        parent.parent().removeRow(parent.index().row())
        if isinstance(item, _Question):
            item.parent.rem_question(item)
        elif isinstance(item, Quiz):
            item.parent = None

    @action_handler
    def _clone_shallow(self, data, item: QStandardItem) -> None:
        self._new_item(copy.copy(data), item.parent(), "question")

    @action_handler
    def _clone_deep(self, data, item: QStandardItem) -> None:
        self._new_item(copy.deepcopy(data), item.parent(), "question")

    def _new_item(self, data: Quiz, parent: QStandardItem, title: str):
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
        self.top_quiz = Quiz.read_files(files)
        self.root_item.clear()
        self._update_tree_item(self.top_quiz, self.root_item)
        self.data_view.expandAll()

    @action_handler
    def _read_folder(self, *args):
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        if not dialog.exec():
            return None
        self.top_quiz = Quiz()
        self.path = None
        for folder in dialog.selectedFiles():
            cat = folder.rsplit("/", 1)[-1]
            quiz = Quiz.read_files(glob.glob(f"{folder}/*"), cat)
            self.top_quiz[cat] = quiz
        self.root_item.clear()
        self._update_tree_item(self.top_quiz, self.root_item)
        self.data_view.expandAll()

    @action_handler
    def _rename_category(self, data, item: QStandardItem):
        popup = NamePopup(False)
        popup.show()
        if not popup.exec():
            return
        data.name = popup.data
        item.setText(popup.data)

    @action_handler
    def _update_item(self, model_index: QModelIndex) -> None:
        item = model_index.data(257)
        if isinstance(item, _Question):
            for key in self._items.values():
                attr = key.get_attr()
                if attr in item.__dict__:
                    key.setEnabled(True)
                    key.from_obj(item)
                else:
                    key.setEnabled(False)
            self._cur_question = item
        path = [f" ({item.__class__.__name__})"]
        while item.parent:
            path.append(item.name)
            item = item.parent
        path.append(item.name)
        path.reverse()
        self.cat_name.setText(" > ".join(path[:-1]) + path[-1] )

    def _update_tree_item(self, data: Quiz, parent: QStandardItem) -> None:
        item = self._new_item(data, parent, "category")
        for k in data.questions:
            self._new_item(k, item, "question")
        for k in data:
            self._update_tree_item(data[k], item)

    def _write_quiz(self, quiz: Quiz, save_as: bool):
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
