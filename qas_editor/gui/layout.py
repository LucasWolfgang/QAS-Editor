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
from typing import TYPE_CHECKING
from PyQt5.QtCore import QPoint, QPointF
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QPushButton, QLabel,\
                            QFrame, QApplication
from PyQt5.QtGui import QColor, QPainter
from ..answer import Answer, DragImage, DragItem, DragGroup, EmbeddedItem, \
                     ACalculated, ANumerical
from ..utils import Hint
from .widget import GCalculated, GCloze, GDrag, GAnswer, GHint, GCheckBox, GField
if TYPE_CHECKING:
    from ..utils import TList


_TYPE_MAP = {
    ACalculated: GCalculated,
    EmbeddedItem: GCloze,
    DragGroup: GDrag,
    DragItem: GDrag,
    DragImage: GDrag,
    Answer: GAnswer,
    ANumerical: GAnswer,
    Hint: GHint
}


class AutoUpdateVBox(QVBoxLayout):
    """A base class for all the other classes defined in this file.
    TODO change it to a QWidget and add a DragAndDrop logic. This will also
    allow removing the selected option, which would replace the "pop the last"
    logic currently being used.
    """

    def __init__(self, parent, toolbar, otype):
        super().__init__()
        self.parent = parent
        self._toolbar = toolbar
        self.__obj: "TList" = None
        self.__type = otype

    def add(self, child=None):
        """_summary_
        Returns:
            _type_: _description_
        """
        if self.__obj is None:
            return
        cls = _TYPE_MAP[self.__obj.datatype]
        item = cls(self._toolbar, self.__obj, child)
        super().addWidget(item)
        return item

    def from_obj(self, obj):
        """_summary_
        Args:
            obj (MultipleTries): _description_
        """
        _obj: "TList" = getattr(obj, self.__type)
        new_size = len(_obj)
        if self.count() != 0:
            to_rem = 0
            if _TYPE_MAP[_obj.datatype] != _TYPE_MAP[self.__obj.datatype]:
                to_rem = self.count()   # Should only happen in flexible lists
            elif self.count() > new_size:
                to_rem = self.count() - new_size
            for _ in range(to_rem):
                item = self.takeAt(0)
                item.widget().deleteLater()
                del item
            for idx in range(self.count()):
                self.itemAt(idx).widget().from_obj(self._obj[idx])
        self.__obj = _obj
        if self.count() < new_size:
            for cloze_item in _obj[self.count():]:
                self.add(cloze_item)

    def get_attr(self):
        """Get attribute.
        """
        return self.__type

    def pop(self):
        """_summary_
        """
        if not self.count():
            return
        self.itemAt(self.count()-1).widget().deleteLater()


class GOptions(AutoUpdateVBox):
    """GUI for GOptions class.
    """

    def __init__(self, parent, toolbar, editor):
        super().__init__(parent, toolbar, "options")
        self.visible = True
        if editor is not None:
            self.add_marker_to_text = editor.add_marker
            self.pop_marker_from_text = editor.pop_marker
        self.setSpacing(5)

    def add(self, child=None):
        item = super().add(child)
        if child is None:
            self.add_marker_to_text()
        return item

    def pop(self):
        """_summary_
        """
        widget = QApplication.focusWidget().parent()
        for idx in range(self.count()):
            if self.itemAt(idx).widget() == widget:
                self.removeWidget(widget)
                widget.deleteLater()
                self.pop_marker_from_text(idx+1)
                break


class GHintsList(AutoUpdateVBox):
    """GUI class for the MultipleTries wrapper
    """

    def __init__(self, parent, toolbar):
        super().__init__(parent, toolbar, "hints")


class GUnits(AutoUpdateVBox):
    """ Wdiget for the Unit data used by Questions.
    """

    def __init__(self, parent, toolbar):
        super().__init__(parent, toolbar, "units")


class GZones(AutoUpdateVBox):
    """ Widget to list Zones used by the question.
    """

    def __init__(self, parent, toolbar):
        super().__init__(parent, toolbar, "zones")
        _row = QHBoxLayout()
        self._background = QPushButton("Background")
        _row.addLayout(self._background)
        self._highlight = GCheckBox("highlight", "Highlight dropzones with inc"
                                    "orrect correct markers placed", parent)


class GCollapsible(QVBoxLayout):
    """Custom QLayout that gives a collapsable (dropdown style) window that
    contains other QWidgets.
    """
    addWidget = property(doc='(!) Disallowed inherited')
    addLayout = property(doc='(!) Disallowed inherited')

    class _GArrow(QFrame):

        def __init__(self, parent, collapsed):
            QFrame.__init__(self, parent)
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
            """Overwritten method. Paint the arrow icon.
            """
            painter = QPainter()
            painter.begin(self)
            painter.setBrush(QColor(192, 192, 192))
            painter.setPen(QColor(64, 64, 64))
            painter.drawPolygon(*self._arrow)
            painter.end()

    class _GTitle(QFrame):

        def __init__(self, parent, toogle_func, title=""):
            QFrame.__init__(self, parent)
            self.arrow = GCollapsible._GArrow(parent, True)
            _title = QLabel(title)
            _title.move(QPoint(24, 0))
            _hlayout = QHBoxLayout(self)
            _hlayout.setContentsMargins(0, 0, 0, 0)
            _hlayout.setSpacing(0)
            _hlayout.addWidget(self.arrow)
            _hlayout.addWidget(_title)
            self.setFixedHeight(24)
            self.__toogle_func = toogle_func

        def mousePressEvent(self, event):  # pylint: disable=C0103
            """Overwritten method. Toogle the arrow icon and toggle items
            visibility when clicked.
            """
            self.__toogle_func()
            return super().mousePressEvent(event)

    def __init__(self, parent, title):
        QVBoxLayout.__init__(self)
        self._is_collasped = True
        self._title_frame = GCollapsible._GTitle(parent, self.toggle, title)
        super().addWidget(self._title_frame)
        self._content = QFrame(parent)
        self._content.setStyleSheet(".QFrame{border:1px solid rgb(41, 41, 41)"
                                    "; background-color: #f0f6ff}")
        self._content.setVisible(not self._is_collasped)
        super().addWidget(self._content)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(0)

    def toggle(self):
        """_summary_
        """
        self._content.setVisible(self._is_collasped)
        self._is_collasped = not self._is_collasped
        self._title_frame.arrow.set_arrow(int(self._is_collasped))

    def setLayout(self, layout) -> None:  # pylint: disable=C0103
        """_summary_

        Args:
            layout (_type_): _description_
        """
        self._content.setLayout(layout)
