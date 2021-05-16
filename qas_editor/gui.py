from qas_editor.answer import Answer
from qas_editor.enums import Format
from qas_editor.wrappers import CombinedFeedback, FText
import sys
import os
import traceback
from os.path import splitext
from uuid import uuid4
from .quiz import Quiz, QTYPES
from . import questions
from typing import Dict, List
from PyQt5.QtCore import Qt, QSize, QPoint, QPointF, pyqtSignal, QVariant
from PyQt5.QtGui import QStandardItemModel, QFont, QImage, QTextDocument, QKeySequence,\
                        QIcon, QColor, QPainter, QStandardItem
from PyQt5.QtWidgets import QApplication, QSizePolicy, QWidget, QHBoxLayout, QVBoxLayout,\
                            QFrame, QSplitter, QTreeView, QTextEdit, QGroupBox,\
                            QMainWindow, QStatusBar, QFileDialog, QToolBar, QMenu,\
                            QFontComboBox, QComboBox, QActionGroup, QMessageBox,\
                            QAction, QCheckBox, QLineEdit, QPushButton, QLabel, QGridLayout

img_path = f"{os.path.dirname(os.path.realpath(__file__))}/images"

class GUI(QMainWindow):
    
    def __init__(self, *args, **kwargs):
        super(GUI, self).__init__(*args, **kwargs)
        self.setWindowTitle("QAS Editor GUI")

        # Data handling variables
        self._blocks: Dict[str, GFrameLayout] = {}
        self._items: Dict[str, QWidget] = {}
        self.path: str = None
        self.top_quiz: Quiz = None
        self.current_category: Quiz = None
        self.current_question = None

        # Create menu bar
        file_menu = self.menuBar().addMenu("&File")
        open_file_action = QAction("Open file...", self)
        open_file_action.setStatusTip("Open file")
        open_file_action.triggered.connect(self.file_open)
        file_menu.addAction(open_file_action)
        save_file_action = QAction("Save", self)
        save_file_action.setStatusTip("Save current page")
        save_file_action.triggered.connect(self.file_save)
        file_menu.addAction(save_file_action)
        saveas_file_action = QAction("Save As...", self)
        saveas_file_action.setStatusTip("Save current page to specified file")
        saveas_file_action.triggered.connect(self.file_saveas)
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
        category_name = QLineEdit()
        category_create = QPushButton("Create")
        category_create.clicked.connect(self.create_category)
        xframe_vbox = QVBoxLayout()
        xframe_vbox.addWidget(self.dataView)
        xframe_vbox.addSpacing(10)
        xframe_vbox.addWidget(box)
        vbox = QVBoxLayout()
        vbox.addWidget(category_name)
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
        #self.status.addWidget(QLabel(self.current_category))

        self.setGeometry(300, 300, 1000, 600)
        self.show()

    def _data_view_context_menu(self, event):
        self.menu = QMenu(self)
        item = self.dataView.indexAt(event).data(257)
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(lambda: self._delete_item(item))
        duplicate_action = QAction("Delete", self)
        duplicate_action.triggered.connect(lambda: self._delete_item(item))
        self.menu.addAction(delete_action)
        self.menu.popup(self.dataView.mapToGlobal(event))

    def _delete_item(self, item) -> None:
        if isinstance(item, questions.Question):
            print("Question!")
        elif isinstance(item, Quiz):
            print("Category!")

    def add_answer_block(self) -> None:
        frame = GFrameLayout(title="Answers")
        self._blocks["answer"] = frame
        self.cframe_vbox.addWidget(frame)

        self._items["shuffle"] = QCheckBox("Shuffle the questions")
        self._items["show_instruction"] =  QCheckBox("Show standard instructions")
        self._items["single"] =  QCheckBox("Single answer")
        self._items["numbering"] = QComboBox()
        self._items["numbering"].addItems(["a, b, c", "A, B, C",  "i, ii, iii", "I, II, III", "1,2,3"])

        # UnitHandling
        self._items["grading"] = QComboBox()   
        self._items["grading"].addItems(["Ignore", "Fraction of reponse", "Fraction of question"])

        # Answers
        aabutton = QPushButton("Add Answer")
        aabutton.clicked.connect(lambda x: abox.addWidget(GAnswer(self.editor_toobar)))
        abox = QHBoxLayout()
        #abutton = QPushButton("Add Answer")

        grid = QGridLayout()
        grid.addWidget(QLabel("Grading"), 0, 0)
        grid.addWidget(self._items["grading"], 0, 1)
        grid.addWidget(QLabel("Numbering"), 1, 0)
        grid.addWidget(self._items["numbering"], 1, 1)
        grid.addWidget(self._items["single"], 0, 2)
        grid.addWidget(self._items["shuffle"], 1, 2)
        grid.addWidget(self._items["show_instruction"], 2, 2)

        frame.addLayout(grid)
        frame.addWidget(aabutton)
        frame.addLayout(abox)
        # Select Option, used in 

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
        grid = QGridLayout()
        grid.addWidget(QLabel("Question name"), 0, 0)
        grid.addWidget(self._items["name"], 0,1)
        grid.setColumnStretch(1, 4)
        grid.addWidget(QLabel("Default grade"), 0, 2)
        grid.addWidget(self._items["default_grade"], 0, 3)
        grid.addWidget(QLabel("ID number"), 0, 4)
        grid.addWidget(self._items["id_number"], 0, 5)
        grid.addWidget(QLabel("Tags"), 1, 0)
        grid.addWidget(GTagBar(), 1, 1)
        frame.addLayout(grid)
        frame.addSpacing(10)
        frame.addWidget(QLabel("Question text"))
        self.editor = GTextEditor(self.editor_toobar)
        frame.addWidget(self.editor)

        #Check      use_latex
        #SmallText  default_grade

    def add_multiple_tries_block(self) -> None:
        frame = GFrameLayout(title="Multiple Tries")
        self._blocks["database"] = frame
        self.cframe_vbox.addWidget(frame)
        # self.hints: List[Hint] = []

    def add_solution_block(self) -> None:
        frame = GFrameLayout(title="Solutions")
        self._blocks["database"] = frame
        self.cframe_vbox.addWidget(frame)

        frame.addWidget(QLabel("Solution"))
        self._items["solution"] = GTextEditor(self.editor_toobar)
        frame.addWidget(self._items["solution"])

    def create_question(self) -> None:
        if self.current_question is None:
            cls = getattr(questions, self.question_type.currentText())
            self.current_question = cls.from_gui(self._items)
        else:
            pass

    def create_category(self) -> None:
        pass

    def dialog_critical(self, s):
        dlg = QMessageBox(self)
        dlg.setText(traceback.format_exc())
        dlg.setIcon(QMessageBox.Critical)
        dlg.show()

    def delete_question(self) -> None:
        pass

    def file_open(self):
        """
        [summary]
        """
        path, _ = QFileDialog.getOpenFileName(self, "Open file", "", 
                    "Aiken (*.txt);Cloze (*.cloze);GIFT (*.gift); Markdown (*.md); "+
                    "LaTex (*.tex);XML (*.xml);All files (*.*)")
        try:
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
        except Exception as e:
            self.dialog_critical(str(e))
        else:
            self.path = path
            data = {}
            self.top_quiz.get_hier(data)
            self.update_data_view(data, self.data_root)
            self.dataView.expandAll()
        
    def file_save(self) -> None:
        """
        [summary]
        """
        if self.path is None:
            return self.file_saveas()
        try:
            pass
        except Exception as e:
            self.dialog_critical(str(e))

    def file_saveas(self) -> None:
        """
        [summary]
        """
        path, _ = QFileDialog.getSaveFileName(self, "Save file", "", 
                        "Aiken (*.txt);Cloze (*.cloze);GIFT (*.gift); Markdown (*.md); "+
                        "LaTex (*.tex);XML (*.xml);All files (*.*)")
        if not path:
            return
        try:
            pass
        except Exception as e:
            self.dialog_critical(str(e))
        else:
            self.path = path

    def update_data_view(self,data: dict, parent: QStandardItem) -> None:
        for k in data:
            if isinstance(data[k], dict):
                node = QStandardItem(QIcon(f"{img_path}/category.png"), k)
                node.setEditable(False)
                node.setData(QVariant(data[k]))
                parent.appendRow(node)
                self.update_data_view(data[k], node)
            elif isinstance(data[k], list):
                for i in data[k]:
                    node = QStandardItem(QIcon(f"{img_path}/question.png"), i.name)
                    node.setEditable(False)
                    node.setData(QVariant(i))
                    parent.appendRow(node)

    def update_item(self, value) -> None:
        print(value.data(257).name)

    def update_question_type(self, value):
        """
        [summary]
        """
        cls = getattr(questions, value)
        init_fields = cls.__init__.__code__.co_varnames[1:-2]
        for item in self._items:
            self._items[item].setVisible(item in init_fields)

