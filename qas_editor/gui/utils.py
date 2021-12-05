from os.path import splitext, dirname
from uuid import uuid4
from ..enums import Format
from ..wrappers import FText, Tags
from PyQt5.QtCore import Qt, QSize, QPoint, QPointF, pyqtSignal
from PyQt5.QtGui import QFont, QImage, QTextDocument, QKeySequence, QIcon, QColor, QPainter
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QFrame, QTextEdit, QToolBar, \
                            QFontComboBox, QComboBox, QActionGroup, QAction, QLineEdit, \
                            QPushButton, QLabel

img_path = __file__.replace('\\', '/').rsplit('/', 2)[0] + "/images"

class GTextEditor(QTextEdit):

    def __init__(self, toolbar: "GTextToolbar") -> None:
        super().__init__()
        self.toolbar = toolbar
        self.text_format: Format = 2
        self.math_type = 0
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

    def setFText(self, text: FText) -> None:
        if text.formatting == Format.MD:
            self.setMarkdown(text.text)
        elif text.formatting == Format.HTML:
            self.setHtml(text.text)
        else:
            self.setPlainText(text.text)

# ----------------------------------------------------------------------------------------
class GTextToolbar(QToolBar):

    FORMATS = {"MarkDown": Format.MD, "HTML": Format.HTML, "PlainText": Format.PLAIN}

    def __init__(self, *args, **kwargs):
        super(GTextToolbar, self).__init__(*args, **kwargs)

        self.editor: GTextEditor = None
        self.setIconSize(QSize(16, 16))

        self.fonts = QFontComboBox()
        self.addWidget(self.fonts)

        self.text_type = QComboBox()
        self.text_type.addItems(list(self.FORMATS.keys()))
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
        if text_editor != self.editor:
            if self.editor is not None:
                self.editor.text_format = self.text_type.currentIndex
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
class GFrameLayout(QVBoxLayout):
    def __init__(self, parent=None, title: str=None):
        QVBoxLayout.__init__(self)

        self._is_collasped = True
        self._title_frame = GTitleFrame(parent, title, True)
        self._title_frame.clicked.connect(self.toggleCollapsed)
        super().addWidget(self._title_frame)
        self._content_layout = QVBoxLayout()
        self._content = QWidget()
        self._content.setStyleSheet(".QWidget{border:1px solid rgb(41, 41, 41); \
                                    background-color: #f0f6ff}")
        self._content.setLayout(self._content_layout)
        self._content.setVisible(not self._is_collasped)
        super().addWidget(self._content)

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

    def create_tags(self):
        new_tags = self.line_edit.text().split(', ')
        self.line_edit.setText('')
        self.tags.extend(new_tags)
        self.tags = list(set(self.tags))
        self.tags.sort(key=lambda x: x.lower())
        self.refresh()

    def from_obj(self, obj: Tags) -> None:
        self.tags = list(obj)

    def refresh(self):
        for i in reversed(range(self.h_layout.count())):
            self.h_layout.itemAt(i).widget().setParent(None)
        for tag in self.tags:
            self.add_tag_to_bar(tag)
        self.h_layout.addWidget(self.line_edit)
        self.line_edit.setFocus()

    def to_obj(self):
        return Tags(self.tags)

# ----------------------------------------------------------------------------------------