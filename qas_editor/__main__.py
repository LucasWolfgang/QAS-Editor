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

import sys
import os
import logging
from PyQt5.QtWidgets import QApplication  # pylint: disable=E0611,E0401
from .gui.main import Editor


def main():
    """Main method. Called when the package runs using -m from CLI.
    """
    log = logging.getLogger("qas_editor")
    log.setLevel(logging.DEBUG)
    var = "USERPROFILE" if os.name == "NT" else "HOME"
    handler = logging.FileHandler(filename=f"{os.environ[var]}/qas_editor.log",
                                  mode="w", encoding="utf-8")
    formatter = logging.Formatter("%(levelname)s [%(asctime)s]: %(message)s")
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)
    log.addHandler(handler)
    app = QApplication(sys.argv)
    Editor()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
