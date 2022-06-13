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
from typing import TYPE_CHECKING
from ..questions import QDescription, QEssay, QTrueFalse, QNumerical,\
                        QMissingWord, QMatching, QShortAnswer, QMultichoice
from ..enums import TextFormat
from ..answer import Answer, ANumerical, Subquestion, SelectOption
from ..utils import LineBuffer, FText, gen_hier
if TYPE_CHECKING:
    from ..category import Category


def _from_qdescription(header):
    formatting = TextFormat(header[1][1:-1]) if header[1] else TextFormat.AUTO
    question = FText("questiontext", header[2], formatting, None)
    return QDescription(name=header[0][2:-2], question=question)


def _from_qessay(header: list):
    formatting = TextFormat(header[1][1:-1]) if header else TextFormat.AUTO
    question = FText("questiontext", header[1], formatting, None)
    return QEssay(name=header[0][2:-2], question=question)


def _from_qtruefalse(header: list, answer: list):
    correct = header[3].lower() in ["true", "t"]
    true_ans = Answer(100 if correct else 0, "true", None, TextFormat.AUTO)
    false_ans = Answer(0 if correct else 100, "false", None, TextFormat.AUTO)
    formatting = TextFormat(header[2][1:-1])
    if formatting is None:
        formatting = TextFormat.MD
    qst = QTrueFalse(options=[true_ans, false_ans], name=header[1],
                question=FText("questiontext", header[3], formatting, None))
    for ans in answer:
        if ans[0] == "####":
            qst.feedback = FText("generalfeedback", ans[2],
                                    TextFormat(header[2][1:-1]))
        elif false_ans.feedback is None:
            false_ans.feedback = FText("feedback", ans[2],
                                        TextFormat(header[2][1:-1]))
        else:
            true_ans = FText("feedback", ans[2], TextFormat(header[2][1:-1]))
    return qst


def _from_qnumerical(header: list, answer: list):
    def _extract(data: str) -> tuple:
        rgx = re.match(r"(.+?)(:|(?:\.\.))(.+)", data)
        if rgx[2] == "..":  # Converts min/max to value +- tol
            txt = (float(rgx[1]) + float(rgx[3]))/2
            tol = txt - float(rgx[1])
            txt = str(txt)
        else:
            txt = rgx[1]
            tol = float(rgx[3])
        return txt, tol
    formatting = TextFormat(header[2][1:-1])
    if formatting is None:
        formatting = TextFormat.MD
    qst = QNumerical(name=header[1], question=FText("questiontext", header[3],
                                                    formatting, None))
    if len(answer) == 1:
        txt, tol = _extract(answer[0][2])
        qst.options.append(ANumerical(tol, fraction=100, text=txt,
                                            formatting=TextFormat.AUTO))
    elif len(answer) > 1:
        for ans in answer[1:]:
            if ans[0] == "=":   # Happens first, thus ans is always defined
                txt, tol = _extract(ans[2])
                fraction = float(ans[1][1:-1]) if ans[0] == "=" else 0
                nans = ANumerical(tol, fraction=fraction, text=txt,
                                        formatting=TextFormat.AUTO)
                qst.options.append(nans)
            elif ans[0] == "~":
                nans = ANumerical(0, fraction=0, text="",
                                        formatting=TextFormat.AUTO)
            elif ans[0] == "#":
                nans.feedback = FText("feedback", ans[2], formatting, None)
    return qst


def _from_qmissingword(header: list, answer: list):
    formatting = TextFormat(header[2][1:-1])
    if formatting is None:
        formatting = TextFormat.MD
    qst = QMissingWord(name=header[1], question=FText("questiontext", header[3],
                                                      formatting, None))
    correct = None
    for i in answer:
        if i[0] == "=":
            correct = SelectOption(i[2], 1)
        else:
            qst.options.append(SelectOption(i[2], 1))
    qst.options.insert(0, correct)
    return qst


def _from_qmatching(cls, header: list, answer: list):
    formatting = TextFormat(header[2][1:-1])
    if formatting is None:
        formatting = TextFormat.MD
    qst = QMatching(name=header[1], question=FText("questiontext", header[3],
                                                   formatting, None))
    for ans in answer:
        if ans[0] == "=":
            rgx = re.match(r"(.*?)(?<!\\)->(.*)", ans[2])
            qst.options.append(Subquestion(formatting, rgx[1].strip(),
                                            rgx[2].strip()))
        elif ans[0] == "####":
            qst.feedback = FText("generalfeedback", ans[2], formatting)
    return qst


