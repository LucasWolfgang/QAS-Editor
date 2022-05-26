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
from PyQt5.QtCore import QPoint, QPointF
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QPushButton, QApplication,\
                            QFrame, QLabel
from PyQt5.QtGui import QColor, QPainter
from ..questions import QCalculatedMultichoice, QCalculatedSimple, QCloze,\
                        QDragAndDropImage, QDragAndDropText, QMatching, \
                        QMissingWord, QMultichoice, QCalculated, QNumerical,\
                        QDragAndDropMarker
from .widget import GCalculated, GCloze, GDrag, GAnswer, GHint, GCheckBox

class GOptions(QVBoxLayout):
    """GUI for GOptions class.
    """
    _TYPES = {
        QCalculated: GCalculated,
        QCalculatedSimple: GCalculated,
        QCalculatedMultichoice: GCalculated,
        QCloze: GCloze,
        QDragAndDropText: GDrag,
        QDragAndDropMarker: GDrag,
        QDragAndDropImage: GDrag,
        QMatching: None,        #Subquestion,
        QMultichoice: GAnswer,
        QNumerical: GAnswer,
        QMissingWord: None     #SelectOption
    }

    def __init__(self, toolbar, **kwargs) -> None:
        super().__init__(**kwargs)
        self.visible = True
        self.toolbar = toolbar
        self.__ctype = None
        self.__obj: list = None
        self.setSpacing(4)

    def add(self, child=None):
        """_summary_

        Raises:
            TypeError: _description_

        Returns:
            _type_: _description_
        """
        cls = self._TYPES[self.__ctype]
        item = cls(self.toolbar, self.__obj, child)
        self.addWidget(item)
        return item

    def from_obj(self, obj) -> None:
        """_summary_

        Args:
            objs (list): _description_
        """
        ctype = self.__ctype
        self.__ctype = type(obj)
        self.__obj = obj.options
        new_size = len(self.__obj)
        if self.count() != 0:
            to_rem = 0
            if self._TYPES[ctype][0] != self._TYPES[self.__ctype][0]:
                to_rem = self.count()
            elif self.count() > new_size:
                to_rem = self.count() - new_size
            for i in reversed(range(to_rem)):
                self.itemAt(i).widget().deleteLater()
            for obj, child in zip(self.__obj, self.children()):
                child.from_obj(obj)
        if self.count() < new_size:
            for obj in self.__obj[self.count():]:
                self.add(obj)

    def get_attr(self):
        return "options"

    def pop(self) -> None:
        """_summary_
        """
        widget = QApplication.focusWidget().parent()
        for idx in range(self.count()):
            if self.itemAt(idx).widget() == widget:
                self.removeWidget(widget)
                widget.deleteLater()

    def setVisible(self, visible: bool):    # pylint: disable=C0103
        """_summary_

        Args:
            visible (bool): _description_
        """
        if self.visible == visible:
            return
        for child in self.children():
            child.setVisible(visible)


class GHintsList(QVBoxLayout):
    """GUI class for the MultipleTries wrapper
    """

    def __init__(self, parent, toolbar) -> None:
        super().__init__(parent)
        self.__obj: list = None
        self._toolbar = toolbar

    def add(self, obj):
        """ Adds a new Hint Widget to the instances's VBox
        """
        hint_widget = GHint(self._toolbar, obj)
        self.__obj.append(hint_widget.obj)
        super().addWidget(hint_widget)
        return hint_widget

    def from_obj(self, obj) -> None:
        """_summary_

        Args:
            obj (MultipleTries): _description_
        """
        self.__obj = obj.hints
        new_size = len(self.__obj)
        if len(self.children()) != 0:
            to_rem = 0
            if self.count() > new_size:
                to_rem = self.count() - new_size
            for i in reversed(range(to_rem)):
                self.itemAt(i).layout().deleteLater()
            for obj, child in zip(self.__obj, self.children()):
                child.from_obj(obj)
        if self.count() < new_size:
            for obj in self.__obj[self.count():]:
                self.add(obj)

    def get_attr(self):
        return "hints"

    def pop(self) -> None:
        """_summary_
        """
        if not self.count():
            return
        self.itemAt(self.count()-1).widget().deleteLater()


