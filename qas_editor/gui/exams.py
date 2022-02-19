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
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..questions import QCrossWord
    from typing import Dict

from .forms import UnitHandling
from PyQt5.QtWidgets import QWidget, QSizePolicy
from PyQt5 import QtGui
from PyQt5 import QtCore

class ECrossword(QWidget):
    """
    Crossword Puzzle Qt widget. It is used to interact with the

    Signals:
    changed()                   Either the puzzle solution or size was changed.
    start()                     A new game was started.
    stop()                      Game was stopped.
    editClues(int, int)         The "edit clues" key has been pressed on given location.
    quitKeyPressed()            The "quit key" has been pressed.
    letterTyped(int, int, const QString&)   A letter has been typed.
    """

    def __init__(self, puzzle: QCrossWord, **kwargs) -> None:
        super().__init__(**kwargs)
        self._editMode = False
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._puzzle = puzzle
        self._font = QtGui.QFont("monospace")
        self._fontSmall = QtGui.QFont("monospace")
        self._fontSmall.setWeight(QtGui.QFont.Bold)
        self._fontBold = QtGui.QFont("monospace")
        self._fontBold.setWeight(QtGui.QFont.Bold)
        self.answer: Dict[str, Dict[str]] = {}
        for word in self._puzzle.words:
            pass


    def char(self, x, y):
        """
        Return a character from the solution grid.
        """
        return self._puzzle[x, y]

    def setChar(self, x, y, c):
        """
        Set a character in the solution grid.
        Emits changed() signal.
        """
        if not self.editMode():
            raise ValueError("puzzle is not in edit mode")
        self._puzzle[x, y] = c
        self.emit(QtCore.SIGNAL("changed()"))

    def answerChar(self, x, y):
        """
        Return a character from the answer grid.
        """
        return self._puzzle.getAnswerChar(x, y)

    def setAnswerChar(self, x, y, c):
        """
        Set a character in the answer grid.
        """
        if not self.active():
            raise ValueError("puzzle is inactive")
        self._puzzle.setAnswerChar(x, y, c)

    def startingPosition(self, x, y, direction):
        """
        Returns the starting position of a word in the solution grid.
        """
        return self._puzzle.getStartingPosition(x, y, direction)

    def par(self):
        """
        Return the par time for this puzzle.
        """
        return self._puzzle.par

    def setPar(self, value):
        """
        Set new par, if in edit mode. Emits changed() signal.
        """
        if not self.editMode():
            raise ValueError("puzzle is not in edit mode")
        self._puzzle.par = value
        self.emit(QtCore.SIGNAL("changed()"))

    def title(self):
        """
        Return the title of the puzzle.
        """
        return self._puzzle.title

    def setTitle(self, value):
        """
        Set a title for the puzzle, if in edit mode. Emits changed() signal.
        """
        if not self.editMode():
            raise ValueError("puzzle is not in edit mode")
        self._puzzle.title = value
        self.emit(QtCore.SIGNAL("changed()"))

    def completed(self):
        c = self._puzzle.getCharacterCount()
        a = self._puzzle.getAnswerCharacterCount()
        if c:
            return float(a) / float(c) * 100.0
        return 0.0
        
    #
    # Methods
    #

    def getStartPosition(self, x, y, direction):
        return self._puzzle.getStartPosition(x, y, direction)

    def clear(self):
        """
        Clear the answers.
        """
        self._puzzle.clear()
        self.emit(QtCore.SIGNAL("changed()"))
        self.update()
                
    def moveCursor(self, dx, dy):
        """
        Move the cursor. While NOT in edit mode it will skip black squares (None's).
        """
        x, y = self.cursor()
        if self.editMode() or not self.restrictedCursor():
            x += dx
            y += dy
            if x < 0:
                x = self.puzzleWidth() - 1
            elif x >= self.puzzleWidth():
                x = 0
            if y < 0:
                y = self.puzzleHeight() - 1
            elif y >= self.puzzleHeight():
                y = 0
            self.setCursor(x, y)
        else:
            safe = self.puzzleWidth() + self.puzzleHeight()
            while safe > 0:
                x += dx
                y += dy
                if x > self.puzzleWidth() - 1:
                    x = 0
                elif x < 0:
                    x = self.puzzleWidth() - 1
                if y > self.puzzleHeight() - 1:
                    y = 0
                elif y < 0:
                    y = self.puzzleHeight() - 1
                if not self.char(x, y) is None:
                    break
                safe -= 1
            self.setCursor(x, y)

    def start(self):
        """
        Start the game. Does nothing if already active.
        """
        self.setActive(True)

    def stop(self):
        """
        Stop the game. Does nothing if already inactive.
        """
        self.setActive(False)

    def restart(self):
        """
        Restart the game.
        """
        self.setActive(True, True)

    def from_obj(self, obj: UnitHandling) -> None:
        pass

    def to_obj(self) -> None:
        pass

    def drawableRect(self):
        """
        Return rect for drawing in this widget.
        """
        margin = 8
        return QtCore.QRect(margin, margin, self.width() - margin * 2, self.height() - margin * 2)
                
    def pixelGeometry(self):
        """
        Returns the width and height of each puzzle cell (in pixels).
        """
        startingRect = self.drawableRect()
        pixelw = int(startingRect.width() / self.puzzleWidth())
        pixelh = int(startingRect.height() / self.puzzleHeight())
        return pixelw, pixelh

    def puzzleDrawingRect(self):
        """
        Returns the rect in which the puzzle is actualy drawn.
        """
        startingRect = self.drawableRect()
        pixelw = int(startingRect.width() / self.puzzleWidth())
        pixelh = int(startingRect.height() / self.puzzleHeight())
        drawRect = QtCore.QRect(0, 0, pixelw * self.puzzleWidth(), pixelh * self.puzzleHeight())
        drawRect.moveTo(startingRect.x() + int((startingRect.width() - drawRect.width()) * 0.5),
                        startingRect.y() + int((startingRect.height() - drawRect.height()) * 0.5))
        return drawRect

    #
    # Events
    #
    def resizeFonts(self, w, h):
        pixelw = int(w / self._puzzle.x_grid)
        pixelh = int(h / self._puzzle.y_grid)
        if pixelw < pixelh:
            self._font.setPixelSize(w * 0.75)
            self._fontSmall.setPixelSize(w * 0.4)
        else:
            self._font.setPixelSize(h * 0.75)
            self._fontSmall.setPixelSize(h * 0.4)
        self.update()

    def resize(self, w, h):
        self.resizeFonts(w, h)
        QtGui.QWidget.resize(self, w, h)
    
    def resizeEvent(self, event):
        w, h = event.size().width(), event.size().height()
        self.resizeFonts(w, h)
        if self.square():
            if w < h:
                self.resize(w, w)
            else:
                self.resize(h, h)
        else:
            self.updateGeometry()
        event.accept()

    def paintEvent(self, event):
        painter = QtGui.QPainter()        
        painter.begin(self)
        # Calculating rects
        drawRect = self.puzzleDrawingRect()
        pixelw, pixelh = self.pixelGeometry()
        # Calculate cursor color
        if self.editMode():
            cursorColor = QtGui.QColor(QtCore.Qt.red)
        elif self.active():
            cursorColor =  QtGui.QColor(self.palette().color(QtGui.QPalette.Highlight))
        else:
            cursorColor =  QtGui.QColor(self.palette().color(QtGui.QPalette.Dark))
        if self.hasFocus():
            cursorColor.setAlphaF(1.0)
        else:
            cursorColor.setAlphaF(0.33)
        # Draw focus border using cursor color
        painter.fillRect(self.drawableRect(), cursorColor)
        # Draw background using Base or AlternateBase color
        painter.fillRect(drawRect, self.palette().color(self.active() and QtGui.QPalette.Base or QtGui.QPalette.AlternateBase))
        # Draw grid using AlternateBase color
        painter.setPen(self.palette().color(QtGui.QPalette.Mid))
        for y in (i * pixelh for i in range(1, self.puzzleHeight())):
            painter.drawLine(drawRect.x(),
                             drawRect.y() + y,
                             drawRect.x() + drawRect.width(),
                             drawRect.y() + y)
        for x in (i * pixelw for i in range(1, self.puzzleWidth())):
            painter.drawLine(drawRect.x() + x,
                             drawRect.y(),
                             drawRect.x() + x,
                             drawRect.y() + drawRect.height())
        # Draw dark squares using Text color
        color = self.palette().color(QtGui.QPalette.Normal, QtGui.QPalette.Text)
        r = QtCore.QRect(drawRect.x(), drawRect.y(), pixelw, pixelh)
        r2 = r.adjusted(0, 0, -1, -1)
        for y in range(self._puzzle.height):
            for x in range(self._puzzle.width):
                if not self.char(x, y):
                    if self.editMode():
                        r2.moveTo(drawRect.x() + x * pixelw, drawRect.y() + y * pixelh)
                        painter.fillRect(r2, color)
                    else:
                        r.moveTo(drawRect.x() + x * pixelw, drawRect.y() + y * pixelh)
                        painter.fillRect(r, color)
        # Draw cursor using cursor color
        if (self._puzzle.getWords()) or self.editMode():
            r = QtCore.QRect(drawRect.x() + self._cursor.x * pixelw + 1,
                             drawRect.y() + self._cursor.y * pixelh + 1,
                             pixelw - 2,
                             pixelh - 2)
            painter.fillRect(r, cursorColor)
        # Draw answered letters using Text color
        positions = {}
        r = QtCore.QRect(drawRect.x(), drawRect.y(), pixelw, pixelh)
        if self.editMode():
            getter = self._puzzle.getChar
        else:
            getter = self._puzzle.getAnswerChar
        painter.setFont(self._font)
        for y in range(self._puzzle.height):
            for x in range(self._puzzle.width):
                letter = getter(x, y)
                if letter:
                    if (x, y) == self.cursor():
                        painter.setPen(self.palette().color(QtGui.QPalette.HighlightedText))
                    else:
                        painter.setPen(self.palette().color(QtGui.QPalette.Text))
                    r.moveTo(drawRect.x() + x * pixelw, drawRect.y() + y * pixelh)
                    painter.drawText(r, QtCore.Qt.AlignCenter, letter.upper())
        # Draw clue numbers
        painter.setFont(self._fontSmall)
        painter.setPen(self.palette().color(QtGui.QPalette.Normal, QtGui.QPalette.Text))
        offset = self._fontSmall.pixelSize() * 0.1
        for (x, y, direction), (id_, word, clue) in self._puzzle.getWords().items():
            if (x, y) == self.cursor():
                painter.setPen(self.palette().color(QtGui.QPalette.HighlightedText))
            else:
                painter.setPen(self.palette().color(QtGui.QPalette.Text))
            r.moveTo(drawRect.x() + x * pixelw + offset, drawRect.y() + y * pixelh + offset)
            painter.drawText(r, QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop, "%d"%id_)
        painter.end()
        event.accept()

    def keyPressEvent(self, event):
        key = event.key()
        letter = event.text().upper()
        if letter:
            letter = letter[0]
        if key in (QtCore.Qt.Key_Left, QtCore.Qt.Key_Right, QtCore.Qt.Key_Up, QtCore.Qt.Key_Down):
            if key == QtCore.Qt.Key_Left:
                self.moveCursor(-1, 0)
            elif key == QtCore.Qt.Key_Right:
                self.moveCursor(1, 0)
            elif key == QtCore.Qt.Key_Up:
                self.moveCursor(0, -1)
            elif key == QtCore.Qt.Key_Down:
                self.moveCursor(0, 1)
            event.accept()
            self.update()
        elif key == QtCore.Qt.Key_Return:
            if self.editMode():
                self.emit(QtCore.SIGNAL("editClues(int, int)"), self._cursor.x, self._cursor.y)
            else:
                self.emit(QtCore.SIGNAL("quitKeyPressed()"))
        elif self.active() or self.editMode():
            if key == QtCore.Qt.Key_Backspace:
                if event.modifiers() & QtCore.Qt.ShiftModifier:
                    self.moveCursor(0, -1)
                else:
                    self.moveCursor(-1, 0)
                if self.editMode():
                    self.setChar(self._cursor.x, self._cursor.y, None)
                else:
                    self.setAnswerChar(self._cursor.x, self._cursor.y, None)
                self.emit(QtCore.SIGNAL("letterTyped(int, int, const QString&)"), self._cursor.x, self._cursor.y, QtCore.QString())
                self.update()
            elif key == QtCore.Qt.Key_Delete:
                if self.editMode():
                    self.setChar(self._cursor.x, self._cursor.y, None)
                else:
                    self.setAnswerChar(self._cursor.x, self._cursor.y, None)
                self.emit(QtCore.SIGNAL("letterTyped(int, int, const QString&)"), self._cursor.x, self._cursor.y, QtCore.QString())
                self.update()
            elif letter:
                if self.editMode():
                    if letter != " ":
                        letter = letter.strip()
                    self.setChar(self._cursor.x, self._cursor.y, letter or None)
                else:
                    self.setAnswerChar(self._cursor.x, self._cursor.y, letter.strip() or None)
                if event.modifiers() & QtCore.Qt.ShiftModifier:
                    self.moveCursor(0, 1)
                else:
                    self.moveCursor(1, 0)
                self.emit(QtCore.SIGNAL("letterTyped(int, int, const QString&)"), self._cursor.x, self._cursor.y,
                          QtCore.QString(letter))
                self.update()
        else:
            event.ignore()

    def mousePressEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            pixelw, pixelh = self.pixelGeometry()
            drawRect = self.puzzleDrawingRect()
            x = (event.x() - drawRect.x()) / pixelw
            y = (event.y() - drawRect.x()) / pixelh
            if self.editMode() or self.char(x, y):
                self.setCursor(x, y)

    def mouseDoubleClickEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            pixelw, pixelh = self.pixelGeometry()
            drawRect = self.puzzleDrawingRect()
            x = (event.x() - drawRect.x()) / pixelw
            y = (event.y() - drawRect.x()) / pixelh
            if self.editMode() and self.char(x, y):
                self.emit(QtCore.SIGNAL("editClues(int, int)"), x, y)

    def timerEvent(self, event):
        self.emit(QtCore.SIGNAL("timeUpdated(int, int)"), self.time(), self._puzzle.par)
        