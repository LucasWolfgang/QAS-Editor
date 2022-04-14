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
import sys
from typing import TYPE_CHECKING
from PyQt5.QtCore import Qt, QVariant
from PyQt5.QtGui import QStandardItemModel, QIcon, QStandardItem
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFrame, QLabel, QGridLayout,\
                            QSplitter, QTreeView, QMainWindow, QStatusBar,\
                            QFileDialog, QMenu, QComboBox, QAction, QAbstractItemView,\
                            QCheckBox, QLineEdit, QPushButton, QScrollArea

from .popups import CategoryPopup, QuestionPopup
from ..quiz import Quiz
from ..questions import QNAME, Question
from ..enums import Numbering
from .utils import GFrameLayout, GTextToolbar, GTextEditor, GTagBar, IMG_PATH,\
                   action_handler
from .forms import GOptions, GUnitHadling, GCFeedback, GMultipleTries
if TYPE_CHECKING:
    from typing import Dict
    from PyQt5.QtGui import QDropEvent
    from PyQt5.QtCore import QModelIndex
LOG = logging.getLogger(__name__)

# ------------------------------------------------------------------------------

class Editor(QMainWindow):
    """This is the main class.
    """

    FORMATS = "Aiken (*.txt);;Cloze (*.cloze);;GIFT (*.gift);;JSON (*.json)"+\
              ";;LaTex (*.tex);;Markdown (*.md);;PDF (*.pdf);;XML (*.xml)"

    def __init__(self, *args, **kwargs):
        super(Editor, self).__init__(*args, **kwargs)
        self.setWindowTitle("QAS Editor GUI")

        self._items: Dict[str, QWidget] = {}
        self.path: str = None
        self.top_quiz = Quiz()
        self.current_category = self.top_quiz
        self.current_question = None
        self.current_item = None
        self.context_menu = QMenu(self)

        self._add_menu_bars()

        # Left side
        self.data_view = QTreeView()
        self.category_name = QLineEdit()
        xframe_vbox = self._add_datatree_viewer()
        left = QWidget()
        left.setLayout(xframe_vbox)

        # Right side
        self.cframe_vbox = QVBoxLayout()
        self._add_general_data_block()
        self._add_answer_block()
        self._add_multiple_tries_block()
        self._add_feedback_block()
        self._add_solution_block()
        self._add_database_block()
        self.cframe_vbox.addStretch()
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
        splitter.setSizes([250, 100])   # The second value does not make difference
        self.setCentralWidget(splitter)

        # Create lower status bar.
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.cat_name = QLabel(self.current_category.name)
        self.status.addWidget(self.cat_name)
        self._update_tree_item(self.top_quiz, self.root_item)
        self.data_view.expandAll()
        self.setGeometry(300, 300, 1000, 600)
        self.show()

    def _add_answer_block(self) -> None:
        frame = GFrameLayout(title="Answers")
        self.cframe_vbox.addLayout(frame)
        self._items["shuffle"] = QCheckBox("Shuffle the answers")
        self._items["show_instruction"] = QCheckBox("Show instructions")
        self._items["single"] = QCheckBox("Single answer")
        self._items["single"].setContentsMargins(10, 0, 0, 0)
        self._items["answer_numbering"] = QComboBox()
        self._items["answer_numbering"].addItems([c.value for c in Numbering])
        self._items["unit_handling"] = GUnitHadling()
        self._items["answers"] = GOptions(self.editor_toolbar)
        aabutton = QPushButton("Add Answer")
        aabutton.clicked.connect(self._items["answers"].add_default)
        ppbutton = QPushButton("Pop Answfer")
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
        self.data_view.customContextMenuRequested.connect(self._data_view_context_menu)
        self.data_view.setDragEnabled(True)
        self.data_view.setAcceptDrops(True)
        self.data_view.setDropIndicatorShown(True)
        self.data_view.setDragDropMode(QAbstractItemView.InternalMove)
        self.data_view.original_dropEvent = self.data_view.dropEvent
        self.data_view.dropEvent = self._dataview_dropevent
        self.root_item = QStandardItemModel(0, 1)
        self.root_item.setHeaderData(0, Qt.Horizontal, "Classification")
        self.data_view.setModel(self.root_item)
        self.question_type = QComboBox()
        self.question_type.addItems(QNAME)
        
        xframe_vbox = QVBoxLayout()
        xframe_vbox.addWidget(self.data_view)
        return xframe_vbox

    def _add_feedback_block(self) -> None:
        frame = GFrameLayout(title="Feedbacks")
        self.cframe_vbox.addLayout(frame)
        self._items["general_feedback"] = GTextEditor(self.editor_toolbar, "generalfeedback")
        self._items["general_feedback"].setFixedHeight(50)
        self._items["combined_feedback"] = GCFeedback(self.editor_toolbar)
        self._items["combined_feedback"].setFixedHeight(110)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("General feedback"))
        layout.addWidget(self._items["general_feedback"])
        layout.addWidget(self._items["combined_feedback"])
        frame.setLayout(layout)

    def _add_general_data_block(self) -> None:
        frame = GFrameLayout(self, title="General Data")
        self.cframe_vbox.addLayout(frame)

        self._items["name"] = QLineEdit()
        self._items["name"].setToolTip("Name used to storage the question in the database.")
        self._items["name"] = QLineEdit()
        self._items["default_grade"] = QLineEdit()
        self._items["default_grade"].setFixedWidth(30)
        self._items["default_grade"].setToolTip("Default grade for the question.")
        self._items["id_number"] = QLineEdit()
        self._items["id_number"].setFixedWidth(40)
        self._items["id_number"].setToolTip("Provides a second way of finding a question.")
        self._items["tags"] = GTagBar()
        self._items["question_text"] = GTextEditor(self.editor_toolbar, "question_text")
        grid = QGridLayout()
        grid.addWidget(QLabel("Name"), 0, 0)
        grid.addWidget(self._items["name"], 0, 1)
        tmp = QLabel("Tags")
        tmp.setContentsMargins(10, 0, 0, 0)
        grid.addWidget(tmp, 0, 2)
        grid.addWidget(self._items["tags"], 0, 3)
        tmp = QLabel("Default grade")
        tmp.setContentsMargins(10, 0, 0, 0)
        grid.addWidget(tmp, 0, 4)
        grid.addWidget(self._items["default_grade"], 0, 5)
        tmp = QLabel("ID")
        tmp.setContentsMargins(10, 0, 0, 0)
        grid.addWidget(tmp, 0, 6)
        grid.addWidget(self._items["id_number"], 0, 7)
        grid.addWidget(self._items["question_text"], 2, 0, 1, 8)
        frame.setLayout(grid)
        frame.toggle_collapsed()

    def _add_menu_bars(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        new_file_action = QAction("New file", self)
        new_file_action.setStatusTip("New file")
        new_file_action.triggered.connect(self._create_file)
        file_menu.addAction(new_file_action)
        open_file_action = QAction("Open file", self)
        open_file_action.setStatusTip("Open file")
        open_file_action.triggered.connect(self._read_file)
        file_menu.addAction(open_file_action)
        open_folder_action = QAction("Open folder", self)
        open_folder_action.setStatusTip("Open folder")
        open_folder_action.triggered.connect(self._read_folder)
        file_menu.addAction(open_folder_action)
        save_file_action = QAction("Save", self)
        save_file_action.setStatusTip("Save top category to specified file on disk")
        save_file_action.triggered.connect(lambda: self._write_file(False))
        file_menu.addAction(save_file_action)
        saveas_file_action = QAction("Save As...", self)
        saveas_file_action.setStatusTip("Save top category to specified file on disk")
        saveas_file_action.triggered.connect(lambda: self._write_file(True))
        file_menu.addAction(saveas_file_action)
        self.editor_toolbar = GTextToolbar()
        self.addToolBar(Qt.TopToolBarArea, self.editor_toolbar)

    def _add_multiple_tries_block(self) -> None:
        frame = GFrameLayout(title="Multiple Tries")
        self.cframe_vbox.addLayout(frame)
        self._items["multiple_tries"] = GMultipleTries(self.editor_toolbar)
        frame.setLayout(self._items["multiple_tries"])

    def _add_solution_block(self) -> None:
        frame = GFrameLayout(title="Solutions")
        self.cframe_vbox.addLayout(frame)
        self._items["solution"] = GTextEditor(self.editor_toolbar, "solution")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Solution"))
        layout.addWidget(self._items["solution"])
        frame.setLayout(layout)

    def _add_new_category(self, quiz: Quiz, parent: QStandardItem):
        popup = CategoryPopup(True)
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
        path, _ = QFileDialog.getOpenFileName(self, "Open file", "", self.FORMATS)
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
        if isinstance(to_obj, Question):
            event.ignore()
            raise TypeError()
        from_obj.parent = to_obj    # This already does all the magic (using @properties)
        self.data_view.original_dropEvent(event)

    def _data_view_context_menu(self, event):
        model_idx = self.data_view.indexAt(event)
        item = self.root_item.itemFromIndex(model_idx)
        data = model_idx.data(257)
        self.context_menu.clear()
        if item != self.root_item.item(0):
            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: self._delete_item(data, item))
            self.context_menu.addAction(delete_action)
            clone_action = QAction("Clone (Shallow)", self)
            clone_action.triggered.connect(lambda: self._clone_shallow(data, item))
            self.context_menu.addAction(clone_action)
            clone_action = QAction("Clone (Deep)", self)
            clone_action.triggered.connect(lambda: self._clone_deep(data, item))
            self.context_menu.addAction(clone_action)
        if isinstance(data, Quiz):
            save_as = QAction("Save as", self)
            save_as.triggered.connect(lambda: self._write_quiz(data, True))
            self.context_menu.addAction(save_as)
            rename = QAction("Rename", self)
            rename.triggered.connect(lambda: self._rename_category(data, item))
            self.context_menu.addAction(rename)
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
        if isinstance(item, Question):
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
        item = QStandardItem(QIcon(f"{IMG_PATH}/{title}.png"), data.name)
        item.setEditable(False)
        item.setData(QVariant(data))
        parent.appendRow(item)
        return item

    @action_handler
    def _read_file(self, *args):
        files, _ = QFileDialog.getOpenFileNames(self, "Open file", "", self.FORMATS)
        if not files:
            return None
        if len(files) == 1:
            self.path = files[0]
        self.top_quiz = Quiz.read_files(files)
        self._set_current_category(self.top_quiz)
        self._update_tree_item(self.top_quiz, self.root_item)

    @action_handler
    def _read_folder(self, *args):
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        if not dialog.exec():
            return None
        popup = CategoryPopup(False)
        popup.show()
        if not popup.exec():
            return None
        self.top_quiz = Quiz(popup.data)
        self.path = None
        for folder in dialog.selectedFiles():
            cat = folder.rsplit("/", 1)[-1]
            quiz = Quiz.read_files(glob.glob(f"{folder}/*"), cat)
            self.top_quiz[cat] = quiz
        self._set_current_category(self.top_quiz)
        self._update_tree_item(self.top_quiz, self.root_item)

    @action_handler
    def _rename_category(self, data: Quiz, item: QStandardItem):
        popup = CategoryPopup(False)
        popup.show()
        if not popup.exec():
            return
        data.name = popup.data
        item.setText(popup.data)

    def _set_current_category(self, item: Quiz):
        path = []
        self.current_category = item
        while item.parent:
            path.append(item.name)
            item = item.parent
        path.append(item.name)
        path.reverse()
        self.cat_name.setText(" > ".join(path))

    @action_handler
    def _update_item(self, model_index: QModelIndex) -> None:
        item = model_index.data(257)
        def __get_set(key, gets, sets, stype):
            if self.current_question and key in self.current_question.__dict__:
                self.current_question.__setattr__(key, self._items[key].__getattribute__(gets)())
            if key in item.__dict__ and item.__dict__[key] is not None:
                value = item.__dict__[key]
                if stype:
                    value = stype(value)
                self._items[key].__getattribute__(sets)(value)
        if isinstance(item, Question):
            init_fields = list(item.__init__.__code__.co_names)
            init_fields.extend(Question.__init__.__code__.co_names)
            for key in self._items:
                if isinstance(self._items[key], QComboBox):
                    __get_set(key, "currentText", "setCurrentText", str)
                elif isinstance(self._items[key], QLineEdit):
                    __get_set(key, "text", "setText", str)
                elif isinstance(self._items[key], GTextEditor):
                    __get_set(key, "get_ftext", "set_ftext", None)
                elif isinstance(self._items[key], QCheckBox):
                    __get_set(key, "isChecked", "setChecked", bool)
                elif hasattr(self._items[key], "from_obj"): # Suposse it als has to_obj
                    __get_set(key, "to_obj", "from_obj", None)
                else:
                    LOG.warning(f"No form defined for {key}")
                self._items[key].setEnabled(key in init_fields)
            self.question_type.setCurrentText(type(item).__name__)
            self.current_question = item
            self.current_item = self.root_item.itemFromIndex(model_index)
        else: # This is a classification
            self._set_current_category(item)

    def _update_tree_item(self, data: Quiz, parent: QStandardItem) -> None:
        item = self._new_item(data, parent, "category")
        for k in data.questions:
            self._new_item(k, item, "question")
        for k in data:
            self._update_tree_item(data[k], item)

    def _write_quiz(self, quiz: Quiz, save_as: bool):
        if save_as:
            path, _ = QFileDialog.getSaveFileName(self, "Save file", "", self.FORMATS)
            if not path:
                return None
        else:
            path = self.path
        if path[-6:] == ".cloze":
            quiz.write_cloze(path)
        elif path[-5:] == ".json":
            quiz.write_json(path, True)
        elif path[-5:] == ".gift":
            quiz.write_gift(path)
        elif path[-3:] == ".md":
            quiz.write_markdown(path)
        elif path[-4:] == ".pdf":
            quiz.write_pdf(path)
        elif path[-4:] == ".tex":
            quiz.write_latex(path)
        elif path[-4:] == ".txt":
            quiz.write_aiken(path)
        elif path[-4:] == ".xml":
            quiz.write_xml(path, True)
        else:
            raise ValueError(f"Extension {path.rsplit('.', 1)[-1]} can not be read")
        return path

    @action_handler
    def _write_file(self, save_as: bool) -> None:
        path = self._write_quiz(self.top_quiz, save_as)
        if path:
            self.path = path


# ----------------------------------------------------------------------------------------
