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
import re
from typing import TYPE_CHECKING, Any, Dict, Generator, Type

from ..answer import ChoiceItem, ChoiceOption, TextItem
from ..enums import Language, MathType, Platform, TextFormat
from ..processors import Proc
from ..question import QQuestion
from .text import FText, Math, Parser, XItem

if TYPE_CHECKING:
    from io import StringIO

    from ..category import Category

_LOG = logging.getLogger(__name__)
_WRITER = XItem.WRITER.setdefault(TextFormat.LATEX, {})  


class CmdParser(Parser):
    
    def parse(self, data: Dict[Any, str|XItem]) -> None:
        if len(data) == 1:
            self.ftext = list(data.values())
        else:
            self.ftext = data[-1]
            for item in self.ftext:
                pass


class LaTexParser:
    """_summary_
    """

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
        self.start = 0
        self.line = " "
        self.lang = lang
        self.end = False
    
    def _build_from(self, item: XItem) -> None:
        pass

    def _next(self):
        self.idx += 1 # This 2 account for the lookahead parts
        if self.idx > len(self.line)-2 and not self.end:
            self.idx = 0
            tmp = self._io.read(self._bsize)
            if len(tmp) < self._bsize:
                self.end = True
            self.line = self.line[self.start:] + tmp
            self.start = 0

    def _cmd_replace(self, item: XItem):
        if item.attrs is None and item.opts is None and len(item) == 0:
            if item.tag in ("newline", "break"):
                return "\n"
            if item.tag == "Vert":
                return "|"
        return item

    def _parse_arg(self, is_opt, prev: int):
        self.start = self.idx + 1
        items = {}
        char = "]" if is_opt else "}"
        while self.idx < len(self.line):
            if self.line[self.idx] == char:
                tmp = self.line[self.start: self.idx]
                if self.start < self.idx and tmp: 
                    tmp = tmp.split(",") if "," in tmp else (tmp,)
                    for val in tmp:
                        if "=" in val:
                           val = val.split("=")   
                           items[val[0].strip()] = val[1]  .strip()
                        else:
                            items[prev] = val.strip()
                            prev += 1
                break
            elif self.line[self.idx] == "\\" and self.line[self.idx+1].isalpha():
                items[prev] = self._parse_cmd()
            self._next()
        self.start = self.idx
        return items, prev

    def _parse_cmd(self):
        self._next()
        self.start = self.idx
        while self.line[self.idx].isalpha():
            self._next()
        tag, args, opts, aprv, oprv = self.line[self.start: self.idx], {}, {}, 0, 0
        while self.idx < len(self.line):
            if self.line[self.idx] == "[":
                items, oprv = self._parse_arg(True, oprv)
                opts.update(items)
            elif self.line[self.idx] == "{":
                items, aprv = self._parse_arg(False, aprv)
                args.update(items)
            elif self.line[self.idx]:
                break
            self._next()
        item = XItem(tag, args, opts)
        if tag == "begin":
            self.start = self.idx
            for env in self._parse_env():
                if isinstance(env, XItem) and env.tag == "end":
                    break
                item.append(env)
            item.tag = None
        self.start = self.idx
        return self._cmd_replace(item)   

    def _parse_string(self):
        string = self.line[self.start: self.idx]
        string = re.sub(r"\n{2,}", r"\\", string)
        string = string.replace("\n","")
        string = string.replace("\\","\n")
        return string

    def _parse_env(self) -> Generator[XItem|str, Any, None]:
        while self.idx < len(self.line):
            if self.line[self.idx] == "\\" and self.line[self.idx+1].isalpha():
                if self.line[self.start: self.idx].strip():
                    yield self._parse_string()
                yield self._parse_cmd()
            elif self.line[self.idx] == "%" and self.line[self.idx-1] != "\\":
                while self.line[self.idx] != "\n": # ignores comments
                    self._next()
                self.start = self.idx + 1
            else:
                self._next()
        if self.line[self.start: self.idx].strip() and self.line[self.start] != "%":
            yield self._parse_string()

    @staticmethod
    def _to_string(item: XItem, *_) -> str:
        tmp = "\\" + item.tag
        if item.opts:
            opt = [f"{k}={v}" if isinstance(k) else f"{v}" for k,v in item.opts.items()]
            tmp += "[" + ",".join(opt) + "]"
        if item.attrs:
            tmp += "{" + "}{".join(item.attrs) + "}"
        return tmp

    def read(self):
        try:
            self._next() # Load the initial bytes
            for item in self._parse_env():
                if not isinstance(item, XItem):
                    continue
                if item.tag == "include":
                    path = item.args[0]
                    if os.path.relpath(path):
                        path = self.path.rsplit("/", 1)[0] + "/" + path
                    with open(path) as ifile:
                        self.__class__(self.cat, ifile, self.lang, self._bsize, path)
                    return True
                elif item.tag in ("usepackage", 'documentclass'):
                    self.cat.metadata.setdefault("latex", []).append(item)
                else:
                    self._build_from(item)
            return True
        except StopIteration:
            return False
