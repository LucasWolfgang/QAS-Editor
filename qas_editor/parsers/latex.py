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

import logging
import os
from typing import TYPE_CHECKING, Any, Generator, Type

from ..answer import Answer, ChoiceItem, ChoiceOption, TextItem
from ..enums import Language, Numbering, Platform
from ..question import QEssay, QMultichoice, QQuestion
from .text import FText

if TYPE_CHECKING:
    from io import StringIO

    from ..category import Category

_LOG = logging.getLogger(__name__)


class Env:

    def __init__(self, name: str, args=None, opt=None):
        self.name = name
        self.args = args  # Does not include the env name
        self.opts = opt
        self.subitems = None

    def get(self, indent=0) -> str:
        tmp = "\\begin\{" + self.name + "}"
        if self.args:
            tmp += "{" + "}{".join(self.args) + "}"
        if self.opts:
            tmp += "[" + "][".join(self.args) + "]"
        tmp += "\t".join(self.subitems)
        tmp += "\\end{" + self.name + "}"
        return tmp

    def __str__(self) -> str:
        return self.get()


class Cmd():
    """_summary_
    """

    def __init__(self, name: str):
        self.name = name
        self.args = []
        self.opts = []

    def __str__(self) -> str:
        return self.name + "{" + "}{".join(self.args) + "}[" + "][".join(self.opts) + "]"


