from qas_editor.answer import CrossWord
import sys
import traceback
from typing import Callable, Dict, List
from PyQt5.QtCore import Qt, QVariant, QBasicTimer
from PyQt5.QtGui import QStandardItemModel, QIcon, QStandardItem
from PyQt5.QtWidgets import QApplication, QLayout, QWidget, QHBoxLayout, QVBoxLayout,\
                            QFrame, QSplitter, QTreeView, QGroupBox,QMainWindow, \
                            QStatusBar, QFileDialog, QMenu, QComboBox, QMessageBox,\
                            QAction, QCheckBox, QLineEdit, QPushButton, QLabel, QGridLayout
from ..quiz import Quiz, QTYPES
from .. import questions
from ..enums import Numbering
from .utils import GFrameLayout, GTextToolbar, GTextEditor, GTagBar, img_path
from .forms import GUnitHadling, GAnswer, GCFeedback, GMultipleTries, GCrosswordPuzzle

def action_handler(function: Callable) -> Callable:
    def wrapper(*args, **kwargs):
        try:
            function(*args, **kwargs)
        except Exception:
            self = args[0]
            dlg = QMessageBox(self)
            dlg.setText(traceback.format_exc())
            dlg.setIcon(QMessageBox.Critical)
            dlg.show()
    return wrapper

