import sys
from PyQt5.QtWidgets import QApplication
from .gui.main import Editor

def main():
    app = QApplication(sys.argv)
    app.setStyle('Breeze')
    w = Editor()
    sys.exit(app.exec_())
main()