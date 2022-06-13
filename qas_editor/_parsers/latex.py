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
import re
import logging
from ..questions import QTYPE
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
    the document is not assigned to any parser. This is a LAZY parser! It
    expects well cats/questions without any fancy stuff (the rest of the doc
    can be formatted however you want it to be).
    See: https://github.com/Guillaume-Garrigos/moodlexport
    """

    _CMDS = {
        "\\title" : "description",
        "\\generalfeedback" : "feedback",
        "\\grade" : "grade",
        "\\penalty" : "penalty",
        "\\hidden" : "",
        "\\idnumber" : "dbid",
        "\\responseformat" : "rsp_format",
        "\\responserequired" : "rsp_required",
        "\\responsefieldlines" : "lines",
        "\\attachments" : "attachments",
        "\\attachmentsrequired" : "atts_required",
        "\\responsetemplate" : "template",
        "\\single" : "single ",
        "\\shuffleanswers" : "shuffle",
        "\\answernumbering" : "numbering",
        "\\correctfeedback" : "if_correct",
        "\\partiallycorrectfeedback" : "if_incomplete",
        "\\incorrectfeedback" : "if_incorrect",
        "\\shownumcorrect" : "show_num",
        "\\answer" : "_add_answer"
    }

    def __init__(self, cls, cat, buffer) -> None:
        self.cls = cls
        self.cat = cat
        self.qst = None
        self.buf = buffer
        self._document()

    def _question(self, qtype):
        self.qst = QTYPE[qtype]()
        for line in self.buf:
            tmp = line.strip()
            if tmp == "\\end{question}":
                break
            match = re.match(_TEX_CMD, tmp)
            if match and match[0] in self._CMDS:
                cmd, opt, value = match
                attrs = self._CMDS.get(cmd, [])
                if len(attrs) == 1:
                    setattr(self.qst, attrs[0], value)
                getattr(self, self._CMDS[match.group(0)])(match[3], match[2])
            else:
                self.qst.question.text += tmp if tmp else line
        self.cat.add_question(self.qst)

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
            else:
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
    category.data["packages"] = []
    tex_class = None
    with open(file_name, 'r', encoding='utf-8') as ifile:
        for line in ifile:
            line = line.strip()
            if tex_class is None and (line[:12] == "\\usepackage{" or
                        line[:15] == "\\documentclass{"):
                pkg = line[12:-1]
                category.data["packages"].append(pkg)
                if pkg in _TEMPLATES:
                    tex_class = _TEMPLATES[pkg]
            elif "\\begin{document}" == line:
                tex_class(cls, category, ifile)
    if len(category) == 1 and category.get_size() == 0:
        category = [category[i] for i in category][0]
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