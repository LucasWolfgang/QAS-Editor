import sys
import os
from os.path import splitext
from uuid import uuid4
from .quiz import Quiz, QTYPES
from . import questions
from typing import Dict, List
from PyQt5.QtCore import Qt, QSize, QPoint, QPointF, pyqtSignal, QVariant
from PyQt5.QtGui import QStandardItemModel, QFont, QImage, QTextDocument, QKeySequence,\
                        QIcon, QColor, QPainter, QStandardItem
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout,\
                            QFrame, QSplitter, QTreeView, QTextEdit, QGroupBox,\
                            QMainWindow, QStatusBar, QFileDialog, QToolBar, QMenu,\
                            QFontComboBox, QComboBox, QActionGroup, QMessageBox,\
                            QAction, QCheckBox, QLineEdit, QPushButton, QLabel, QGridLayout

from qas_editor import quiz

img_path = f"{os.path.dirname(os.path.realpath(__file__))}/images"

class GUI(QMainWindow):
    
    def __init__(self, *args, **kwargs):
        super(GUI, self).__init__(*args, **kwargs)
        self.setWindowTitle('PyQt5 Treeview Example - pythonspot.com')

        # Data handling variables
        self._blocks: List[FrameLayout] = []
        self.path = None
        self.top_quiz = None
        self.current_category = None
        self.general_block = None
        self.multiple_tries_block = None
        self.answer_block = None
        self.solution_block = None
        self.blocks = []

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
        self.editor_toobar = TextToolbar()
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
        question_type = QComboBox()
        question_type.addItems(QTYPES)
        question_type.currentTextChanged.connect(self.update_question_type)
        question_create = QPushButton("Create")
        question_create.clicked.connect(self.create_question)
        vbox = QVBoxLayout()
        vbox.addWidget(question_type)
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
        renameAction = QAction('Delete', self)
        renameAction.triggered.connect(lambda: self._delete_item(item))
        self.menu.addAction(renameAction)
        self.menu.popup(self.dataView.mapToGlobal(event))

    def _delete_item(self, item) -> None:
        if isinstance(item, questions.Question):
            print("Question!")
        elif isinstance(item, Quiz):
            print("Category!")

    def add_answer_block(self) -> None:
        if self.answer_block is not None:
            return
        self.answer_block = FrameLayout(title="Answers")
        self.cframe_vbox.addWidget(self.answer_block)
        check1 = QCheckBox("Shuffle the questions")

    def add_feedback_block(self) -> None:
        frame = FrameLayout(title="Feedbacks")
        self._blocks.append(frame)
        self.cframe_vbox.addWidget(frame)

        frame.addWidget(QLabel("General feedback"))
        self.general_feedback = TextEdit(self.editor_toobar)
        frame.addWidget(self.general_feedback)

        self.correct_feedback = TextEdit(self.editor_toobar)
        self.incomplete_feedback = TextEdit(self.editor_toobar)
        self.incorrect_feedback = TextEdit(self.editor_toobar)
        self.shuffle = QCheckBox("Show the number of correct responses once the question has finished")
        wdt = QWidget()
        cfeedback = QVBoxLayout(wdt)
        cfeedback.addWidget(QLabel("Feedback for correct answer"))
        cfeedback.addWidget(self.correct_feedback)
        cfeedback.addWidget(QLabel("Feedback for incomplete answer"))
        cfeedback.addWidget(self.incomplete_feedback)
        cfeedback.addWidget(QLabel("Feedback for incorrect answer"))
        cfeedback.addWidget(self.incorrect_feedback)
        cfeedback.addWidget(self.shuffle)
        frame.addWidget(wdt, "combined_feedback")

    def add_general_data_block(self) -> None:
        if self.general_block is not None:
            return
        self.general_block = FrameLayout(title="General Data")
        self.cframe_vbox.addWidget(self.general_block)

        self.question_name = QLineEdit()
        self.question_name.setToolTip("Name used to storage the question in the database.")
        self.default_mark = QLineEdit()
        self.default_mark.setToolTip("Default mark for the question.")
        self.id_number = QLineEdit()
        self.id_number.setToolTip("Provides a second way of finding a question.")
        self.default_grade = QLineEdit()
        self.default_grade.setToolTip("Default grade of the question.")
        grid = QGridLayout()
        grid.addWidget(QLabel("Question name"), 0, 0)
        grid.addWidget(self.question_name, 0,1)
        grid.setColumnStretch(1, 4)
        grid.addWidget(QLabel("Default mark"), 0, 2)
        grid.addWidget(self.default_mark, 0, 3)
        grid.addWidget(QLabel("ID number"), 0, 4)
        grid.addWidget(self.id_number, 0, 5)
        grid.addWidget(QLabel("Tags"), 1, 0)
        grid.addWidget(TagBar(), 1, 1)
        grid.addWidget(QLabel("Default grade"), 1, 2)
        grid.addWidget(self.default_grade, 1, 3)
        self.general_block.addLayout(grid)
        self.general_block.addSpacing(10)
        self.general_block.addWidget(QLabel("Question text"))
        self.editor = TextEdit(self.editor_toobar)
        self.general_block.addWidget(self.editor)

        #Check      use_latex
        #SmallText  default_grade

    def add_multiple_tries_block(self) -> None:
        if self.multiple_tries_block is not None:
            return
        self.multiple_tries_block = FrameLayout(title="Multiple Tries")
        self.cframe_vbox.addWidget(self.multiple_tries_block)
        # self.hints: List[Hint] = []

    def add_solution_block(self) -> None:
        if self.solution_block is not None:
            return
        self.solution_block = FrameLayout(title="Solutions")
        self.cframe_vbox.addWidget(self.solution_block)

        self.solution_block.addWidget(QLabel("Solution"))
        self.solution = TextEdit(self.editor_toobar)
        self.solution_block.addWidget(self.solution)

    def create_question(self) -> None:
        pass

    def create_category(self) -> None:
        pass

    def dialog_critical(self, s):
        dlg = QMessageBox(self)
        dlg.setTedxt(s)
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
        for block in self._blocks:
            block.update_visible_items(init_fields)