# ----------------------------------------------------------------------------------------

class GTextEditor(QTextEdit):

    def __init__(self, toolbar: "GTextToolbar") -> None:
        super().__init__()
        self.toolbar = toolbar
        self.setAutoFormatting(QTextEdit.AutoAll)
        self.selectionChanged.connect(lambda: toolbar.update_editor(self))
        self.setFont(QFont('Times', 12))
        self.setFontPointSize(12)   

    def canInsertFromMimeData(self, source) -> bool:
        """[summary]

        Args:
            source ([type]): [description]

        Returns:
            bool: [description]
        """
        if source.hasImage():
            return True
        else:
            return super(GTextEditor, self).canInsertFromMimeData(source)

    def insertFromMimeData(self, source):
        """[summary]

        Args:
            source ([type]): [description]
        """
        cursor = self.textCursor()
        document = self.document()

        if source.hasUrls():
            for u in source.urls():
                file_ext = splitext(str(u.toLocalFile()))[1].lower()
                if u.isLocalFile() and file_ext in ['.jpg','.png','.bmp']:
                    image = QImage(u.toLocalFile())
                    document.addResource(QTextDocument.ImageResource, u, image)
                    cursor.insertImage(u.toLocalFile())
                else:
                    break
            else:
                return
        elif source.hasImage():
            image = source.imageData()
            uuid = uuid4().hex
            document.addResource(QTextDocument.ImageResource, uuid, image)
            cursor.insertImage(uuid)
            return
        super(GTextEditor, self).insertFromMimeData(source)

    def getFText(self) -> FText:
        """[summary]

        Returns:
            FText: [description]
        """
        tp = self.toolbar.text_type.currentIndex()
        if tp == 0:
            txt = self.toMarkdown()
            return FText(txt, Format.MD)
        elif tp == 1:
            txt = self.toHtml()
            return FText(txt, Format.HTML)
        else:
            txt = self.toPlainText()
            return FText(txt, Format.PLAIN)

