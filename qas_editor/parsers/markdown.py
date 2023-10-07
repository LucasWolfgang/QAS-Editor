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
"""
import re

from ..enums import TextFormat
from ..question import QMultichoice
from ..answer import Answer
from .text import FText


class DefaultMD:

    PFX = "mk_"
    ANS = r"\s*-\s+(!)?(.*)"
    QST = r"\s*\*\s+(.*)"
    CAT = r"\s*#\s+(.*)"

    @staticmethod
    def gen_hier(cls, top, category: str):
        cat_list = category.strip().split("/")
        quiz = top
        for i in cat_list:
            quiz.add_subcat(cls(i))
            quiz = quiz[i]
        return quiz


# ----------------------------------------------------------------------------


def _from_QMultichoice(lines: list, form: DefaultMD, name: str):
    data = ""
    match = re.match(form.ANS, lines[-1])
    while lines and match is None:
        data += lines.pop().strip()
        match = re.match(form.ANS, lines[-1])
    text = FText(data,  TextFormat.MD, None)
    question = QMultichoice(name=name, question=text)
    regex_exp = f"({form.QST})|({form.ANS})"
    while lines:
        match = re.match(regex_exp, lines.pop())
        if match and match[3]:
            ans = Answer(100.0 if match[4] is not None else 0.0, match[5],
                         None, TextFormat.HTML)
            question.options.append(ans)
        else:
            break
    return question


# ----------------------------------------------------------------------------


def read_markdown(cls, file_path: str, form: DefaultMD, category="$course$"):
    """[summary]
    Args:
        file_path (str): [description]
        question_mkr (str, optional): [description].
        answer_mkr (str, optional): [description].
        category_mkr (str, optional): [description].

    Raises:
        ValueError: [description]
    """
    with open(file_path, encoding="utf-8") as infile:
        lines = infile.readlines()
    lines.append("\n")
    lines.append("\n")
    lines.reverse()
    cnt = 0
    top_quiz = cls(category)
    quiz = top_quiz
    while lines:
        match = re.match(f"({form.CAT})|({form.QST})|({form.ANS})", lines[-1])
        if match:
            if match[1]:
                quiz = form.gen_hier(top_quiz, match[2])
                lines.pop()
            elif match[3]:
                if quiz is None:
                    raise ValueError("No classification defined")
                _from_QMultichoice(lines, form, f"{form.PFX}_{cnt}")
                cnt += 1
            elif match[5]:
                raise ValueError(f"Answer found out of a question "
                                 f"block: {match[5]}.")
        else:
            lines.pop()
    return top_quiz


def write_markdown(self, file_path: str) -> None:
    """_summary_

    Args:
        file_path (str): _description_

    Raises:
        NotImplementedError: _description_
    """
    raise NotImplementedError("Markdown not implemented")