class LaTex():
    """_summary_
    """

    _NAME = ""
    _CMDS = {}
    _QTYPE = {}
    _HEADER = ""

    def __init__(self, cat: Category, buffer: StringIO, lang: Language, 
                 bsize: int, path: str):
        self.cat = cat
        self._io = buffer
        self._bsize = bsize
        self.path = path
        self.idx = 0
        self.line = "\n"
        self.lang = lang

    def _next(self):
        self.idx += 1
        if self.idx > len(self.line)-1:
            self.idx = 0
            self.line = self._io.read(self._bsize)

    @staticmethod
    def _wrap_env(items: list):
        env_name = items.pop().args[0]
        data = []
        cmd = items.pop()
        while isinstance(cmd, str) or not (cmd.name == "begin" and 
                cmd.args[0] == env_name):
            data.append(cmd)
            cmd = items.pop()
        data.reverse()
        cmd = Env(env_name, cmd.args[1:], cmd.opts)
        cmd.subitems = data
        items.append(cmd)

    def _parse_opt(self):
        start = self.idx + 1
        while self.line[self.idx] != "]":
            self._next() 
        return self.line[start:self.idx]

    def _parse_arg(self):
        start = self.idx + 1
        items = []
        while self.line:
            if self.line[self.idx] == "}":
                tmp = self.line[start: self.idx].strip()
                if start < self.idx and tmp:
                    items.append(tmp)
                break
            elif self.line[self.idx] == "\\":
                tmp = self.line[start: self.idx].strip()
                if start < self.idx and tmp:
                    items.append(tmp)
                items.append(self._parse_cmd())
                if items[-1].name == "end":
                    self._wrap_env(items)
                start = self.idx
            self._next()
        return items if len(items) > 1 else items[0]

    def _parse_cmd(self):
        self._next()
        start = self.idx
        while self.line[self.idx].isalpha():
            self._next()
        cmd = Cmd(self.line[start: self.idx])
        while self.line:
            if self.line[self.idx] == "[":
                cmd.opts.append(self._parse_opt())
            elif self.line[self.idx] == "{":
                cmd.args.append(self._parse_arg())
            elif self.line[self.idx]:
                break
            self._next()
        return cmd

    def _parse(self) -> Generator[Cmd|str, Any, None]:
        start = 0
        self._next()
        while self.line:
            if self.line[self.idx] == "\\" and self.line[self.idx+1].isalpha():
                if self.line[start: self.idx].strip():
                    yield self.line[start: self.idx]
                yield self._parse_cmd()
                start = self.idx + 1
            elif self.line[self.idx] == "%":
                while self.line[self.idx] != "\n": # ignores comments
                    self._next()
                start = self.idx + 1
            self._next()
        if self.line[start: self.idx].strip() and self.line[start] != "%":
            yield self.line[start: self.idx]

    def build(self, cmd: Cmd|str, gen: Generator):
        if not isinstance(cmd, Cmd):
            return None
        if cmd.name == "include":
            path = cmd.args[0]
            if os.path.relpath(path):
                path = self.path.rsplit("/", 1)[0] + "/" + path
            with open(path) as ifile:
                self.__class__(self.cat, ifile, path)
            return True
        elif cmd.name in ("usepackage", 'documentclass'):
            self.cat.metadata.setdefault("latex", []).append(cmd)
            return True
        return False

    def read(self):
        try:
            gen = self._parse()
            for cmd in gen:
                self.build(cmd, gen)
            return True
        except StopIteration:
            return False


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

    def _question_essay(self, question: QQuestion, gen: Generator):
        for item in gen:
            if isinstance(item, Cmd):
                value = item.args[0] if len(item.args) > 0 else None
                if item.name == "end" and value == "question":
                    break
                elif item.name in self._CMDS:
                    key, cast = self._CMDS[item.name]
                    if isinstance(cast, str):
                        val = getattr(self, cast)(value)
                    else:
                        val = cast(value)
                    setattr(question, key, val)
                else:
                    question.body[self.lang].add(str(item))
            else:
                question.body[self.lang].add(item)

    def _question(self, cmd: Cmd, gen: Generator):
        question = QQuestion({self.lang: ""})
        if cmd.opts[0] == "multichoice":
            pass
        elif cmd.opts[0] == "eassay":
            self._question_essay(question, gen)
        else:
            _LOG.warning("LATEX: Question type is not valid: %s", cmd.opts)
            return
        self.cat.add_question(question)

    def _category(self, cmd: Cmd|str, gen: Generator):
        tmp = self.cat
        try:
            self.cat = self.cat.__class__(cmd.opts[0])
            tmp.add_subcat(self.cat)
            for _cmd in gen:
                if isinstance(_cmd, str):
                    _LOG.warning("LATEX: Unexpected string '%s' after cat start.",
                                 _cmd)
                    continue
                if _cmd.name == "begin":
                    if "question" in _cmd.args:
                        self._question(_cmd, gen)
                    elif "category" in _cmd.args:
                        self._category(_cmd, gen)
                elif _cmd.name == "end" and "category" in _cmd.args:
                    break
                else:
                    raise ValueError(f"Couldnt map line {self.line}")
        except ValueError:
            _LOG.exception(f"Failed to parse category {cmd.opts[0]}")
        self.cat = tmp

    def build(self, cmd: Cmd|str, gen: Generator) -> bool|None:
        if super().build(cmd, gen) in (None, True):
            return None
        if cmd.name == "begin":
            if "category" in cmd.args:
                self._category(cmd, gen)
            elif "question" in cmd.args:
                self._question(cmd, gen)
        return False


# -----------------------------------------------------------------------------


def read_amc(cls: Type[Category], file_name: str, lang: Language):
    category = cls()
    with open(file_name, 'r', encoding='utf-8') as ifile:
        _PkgAMQ(category, ifile, lang, 1024, file_name).read()
    return category


def read_l2m(cls: Type[Category], file_name: str, lang: Language):
    category = cls()
    with open(file_name, 'r', encoding='utf-8') as ifile:
        _PkgLatexToMoodle(category, ifile, lang, 2048, file_name).read()
    return category


# ----------------------------------------------------------------------------


def write_latex(self, file_path: str, ftype: type, lang: Language) -> None:
    """_summary_
    Args:
        file_path (str): _description_
    Raises:
        NotImplementedError: _description_
    """
    raise NotImplementedError("LaTex not implemented")