def _from_qshortanswer(header: list, answer: list):
    formatting = TextFormat(header[2][1:-1])
    if formatting is None:
        formatting = TextFormat.MD
    qst = QShortAnswer(name=header[1], question=FText("questiontext", header[3],
                                                      formatting, None))
    for ans in answer:
        fraction = 100 if not ans[1] else float(ans[1][1:-1])
        qst.options.append(Answer(fraction, ans[2], formatting))
    return qst


def _from_qmultichoice(header: list, answer: list):
    formatting = TextFormat(header[2][1:-1])
    if formatting is None:
        formatting = TextFormat.MD
    qst = QMultichoice(name=header[1], question=FText("questiontext", header[3],
                                                      formatting, None))
    prev_answer = None
    for ans in answer:
        txt = ans[2]
        if ans[0] == "~":  # Wrong or partially correct answer
            fraction = 0 if not ans[1] else float(ans[1][1:-1])
            prev_answer = Answer(fraction, txt, None, formatting)
            qst.options.append(prev_answer)
        elif ans[0] == "=":  # Correct answer
            prev_answer = Answer(100, txt, None, formatting)
            qst.options.append(prev_answer)
        elif ans[0] == "#":  # Answer feedback
            prev_answer.feedback = FText("feedback", ans[2],
                                            formatting, None)
    return qst


def _from_parser(question: str):
    myiter = question.__iter__()
    char = [next(myiter), next(myiter)]
    name = None
    if char == [":", ":"]:
        char.append(next(myiter))
        while char[-2:] != [":", ":"] or char[-3] == "\\":
            char.append(next(myiter))
        name = "".join(char[2:-2]).replace("\\", "")
        char = [next(myiter)]
    if char[1] == "[":
        char += next(myiter)
        while char[-1] != "]" or char[-2] == "\\":
            char += next(myiter)
        cformat = "".join(char[1:-1]).replace("\\", "")
        char = [next(myiter)]
    while char[-1] not in ["{", None] or char[-2] == "\\":
        char = [next(myiter, None)]
    text = "".join(char[1:-1]).replace("\\", "")


def read_gift(cls, file_path: str, comment=None) -> "Category":
    top_quiz = cls()
    quiz = top_quiz
    with open(file_path, "r", encoding="utf-8") as ifile:
        buffer = LineBuffer(ifile)
        while not buffer.eof:
            tmp = buffer.read()
            if not tmp or tmp[:2] == "//":
                continue
            if tmp[:10] == "$CATEGORY:":
                quiz = gen_hier(cls, top_quiz, tmp[10:])
                continue
            tmp = re.match(r"(\:\:.+?\:\:)?(\[.+?\])?(.+)(?:(?<!\\)\{(.*)"
                            r"(?<!\\)\})?(.*)?", buffer.read("\n")).groups()
            if tmp[3] is None:
                question = _from_qdescription(tmp)
            else:
                ans = re.findall(r"((?<!\\)(?:=|~|#))(%[\d\.]+%)?"
                                    r"((?:(?<=\\)[=~#]|[^~=#])*)", tmp[4])
                if not tmp[3]:
                    question = _from_qessay(tmp, ans)
                elif tmp[3][0] in ["T", "F"]:
                    question = _from_qtruefalse(tmp, ans)
                if tmp[3][0] == "#":
                    question = _from_qnumerical(tmp, ans)
                elif tmp[4]:
                    question = _from_qmissingword(tmp, ans)
                elif all(a[0] in ["=", "#", "####"] for a in ans):
                    if re.match(r"(.*?)(?<!\\)->(.*)", ans[0][2]):
                        question = _from_qmatching(tmp, ans)
                    else:
                        question = _from_qshortanswer(tmp, ans)
                else:
                    question = _from_qmultichoice(tmp, ans)
            quiz.add_question(question)


def write_gift(self, file_path: str) -> None:
    """_summary_

    Args:
        file_path (str): _description_
    """
    # TODO
    raise NotImplementedError("Gift not implemented")