_WRITER[Platform.NONE] = LaTexParser._to_string 


class LatexWriter:

    def __init__(self, buffer: StringIO, cat: Category, lang: Language) -> None:
        self.buffer = buffer
        self.lang = lang
        self.cat = cat

    def _write_cat(self, cat: Category):
        self.buffer.write("\\begin{category}[" + cat.name + "]\n")
        for qst in cat.questions:
            self._write_ftext(qst.body[self.lang])      
        for name in cat:
            self._write_cat(cat[name])
        self.buffer.write("\\end{category}]\n")

    def _write_header(self, cat: Category):
        if "latex" in cat.metadata:
            for meta in cat.metadata["latex"]:
                self.buffer.write(str(meta)+ "\n")
        self.buffer.write("\n")

    def _write_ftext(self, ftext: FText):
        for item in ftext:
            if isinstance(item, str):
                self.buffer.write(item)
            elif isinstance(item, XItem):
                pass
            elif isinstance(item, Math):
                self.buffer.write(item.get(MathType.LATEX, None))

    def write(self):
        self._write_header(self.cat)
        self.buffer.write("\\begin{document}\n")
        self._write_cat(self.cat)
        self.buffer.write("\\end{document}\n")



class _ClsExamParser(LaTexParser):
    """See: https://ctan.org/pkg/exam
    """
    _NAME = "exam"


class _AMQReader(LaTexParser):
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


class _McExamParser(LaTexParser):
    """See: https://ctan.org/pkg/mcexam
    """
    _NAME = "mcexam"


class _AlterQCMParser(LaTexParser):
    """See: https://www.ctan.org/pkg/alterqcm
    """
    _NAME = "alterqcm"