# ----------------------------------------------------------------------------------------

class GTextToolbar(QToolBar):

    def __init__(self, *args, **kwargs):
        super(GTextToolbar, self).__init__(*args, **kwargs)

        self.editor: GTextEditor = None
        self.setIconSize(QSize(16, 16))

        self.fonts = QFontComboBox()
        self.addWidget(self.fonts)

        self.text_type = QComboBox()
        self.text_type.addItems(["MarkDown", "HTML", "PlainText"])
        self.addWidget(self.text_type)

        self.math_type = QComboBox()
        self.math_type.addItems(["LaTex", "MathML", "Ignore"])
        self.addWidget(self.math_type)

        self.fontsize = QComboBox()
        self.fontsize.addItems(["7", "8", "9", "10", "11", "12", "13", "14", "18", "24", "36", "48", "64"])
        self.addWidget(self.fontsize)
        self.addSeparator()

        self.bold_action = QAction(QIcon(f"{img_path}/edit-bold.png"), "Bold", self)
        self.bold_action.setStatusTip("Bold")
        self.bold_action.setShortcut(QKeySequence.Bold)
        self.bold_action.setCheckable(True)
        self.addAction(self.bold_action)

        self.italic_action = QAction(QIcon(f"{img_path}/edit-italic.png"), "Italic", self)
        self.italic_action.setStatusTip("Italic")
        self.italic_action.setShortcut(QKeySequence.Italic)
        self.italic_action.setCheckable(True)
        self.addAction(self.italic_action)

        self.underline_action = QAction(QIcon(f"{img_path}/edit-underline.png"), "Underline", self)
        self.underline_action.setStatusTip("Underline")
        self.underline_action.setShortcut(QKeySequence.Underline)
        self.underline_action.setCheckable(True)
        self.addAction(self.underline_action)
        self.addSeparator()

        self.alignl_action = QAction(QIcon(f"{img_path}/edit-alignment.png"), "Align left", self)
        self.alignl_action.setStatusTip("Align text left")
        self.alignl_action.setCheckable(True)
        self.addAction(self.alignl_action)

        self.alignc_action = QAction(QIcon(f"{img_path}/edit-alignment-center.png"), "Align center", self)
        self.alignc_action.setStatusTip("Align text center")
        self.alignc_action.setCheckable(True)
        self.addAction(self.alignc_action)

        self.alignr_action = QAction(QIcon(f"{img_path}/edit-alignment-right.png"), "Align right", self)
        self.alignr_action.setStatusTip("Align text right")
        self.alignr_action.setCheckable(True)
        self.addAction(self.alignr_action)

        self.alignj_action = QAction(QIcon(f"{img_path}/edit-alignment-justify.png"), "Justify", self)
        self.alignj_action.setStatusTip("Justify text")
        self.alignj_action.setCheckable(True)
        self.addAction(self.alignj_action)

        format_group = QActionGroup(self)
        format_group.setExclusive(True)
        format_group.addAction(self.alignl_action)
        format_group.addAction(self.alignc_action)
        format_group.addAction(self.alignr_action)
        format_group.addAction(self.alignj_action)

        self.wrap_action = QAction(QIcon(f"{img_path}/arrow-continue.png"), "Wrap text to window", self)
        self.wrap_action.setStatusTip("Toggle wrap text to window")
        self.wrap_action.setCheckable(True)
        self.wrap_action.setChecked(True)
        self.addAction(self.wrap_action)

        # A list of all format-related widgets/actions, so we can disable/enable signals when updating.
        self._format_actions = [ self.fonts, self.fontsize, self.bold_action, 
                                 self.underline_action, self.italic_action ]
        # We don't need to disable signals for alignment, as they are paragraph-wide.
        

    def update_editor(self, text_editor: GTextEditor) -> None:
        """Update the font format toolbar/actions when a new text selection is made. 
        This is neccessary to keep toolbars/etc. in sync with the current edit state.
        """
        print(text_editor.textCursor().position())     
        if text_editor != self.editor:
            if self.editor is not None:
                self.fonts.currentFontChanged.disconnect()
                self.fontsize.currentIndexChanged[str].disconnect()
                self.bold_action.toggled.disconnect()
                self.underline_action.toggled.disconnect()
                self.italic_action.toggled.disconnect()
                self.alignl_action.triggered.disconnect()
                self.alignc_action.triggered.disconnect()
                self.alignr_action.triggered.disconnect()
                self.alignj_action.triggered.disconnect()
                self.wrap_action.triggered.disconnect()
            self.editor = text_editor
            self.fonts.currentFontChanged.connect(self.editor.setCurrentFont)
            self.fontsize.currentIndexChanged[str].connect(lambda s: self.editor.setFontPointSize(float(s)))
            self.bold_action.toggled.connect(lambda x: self.editor.setFontWeight(QFont.Bold if x else QFont.Normal))
            self.underline_action.toggled.connect(self.editor.setFontUnderline)
            self.italic_action.toggled.connect(self.editor.setFontItalic)
            self.alignl_action.triggered.connect(lambda: self.editor.setAlignment(Qt.AlignLeft))
            self.alignc_action.triggered.connect(lambda: self.editor.setAlignment(Qt.AlignCenter))
            self.alignr_action.triggered.connect(lambda: self.editor.setAlignment(Qt.AlignRight))
            self.alignj_action.triggered.connect(lambda: self.editor.setAlignment(Qt.AlignJustify))
            self.wrap_action.triggered.connect(lambda: self.editor.setLineWrapMode(int(self.editor.lineWrapMode() == 0)))

        for o in self._format_actions:  # Disable signals for all format widgets
            o.blockSignals(True)
        self.fonts.setCurrentFont(self.editor.currentFont())
        self.fontsize.setCurrentText(str(int(self.editor.fontPointSize())))
        self.italic_action.setChecked(self.editor.fontItalic())
        self.underline_action.setChecked(self.editor.fontUnderline())
        self.bold_action.setChecked(self.editor.fontWeight() == QFont.Bold)
        self.alignl_action.setChecked(self.editor.alignment() == Qt.AlignLeft)
        self.alignc_action.setChecked(self.editor.alignment() == Qt.AlignCenter)
        self.alignr_action.setChecked(self.editor.alignment() == Qt.AlignRight)
        self.alignj_action.setChecked(self.editor.alignment() == Qt.AlignJustify)
        for o in self._format_actions:
            o.blockSignals(False)

