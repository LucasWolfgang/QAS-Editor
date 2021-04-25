import sys
from os.path import splitext
from uuid import uuid4
from .quiz import Quiz
from . import questions
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QStandardItemModel, QFont, QImage, QTextDocument, QKeySequence,\
                        QIcon
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout,\
                            QFrame, QSplitter, QTreeView, QTextEdit,\
                            QMainWindow, QStatusBar, QFileDialog, QToolBar,\
                            QFontComboBox, QComboBox, QActionGroup, QMessageBox,\
                            QAction, QGroupBox, QCheckBox, QLineEdit, QPushButton

class GUI(QMainWindow):
    
    def __init__(self, *args, **kwargs):
        super(GUI, self).__init__(*args, **kwargs)
        self.setWindowTitle('PyQt5 Treeview Example - pythonspot.com')

        # Data handling variables
        self.path = None
        self.quiz = None

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

        # Create main window divider for the splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([125, 150])
        hbox = QHBoxLayout()
        hbox.addWidget(splitter)
        container = QWidget()
        container.setLayout(hbox)
        self.setCentralWidget(container)

        # Create main window data view using a QTreeVire
        self.dataView = QTreeView()
        self.dataView.setRootIsDecorated(False)
        self.dataView.setAlternatingRowColors(True)
        self.dataView.setHeaderHidden(True)
        model = QStandardItemModel(0, 1)
        model.setHeaderData(0, Qt.Horizontal, "Classification")
        splitter.addWidget(self.dataView)

        # Create right part of the splitter (type, text, options)
        right = QFrame()
        vbox = QVBoxLayout(right)
        right.setLayout(vbox)
        splitter.addWidget(right)
        
        self.question_type = QComboBox()
        types = []
        for m in dir(questions):
            cls = getattr(questions, m)
            try:
                if issubclass(cls, questions.Question):
                    types.append(m)
            except TypeError:
                pass
        self.question_type.addItems(types)
        self.question_type.setStyleSheet("margin: 0px 20px 0px 0px")
        self.question_type.currentTextChanged.connect(self.update_question_type)
        check1 = QCheckBox("Use auto name")
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
        type_box = QGroupBox("Question Definition")
        type_box.setLayout(hbox)
        vbox.addWidget(type_box)

        self.editor = TextEdit()
        self.editor_toobar = TextToolbar(self.editor)
        vbox.addWidget(self.editor_toobar)
        self.editor.setAutoFormatting(QTextEdit.AutoAll)
        self.editor.selectionChanged.connect(self.editor_toobar.update_format)
        self.editor.setFont(QFont('Times', 12))
        self.editor.setFontPointSize(12)   
        vbox.addWidget(self.editor)

        # Create lower status bar. probably will be removed.
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        self.setGeometry(300, 300, 1000, 600)
        self.show()

    def file_open(self):
        """
        [summary]
        """
        path, _ = QFileDialog.getOpenFileName(self, "Open file", "", 
                    "Aiken (*.txt);Cloze (*.cloze);GIFT (*.gift); Markdown (*.md); "+
                    "LaTex (*.tex);XML (*.xml);All files (*.*)")
        try:
            if path[-4:] == ".xml":
                Quiz.read_xml(path)
        except Exception as e:
            self.dialog_critical(str(e))
        else:
            self.path = path

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

    def update_question_type(self, value):
        """
        [summary]
        """
        cls = getattr(questions, value)
        init_fields = cls.__init__.__code__.co_varnames[1:-2]
        actions = list(filter(lambda x: '_' not in x[0], dir(cls)))[1:]
        print(f"Changed: {init_fields}\n\t{actions}")

    def dialog_critical(self, s):
        dlg = QMessageBox(self)
        dlg.setText(s)
        dlg.setIcon(QMessageBox.Critical)
        dlg.show()

# ----------------------------------------------------------------------------------------