class Editor(QMainWindow):
    
    def __init__(self, *args, **kwargs):
        super(Editor, self).__init__(*args, **kwargs)
        self.setWindowTitle("QAS Editor GUI")

        # Data handling variables
        self._blocks: Dict[str, GFrameLayout] = {}
        self._items: Dict[str, QWidget] = {}
        self.path: str = None
        self.top_quiz = Quiz()
        self.current_category = self.top_quiz
        self.current_question = None

        # Create menu bar
        file_menu = self.menuBar().addMenu("&File")
        new_file_action = QAction("New file", self)
        new_file_action.setStatusTip("New file")
        new_file_action.triggered.connect(self.new_file)
        file_menu.addAction(new_file_action)
        open_file_action = QAction("Open file", self)
        open_file_action.setStatusTip("Open file")
        open_file_action.triggered.connect(self.file_open)
        file_menu.addAction(open_file_action)
        merge_file_action = QAction("Merge file", self)
        merge_file_action.setStatusTip("Merge file")
        merge_file_action.triggered.connect(self.merge_file)
        file_menu.addAction(merge_file_action)
        save_file_action = QAction("Save", self)
        save_file_action.setStatusTip("Save current page")
        save_file_action.triggered.connect(lambda: self.file_save(False))
        file_menu.addAction(save_file_action)
        saveas_file_action = QAction("Save As...", self)
        saveas_file_action.setStatusTip("Save current page to specified file")
        saveas_file_action.triggered.connect(lambda: self.file_save(True))
        file_menu.addAction(saveas_file_action)
        self.editor_toobar = GTextToolbar()
        self.addToolBar(Qt.TopToolBarArea, self.editor_toobar)

        # Left side
        self.dataView = QTreeView()
        self.dataView.setStyleSheet("margin: 5px 5px 0px 5px")
        self.dataView.setHeaderHidden(True)
        self.dataView.doubleClicked.connect(self.update_item)
        self.dataView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.dataView.customContextMenuRequested.connect(self._data_view_context_menu)
        self.data_root = QStandardItemModel(0, 1)
        self.data_root.setHeaderData(0, Qt.Horizontal, "Classification")
        self.dataView.setModel(self.data_root)
        self.dataView.selectionModel().selectionChanged.connect(self._update_category)
        self.question_type = QComboBox()
        self.question_type.addItems(QTYPES)
        self.question_type.currentTextChanged.connect(self.update_question_type)
        question_create = QPushButton("Create")
        question_create.clicked.connect(self.create_question)
        vbox = QVBoxLayout()
        vbox.addWidget(self.question_type)
        vbox.addWidget(question_create)
        box = QGroupBox("Questions")
        box.setLayout(vbox)
        self.category_name = QLineEdit()
        category_create = QPushButton("Create")
        category_create.clicked.connect(self.create_category)
        xframe_vbox = QVBoxLayout()
        xframe_vbox.addWidget(self.dataView)
        xframe_vbox.addSpacing(10)
        xframe_vbox.addWidget(box)
        vbox = QVBoxLayout()
        vbox.addWidget(self.category_name)
        vbox.addWidget(category_create)
        box = QGroupBox("Categories")
        box.setLayout(vbox)
        xframe_vbox.addSpacing(20)
        xframe_vbox.addWidget(box)
        left = QWidget()
        left.setLayout(xframe_vbox)

        # Right side   
        self.cframe_vbox = QVBoxLayout()
        self.add_general_data_block()
        self.add_answer_block()
        self.add_multiple_tries_block()
        self.add_feedback_block()
        self.add_solution_block()
        self.add_database_block()
        self.cframe_vbox.addStretch()
        right = QFrame()
        right.setLineWidth(2)
        right.setLayout(self.cframe_vbox)

        # Create main window divider for the splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([150, 80])
        self.setCentralWidget(splitter)

        # Create lower status bar. probably will be removed.
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.cat_name = QLabel(self.current_category.category_name)
        self.status.addWidget(self.cat_name)
        
        self.update_tree()
        self.setGeometry(300, 300, 1000, 600)
        self.show()

    def _data_view_context_menu(self, event):
        self.menu = QMenu(self)
        item = self.dataView.indexAt(event).data(257)
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(lambda: self._delete_item(item))
        duplicate_action = QAction("Duplicate", self)
        duplicate_action.triggered.connect(lambda: self._delete_item(item))
        self.menu.addAction(delete_action)
        self.menu.addAction(duplicate_action)
        self.menu.popup(self.dataView.mapToGlobal(event))

    def _delete_item(self, item) -> None:
        if isinstance(item, questions.Question):
            parent: Quiz = item.parent
            parent.questions.remove(item)
            self.update_tree()
        elif isinstance(item, Quiz):
            print("Category!")

    def _duplicate_item(self, item) -> None:
        if isinstance(item, questions.Question):
            print("Question!")
        elif isinstance(item, Quiz):
            print("Category!")

    def _update_category(self, selected, deselected) -> None:
        item = selected.indexes()[0].data(257)
        if isinstance(item, Quiz):
            self.cat_name.setText(item.category_name)
            self.current_category = item

    def _update_data_view(self,data: Quiz, parent: QStandardItem) -> None:
        for k in data.questions:
            node = QStandardItem(QIcon(f"{img_path}/question.png"), k.name)
            node.setEditable(False)
            node.setData(QVariant(k))
            parent.appendRow(node)
        for k in data.children:
            node = QStandardItem(QIcon(f"{img_path}/category.png"), k)
            node.setEditable(False)
            node.setData(QVariant(data.children[k]))
            parent.appendRow(node)
            self._update_data_view(data.children[k], node)

    def add_answer_block(self) -> None:
        frame = GFrameLayout(title="Answers")
        self._blocks["answer"] = frame
        self.cframe_vbox.addWidget(frame)

        self._items["shuffle"] = QCheckBox("Shuffle the answers")
        self._items["show_instruction"] =  QCheckBox("Show standard instructions")
        self._items["single"] =  QCheckBox("Single answer")
        self._items["answer_numbering"] = QComboBox()
        self._items["answer_numbering"].addItems([c.value for c in Numbering])
        self._items["unit_handling"] = GUnitHadling()

        # Answers
        aabutton = QPushButton("Add Answer")
        aabutton.clicked.connect(lambda: self._items["answers"].addWidget(GAnswer(self.editor_toobar)))
        self._items["answers"] = QHBoxLayout()

        grid = QHBoxLayout()
        grid.addWidget(QLabel("Numbering"))
        grid.addWidget(self._items["answer_numbering"])
        grid.addStretch()
        grid.addWidget(self._items["single"])
        grid.addWidget(self._items["shuffle"])
        grid.addWidget(self._items["show_instruction"])

        frame.addLayout(grid)
        frame.addWidget(self._items["unit_handling"])
        frame.addWidget(aabutton)
        frame.addLayout(self._items["answers"])
        # Select Option, used in 

        #test
        puzzle = CrossWord()
        self._items["cross_word"] = GCrosswordPuzzle()
        frame.addWidget(self._items["cross_word"])

    def add_database_block(self) -> None:
        frame = GFrameLayout(title="Database")
        self._blocks["database"] = frame
        self.cframe_vbox.addWidget(frame)

    def add_feedback_block(self) -> None:
        frame = GFrameLayout(title="Feedbacks")
        self._blocks["feedback"] = frame
        self.cframe_vbox.addWidget(frame)
        self._items["general_feedback"] = GTextEditor(self.editor_toobar)
        self._items["combined_feedback"] = GCFeedback(self.editor_toobar)
        frame.addWidget(QLabel("General feedback"))
        frame.addWidget(self._items["general_feedback"])
        frame.addWidget(self._items["combined_feedback"])
    
    def add_general_data_block(self) -> None:
        frame = GFrameLayout(title="General Data")
        self._blocks["database"] = frame
        self.cframe_vbox.addWidget(frame)

        self._items["name"] = QLineEdit()
        self._items["name"].setToolTip("Name used to storage the question in the database.")
        self._items["default_grade"] = QLineEdit()
        self._items["default_grade"].setToolTip("Default grade for the question.")
        self._items["id_number"] = QLineEdit()
        self._items["id_number"].setToolTip("Provides a second way of finding a question.")
        self._items["tags"] = GTagBar()
        self._items["question_text"] = GTextEditor(self.editor_toobar)
        grid = QGridLayout()
        grid.addWidget(QLabel("Question name"), 0, 0)
        grid.addWidget(self._items["name"], 0,1)
        grid.addWidget(QLabel("Default grade"), 0, 2)
        grid.addWidget(self._items["default_grade"], 0, 3)
        grid.addWidget(QLabel("ID number"), 1, 2)
        grid.addWidget(self._items["id_number"], 1, 3)
        grid.addWidget(QLabel("Tags"), 1, 0)
        grid.addWidget(self._items["tags"], 1, 1)
        grid.setColumnStretch(1, 4)
        grid.setColumnStretch(3, 1)
        frame.addLayout(grid)
        frame.addSpacing(10)
        frame.addWidget(QLabel("Question text"))
        frame.addWidget(self._items["question_text"])

    def add_multiple_tries_block(self) -> None:
        frame = GFrameLayout(title="Multiple Tries")
        self.cframe_vbox.addWidget(frame)
        self._items["multiple_tries"] = GMultipleTries(self.editor_toobar)
        frame.addWidget(self._items["multiple_tries"])

    def add_solution_block(self) -> None:
        frame = GFrameLayout(title="Solutions")
        self._blocks["database"] = frame
        self.cframe_vbox.addWidget(frame)

        frame.addWidget(QLabel("Solution"))
        self._items["solution"] = GTextEditor(self.editor_toobar)
        frame.addWidget(self._items["solution"])

    @action_handler
    def create_question(self, stat: bool) -> None:
        output = {}
        cls = getattr(questions, self.question_type.currentText())
        cls.__init__.__code__.co_names
        for key in self._items:
            if isinstance(self._items[key], QComboBox):
                output[key] = self._items[key].currentText()
            elif isinstance(self._items[key], QLineEdit):
                output[key] = self._items[key].text()
            elif isinstance(self._items[key], GTextEditor):
                output[key] = self._items[key].getFText()
            elif isinstance(self._items[key], QCheckBox):
                output[key] = self._items[key].isChecked()
            elif isinstance(self._items[key], QLayout):
                output[key] = []
                for num in range(self._items[key].count()):
                    output[key].append(self._items[key].itemAt(num).to_obj())
            elif "to_obj" in dir(self._items[key].__class__):
                output[key] = self._items[key].to_obj()
            else:
                print("Oooops: ", self._items[key])
        self.current_category.add_question(cls(**output))
        self.update_tree()

    def create_category(self, event) -> None:
        name = f"{self.current_category.category_name}/{self.category_name.text()}"
        quiz = Quiz(name, parent=self.current_category)
        self.current_category.children[self.category_name.text()] = quiz
        self.update_tree()

    def dialog_critical(self):
        dlg = QMessageBox(self)
        dlg.setText(traceback.format_exc())
        dlg.setIcon(QMessageBox.Critical)
        dlg.show()

    @action_handler
    def new_file(self, stat: bool):
        """[summary]

        Args:
            stat (bool): [description]
        """
        self.top_quiz = Quiz()
        self.path = None
        self.update_tree()

    @action_handler
    def merge_file(self, stat: bool):
        parent = self.current_category.parent
        path, _ = QFileDialog.getOpenFileName(self, "Open file", "", 
                    "Aiken (*.txt);Cloze (*.cloze);GIFT (*.gift); Markdown (*.md); "+
                    "LaTex (*.tex);XML (*.xml);All files (*.*)")
        if path[-4:] == ".xml":
            quiz = Quiz.read_xml(path)
        elif path[-4:] == ".txt":
            quiz = Quiz.read_aiken(path)
        elif path[-5:] == ".gift":
            quiz = Quiz.read_gift(path)
        elif path[-3:] == ".md":
            quiz = Quiz.read_markdown(path)
        else:
            raise ValueError(f"Extension {path.rplist('.', 1)[-1]} can not be read")
        quiz.parent = self.current_category
        quiz.category_name = self.current_category.category_name + "/" + quiz.category_name 
        self.current_category.children[quiz.category_name.rsplit("/", 1)[-1]] = quiz
        self.update_tree()

    @action_handler
    def file_open(self, stat:bool):
        """
        [summary]
        """
        path, _ = QFileDialog.getOpenFileName(self, "Open file", "", 
                    "Aiken (*.txt);Cloze (*.cloze);GIFT (*.gift); Markdown (*.md); "+
                    "LaTex (*.tex);XML (*.xml);All files (*.*)")
        if path[-4:] == ".xml":
            self.top_quiz = Quiz.read_xml(path)
        elif path[-4:] == ".txt":
            self.top_quiz = Quiz.read_aiken(path)
        elif path[-5:] == ".gift":
            self.top_quiz = Quiz.read_gift(path)
        elif path[-3:] == ".md":
            self.top_quiz = Quiz.read_markdown(path)
        else:
            raise ValueError(f"Extension {path.rplist('.', 1)[-1]} can not be read")
        self.path = path
        self.update_tree()

    @action_handler
    def file_save(self, saveas: bool) -> None:
        """
        [summary]
        """
        if saveas:
            path, _ = QFileDialog.getSaveFileName(self, "Save file", "", 
                    "Aiken (*.txt);Cloze (*.cloze);GIFT (*.gift); Markdown (*.md); "+
                    "LaTex (*.tex);XML (*.xml);All files (*.*)")
        else:
            path = self.path
        if path[-4:] == ".xml":
            self.top_quiz.write_xml(path, True)
        elif path[-4:] == ".txt":
            self.top_quiz.write_aiken(path)
        elif path[-5:] == ".gift":
            raise NotImplemented("Gift not implemented")
        elif path[-3:] == ".md":
            raise NotImplemented("Markdown implemented")
        else:
            raise ValueError(f"Extension {path.rplist('.', 1)[-1]} can not be read")
        self.path = path

    @action_handler
    def update_item(self, value) -> None:
        item = value.data(257)
        if isinstance(item, questions.Question):
            for key in self._items:
                if key in item.__dict__ and item.__dict__[key] is not None:
                    if isinstance(self._items[key], QComboBox):
                        self._items[key].setCurrentText(str(item.__dict__[key]))
                    elif isinstance(self._items[key], QLineEdit):
                        self._items[key].setText(str(item.__dict__[key]))
                    elif isinstance(self._items[key], GTextEditor):
                        self._items[key].setFText(item.__dict__[key])
                    elif isinstance(self._items[key], QCheckBox):
                        self._items[key].setChecked(item.__dict__[key])
                    elif isinstance(self._items[key], QLayout):
                        print(item.__dict__[key])
                    elif "from_obj" in dir(self._items[key].__class__):
                        self._items[key].from_obj(item.__dict__[key])
                    else:
                        print("Oooops: ", self._items[key])
            self.question_type.setCurrentText(type(item).__name__)
        else: # This is a classification
            pass

    def update_question_type(self, value: str) -> None:
        """
        [summary]
        """
        cls = getattr(questions, value)
        init_fields: List = list(cls.__init__.__code__.co_names)
        init_fields.extend(questions.Question.__init__.__code__.co_names)
        for item in self._items:
            if isinstance(self._items[item], QLayout):
                for num in range(self._items[item].count()):
                    self._items[item].itemAt(num).setVisible(item in init_fields)
            if isinstance(self._items[item], QWidget):
                self._items[item].setVisible(item in init_fields)

    def update_tree(self) -> None:
        self.data_root.clear()
        parent = QStandardItem(QIcon(f"{img_path}/category.png"), self.top_quiz.category_name)
        parent.setData(QVariant(self.top_quiz)) # This first loop is "external" to allow
        parent.setEditable(False)               # using the dict key without passing it as  
        self.data_root.appendRow(parent)        # argument during recursion
        self._update_data_view(self.top_quiz, parent)
        self.dataView.expandAll()

# 
class QTest(QWidget):

        def __init__(self, **kwargs) -> None:
            super().__init__(**kwargs)
            self._timer = QBasicTimer()

# ----------------------------------------------------------------------------------------

def main():
    app = QApplication(sys.argv)
    app.setStyle('Breeze')
    w = Editor()
    sys.exit(app.exec_())