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
from typing import TYPE_CHECKING
from ..questions import MARKER_INT, QMatching, QEssay, QTrueFalse, QNumerical,\
                        QDescription,QShortAnswer, QMultichoice
from ..enums import TextFormat
from ..answer import Answer, ANumerical, Subquestion
from ..utils import FText, gen_hier
if TYPE_CHECKING:
    from ..category import Category
_LOG = logging.getLogger(__name__)

def _nxt(stt: list, qst: str):
    stt[1] = (qst[stt[0]] == "\\") and not stt[1]
    stt[0] += 1


def _next(stt: list, string: str, comp: list, size: int = 1) -> str:
    start = stt[0]
    stt[0] += 1
    while string[stt[0]:stt[0]+size] not in comp or stt[1]:
        stt[1] = (string[stt[0]] == "\\") and not stt[1]
        stt[0] += 1
    return string[start:stt[0]]

def _from_qdescription(name: str, text: FText):
    return QDescription(name=name, question=text)


def _from_qessay(name: str, text: FText):
    return QEssay(name=name, question=text)


def _from_qtruefalse(name: str, header: FText, stt: list, qst_blk: str):
    correct = _next(stt, qst_blk, ["}", "#"], 1).lower() in ["true", "t"]
    fdbk_false = fdbk_true = fdbk_general = ""
    if qst_blk[stt[0]] != "}":
        fdbk_false = _next(stt, qst_blk, ("}", "#"), 1)
    if qst_blk[stt[0]] != "}":
        fdbk_true = _next(stt, qst_blk, ("}", "#"), 1)
    if qst_blk[stt[0]] != "}":
        fdbk_general = _next(stt, qst_blk, ("}"), 1)[3:]
    return QTrueFalse(correct, fdbk_true, fdbk_false, name=name, 
                      question=header, feedback=fdbk_general)


def _set_value_tolerance(mtype:str, val: str, tol: str):
    tol = float(tol)
    if mtype == "..":
        val = (float(val) + tol)/2
        tol = val - tol
    return str(val), tol


def _from_qnumerical(name: str, header: FText, stt: list, qst_blk: str):
    qst = QNumerical(name=name, question=header)
    stt[0] += 1   # Jump the Question type marker
    if qst_blk[stt[0]] not in  ["=", "~"]:
        rgx = re.match(r"([.0-9-]+)(:|(?:\.\.))([.0-9-]+)\}", qst_blk[stt[0]:])
        val, tol = _set_value_tolerance(rgx[2], rgx[1], rgx[3])
        qst.options.append(ANumerical(tol, fraction=100, text=val))
    else:
        rgx = re.compile(r"([=~])(%\d+%)?([.0-9-]+)(:|(?:\.\.))([.0-9-]+)")
        while qst_blk[stt[0]] != "}":
            if qst_blk[stt[0]:stt[0]+4] == "####":
                qst.feedback = _next(stt, qst_blk, ["}"], 1)[4:]
                continue
            txt = _next(stt, qst_blk, ["=", "~", "#", "}"], 1)
            if txt[0] == "#":
                ans.feedback = txt[1:]
                continue
            if txt[0] == "~":          # Wrong answer. Created only to hold a
                frac = val = tol = 0   # feedback. If no feedback.. something
            else:                      # is wrong
                mtc = rgx.match(txt)
                val, tol = _set_value_tolerance(mtc[4], mtc[3], mtc[5])
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
    qst = QShortAnswer(name=name, question=header)   # Moodle does this way,                               # so I will do the same
    for frac, val, fdbk in options:
        qst.options.append(Answer(frac, val, fdbk))
    return qst


def _from_qmultichoice(name: str, header: FText, options: list):
    qst = QMultichoice(name=name, question=header)   # Moodle does this way,                               # so I will do the same
    for frac, val, fdbk in options:
        qst.options.append(Answer(frac, val, fdbk))
    return qst


