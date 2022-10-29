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
from __future__ import annotations
import re
import os
import logging

from ..enums import Numbering
from ..utils import FText
from ..answer import Answer
from ..question import QEssay, QMultichoice
from typing import TYPE_CHECKING, Type, List, Tuple
if TYPE_CHECKING:
    from ..category import Category
    from io import StringIO

_LOG = logging.getLogger(__name__)
_TEX_BASE_CMD = re.compile(r"\\(\w+).*(?:\{(.+)\})")


class _Cmd():

    def __init__(self, name: str):
        self.name = name
        self.env = name in ("begin", "end")
        self.text = None
        self.args = []
        self.opts = []
        self.subitems = []

    def __str__(self) -> str:
        return self.name + "{" + "}{".join(self.args) + "}[" + "][".join(self.opts) + "]"


_TEMPLATES = {}
class LaTex():

    _NAME = ""
    _CMDS = {}
    _QTYPE = {}
    _HEADER = ""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls._NAME is not None:
            _TEMPLATES[cls._NAME] = cls

    def __init__(self, cat: Category, buffer: StringIO, path: str):
        self.cat = cat
        self.buf = buffer
        self.path = path
        self.idx = 0
        self.line = "\n"

    def read(self):
        while self.line:
            for cmd in self._document():
                if isinstance(cmd, _Cmd) and cmd.name == "end" and cmd.args[0] == "document":
                    return

    def _document(self):
        data = self._parse()
        for cmd in data:
            if isinstance(cmd, _Cmd) and cmd.name == "include":
                path = cmd.args[0]
                if os.path.relpath(path):
                    path = self.path.rsplit("/", 1)[0] + "/" + path
                with open(path) as ifile:
                    self.__class__(self.cat, ifile, path)
        return data

    def _parse_cmd(self, open_groups: list):
        self.idx += 1
        start = self.idx
        while self.line[self.idx].isalpha():
            self.idx += 1
        cmd = _Cmd(self.line[start: self.idx])
        while self.idx < len(self.line):
            if self.line[self.idx] in ("{", "["):
                open_groups.append(self.idx)
            elif self.line[self.idx] == "}":
                if self.line[open_groups[-1]] != "{":
                    raise ValueError(f"Incorrect pattern: {self.line}")
                start = open_groups.pop() + 1
                cmd.args.append(self.line[start:self.idx])
            elif self.line[self.idx] == "]":
                if self.line[open_groups[-1]] != "[":
                    raise ValueError(f"Incorrect pattern: {self.line}")
                start = open_groups.pop() + 1
                cmd.opts.append(self.line[start:self.idx])
            elif self.line[self.idx] == "\\":
                self._parse_cmd(open_groups)
            elif len(open_groups) == 0 and self.line[self.idx]:
                break
            if self.idx == len(self.line)-1 and len(open_groups) != 0:
                self.line += next(self.buf).strip()
            self.idx += 1
        return cmd

    def _parse(self) -> list:
        self.idx = start = 0
        data = []
        self.line = next(self.buf)
        while self.idx < len(self.line):
            if self.line[self.idx] == "\\" and self.line[self.idx+1].isalpha():
                if self.idx > start + 1:
                    data.append(self.line[start: self.idx])
                data.append(self._parse_cmd([]))
                start = self.idx + 1
            self.idx += 1
        data.append(self.line[start: self.idx])
        return data


class _ClassExam(LaTex):
    """See: https://ctan.org/pkg/exam
    """
    _NAME = "exam"


class _PkgAMQ(LaTex):
    """See: https://www.auto-multiple-choice.net/
    """
    _NAME = "automultiplechoice"

    _HEADER = """\\documentclass[a4paper]{article}
        % -------------------------::== package ==::---------------------------
        \\usepackage[utf8]{inputenc}
        \\usepackage[T1]{fontenc}
        \\usepackage{alltt}
        \\usepackage{multicol}
        \\usepackage{amsmath,amssymb}
        \\usepackage{color}
        \\usepackage{graphicx}
        % Mandatory for conversion
        \\usepackage[francais,bloc,completemulti]{automultiplechoice}
        \\usepackage{tikz}
        \\usepackage{hyperref}
        \\usepackage{ulem} % strike text

        % -----------------------::== newcommand ==::--------------------------
        \\newcommand{\\feedback}[1]{}
        \\begin{document}
    """


class _PkgMcExam(LaTex):
    """See: https://ctan.org/pkg/mcexam
    """
    _NAME = "mcexam"


class _PkgAlterQCM(LaTex):
    """See: https://www.ctan.org/pkg/alterqcm
    """
    _NAME = "alterqcm"


class _PkgLatexToMoodle(LaTex):
    """Parsers the package created by Guillame for the latextomoodle repo.
    Since document classes have priority, it will only be used if the class of
    the document is not assigned to any parser. This is a LAZY parser! It is
    meant to be simple and fast, and not to consider all possibilities.
    See: https://github.com/Guillaume-Garrigos/moodlexport
    """
    _NAME = "latextomoodle"

    _QTYPE = {
        "multichoice": QMultichoice,
        "essay": QEssay
    }

    _CMDS = {
        "title": ("name", str),
        "generalfeedback": ("feedback", "_ftext"),
        "grade": ("default_grade", float),
        "penalty": ("max_tries", lambda x: int(1/float(x)) if float(x) != 0 else -1),
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
        "shownumcorrect": ("show_ans", bool),
    }

    def _ftext(string: str):
        return FText(string)

    def _question(self, qtype: str):
        params = {"question": FText()}
        options = []
        while self.line:
            data = self._parse()
            if data and isinstance(data[0], _Cmd):
                if data[0].name == "end" and data[0].args[0] == "question":
                    if options:
                        params["options"] = options
                    break
                else:
                    value = data[0].args[0]
                    if data[0].name == "answer":
                        options.append(Answer(float(data[0].opts[0]), value))
                    elif data[0].name in self._CMDS:
                        key, cast = self._CMDS[data[0].name]
                        if isinstance(cast, str):
                            params[key] = getattr(self, cast)(value)
                        else:
                            params[key] = cast(value)
            elif self.line:
                params["question"].text.append(self.line)
        params["question"].text = params["question"].get().strip() 
        self.cat.add_question(self._QTYPE[qtype](**params))

    def _category(self, name):
        tmp = self.cat
        try:
            self.cat = self.cat.__class__(name)
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
        data = super()._document()
        if data and isinstance(data[0], _Cmd) and data[0].env:
            if "category" in data[0].args:
                self._category(data[0].opts[0])
            elif "question" in data[0].args:
                self._question(data[0].opts[0])
        elif self.line:
            raise ValueError("Couldnt map line:\n\t%s", self.line)
        return data


def read_latex(cls: Type[Category], file_name: str) -> "Category":
    """
    """
    category = cls()
    category.metadata["latex"] = []
    tex_class = None
    with open(file_name, 'r', encoding='utf-8') as ifile:
        for line in ifile:
            if tex_class is None:
                match = _TEX_BASE_CMD.match(line.strip())
                if match:
                    cmd, value = match.groups()
                    category.metadata["latex"].append((cmd, value))
                    if cmd in ("usepackage", "documentclass"):
                        if value in _TEMPLATES:
                            tex_class = _TEMPLATES[value]
            elif line == "\\begin{document}\n":
                tex = tex_class(category, ifile, file_name)
                tex.read()
                break
    return category


def write_latex(self, file_path: str, ftype: type) -> None:
    """_summary_
    Args:
        file_path (str): _description_
    Raises:
        NotImplementedError: _description_
    """
    raise NotImplementedError("LaTex not implemented")