# ----------------------------------------------------------------------------------------

class TextEdit(QTextEdit):

    def __init__(self, toolBar: "TextToolbar") -> None:
        super().__init__()
        self.setAutoFormatting(QTextEdit.AutoAll)
        self.selectionChanged.connect(lambda: toolBar.update_editor(self))
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
            return super(TextEdit, self).canInsertFromMimeData(source)

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
        super(TextEdit, self).insertFromMimeData(source)

# ----------------------------------------------------------------------------------------

class TextToolbar(QToolBar):

    def __init__(self, *args, **kwargs):
        super(TextToolbar, self).__init__(*args, **kwargs)

        self.editor: TextEdit = None
        self.setIconSize(QSize(16, 16))

        self.fonts = QFontComboBox()
        self.addWidget(self.fonts)

        self.text_type = QComboBox()
        self.text_type.addItems(["MarkDown", "PlainText", "HTML"])
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
        

    def update_editor(self, text_editor: TextEdit) -> None:
        """Update the font format toolbar/actions when a new text selection is made. 
        This is neccessary to keep toolbars/etc. in sync with the current edit state.
        """     
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

class Arrow(QFrame):
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

class TitleFrame(QFrame):

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

        self._arrow = Arrow(collapsed=collapsed)
        self._arrow.setStyleSheet("border:0px")
        self._title = QLabel(title)
        self._title.setFixedHeight(24)
        self._title.move(QPoint(24, 0))
        self._title.setStyleSheet("border:0px")

        self._hlayout.addWidget(self._arrow)
        self._hlayout.addWidget(self._title)

    def mousePressEvent(self, event):
        self.clicked.emit()
        return super(TitleFrame, self).mousePressEvent(event)

# ----------------------------------------------------------------------------------------

class FrameLayout(QWidget):
    def __init__(self, parent=None, title: str=None):
        QFrame.__init__(self, parent=parent)

        self._is_collasped: bool = True
        self._items: Dict[str, QWidget] = {}
        self._title_frame: TitleFrame = TitleFrame(title=title, collapsed=True)
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

    def addLayout(self, layout, name:str=None):
        self._content_layout.addLayout(layout)
        if name is not None:
            self._items[name] = layout

    def addWidget(self, widget: QWidget, name:str=None):
        self._content_layout.addWidget(widget)
        if name is not None:
            self._items[name] = widget

    def update_visible_items(self, items: List[str]) -> None:
        for item in self._items:
            self._items[item].setVisible(item in items)

    def toggleCollapsed(self):
        self._content.setVisible(self._is_collasped)
        self._is_collasped = not self._is_collasped
        self._title_frame._arrow.setArrow(int(self._is_collasped))

# ----------------------------------------------------------------------------------------

class TagBar(QWidget):
    def __init__(self):
        super(TagBar, self).__init__()
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

def main():
    app = QApplication(sys.argv)
    app.setStyle('Breeze')
    w = GUI()
    sys.exit(app.exec_())