class _LatexToMoodleParser(LaTexParser):
    """Parsers the package created by Guillame for the latextomoodle repo.
    Since document classes have priority, it will only be used if the class of
    the document is not assigned to any parser. This is a LAZY parser! It is
    meant to be simple and fast, and not to consider all possibilities.
    See: https://github.com/Guillaume-Garrigos/moodlexport
    """
    _NAME = "latextomoodle"

    _CMDS = {
        "title":  "_set_title",
        "generalfeedback": "_set_generalfeedback",
        "grade": "_set_grade",
        "penalty": "_set_penalty",
        "answer": "_set_answer",
        "idnumber": "_set_dbid",
        "responseformat": "_set_rsp_format",
        "responserequired": "_set_rsp_required",
        "responsefieldlines": "_set_lines",
        "attachments": "_set_attachments",
        "attachmentsrequired": "_set_atts_required",
        "responsetemplate": "_set_template",
        "single": "_set_single",
        "shuffleanswers": "_set_shuffle",
        "answernumbering": "_set_numbering",
        "shownumcorrect": "_set_show_ans"
    }

    def _set_answer(self, _, item: XItem):
        return (item.attrs, float(item.opts[0]))

    def _set_dbid(question: QQuestion, item: XItem):
        question.dbid = item

    def _set_generalfeedback(self, question: QQuestion, item: XItem):
        question.feedback[self.lang].append(item)
        question.procs.append(Proc.from_str())

    def _set_grade(self, _, item: XItem):
        return float(item.attrs[0])

    def _set_penalty(self, _, item: XItem):
        return float(item.attrs[0])

    def _set_numbering(self, _, item: XItem):
        return item.attrs[0]

    def _set_rsp_format(self, _, item: XItem):
        return item.attrs[0]
    
    def _set_rsp_required(self, _, item: XItem):
        return item.attrs[0]

    def _set_single(self, _, item: XItem):
        return item.attrs[0].lower() == "true"
    
    def _set_show_ans(self, _, item: XItem):
        return item.attrs[0].lower() == "true"

    def _set_shuffle(self, _, item: XItem):
        return item.attrs[0].lower() == "true"

    def _set_template(self, _, item: XItem):
        return item.attrs[0]

    def _set_title(self, question: QQuestion, item: XItem):
        question.name[self.lang] = item

    def _question_essay(self, question: QQuestion, opts: Dict[str,XItem]):
        args = {}
        args["grade"] = opts["grade"][-1]
        args["penalty"] = opts["penalty"][-1]
        item = TextItem(None, Proc.from_template("no_result", args))
        question.body[self.lang].text.append(item)

    def _question_multichoice(self, question: QQuestion, opts: Dict[str,XItem]):
        args = {"values": {}}
        args["grade"] = opts["grade"][-1]
        args["penalty"] = opts["penalty"][-1]
        item = ChoiceItem()
        for idx, (ans, val) in enumerate(opts["answer"]):
            args["values"][idx] = {"value": val}
            parser = CmdParser()
            parser.parse(ans)
            item.options.append(ChoiceOption(FText(parser)))
        item.processor = Proc.from_template("mapper", args)
        question.body[self.lang].text.append(item)

    def _question(self, items: XItem):
        question = QQuestion({self.lang: ""})
        opt = {"grade": [1], "penalty": [0]}
        for item in items:
            if isinstance(item, XItem):
                if item.tag in self._CMDS:
                    res = getattr(self, self._CMDS[item.tag])(question, item)
                    if res:
                        opt.setdefault(item.tag, []).append(res)
                else:
                    question.body[self.lang].add(item.get("", Platform.NONE, TextFormat.LATEX))
            else:
                question.body[self.lang].add(item)
        if items.opts[0] == "multichoice":
            self._question_multichoice(question, opt)
        elif items.opts[0] == "essay":
            self._question_essay(question, opt)
        else:
            _LOG.warning("LATEX: Question type is not valid: %s", items.opts)
            return
        self.cat.add_question(question)

    def _category(self, item: XItem):
        tmp = self.cat
        try:
            self.cat = self.cat.__class__(item.opts[0])
            tmp.add_subcat(self.cat)
            for _cmd in item:
                if isinstance(_cmd, str):
                    _LOG.warning("LATEX: Unexpected string '%s' after cat start.",
                                 _cmd)
                    continue
                elif _cmd.tag is None:
                    if _cmd.attrs.get(0) == "question":
                        self._question(_cmd)
                    elif _cmd.attrs.get(0) == "category":
                        self._category(_cmd)
                elif _cmd.tag == "end" and "category" in _cmd.attrs:
                    break
                else:
                    raise ValueError(f"Couldnt map line {self.line}")
        except ValueError:
            _LOG.exception(f"Failed to parse category {item.opts[0]}")
        self.cat = tmp

    @staticmethod
    def _to_string(item: XItem, *args):
        pass

    def _build_from(self, item: XItem) -> None:
        if item.tag is None:
            if item.attrs.get(0) == "category":
                self._category(item)
            elif item.attrs.get(0) == "question":
                self._question(item)
            elif item.attrs.get(0) == "document":
                for _item in item:
                    self._build_from(_item)
_WRITER[Platform.LATEX_L2M] = _LatexToMoodleParser._to_string 


class _LatexToMoodleWriter(LatexWriter):
    pass


# -----------------------------------------------------------------------------


def read_amc(cls: Type[Category], file_name: str, lang: Language):
    category = cls()
    with open(file_name, 'r', encoding='utf-8') as ifile:
        _AMQReader(category, ifile, lang, 1024, file_name).read()
    return category


def read_l2m(cls: Type[Category], file_name: str, lang: Language):
    category = cls()
    with open(file_name, 'r', encoding='utf-8') as ifile:
        _LatexToMoodleParser(category, ifile, lang, 2048, file_name).read()
    return category


# ----------------------------------------------------------------------------


def write_l2m(self: Category, file_name: str, lang: Language) -> None:
    """_summary_
    Args:
        file_path (str): _description_
    """
    with open(file_name, 'w', encoding='utf-8') as ofile:
        _write_header(self, ofile)
        ofile.write("\\begin{document}\n")
        _write_cat(self, ofile, lang, Platform.LATEX_L2M)
        ofile.write("\\end{document}\n")
     
