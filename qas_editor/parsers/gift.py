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
import re
from typing import TYPE_CHECKING

from ..answer import Answer, ANumerical, Subquestion, TextItem
from ..enums import Language, TextFormat
from ..question import (MARKER_INT, QEssay, QMatching, QMultichoice,
                        QNumerical, QQuestion, QShortAnswer, QTrueFalse)
from ..utils import gen_hier
from .text import FText, PlainParser, XHTMLParser

if TYPE_CHECKING:
    from ..category import Category
_LOG = logging.getLogger(__name__)


class _FromParser:

    PARSER = {TextFormat.PLAIN: PlainParser, TextFormat.HTML: XHTMLParser}

    def __init__(self) -> None:
        self._pos = 0
        self._scp = False
        self._str = ""

    def _nxt(self):
        self._scp = (self._str[self._pos] == "\\") and not self._scp
        self._pos += 1

    def _next(self, comp: list, size: int = 1) -> str:
        start = self._pos
        self._pos += 1
        while self._str[self._pos:self._pos+size] not in comp or self._scp:
            self._scp = (self._str[self._pos] == "\\") and not self._scp
            self._pos += 1
        return self._str[start:self._pos]

    def _handle_item(self):
        options = []
        rgx = re.compile(r"([=~])(%+\d%)?(.+)")
        feedback = ""
        all_equals = True
        while self._str[self._pos] != "}" or self._scp:
            if self._str[self._pos] in ["=", "~"] and not self._scp:
                mch = rgx.match(self._next(["=", "~", "#", "}"]))
                all_equals &= mch[1] == "="
                if mch[2]:
                    frac = int(mch[2][1:-1])
                elif mch[1] == "~":
                    frac = 0
                else:
                    frac = 100
                if self._str[self._pos:self._pos+4] != "####" and self._str[self._pos] == "#":
                    fdbk = self._next(["=", "~", "#", "}"])
                else:
                    fdbk = ""
                options.append((frac, mch[3], fdbk))
            elif self._str[self._pos:self._pos+4] == "####":
                feedback = self._next(["}"], 1)[4:]
            else:
                _LOG.info("Char may be incorrectly placed: %s", self._str[self._pos])
                self._nxt()
        return feedback, options, all_equals

    def _set_value_tolerance(self, mtype: str, val: str, tol: str):
        tol = float(tol)
        if mtype == "..":
            val = (float(val) + tol)/2
            tol = val - tol
        return str(val), tol

    def _from_qessay(self, body: list):
        body.append(TextItem())

    def _from_qtruefalse(self, name: str, header: FText):
        correct = self._next(["}", "#"], 1).lower() in ["true", "t"]
        fdbk_false = fdbk_true = fdbk_general = ""
        if self._str[self._pos] != "}":
            fdbk_false = self._next(("}", "#"), 1)
        if self._str[self._pos] != "}":
            fdbk_true = self._next(("}", "#"), 1)
        if self._str[self._pos] != "}":
            fdbk_general = self._next(("}",), 1)[3:]
        return QTrueFalse(correct, fdbk_true, fdbk_false, name=name,
                        question=header, remarks=fdbk_general)

    def _from_qnumerical(self, name: str, header: FText):
        qst = QNumerical(name=name, question=header)
        self._pos += 1   # Jump the Question type marker
        if self._str[self._pos] not in ["=", "~"]:
            rgx = re.match(r"([.0-9-]+)(:|(?:\.\.))([.0-9-]+)\}", self._str[self._pos:])
            val, tol = self._set_value_tolerance(rgx[2], rgx[1], rgx[3])
            qst.options.append(ANumerical(tol, fraction=100, text=val))
        else:
            rgx = re.compile(r"([=~])(%\d+%)?([.0-9-]+)(:|(?:\.\.))([.0-9-]+)")
            ans = None
            while self._str[self._pos] != "}":
                if self._str[self._pos:self._pos+4] == "####":
                    qst.remarks = self._next(["}"], 1)[4:]
                    continue
                txt = self._next(["=", "~", "#", "}"], 1)
                if txt[0] == "#":           # Should only happen after "ans" is
                    ans.feedback = txt[1:]  # defined, so this is secure
                    continue
                if txt[0] == "~":           # Wrong answer. Created only to hold a
                    frac = val = tol = 0    # feedback. If no feedback.. something
                else:                       # is wrong
                    mtc = rgx.match(txt)
                    val, tol = self._set_value_tolerance(mtc[4], mtc[3], mtc[5])
                    if mtc[1] == "~":
                        frac = 0
                    elif mtc[2]:
                        frac = int(mtc[2][1:-1])
                    else:
                        frac = 100
                ans = ANumerical(tol, fraction=frac, text=val)
                qst.options.append(ans)
        return qst


    def _from_qmatching(name: str, header: FText, options: list):
        qst = QMatching(name=name, question=header)
        for _, val, _ in options:
            mch = re.match(r"(.*?)(?<!\\) -> (.*)", val)
            qst.options.append(Subquestion(mch[1], mch[2]))
        return qst


    def _from_qshortanswer(name: str, header: FText, options: list):
        qst = QShortAnswer(name=name, question=header)   # Moodle does this way,
        for frac, val, fdbk in options:                  # so I will do the same
            qst.options.append(Answer(frac, val, fdbk))
        return qst


    def _from_qmultichoice(name: str, header: FText, options: list):
        qst = QMultichoice(name=name, question=header)   # Moodle does this way,
        for frac, val, fdbk in options:                  # so I will do the same
            qst.options.append(Answer(frac, val, fdbk))
        return qst


    def _from_block(self, name: str, header: FText, question: QQuestion, lang: Language):
        """ Essay differs to Description only because they have an empty block.
        T/F starts with T or F. Numerical, with #. The others requires identifing
        the type of answers given in the block, except MissingWord and ShortAnswer.
        The only difference between these 2 is that the first has a tail text.
        """
        self._nxt()
        if self._str[self._pos] in ["T", "F"]:
            return self._from_qtruefalse(name, header)
        if self._str[self._pos] == "#" and self._str[self._pos:self._pos+4] != "####":
            return self._from_qnumerical(name, header)
        feedback, options, all_equals = self._handle_item()
        if not options:
            self._from_qessay(question.body[lang].text)
        elif " -> " in options[0][1]:
            question = self._from_qmatching(name, header, options)
        elif all_equals:
            question = self._from_qshortanswer(name, header, options)
        else:   # Moodle traits MissingWord as a Multichoice...
            question = self._from_qmultichoice(name, header, options)
        if feedback:
            question.feedback[lang] = feedback


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
            self._pos += 1              # that if any '\' appears, it should be an
            start = self._pos           # error anyway.
            while self._str[self._pos] != "]":
                self._pos += 1
            cformat = TextFormat(self._str[start:self._pos])
            self._nxt()
        parser = self.PARSER.get(cformat, PlainParser)()
        start = self._pos
        while self._pos < len(self._str) and self._str[self._pos] != "{" or self._scp:
            self._nxt()
        parser.parse(self._str[start:self._pos])
        lang = self._attr.get("lang", Language.EN_US)
        question = QQuestion({lang: name}, self._attr.get("id"), 
                             self._attr.get("tags"))
        question.body[lang].add(parser)
        if self._pos < len(self._str) and self._str[self._pos] == "{":
            self._from_block(name, None, question, lang)
        tail = self._str[self._pos+1:]
        if tail:
            parser = self.PARSER.get(cformat, PlainParser)()
            parser.parse(tail)
            question.body[lang].add(parser)
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
    parser = _FromParser()
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
                        attrs["id"] = match[3:]
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