# ----------------------------------------------------------------------------------------

class GArrow(QFrame):
    def __init__(self, parent=None, collapsed=False):
        QFrame.__init__(self, parent=parent)
        self.setMaximumSize(24, 24)
        self._arrow_horizontal = (QPointF(7.0, 8.0), QPointF(17.0, 8.0), QPointF(12.0, 13.0))
        self._arrow_vertical = (QPointF(8.0, 7.0), QPointF(13.0, 12.0), QPointF(8.0, 17.0))
        self._arrow = None
        self.setArrow(int(collapsed))

    def setArrow(self, arrow_dir: bool):
        self._arrow = self._arrow_vertical if arrow_dir else self._arrow_horizontal

    def paintEvent(self, event):
        painter = QPainter()
        painter.begin(self)
        painter.setBrush(QColor(192, 192, 192))
        painter.setPen(QColor(64, 64, 64))
        painter.drawPolygon(*self._arrow)
        painter.end()

# ----------------------------------------------------------------------------------------

class GTitleFrame(QFrame):

    clicked = pyqtSignal()

    def __init__(self, parent=None, title="", collapsed=False):
        QFrame.__init__(self, parent=parent)

        self.setFixedHeight(26)
        self.move(QPoint(24, 0))
        self.setFrameShadow(QFrame.Sunken)
        self.setStyleSheet("border:1px solid rgb(41, 41, 41); background-color: #acc5f2;")

        self._hlayout = QHBoxLayout(self)
        self._hlayout.setContentsMargins(0, 0, 0, 0)
        self._hlayout.setSpacing(0)

        self._arrow = GArrow(collapsed=collapsed)
        self._arrow.setStyleSheet("border:0px")
        self._title = QLabel(title)
        self._title.setFixedHeight(24)
        self._title.move(QPoint(24, 0))
        self._title.setStyleSheet("border:0px")

        self._hlayout.addWidget(self._arrow)
        self._hlayout.addWidget(self._title)

    def mousePressEvent(self, event):
        self.clicked.emit()
        return super(GTitleFrame, self).mousePressEvent(event)

