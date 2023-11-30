# Question and Answer Sheet Editor <https://github.com/LucasWolfgang/QAS-Editor>
# Copyright (C) 2022  Lucas Wolfgang
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
## Description

"""
import logging
import os
import re
from typing import TYPE_CHECKING

from ..answer import (ChoiceItem, ChoiceOption, EntryItem, MatchItem,
                      MatchOption, TextItem)
from ..enums import Language, TextFormat
from ..processors import Proc
from ..question import QQuestion
from ..utils import gen_hier
from .text import FText, PlainParser, XHTMLParser

if TYPE_CHECKING:
    from ..category import Category
_LOG = logging.getLogger(__name__)


def _unescape(data: str) -> str:
    for repl in (("\\:", ":"), ("\\~", "~"), ("\\=", "="), ("\\#", "#"), 
                 ("\\{", "{"), ("\\}", "}")):
        data = data.replace(*repl)
    return data

def _escape(data: str) -> str:
    for repl in ((":", "\\:"), ("~", "\\~"), ("=", "\\="), ("#", "\\#"), 
                 ("{", "\\{"), ("}", "\\}")):
        data = data.replace(*repl)
    return data


class GiftXHTMLParser(XHTMLParser):

    def handle_startendtag(self, tag: str, attrs: list):
        for idx, (key, val) in enumerate(attrs):
            attrs[idx] = (key[:-1], val)
        super().handle_startendtag(tag,attrs)

    def handle_data(self, data: str):
        return super().handle_data(_unescape(data))


class _Reader:

    PARSER = {TextFormat.PLAIN: PlainParser, TextFormat.HTML: GiftXHTMLParser}
    NUM_RGX = re.compile(r"=(%\d+%)?([.0-9-]+)(:|(?:\.\.))([.0-9-]+)")
    ANY_RGX = re.compile(r"([=~])(%\d+%)?(.+)")
    MTCH_RGX = re.compile(r"(.*?)(?<!\\) -> (.*)")

    def __init__(self, path: str) -> None:
        self._pos = 0
        self._scp = False
        self._str = ""
        self._qst = self._lng = self._fmt = None
        self._rpath = path.replace("\\", "/")

    def _nxt(self):
        self._scp = (self._str[self._pos] == "\\") and not self._scp
        self._pos += 1

    def _next(self, comp: list) -> str:
        start = self._pos
        self._pos += 1
        while not any(self._str[self._pos:self._pos+len(x)] == x for x in comp) or self._scp:
            self._nxt()
        return self._str[start:self._pos]

    def _handle_item(self):
        all_equals, options = True, []
        while self._str[self._pos] != "}" or self._scp:
            if self._str[self._pos] in ["=", "~"] and not self._scp:
                mch = self.ANY_RGX.match(self._next(["=", "~", "#", "}"]))
                all_equals &= mch[1] == "="
                if mch[2]:
                    frac = int(mch[2][1:-1])
                elif mch[1] == "~":
                    frac = 0
                else:
                    frac = 100
                if self._str[self._pos] == "#" and self._str[self._pos:self._pos+4] != "####":
                    fdbk = FText(self._parse_text(self._next(["=", "~", "#", "}"]).strip()))
                else:
                    fdbk = None
                options.append((frac, mch[3].strip(), fdbk))
            elif self._str[self._pos:self._pos+4] == "####":
                feedback = self._parse_text(self._next(["}"])[4:])
                self._qst.feedback[self._lng].append(FText(feedback))
            else:
                _LOG.info("GIFT: Char may be incorrectly placed: %s", self._str[self._pos])
                self._nxt()
        return options, all_equals

    def _set_value_tolerance(self, mtype: str, val: str, tol: str):
        tol = float(tol)
        if mtype == "..":
            val = (float(val) + tol)/2
            tol = val - tol
        return float(val), tol

    def _parse_text(self, text: str):
        parser = self.PARSER[self._fmt](self._rpath)
        parser.parse(text)
        return parser

    def _from_qessay(self):
        self._qst.body[self._lng].text.append(TextItem())

    def _from_qtruefalse(self):
        args, feeds = {"values": {0: {"value": 0}, 1: {"value": 0}}}, []
        if self._next(["}", "#"]).lower() in ["true", "t"]:
            args["values"][0]["value"] = 100
        else:
            args["values"][1]["value"] = 100
        if self._str[self._pos] != "}":
            args["values"][0]["feedback"] = len(feeds)
            feeds.append(FText(self._parse_text(self._next(("}", "#")))))
        if self._str[self._pos] != "}":
            args["values"][1]["feedback"] = len(feeds)
            feeds.append(FText(self._parse_text(self._next(("}", "#")))))
        if self._str[self._pos] != "}":
            txt = FText(self._parse_text(self._next(("}",))[3:]))
            self._qst.feedback[self._lng].append(txt)
        item = ChoiceItem(feeds, Proc.from_template("mapper", args))
        item.options.append(ChoiceOption(FText("True")))
        item.options.append(ChoiceOption(FText("False")))
        self._qst.body[self._lng].text.append(item)

    def _from_qnumerical(self):
        self._pos += 1   # Jump the Question type marker
        args = {"values": []}
        feeds = []
        if self._str[self._pos] not in ["=", "~"]:
            rgx = re.match(r"([.0-9-]+)(:|(?:\.\.))([.0-9-]+)\}", self._str[self._pos:])
            val, tol = self._set_value_tolerance(rgx[2], rgx[1], rgx[3])
            args["values"].append({"tol": tol, "grade": 100, "value": val})
        else:
            while self._str[self._pos] != "}" and not self._scp:
                if self._str[self._pos:self._pos+4] == "####":
                    txt = self._next(("=", "~", "}"))
                    self._qst.feedback[self._lng].append(FText(self._parse_text(txt[4:])))
                else:
                    txt = self._next(("#", "=", "~", "}"))
                    if txt[0] in "~":
                        frac = val = tol = 0
                    else:
                        mtc = self.NUM_RGX.match(txt)
                        val, tol = self._set_value_tolerance(mtc[3], mtc[2], mtc[4])
                        frac = int(mtc[1][1:-1]) if mtc[1] else 100
                    arg = {"tol": tol, "grade": frac, "value": val}
                    if self._str[self._pos] == "#" and self._str[self._pos+1] != "#":
                        txt = self._next(("=", "~", "}", "#"))
                        feeds.append(FText(self._parse_text(txt[1:])))
                        arg["feedback"] = len(feeds)-1
                    args["values"].append(arg)
        item = EntryItem(feeds, Proc.from_template("numeric_value", args))
        self._qst.body[self._lng].text.append(item)
        
    def _from_match_opt(self, string: str, setx: list):
        opt = MatchOption(FText(self._parse_text(string)))
        opt.match_max = 1
        setx.append(opt)

    def _from_matching(self, options: list):
        item = MatchItem()
        args = {}
        for frac, val, _ in options:
            mch = self.MTCH_RGX.match(" " + val)
            self._from_match_opt(mch[1], item.set_from)
            self._from_match_opt(mch[2], item.set_to)
            args[mch[1]] = {mch[2]: frac}
        item.processor = Proc.from_template("matching", {"values":args})
        self._qst.body[self._lng].text.append(item)

    def _from_qshortanswer(self, options: list):
        args = {"values": {}}
        feeds = []
        for frac, val, fdbk in options:
            tmp = {"value": frac}
            if fdbk:
                tmp["feedback"] = len(feeds)
                feeds.append(fdbk)
            args["values"][val] = tmp
        item = EntryItem(feeds, Proc.from_template("mapper", args))
        self._qst.body[self._lng].text.append(item)

    def _from_qmultichoice(self, options: list):
        item = ChoiceItem()
        item.max_choices = 1
        args = {"values": {}}
        for idx, (frac, val, fdbk) in enumerate(options):
            item.options.append(ChoiceOption(FText(self._parse_text(val.strip()))))
            args["values"][idx] = {"value": frac, "feedback": len(item.feedbacks)}
            item.feedbacks.append(fdbk)
        item.processor = Proc.from_template("mapper", args)
        self._qst.body[self._lng].text.append(item)

    def _from_block(self):
        """ Essay differs to Description only because they have an empty block.
        T/F starts with T or F. Numerical, with #. The others requires identifing
        the type of answers given in the block, except MissingWord and ShortAnswer.
        The only difference between these 2 is that the first has a tail text.
        """
        self._nxt()
        if self._str[self._pos] in ["T", "F"]:
            return self._from_qtruefalse()
        if self._str[self._pos] == "#" and self._str[self._pos:self._pos+4] != "####":
            return self._from_qnumerical()
        options, all_equals = self._handle_item()
        if not options:
            self._from_qessay()
        elif " -> " in options[0][1]:
            self._from_matching(options)
        elif all_equals:
            self._from_qshortanswer(options)
        else:   # GIFT traits MissingWord as a Multichoice...
            self._from_qmultichoice(options)

    def get(self):
        """Was initially using regex, but it does not handle escaped char in
        every situation so I prefered implementing a char parse.
        """
        name = "default"
        cformat = TextFormat.PLAIN
        if self._str[:2] == "::":
            self._pos = 3
            while self._str[self._pos:self._pos+2] != "::" or self._scp:
                self._nxt()
            name = self._str[2:self._pos].replace("\\", "")
            self._pos += 2
        if self._str[self._pos] == "[":  # The types are limited, so we can consider
            self._pos += 1               # that if any '\' appears, it should be an
            start = self._pos            # error anyway.
            while self._str[self._pos] != "]":
                self._pos += 1
            cformat = TextFormat(self._str[start:self._pos])
            self._nxt()
        start = self._pos
        while self._pos < len(self._str) and self._str[self._pos] != "{" or self._scp:
            self._nxt()
        lang = self._attr.get("lang", Language.EN_US)
        question = QQuestion({lang: name}, self._attr.get("id"), 
                             self._attr.get("tags"))
        self._qst, self._lng, self._fmt = question, lang, cformat
        question.body[lang].add(self._parse_text(self._str[start:self._pos]))
        if self._pos < len(self._str) and self._str[self._pos] == "{":
            self._from_block()
        tail = self._str[self._pos+1:]
        if tail:
            question.body[lang].add(self._parse_text(tail))
        return question

    def reset(self, data: str, attrs: dict) -> None:
        self._pos = 0
        self._scp = False
        self._str = data
        self._attr = attrs

# -----------------------------------------------------------------------------


def read_gift(cls, file_path: str, comment=None) -> "Category":
    """
    """
    top_quiz: "Category" = cls()
    quiz = top_quiz
    parser = _Reader(os.path.dirname(file_path))
    attrs = {}
    with open(file_path, "r", encoding="utf-8") as ifile:
        for line in ifile:
            tmp = line.strip()
            if not tmp or tmp[:2] == "//":
                attrs.clear()
                for match in re.findall("\[(.+?)\]", tmp):
                    if match[:5] == "tags:":
                        attrs["tags"] = match[5:].split()
                    elif match[:3] == "id:":
                        attrs["id"] = int(match[3:])
                    elif match[:5] == "lang:":
                        try:
                            attrs["lang"] = Language(match[5:])
                        except:
                            _LOG.error("GIFT: Language is not valid")
                continue
            if tmp[:10] == "$CATEGORY:":
                quiz = gen_hier(cls, top_quiz, tmp[10:].strip())
                continue
            for line in ifile:
                tmp += line.strip()
                if line == "\n":
                    break
            parser.reset(tmp, attrs)
            quiz.add_question(parser.get())
    return top_quiz


def write_gift(self, file_path: str) -> None:
    """_summary_

    Args:
        file_path (str): _description_
    """
    # TODO
    raise NotImplementedError("Gift not implemented")