class TextEdit(QTextEdit):

    def canInsertFromMimeData(self, source):
        """
        [summary]

        Args:
            source ([type]): [description]

        Returns:
            [type]: [description]
        """
        if source.hasImage():
            return True
        else:
            return super(TextEdit, self).canInsertFromMimeData(source)

    def insertFromMimeData(self, source):
        """
        [summary]

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
                    # If we hit a non-image or non-local URL break the loop and fall out
                    # to the super call & let Qt handle it
                    break
            else:
                # If all were valid images, finish here.
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

    def __init__(self, editor: TextEdit, *args, **kwargs):
        super(TextToolbar, self).__init__(*args, **kwargs)

        self.editor = editor
        self.setIconSize(QSize(16, 16))

        # We need references to these actions/settings to update as selection changes, so attach to self.
        self.fonts = QFontComboBox()
        self.fonts.currentFontChanged.connect(editor.setCurrentFont)
        self.addWidget(self.fonts)

        self.fontsize = QComboBox()
        self.fontsize.addItems(["7", "8", "9", "10", "11", "12", "13", "14", "18", "24", "36", "48", "64"])

        # Connect to the signal producing the text of the current selection. Convert the string to float
        # and set as the pointsize. We could also use the index + retrieve from 
        self.fontsize.currentIndexChanged[str].connect(lambda s: editor.setFontPointSize(float(s)) )
        self.addWidget(self.fontsize)

        self.bold_action = QAction(QIcon('images/edit-bold.png'), "Bold", self)
        self.bold_action.setStatusTip("Bold")
        self.bold_action.setShortcut(QKeySequence.Bold)
        self.bold_action.setCheckable(True)
        self.bold_action.toggled.connect(lambda x: editor.setFontWeight(QFont.Bold if x else QFont.Normal))
        self.addAction(self.bold_action)

        self.italic_action = QAction(QIcon('./images/edit-italic.png'), "Italic", self)
        self.italic_action.setStatusTip("Italic")
        self.italic_action.setShortcut(QKeySequence.Italic)
        self.italic_action.setCheckable(True)
        self.italic_action.toggled.connect(editor.setFontItalic)
        self.addAction(self.italic_action)

        self.underline_action = QAction(QIcon('./images/edit-underline.png'), "Underline", self)
        self.underline_action.setStatusTip("Underline")
        self.underline_action.setShortcut(QKeySequence.Underline)
        self.underline_action.setCheckable(True)
        self.underline_action.toggled.connect(editor.setFontUnderline)
        self.addAction(self.underline_action)

        self.alignl_action = QAction(QIcon('./images/edit-alignment.png'), "Align left", self)
        self.alignl_action.setStatusTip("Align text left")
        self.alignl_action.setCheckable(True)
        self.alignl_action.triggered.connect(lambda: editor.setAlignment(Qt.AlignLeft))
        self.addAction(self.alignl_action)

        self.alignc_action = QAction(QIcon('./images/edit-alignment-center.png'), "Align center", self)
        self.alignc_action.setStatusTip("Align text center")
        self.alignc_action.setCheckable(True)
        self.alignc_action.triggered.connect(lambda: editor.setAlignment(Qt.AlignCenter))
        self.addAction(self.alignc_action)

        self.alignr_action = QAction(QIcon('images/edit-alignment-right.png'), "Align right", self)
        self.alignr_action.setStatusTip("Align text right")
        self.alignr_action.setCheckable(True)
        self.alignr_action.triggered.connect(lambda: editor.setAlignment(Qt.AlignRight))
        self.addAction(self.alignr_action)

        self.alignj_action = QAction(QIcon('./images/edit-alignment-justify.png'), "Justify", self)
        self.alignj_action.setStatusTip("Justify text")
        self.alignj_action.setCheckable(True)
        self.alignj_action.triggered.connect(lambda: editor.setAlignment(Qt.AlignJustify))
        self.addAction(self.alignj_action)

        format_group = QActionGroup(self)
        format_group.setExclusive(True)
        format_group.addAction(self.alignl_action)
        format_group.addAction(self.alignc_action)
        format_group.addAction(self.alignr_action)
        format_group.addAction(self.alignj_action)

        wrap_action = QAction(QIcon('./images/arrow-continue.png'), "Wrap text to window", self)
        wrap_action.setStatusTip("Toggle wrap text to window")
        wrap_action.setCheckable(True)
        wrap_action.setChecked(True)
        wrap_action.triggered.connect(self.edit_toggle_wrap)
        self.addAction(wrap_action)

        # A list of all format-related widgets/actions, so we can disable/enable signals when updating.
        self._format_actions = [
            self.fonts,
            self.fontsize,
            self.bold_action,
            self.italic_action,
            self.underline_action,
            # We don't need to disable signals for alignment, as they are paragraph-wide.
        ]
        self.update_format()

    def block_signals(self, objects, b):
        for o in objects:
            o.blockSignals(b)

    def update_format(self):
        """
        Update the font format toolbar/actions when a new text selection is made. This is neccessary to keep
        toolbars/etc. in sync with the current edit state.
        :return:
        """
        # Disable signals for all format widgets, so changing values here does not trigger further formatting.
        self.block_signals(self._format_actions, True)

        #self.fonts.setCurrentFont(self.editor.currentFont())
        # Nasty, but we get the font-size as a float but want it was an int
        self.fontsize.setCurrentText(str(int(self.editor.fontPointSize())))

        self.italic_action.setChecked(self.editor.fontItalic())
        self.underline_action.setChecked(self.editor.fontUnderline())
        self.bold_action.setChecked(self.editor.fontWeight() == QFont.Bold)

        self.alignl_action.setChecked(self.editor.alignment() == Qt.AlignLeft)
        self.alignc_action.setChecked(self.editor.alignment() == Qt.AlignCenter)
        self.alignr_action.setChecked(self.editor.alignment() == Qt.AlignRight)
        self.alignj_action.setChecked(self.editor.alignment() == Qt.AlignJustify)

        self.block_signals(self._format_actions, False)

    def edit_toggle_wrap(self):
        self.editor.setLineWrapMode( 1 if self.editor.lineWrapMode() == 0 else 0 )


class QuestionSpecificBox(QHBoxLayout):

    def __init__(self, editor: TextEdit, *args, **kwargs):
        super(QuestionSpecificBox, self).__init__(*args, **kwargs)
    pass

def main():
    app = QApplication(sys.argv)
    app.setStyle('Breeze')
    w = GUI()
    sys.exit(app.exec_())