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

Flatex based on https://github.com/nennigb/amc2moodle.
Copyright, 2016  Benoit Nennig (benoit.nennig@supmeca.fr)
Distributed under the terms of the GNU General Public License
See http://www.gnu.org/licenses/gpl.txt for details.
"""
import re
import os
import logging

from ..enums import Numbering
from ..utils import FText
from ..answer import Answer
from ..question import QEssay, QMultichoice
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
        "title": ("name", str),
        "generalfeedback": ("feedback", FText),
        "grade": ("default_grade", float),
        "penalty": ("penalty", float),
        "idnumber": ("dbid", int),
        "responseformat": ("rsp_format", str),
        "responserequired": ("rsp_required", bool),
        "responsefieldlines": ("lines", int),
        "attachments": ("attachments", int),
        "attachmentsrequired": ("atts_required", bool),
        "responsetemplate": ("template", str),
        "single": ("single", bool),
        "shuffleanswers": ("shuffle", bool),
        "answernumbering": ("numbering", Numbering),
        # "correctfeedback": ("if_correct", FText),
        # "partiallycorrectfeedback": ("if_incomplete", FText),
        # "incorrectfeedback": ("if_incorrect", FText),
        "shownumcorrect": ("show_ans", bool),
    }

    def __init__(self, cls, cat, buffer) -> None:
        self.cls = cls
        self.cat = cat
        self.buf = buffer
        self._document()

    def _question(self, qtype):
        params = {"question": FText()}
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
            elif line == "\\end{document}":
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


class Flatex:
    """ Merge all included tex files in one.
    """

    TEX_INPUT = re.compile(r"(^[^\%]*\\input{[^}]*})|(^[^\%]*\\include{[^}]*})")

    def __init__(self, base_file: str, noline=False, magic_flag=True):
        """Create a new Flatex instance.
        Args:
            base_file (_type_): Input tex filename.
            noline (bool, optional): Add blank line after include/input Defaults to False.
            magic_flag (bool, optional): Remove or not the magic comment tag. Defaults to True.
        """
        # store
        self.base_file = base_file
        self.noline = noline
        self.magic_flag = magic_flag

        # define the tag used to prefix the 'magic comments'
        self.magictag = '%amc2moodle '

        # define state variable for log
        self._magic_comments_number = 0
        self._included_files_list = [base_file]

    @staticmethod
    def _get_input(line):
        """ Gets the file name from a line containing an input statement.
        """
        tex_input_filename_re = r"""{[^}]*"""
        m = re.search(tex_input_filename_re, line)
        return m.group()[1:]

    @staticmethod
    def _combine_path(base_path, relative_ref):
        """ Return the absolute filename path of the included tex file.
        """
        # check for absolute path
        if not os.path.isabs(relative_ref):
            abs_path = os.path.join(base_path, relative_ref)
        else:
            abs_path = relative_ref
        # Handle if .tex is supplied directly with file name or not
        if not relative_ref.endswith('.tex'):
            abs_path += '.tex'
        return abs_path

    def _expand_file(self, base_file, current_path):
        """ Recursively-defined function that takes as input a file and returns
        it with all the inputs replaced with the contents of the referenced file.
        """
        output_lines = []
        with open(base_file, "r") as f:
            for line in f:
                # test if it contains an '\include' or '\input'
                if self.TEX_INPUT.search(line):
                    new_base_file = self._combine_path(current_path,
                                                      self._get_input(line))
                    output_lines += self._expand_file(new_base_file, current_path)
                    self._included_files_list.append(new_base_file)
                    if self.noline:
                        pass
                    else:
                        # add a new line after each inclided file
                        output_lines.append('\n')
                # test if magic coment
                elif self.magic_flag and line.lstrip().startswith(self.magictag):
                    output_lines += line.replace(self.magictag, '')
                    # count it
                    self._magic_comments_number += 1
                # else append line
                else:
                    output_lines.append(line)
        return output_lines

    def expand(self) -> str:
        """ This "flattens" a LaTeX document by replacing all \\input{X} lines
        with the text actually contained in X.
        """
        current_path = os.path.split(self.base_file)[0]
        data = ''.join(self._expand_file(self.base_file, current_path))
        _LOG.info(f"{self._magic_comments_number} magic comments found, in "
                  f"{len(self._included_files_list)} tex files.")
        return data


def read_latex(cls, file_name) -> "Category":
    """
    """
    category = cls()
    category.data["latex"] = []
    tex_class = None
    with open(file_name, 'r', encoding='utf-8') as ifile:
        for line in ifile:
            if tex_class is None:
                match = _TEX_CMD.match(line.strip())
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
    raise NotImplementedError("LaTex not implemented")
