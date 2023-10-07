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
from typing import TYPE_CHECKING, Type, List, Tuple
import re
import os
import logging

from ..enums import Numbering
from ..answer import Answer
from ..question import QEssay, QMultichoice
from .text import FText
if TYPE_CHECKING:
    from ..category import Category
    from io import StringIO

_LOG = logging.getLogger(__name__)
_TEX_BASE_CMD = re.compile(r"\\(\w+).*(?:\{(.+)\})")

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


_TEMPLATES = {}
class LaTex():
    """_summary_
    """

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
        while self.idx < len(self.line) and self.line[self.idx] != "]":
            self.idx += 1
            if self.idx > len(self.line)-1:
                self.line += next(self.buf, "") 
        return self.line[start:self.idx]

    def _parse_arg(self):
        start = self.idx + 1
        items = []
        while self.idx < len(self.line):
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
            self.idx += 1
            if self.idx > len(self.line)-1:
                self.line += next(self.buf, "")
        return items if len(items) > 1 else items[0]

    def _parse_cmd(self):
        self.idx += 1
        start = self.idx
        while self.line[self.idx].isalpha():
            self.idx += 1
        cmd = Cmd(self.line[start: self.idx])
        while self.idx < len(self.line):
            if self.line[self.idx] == "[":
                cmd.opts.append(self._parse_opt())
            elif self.line[self.idx] == "{":
                cmd.args.append(self._parse_arg())
            elif self.line[self.idx]:
                break
            self.idx += 1
            if self.idx > len(self.line)-1:
                self.line += next(self.buf, "")
        return cmd

    def _parse(self):
        self.idx = start = 0
        self.line = next(self.buf, "")
        while self.idx < len(self.line):
            if self.line[self.idx] == "\\" and self.line[self.idx+1].isalpha():
                if self.line[start: self.idx].strip():
                    yield self.line[start: self.idx]
                yield self._parse_cmd()
                start = self.idx + 1
            elif self.line[self.idx] == "%":
                start = self.idx
                break
            self.idx += 1
        if self.line[start: self.idx].strip() and self.line[start] != "%":
            yield self.line[start: self.idx]

    def build(self, cmd: Cmd|Env|str):
        if isinstance(cmd, Cmd) and cmd.name == "include":
            path = cmd.args[0]
            if os.path.relpath(path):
                path = self.path.rsplit("/", 1)[0] + "/" + path
            with open(path) as ifile:
                self.__class__(self.cat, ifile, path)

    def read(self):
        try:
            while self.line:
                for cmd in self._parse():
                    self.build(cmd)
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
        ended = False
        while self.line and not ended:
            for item in self._parse():
                if isinstance(item, Cmd):
                    value = item.args[0] if len(item.args) >0 else None
                    if item.name == "end" and value == "question":
                        if options:
                            params["options"] = options
                        ended = True
                        break
                    elif item.name == "answer":
                        options.append(Answer(float(item.opts[0]), value))
                    elif item.name in self._CMDS:
                        key, cast = self._CMDS[item.name]
                        if isinstance(cast, str):
                            params[key] = getattr(self, cast)(value)
                        else:
                            params[key] = cast(value)
                    else:
                        params["question"].text.append(item)
                elif item.strip():
                    params["question"].text.append(item)
        params["question"].text.pop(0)
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
                    raise ValueError(f"Couldnt map line {self.line}")
        except ValueError:
            _LOG.exception(f"Failed to parse category {name}")
        self.cat = tmp

    def build(self, cmd):
        super().build(cmd)
        if isinstance(cmd, Cmd):
            if "category" in cmd.args:
                self._category(cmd.opts[0])
            elif "question" in cmd.args:
                self._question(cmd.opts[0])


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
