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
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Type

from .. import processors as prcs
from ..answer import Choice, ChoicesItem, EntryItem
from ..enums import EmbeddedFormat, Language, Orientation
from ..question import QQuestion
from .text import FText

if TYPE_CHECKING:
    from ..category import Category


_LOG = logging.getLogger(__name__)
_CLOZE_PATTERN = re.compile(r"(?!\\)\{(\d+)?(?:\:(.*?)\:)(.*?(?!\\)\})")


def _parse_mc(opts: dict, feeds: list, _type: EmbeddedFormat):
    tmp = ChoicesItem(feeds)
    res = {}
    if _type in (EmbeddedFormat.MR, EmbeddedFormat.MC):
        tmp.orientation = Orientation.VER
    for idx, (key, val) in enumerate(opts.items()):
        tmp.options.append(Choice(key))
        res[idx] = val
    tmp.processor = prcs.Proc(prcs.mapper, res)
    return tmp


def _parse_sa(opts: dict, feeds: list, _type: EmbeddedFormat):
    tmp = EntryItem(feeds)
    func = prcs.mapper if _type == EmbeddedFormat.SA else prcs.mapper_nocase
    tmp.processor = prcs.Proc(func, opts)
    return tmp


def _parse_num(opts: dict, feeds: list, _):
    tmp = EntryItem(feeds)
    tmp.processor = prcs.Proc(prcs.numerical_range, opts)
    return tmp


OPTIONS = {
    EmbeddedFormat.MC : _parse_mc,
    EmbeddedFormat.MCH : _parse_mc,
    EmbeddedFormat.MR : _parse_mc,
    EmbeddedFormat.MRH : _parse_mc,
    EmbeddedFormat.NUM : _parse_num,
    EmbeddedFormat.SA : _parse_sa,
    EmbeddedFormat.SAC : _parse_sa,
}

def _from_cloze_text(data: str, lang: Language, embedded_name: bool):
    """Return a tuple with the Marked text and the data extracted.
    """
    if embedded_name:
        name, text = data.split("\n", 1)
    else:
        name = "Cloze"
        text = data
    question = QQuestion({lang: name})
    start = 0
    for imatch in _CLOZE_PATTERN.finditer(text):
        opts = {}
        feeds = []
        fmt = EmbeddedFormat(imatch[2])
        grade, parser = int(imatch[1]), OPTIONS[fmt]
        for idx, opt in enumerate(imatch[3].split("~")):
            if not opt:
                continue
            tmp = opt.strip("}~").split("#")
            if len(tmp) == 2:
                tmp, fdb = tmp
            else:
                tmp, fdb = tmp[0], ""
            frac = 0.0
            if tmp[0] == "=":
                frac = grade
                tmp = tmp[1:]
            elif tmp[0] == "%":
                frac, tmp = tmp[1:].split("%")
                frac = float(frac)*grade/100
            feedback = FText()
            feedback.text.append(fdb)
            if fmt == EmbeddedFormat.NUM:
                tmp = tuple(map(float, tmp.split(":")))
                tmp = (tmp[0]-tmp[1], tmp[0]+tmp[1])
            opts[tmp] = {"value": frac, "feedback": idx}
            feeds.append(feedback)
        question.body[lang].text.append(text[start: imatch.start()])
        question.body[lang].text.append(parser(opts, feeds, fmt))
        start = imatch.end()
    question.body[lang].text.append(text[start:])
    return question


# -----------------------------------------------------------------------------


def _get_format(item: ChoicesItem|EntryItem):
    if isinstance(item, EntryItem):
        if len(next(iter(item.processor.args))) == 2:
            return EmbeddedFormat.NUM
        for key, value in item.processor.args.items():
            if value != 0:
                if item.processor.func(key.upper())["value"] == 0:
                    fmt = EmbeddedFormat.SAC
                else:
                    fmt = EmbeddedFormat.SA
                break
        else:
            fmt = EmbeddedFormat.SA
    else:
        if item.max_choices > 1:
            if item.orientation == Orientation.HOR:
                fmt = EmbeddedFormat.MRH
            else:
                fmt = EmbeddedFormat.MR
        else:
            if item.orientation == Orientation.HOR:
                fmt = EmbeddedFormat.MCH
            else:
                fmt = EmbeddedFormat.MC
    return fmt


def _get_options(item: ChoicesItem|EntryItem, grade: float, fmt: EmbeddedFormat):
    def to_item(key, value):
        feed = item.feedbacks[value['feedback']] if 'feedback' in value else ''
        if fmt == EmbeddedFormat.NUM:
            key = f"{sum(key)/2}:{round((key[1] - key[0])/2, 4)}"
        if value["value"] == grade:
            return f"~={key}#{feed.get()}"
        if value["value"] == 0:
            return f"~{key}#{feed.get()}"
        tmp = int(value['value']/grade*100)
        return f"~%{tmp}%{key}#{feed.get()}"
    text = ""
    if isinstance(item, EntryItem):
        for key, value in item.processor.args.items():
            text += to_item(key, value)
    else:
        for idx, opt in enumerate(item.options):
            text += to_item(str(opt), item.processor.func(idx))
    return text

def _to_cloze_text(buffer, qst: QQuestion, embedded_name: bool, lang: Language):
    """Return the text formatted as expected by the end-tool, which is
    currently only moodle.
    """
    if embedded_name:
        buffer.write(qst.name[lang] + "\n")
    for item in qst.body[lang].text:
        if isinstance(item, str):
            buffer.write(item)
        elif isinstance(item, (ChoicesItem, EntryItem)):
            grade = max(a["value"] for a in item.processor.args.values())
            fmt = _get_format(item)
            text = _get_options(item, grade, fmt)
            text = "{" + f"{grade}:{fmt.value}:" + text[1:] + "}"
            buffer.write(text)


# -----------------------------------------------------------------------------


def read_cloze(cls: Type[Category], file_path: str, lang: Language,
               multiquestion=None, embedded_name=False) -> Category:
    """_summary_
    Args:
        cls (Type[Category]): _description_
        file_path (str): _description_
        embedded (bool, optional): _description_. Defaults to False.
    Returns:
        Category: _description_
    """
    top_quiz = cls()
    with open(file_path, "r", encoding="utf-8") as buffer:
        data = buffer.read()
        if multiquestion is not None:
            for text in data.split(multiquestion):
                top_quiz.add_question(_from_cloze_text(text, lang, embedded_name))
        else:
            top_quiz.add_question(_from_cloze_text(data, lang, embedded_name))
    _LOG.info(f"Created new Quiz instance from cloze file {file_path}")
    return top_quiz


def write_cloze(cat: Category, file_path: str, lang: Language,
                multiquestion=None, embedded_name=False):
    """_summary_
    Args:
        file_path (str): _description_
    """
    def _to_cloze(buffer, _cat: Category, _cnt: int):
        for item in _cat.questions:
            if multiquestion is not None:
                _to_cloze_text(buffer, item, embedded_name, lang)
                buffer.write(multiquestion)
            else:
                name = f"{file_path.rsplit('.', 1)[0]}__cnt.cloze"
                with open(name, "w", encoding="utf-8") as ofile:
                    _to_cloze_text(ofile, item, embedded_name, lang)
                _cnt += 1
        for child in _cat:
            _cnt = _to_cloze(buffer, _cat[child], _cnt)
        return _cnt
    if multiquestion is not None:
        with open(file_path, "w", encoding="utf-8") as ofile:
            _to_cloze(ofile, cat, 0)
    else:
        _to_cloze(None, cat, 0)