class GUnits(QVBoxLayout):
    """ Wdiget for the Unit data used by Questions.
    """

    def __init__(self):
        super().__init__()

    def get_attr(self):
        return "units"


class GZones(QVBoxLayout):
    """ Widget to list Zones used by the question.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.__obj = None
        _row = QHBoxLayout()
        self._background = QPushButton("Background")
        _row.addLayout(self._background)
        self._highlight = GCheckBox("highlight", "Highlight dropzones with inc"
                                    "orrect correct markers placed", parent)

    def from_obj(self, obj) -> None:
        """_summary_

        Args:
            obj (MultipleTries): _description_
        """
        self.__obj = obj.hints
        new_size = len(self.__obj)
        if len(self.children()) != 0:
            to_rem = 0
            if self.count() > new_size:
                to_rem = self.count() - new_size
            for i in reversed(range(to_rem)):
                self.itemAt(i).layout().deleteLater()
            for key, child in zip(self.__obj, self.children()):
                child.from_obj(key)
        if self.count() < new_size:
            for data in self.__obj[self.count():]:
                item = self.add()
                item.from_obj(data)

    def get_attr(self):
        return "zones"


class GCollapsible(QVBoxLayout):
    """Custom widget that gives a collapsable (dropdown style) window that
    contains other QWidgets.
    """
    addWidget = property(doc='(!) Disallowed inherited')
    addLayout = property(doc='(!) Disallowed inherited')

    class _GArrow(QFrame):

        def __init__(self, parent=None, collapsed=False):
            QFrame.__init__(self, parent=parent)
            self.setMaximumSize(24, 24)
            self.__hori = (QPointF(7, 8), QPointF(17, 8), QPointF(12, 13))
            self.__vert = (QPointF(8, 7), QPointF(13, 12), QPointF(8, 17))
            self._arrow = None
            self.set_arrow(int(collapsed))

        def set_arrow(self, arrow_dir: bool):
            """_summary_

            Args:
                arrow_dir (bool): _description_
            """
            self._arrow = self.__vert if arrow_dir else self.__hori
            self.update()

        def paintEvent(self, _):    # pylint: disable=C0103
            """_summary_

            Args:
                _ (_type_): _description_
            """
            painter = QPainter()
            painter.begin(self)
            painter.setBrush(QColor(192, 192, 192))
            painter.setPen(QColor(64, 64, 64))
            painter.drawPolygon(*self._arrow)
            painter.end()


    class _GTitle(QFrame):

        def __init__(self, parent, toogle_func, title=""):
            QFrame.__init__(self, parent=parent)
            self.setFrameShadow(QFrame.Sunken)
            self._arrow = GCollapsible._GArrow(collapsed=True)
            self._arrow.setStyleSheet("border:0px")
            _title = QLabel(title)
            _title.setFixedHeight(24)
            _title.move(QPoint(24, 0))
            _title.setStyleSheet("border:0px")
            _hlayout = QHBoxLayout(self)
            _hlayout.setContentsMargins(0, 0, 0, 0)
            _hlayout.setSpacing(0)
            _hlayout.addWidget(self._arrow)
            _hlayout.addWidget(_title)
            self.__toogle_func = toogle_func

        def mousePressEvent(self, event):  # pylint: disable=C0103
            self.__toogle_func()
            return super().mousePressEvent(event)


    def __init__(self, parent=None, title="", content=None):
        QVBoxLayout.__init__(self)
        self._is_collasped = True
        self._title_frame = GCollapsible._GTitle(parent, self._toggle, title)
        super().addWidget(self._title_frame)
        self._content = QFrame(parent) if content is None else content
        self._content.setStyleSheet(".QFrame{border:1px solid rgb(41, 41, 41)"
                                    "; background-color: #f0f6ff}")
        self._content.setVisible(not self._is_collasped)
        super().addWidget(self._content)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(0)

    def _toggle(self):
        """_summary_
        """
        self._content.setVisible(self._is_collasped)
        self._is_collasped = not self._is_collasped
        self._title_frame._arrow.set_arrow(int(self._is_collasped))

    def setLayout(self, layout) -> None:  # pylint: disable=C0103
        """_summary_

        Args:
            layout (_type_): _description_
        """
        self._content.setLayout(layout)
