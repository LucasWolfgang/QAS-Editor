import sys
from qas_editor import GUI
from PyQt5.QtWidgets import QApplication

def main():
    app = QApplication(sys.argv)
    app.setStyle('Breeze')
    w = GUI()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