def _from_block(name: str, header: FText, stt: list, qst_blk: str):
    """ Essay differs to Description only because they have an empty block.
    T/F starts with T or F. Numerical, with #. The others requires identifing
    the type of answers given in the block, except MissingWord and ShortAnswer.
    The only difference between these 2 is that the first has a tail text.
    """
    _nxt(stt, qst_blk)
    if qst_blk[stt[0]] in ["T", "F"]:
        return _from_qtruefalse(name, header, stt, qst_blk)
    if qst_blk[stt[0]] == "#" and qst_blk[stt[0]:stt[0]+4] != "####":
        return _from_qnumerical(name, header, stt, qst_blk)
    options = []
    rgx = re.compile(r"([=~])(%+\d%)?(.+)")
    feedback = ""
    all_equals = True
    while qst_blk[stt[0]] != "}" or stt[1]:
        if qst_blk[stt[0]] in ["=", "~"] and not stt[1]:
            mch = rgx.match(_next(stt, qst_blk, ["=", "~", "#", "}"]))
            all_equals &= mch[1] == "="
            if mch[2]:
                frac = int(mch[2][1:-1])
            elif mch[1] == "~":
                frac = 0
            else:
                frac = 100
            if qst_blk[stt[0]:stt[0]+4] != "####" and qst_blk[stt[0]] == "#":
                fdbk = _next(stt, qst_blk, ["=", "~", "#", "}"])
            else:
                fdbk = ""
            options.append((frac, mch[3], fdbk))
        elif qst_blk[stt[0]:stt[0]+4] == "####":
            feedback = _next(stt, qst_blk, ["}"], 1)[4:]
        else:
            _LOG.info("Char may be incorrectly placed: %s", qst_blk[stt[0]])
            _nxt(stt, qst_blk)
    tail = qst_blk[stt[0]+1:]
    if tail:   
        header.text = f"{header.text}{chr(MARKER_INT)}{tail}"
    if not options:
        question = _from_qessay(name, header)
    elif " -> " in options[0][1]:
        question = _from_qmatching(name, header, options)
    elif all_equals:
        question = _from_qshortanswer(name, header, options)
    else:   # Moodle traits MissingWord as a Multichoice...
        question = _from_qmultichoice(name, header, options)
    question.feedback = feedback
    return question
    

def _from_question(qst_blk: str):
    """Was initially using regex, but it does not handle escaped char in every
    situation so I prefered implementing a char parse. TODO measure performance
    regex was r"(\:\:.+?\:\:)?(\[.+?\])?(.+)(?:(?<!\\)\{(.*)(?<!\\)\})?(.*)?"
    """
    stt = [0, False]   # Used instead of discrete vars cause python fails to 
    name = "default"   # map them to the internal _nxt function
    cformat = TextFormat.AUTO 
    if qst_blk[:2] == "::":
        stt[0] = 3
        while qst_blk[stt[0]:stt[0]+2] != "::" or stt[1]:
            _nxt(stt, qst_blk)
        name = qst_blk[2:stt[0]].replace("\\", "")
        stt[0] += 2
    if qst_blk[stt[0]] == "[":  # The types are limited, so we can consider
        stt[0] += 1              # that if any '\' appears, it should be an
        start = stt[0]           # error anyway.
        while qst_blk[stt[0]] != "]":
            stt[0] += 1
        cformat = TextFormat(qst_blk[start:stt[0]])
        _nxt(stt, qst_blk)
    start = stt[0]
    while stt[0] < len(qst_blk) and qst_blk[stt[0]] != "{" or stt[1]:
        _nxt(stt, qst_blk)
    text = qst_blk[start:stt[0]].replace("\\", "")
    header = FText("questiontext", text.strip("\\"), cformat)
    if stt[0] < len(qst_blk) and qst_blk[stt[0]] == "{":
        result = _from_block(name, header, stt, qst_blk)
    else:
        result = _from_qdescription(name, header)
    return result


def read_gift(cls, file_path: str, comment=None) -> "Category":
    """
    """
    top_quiz: "Category" = cls()
    quiz = top_quiz
    with open(file_path, "r", encoding="utf-8") as ifile:
        for line in ifile:
            tmp = line.strip()
            if not tmp or tmp[:2] == "//":
                continue
            if tmp[:10] == "$CATEGORY:":
                quiz = gen_hier(cls, top_quiz, tmp[10:].strip())
                continue
            for line in ifile:       # TODO Which the best way to do this?
                tmp += line.strip()
                if line == "\n":
                    break
            quiz.add_question(_from_question(tmp))
    return top_quiz


def write_gift(self, file_path: str) -> None:
    """_summary_

    Args:
        file_path (str): _description_
    """
    # TODO
    raise NotImplementedError("Gift not implemented")