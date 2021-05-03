import sys
import os
from os.path import splitext
from uuid import uuid4
from .quiz import Quiz, QTYPES
from . import questions
from typing import List
from PyQt5.QtCore import Qt, QSize, QPoint, QPointF, pyqtSignal, QVariant
from PyQt5.QtGui import QStandardItemModel, QFont, QImage, QTextDocument, QKeySequence,\
                        QIcon, QColor, QPainter, QStandardItem
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout,\
                            QFrame, QSplitter, QTreeView, QTextEdit,\
                            QMainWindow, QStatusBar, QFileDialog, QToolBar,\
                            QFontComboBox, QComboBox, QActionGroup, QMessageBox,\
                            QAction, QCheckBox, QLineEdit, QPushButton, QLabel

img_path = f"{os.path.dirname(os.path.realpath(__file__))}/images"

class GUI(QMainWindow):
    
    def __init__(self, *args, **kwargs):
        super(GUI, self).__init__(*args, **kwargs)
        self.setWindowTitle('PyQt5 Treeview Example - pythonspot.com')

        # Data handling variables
        self.path = None
        self.top_quiz = None
        self.current_category=None

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

        # Create main window divider for the splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([125, 150])
        self.setCentralWidget(splitter)

        # Create main window data view using a QTreeVire
        self.dataView = QTreeView()
        self.dataView.setHeaderHidden(True)
        self.dataView.doubleClicked.connect(self.update_item)
        self.data_root = QStandardItemModel(0, 1)
        self.data_root.setHeaderData(0, Qt.Horizontal, "Classification")
        self.dataView.setModel(self.data_root)
        splitter.addWidget(self.dataView)

        # Create right part of the splitter (type, text, options)
        self.general_data = None
        self.combined_feedback = None
        self.multiple_tries = None

        right = QFrame()
        splitter.addWidget(right)
        self.cframe_vbox = QVBoxLayout()
        right.setLayout(self.cframe_vbox)
        self.add_general_data()
        self.cframe_vbox.addStretch()
        
        # Create lower status bar. probably will be removed.
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        self.setGeometry(300, 300, 1000, 600)
        self.show()

    def add_general_data(self) -> None:
        if self.general_data is not None:
            return
        self.general_data = FrameLayout(title="General Data")
        self.cframe_vbox.addWidget(self.general_data)

        self.question_type = QComboBox()
        self.question_type.addItems(QTYPES)
        self.question_type.currentTextChanged.connect(self.update_question_type)
        check1 = QCheckBox("Use auto name")
        check1.setStyleSheet("margin: 0px 0px 0px 20px")
        self.question_name = QLineEdit()
        self.question_name.setText("Question name")
        self.question_name.setToolTip("Name used to storage the question in the database.")
        self.question_name.setStyleSheet("margin: 0px 40px 0px 0px")
        new_button = QPushButton("Create")
        hbox = QHBoxLayout()
        hbox.addWidget(self.question_type)
        hbox.addWidget(check1)
        hbox.addWidget(self.question_name)
        hbox.addWidget(new_button)
        self.general_data.addLayout(hbox)

        self.editor = TextEdit(self.editor_toobar)
        self.general_data.addWidget(self.editor)


    def dialog_critical(self, s):
        dlg = QMessageBox(self)
        dlg.setTedxt(s)
        dlg.setIcon(QMessageBox.Critical)
        dlg.show()

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
        actions = list(filter(lambda x: '_' not in x[0], dir(cls)))[1:]
        print(f"Changed: {init_fields}\n\t{actions}")

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
                self.alignl_action.triggered.diconnect()
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
        self.setStyleSheet("border:1px solid rgb(41, 41, 41); ")

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
        self._title_frame: TitleFrame = TitleFrame(title=title, collapsed=True)
        self._content = QWidget()
        self._content_layout = QVBoxLayout()
        self._content.setLayout(self._content_layout)
        self._content.setVisible(not self._is_collasped)

        self._main_v_layout = QVBoxLayout(self)
        self._main_v_layout.addWidget(self._title_frame)
        self._main_v_layout.addWidget(self._content)
        self._title_frame.clicked.connect(self.toggleCollapsed)

    def addWidget(self, widget: QWidget):
        self._content_layout.addWidget(widget)

    def addLayout(self, layout):
        self._content_layout.addLayout(layout)

    def toggleCollapsed(self):
        self._content.setVisible(self._is_collasped)
        self._is_collasped = not self._is_collasped
        self._title_frame._arrow.setArrow(int(self._is_collasped))

# ----------------------------------------------------------------------------------------

class QGlobals(QHBoxLayout):

    def __init__(self, editor: TextEdit, *args, **kwargs):
        super().__init__(*args, **kwargs)
    pass

def main():
    app = QApplication(sys.argv)
    app.setStyle('Breeze')
    w = GUI()
    sys.exit(app.exec_())