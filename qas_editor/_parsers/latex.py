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
import re
import logging

from ..enums import Numbering
from ..utils import FText
from ..answer import Answer
from ..questions import QEssay, QMultichoice
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..category import Category

_LOG = logging.getLogger(__name__)
_TEX_CMD = re.compile(r"\\(\w+)(?:\[(.+)\])?\{(.*)\}$")

class _ClassExam():
    """
    See: https://ctan.org/pkg/exam
    """


class _PkgAMQ():
    """
    See: https://www.auto-multiple-choice.net/
    """


class _PkgMcExam():
    """
    See: https://ctan.org/pkg/mcexam
    """


class _PkgAlterQCM():
    """
    See: https://www.ctan.org/pkg/alterqcm
    """


class _PkgGuillaume():
    """Parsers the package created by Guillame for the latextomoodle repo.
    Since document classes have priority, it will only be used if the class of
    the document is not assigned to any parser. This is a LAZY parser! It is
    meant to be simple and fast, and not to consider all possibilities.
    See: https://github.com/Guillaume-Garrigos/moodlexport
    """

    _QTYPE = {
        "multichoice": QMultichoice,
        "essay": QEssay
    }

    _CMDS = {
        "title" : ("name", str),
        "generalfeedback" : ("feedback", FText),
        "grade" : ("default_grade", float),
        "penalty" : ("penalty", float),
        "idnumber" : ("dbid", int),
        "responseformat" : ("rsp_format", str),
        "responserequired" : ("rsp_required", bool),
        "responsefieldlines" : ("lines", int),
        "attachments" : ("attachments", int),
        "attachmentsrequired" : ("atts_required", bool),
        "responsetemplate" : ("template", str),
        "single" : ("single", bool),
        "shuffleanswers" : ("shuffle", bool),
        "answernumbering" : ("numbering", Numbering),
        "correctfeedback" : ("if_correct", FText),
        "partiallycorrectfeedback" : ("if_incomplete", FText),
        "incorrectfeedback" : ("if_incorrect", FText),
        "shownumcorrect" : ("show_num", bool),
    }

    def __init__(self, cls, cat, buffer) -> None:
        self.cls = cls
        self.cat = cat
        self.buf = buffer
        self._document()

    def _question(self, qtype):
        params = {"question": FText("questiontext")}
        options = []
        for line in self.buf:
            tmp = line.strip()
            if tmp == "\\end{question}":
                if options:
                    params["options"] = options
                break
            match = _TEX_CMD.match(tmp)
            if match:
                cmd, opt, value = match.groups()
                if cmd == "answer":
                    options.append(Answer(float(opt), value))
                elif cmd not in self._CMDS:
                    continue
                else:
                    key, cast = self._CMDS[cmd]
                    params[key] = cast(value)
            else:
                params["question"].text += tmp if tmp else line
        params["question"].text = params["question"].text.strip()
        self.cat.add_question(self._QTYPE[qtype](**params))

    def _category(self, name):
        tmp = self.cat
        try:  
            self.cat = self.cls(name)
            tmp.add_subcat(self.cat)
            for line in self.buf:
                line = line.strip()
                if not line:
                    continue
                if line[:16] == "\\begin{question}":
                    self._question(line[17:-1])
                elif line[:16] == "\\begin{category}":
                    self._category(line[17:-1])
                elif line == "\\end{category}":
                    break
                else:
                    raise ValueError("Couldnt map line %s", line)
        except ValueError:
            _LOG.exception("Failed to parse category %s", name)
        self.cat = tmp
        
    def _document(self):
        for line in self.buf:
            line = line.strip()
            if line[:16] == "\\begin{category}":
                self._category(line[17:-1])
            elif line[:16] == "\\begin{question}":
                self._question(line[17:-1])
            elif line == "\end{document}":
                break
            elif line:
                raise ValueError("Couldnt map line %s", line)


_TEMPLATES = {
    "latextomoodle": _PkgGuillaume,
    "automultiplechoice": _PkgAMQ,
    "mcexam": _PkgMcExam,
    "alterqcm": _PkgAlterQCM, 
    "exam": _ClassExam
}


def read_latex(cls, file_name) -> "Category":
    """
    """
    category = cls()
    category.data["latex"] = []
    tex_class = None
    with open(file_name, 'r', encoding='utf-8') as ifile:
        for line in ifile:
            if tex_class is None:
                match =  _TEX_CMD.match(line.strip())
                if not match:
                    continue
                cmd, opt, value = match.groups()
                if cmd in ("usepackage", "documentclass"):
                    category.data["latex"].append((cmd, opt, value))
                    if value in _TEMPLATES:
                        tex_class = _TEMPLATES[value]
            elif line == "\\begin{document}\n":
                tex_class(cls, category, ifile)
    return category


def write_latex(self, file_path: str) -> None:
    """_summary_

    Args:
        file_path (str): _description_

    Raises:
        NotImplementedError: _description_
    """
    # TODO
    raise NotImplementedError("LaTex not implemented")