# ----------------------------------------------------------------------------------------

class GFrameLayout(QWidget):
    def __init__(self, parent=None, title: str=None):
        QFrame.__init__(self, parent=parent)

        self._is_collasped = True
        self._title_frame = GTitleFrame(title=title, collapsed=True)
        self.setStyleSheet(".QWidget{border:1px solid rgb(41, 41, 41); background-color: #f0f6ff}")
        self._content = QWidget()
        self._content_layout = QVBoxLayout()
        self._content.setLayout(self._content_layout)
        self._content.setVisible(not self._is_collasped)

        self._main_v_layout = QVBoxLayout(self)
        self._main_v_layout.addWidget(self._title_frame)
        self._main_v_layout.addWidget(self._content)
        self._title_frame.clicked.connect(self.toggleCollapsed)

    def addSpacing(self, size: int) -> None:
        self._content_layout.addSpacing(size)

    def addLayout(self, layout):
        """[summary]

        Args:
            layout ([type]): [description]
            name (str, optional): [description]. Defaults to None.
        """
        self._content_layout.addLayout(layout)

    def addWidget(self, widget: QWidget):
        """[summary]

        Args:
            widget (QWidget): [description]
            name (str, optional): A name if used to tag the widget. If none, the widget
                will not be tagged to be updated. If string, should be a string. If dict,
                should have tags as keys and QWidgets as values. Defaults to None.
        """
        self._content_layout.addWidget(widget)

    def toggleCollapsed(self):
        self._content.setVisible(self._is_collasped)
        self._is_collasped = not self._is_collasped
        self._title_frame._arrow.setArrow(int(self._is_collasped))

# ----------------------------------------------------------------------------------------

