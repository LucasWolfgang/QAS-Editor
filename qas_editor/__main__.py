import sys
from PyQt5.QtWidgets import QApplication
from .gui.main import Editor
from .utils import conf_logger

def main():
    conf_logger()
    app = QApplication(sys.argv)
    app.setStyle('Breeze')
    w = Editor()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()