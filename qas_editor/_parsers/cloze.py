"""
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
import logging
from typing import TYPE_CHECKING
from ..question import QCloze
if TYPE_CHECKING:
    from ..category import Category


_LOG = logging.getLogger(__name__)


def _from_QCloze(buffer, embedded_name):
    data: str = buffer.read()
    if embedded_name:
        name, text = data.split("\n", 1)
    else:
        name = "Cloze"
        text = data
    text, opts = QCloze.get_items(text.strip())
    return QCloze(name=name, question=text, options=opts)


# -----------------------------------------------------------------------------


def read_cloze(cls, file_path: str, embedded_name=False) -> "Category":
    """Reads a Cloze file.

    Args:
        file_path (str): _description_
        category (str, optional): _description_. Defaults to "$".

    Returns:
        Quiz: _description_
    """
    top_quiz = cls()
    with open(file_path, "r", encoding="utf-8") as ifile:
        top_quiz.add_question(_from_QCloze(ifile, embedded_name))
    _LOG.info(f"Created new Quiz instance from cloze file {file_path}")
    return top_quiz


def write_cloze(cat, file_path: str, embedded_name=False):
    """_summary_

    Args:
        file_path (str): _description_
    """
    def _to_cloze(path, counter=0):
        for question in cat.questions:
            if isinstance(question, QCloze):
                name = f"{path}_{counter}.cloze"
                with open(name, "w", encoding="utf-8") as ofile:
                    ofile.write(f"{question.pure_text(embedded_name)}\n")
                    counter += 1
        for child in cat:
            _to_cloze(cat[child], f"{path}_{child.name}", counter)
    _to_cloze(file_path.rsplit(".", 1)[0])