class GTagBar(QWidget):

    def __init__(self):
        super(GTagBar, self).__init__()
        self.tags = []
        self.h_layout = QHBoxLayout()
        self.h_layout.setSpacing(4)
        self.setLayout(self.h_layout)
        self.line_edit = QLineEdit()
        self.h_layout.setContentsMargins(2,2,2,2)
        self.refresh()
        self.line_edit.returnPressed.connect(self.create_tags)

    def create_tags(self):
        new_tags = self.line_edit.text().split(', ')
        self.line_edit.setText('')
        self.tags.extend(new_tags)
        self.tags = list(set(self.tags))
        self.tags.sort(key=lambda x: x.lower())
        self.refresh()

    def refresh(self):
        for i in reversed(range(self.h_layout.count())):
            self.h_layout.itemAt(i).widget().setParent(None)
        for tag in self.tags:
            self.add_tag_to_bar(tag)
        self.h_layout.addWidget(self.line_edit)
        self.line_edit.setFocus()

    def add_tag_to_bar(self, text):
        tag = QFrame()
        tag.setStyleSheet('border:1px solid rgb(192, 192, 192); border-radius: 4px;')
        tag.setContentsMargins(2, 2, 2, 2)
        tag.setFixedHeight(20)
        hbox = QHBoxLayout()
        hbox.setContentsMargins(4, 0, 4, 4)
        hbox.setSpacing(10)
        tag.setLayout(hbox)
        label = QLabel(text)
        label.setStyleSheet('border:0px')
        label.setFixedHeight(16)
        hbox.addWidget(label)
        x_button = QPushButton('x')
        x_button.setFixedSize(16, 16)
        x_button.setStyleSheet('border:0px; font-weight:bold')
        x_button.clicked.connect(lambda: self.delete_tag(text))
        hbox.addWidget(x_button)
        self.h_layout.addWidget(tag)

    def delete_tag(self, tag_name):
        self.tags.remove(tag_name)
        self.refresh()

# ----------------------------------------------------------------------------------------

class GAnswer(QFrame):

    def __init__(self, controls: GTextToolbar, **kwargs) -> None:
        super(GAnswer, self).__init__(**kwargs)
        self.setStyleSheet(".GAnswer{border:1px solid rgb(41, 41, 41); background-color: #e4ebb7}")
        _content = QGridLayout(self)
        _content.addWidget(QLabel("Text"), 0, 0)
        self._text = GTextEditor(controls)
        _content.addWidget(self._text, 0, 1)
        _content.addWidget(QLabel("Grade"), 1, 0)
        self._grade = QLineEdit()
        _content.addWidget(self._grade, 1, 1)
        _content.addWidget(QLabel("Feedback"), 2, 0)
        self._feedback = GTextEditor(controls)
        _content.addWidget(self._feedback, 2, 1)
        _content.setRowStretch(0, 4)
        self.setFixedHeight(140)
        self.setFixedWidth(220)

    def to_gui(self, items: dict) -> None:
        """[summary]

        Args:
            items (dict): [description]
        """
        fraction = float(self._grade.text())
        tp = self._text.toolbar.text_type.currentIndex()
        if tp == 0:
            text = self._text.toMarkdown()
            formatting = Format.MD
        elif tp == 1:
            text = self._text.toHtml()
            formatting = Format.HTML
        else:
            text = self._text.toPlainText()
            formatting = Format.PLAIN
        feedback = self._feedback.getFText()
        if "answer" not in items:
            items["answer"] = []
        items["answer"].append(Answer(fraction, text, feedback, formatting))

# ----------------------------------------------------------------------------------------

class GCFeedback(QFrame):

    def __init__(self, toolbar: GTextToolbar, **kwargs) -> None:
        super().__init__(**kwargs)
        self.setStyleSheet(".GCFeedback{border:1px solid rgb(41, 41, 41); background-color: #e4ebb7}")
        self._correct = GTextEditor(toolbar)
        self._incomplete = GTextEditor(toolbar)
        self._incorrect  = GTextEditor(toolbar)
        self._show = QCheckBox("Show the number of correct responses once the question has finished")
        _content = QGridLayout(self)
        _content.addWidget(QLabel("Feedback for correct answer"), 0, 0)
        _content.addWidget(self._correct, 1, 0)
        _content.addWidget(QLabel("Feedback for incomplete answer"), 0, 1)
        _content.addWidget(self._incomplete, 1, 1)
        _content.addWidget(QLabel("Feedback for incorrect answer"), 0, 2)
        _content.addWidget(self._incorrect, 1, 2)
        _content.addWidget(self._show, 2, 0, 1, 3)
        
    def to_gui(self, items: dict) -> None:
        correct = self._correct.getFText()
        incomplete = self._incomplete.getFText()
        incorrect = self._incorrect.getFText()
        items["combined_feedback"] = CombinedFeedback(correct, incomplete, incorrect, self._show.isChecked())

# ----------------------------------------------------------------------------------------


def main():
    app = QApplication(sys.argv)
    app.setStyle('Breeze')
    w = GUI()
    sys.exit(app.exec_())