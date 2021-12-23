import logging
from typing import Dict
from PyQt5.QtCore import Qt, QVariant, QBasicTimer
from PyQt5.QtGui import QStandardItemModel, QIcon, QStandardItem
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFrame, QLabel, QGridLayout,\
                            QSplitter, QTreeView, QGroupBox,QMainWindow, QStatusBar,\
                            QFileDialog, QMenu, QComboBox,QAction,\
                            QCheckBox, QLineEdit, QPushButton
from ..quiz import Quiz, QTYPES
from .. import questions
from ..enums import Numbering
from .utils import GFrameLayout, GTextToolbar, GTextEditor, GTagBar, img_path, action_handler
from .forms import GOptions, GUnitHadling, GCFeedback, GMultipleTries

log = logging.getLogger(__name__)

# ----------------------------------------------------------------------------------------

class Editor(QMainWindow):
    
    def __init__(self, *args, **kwargs):
        super(Editor, self).__init__(*args, **kwargs)
        self.setWindowTitle("QAS Editor GUI")

        # Data handling variables
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
        save_file_action.setStatusTip("Save top category to specified file on disk")
        save_file_action.triggered.connect(lambda: self.file_save(False))
        file_menu.addAction(save_file_action)
        saveas_file_action = QAction("Save As...", self)
        saveas_file_action.setStatusTip("Save top category to specified file on disk")
        saveas_file_action.triggered.connect(lambda: self.file_save(True))
        file_menu.addAction(saveas_file_action)
        self.editor_toolbar = GTextToolbar()
        self.addToolBar(Qt.TopToolBarArea, self.editor_toolbar)

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
        self.question_type = QComboBox()
        self.question_type.addItems(QTYPES)
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

        # Create lower status bar.
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
        self.menu.addAction(delete_action)
        duplicate_action = QAction("Duplicate", self)
        duplicate_action.triggered.connect(lambda: self._duplicate_item(item))
        self.menu.addAction(duplicate_action)
        save_as = QAction("Save as", self)
        #save_as.triggered.connect(lambda: self._delete_item(item))
        self.menu.addAction(save_as)
        import_as = QAction("Import", self)
        #import_as.triggered.connect(lambda: self._delete_item(item))
        self.menu.addAction(import_as)
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
            pass
        self.update_tree()

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
        self.cframe_vbox.addLayout(frame)
        self._items["shuffle"] = QCheckBox("Shuffle the answers")
        self._items["show_instruction"] =  QCheckBox("Show instructions")
        self._items["single"] =  QCheckBox("Single answer")
        self._items["single"].setContentsMargins(10,0,0,0)
        self._items["answer_numbering"] = QComboBox()
        self._items["answer_numbering"].addItems([c.value for c in Numbering])
        self._items["unit_handling"] = GUnitHadling()
        self._items["answers"] = GOptions(self.editor_toolbar)
        aabutton = QPushButton("Add Answer")
        aabutton.clicked.connect(lambda: self._items["answers"].add_default())
        ppbutton = QPushButton("Pop Answer")
        ppbutton.clicked.connect(lambda: self._items["answers"].pop())

        grid = QGridLayout()
        grid.addWidget(QLabel("Numbering"), 0, 0)
        grid.addWidget(self._items["answer_numbering"], 0, 1, Qt.AlignLeft)
        grid.addWidget(self._items["show_instruction"], 1, 0, 1, 2)
        grid.addWidget(self._items["single"], 0, 2)
        grid.addWidget(self._items["shuffle"], 1, 2)
        grid.addWidget(self._items["unit_handling"], 0, 3, 2, 1 )
        grid.addWidget(aabutton, 0, 4)
        grid.addWidget(ppbutton, 1, 4)
        grid.addLayout(self._items["answers"], 2, 0, 1, 5)
        grid.setColumnStretch(4, 1)
        frame.setLayout(grid)

    def add_database_block(self) -> None:
        frame = GFrameLayout(title="Database")
        self.cframe_vbox.addLayout(frame)

    def add_feedback_block(self) -> None:
        frame = GFrameLayout(title="Feedbacks")
        self.cframe_vbox.addLayout(frame)
        self._items["general_feedback"] = GTextEditor(self.editor_toolbar)
        self._items["general_feedback"].setFixedHeight(50)
        self._items["combined_feedback"] = GCFeedback(self.editor_toolbar)
        self._items["combined_feedback"].setFixedHeight(110)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("General feedback"))
        layout.addWidget(self._items["general_feedback"])
        layout.addWidget(self._items["combined_feedback"])
        frame.setLayout(layout)
    
    def add_general_data_block(self) -> None:
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
        self._items["question_text"] = GTextEditor(self.editor_toolbar)
        grid = QGridLayout()
        grid.addWidget(QLabel("Name"), 0, 0)
        grid.addWidget(self._items["name"], 0,1)
        tmp = QLabel("Tags")
        tmp.setContentsMargins(10,0,0,0)
        grid.addWidget(tmp, 0, 2)
        grid.addWidget(self._items["tags"], 0, 3)
        tmp = QLabel("Default grade")
        tmp.setContentsMargins(10,0,0,0)
        grid.addWidget(tmp, 0, 4)
        grid.addWidget(self._items["default_grade"], 0, 5)
        tmp = QLabel("ID")
        tmp.setContentsMargins(10,0,0,0)
        grid.addWidget(tmp, 0, 6)
        grid.addWidget(self._items["id_number"], 0, 7)
        grid.addWidget(QLabel("Question text"), 2, 0, 1, 2)
        grid.addWidget(self._items["question_text"], 3, 0, 1, 8)
        frame.setLayout(grid)
        frame.toggleCollapsed()

    def add_multiple_tries_block(self) -> None:
        frame = GFrameLayout(title="Multiple Tries")
        self.cframe_vbox.addLayout(frame)
        self._items["multiple_tries"] = GMultipleTries(self.editor_toolbar)
        frame.setLayout(self._items["multiple_tries"])

    def add_solution_block(self) -> None:
        frame = GFrameLayout(title="Solutions")
        self.cframe_vbox.addLayout(frame)
        self._items["solution"] = GTextEditor(self.editor_toolbar)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Solution"))
        layout.addWidget(self._items["solution"])
        frame.setLayout(layout)

    @action_handler
    def create_question(self, stat: bool) -> None:
        cls = getattr(questions, self.question_type.currentText())
        self.current_category.add_question(cls(name="New Question"))
        self.update_tree()
        for key in self._items:
            if key == "name": continue
            if hasattr(self._items[key], "clear"): self._items[key].clear()

    @action_handler
    def create_category(self, event) -> None:
        name = f"{self.current_category.category_name}/{self.category_name.text()}"
        quiz = Quiz(name, parent=self.current_category)
        self.current_category.children[self.category_name.text()] = quiz
        self.update_tree()

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
        path, _ = QFileDialog.getOpenFileName(self, "Open file", "", 
                    "Aiken (*.txt);Cloze (*.cloze);GIFT (*.gift); Markdown (*.md); "+
                    "LaTex (*.tex);XML (*.xml);All files (*.*)")
        if not path: return
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
                    "Aiken (*.txt);Cloze (*.cloze);GIFT (*.gift);JSON (*.json);"+
                    "LaTex (*.tex);Markdown (*.md);PDF (*.pdf);XML (*.xml);All files (*.*)")
        if not path: return
        if path[-4:] == ".xml":
            self.top_quiz = Quiz.read_xml(path)
        elif path[-4:] == ".txt":
            self.top_quiz = Quiz.read_aiken(path)
        elif path[-5:] == ".gift":
            self.top_quiz = Quiz.read_gift(path)
        elif path[-3:] == ".md":
            self.top_quiz = Quiz.read_markdown(path)
        elif path[-6:] == ".cloze":
            self.top_quiz = Quiz.read_cloze(path)
        elif path[-5:] == ".json":
            self.top_quiz = Quiz.read_json(path)
        elif path[-4:] == ".pdf":
            self.top_quiz = Quiz.read_pdf(path)
        elif path[-4:] == ".tex":
            self.top_quiz = Quiz.read_latex(path)
        else:
            raise ValueError(f"Extension {path.rsplit('.', 1)[-1]} can not be read")
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
        def __get_set(key, gets, sets, stype):
            if self.current_question and key in self.current_question.__dict__:
                self.current_question.__setattr__(key, self._items[key].__getattribute__(gets)())
            if key in item.__dict__ and item.__dict__[key] is not None:
                value = item.__dict__[key]
                if stype: value = stype(value)
                self._items[key].__getattribute__(sets)(value)
        if isinstance(item, questions.Question):
            init_fields = list(item.__init__.__code__.co_names)
            init_fields.extend(questions.Question.__init__.__code__.co_names)
            for key in self._items:
                if isinstance(self._items[key], QComboBox):
                    __get_set(key, "currentText", "setCurrentText", str)
                elif isinstance(self._items[key], QLineEdit):
                     __get_set(key, "text", "setText", str)
                elif isinstance(self._items[key], GTextEditor):
                    __get_set(key, "getFText", "setFText", None)
                elif isinstance(self._items[key], QCheckBox):
                    __get_set(key, "isChecked", "setChecked", bool)
                elif hasattr(self._items[key], "from_obj"): # Suposse it als has to_obj
                    __get_set(key, "to_obj", "from_obj", None)
                else:
                    log.warning(f"No form defined for {key}")
                self._items[key].setEnabled(key in init_fields)
            self.question_type.setCurrentText(type(item).__name__)
            self.current_question = item
            self.update_tree()
        else: # This is a classification
            path = []
            self.current_category = item
            path.append(item.category_name)
            while item.parent:
                item = item.parent
                path.append(item.category_name)
            self.cat_name.setText(" > ".join(path))  

    def update_tree(self) -> None:
        self.data_root.clear()
        parent = QStandardItem(QIcon(f"{img_path}/category.png"), self.top_quiz.category_name)
        parent.setData(QVariant(self.top_quiz)) # This first loop is "external" to allow
        parent.setEditable(False)               # using the dict key without passing it as  
        self.data_root.appendRow(parent)        # argument during recursion
        self._update_data_view(self.top_quiz, parent)
        self.dataView.expandAll()

# ----------------------------------------------------------------------------------------
class QTest(QWidget):

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._timer = QBasicTimer()

# ----------------------------------------------------------------------------------------
