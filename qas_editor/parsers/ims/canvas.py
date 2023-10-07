"""
Question and Answer Sheet Editor <https://github.com/LucasWolfgang/QAS-Editor>
Copyright (C) 2023  Lucas Wolfgang

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
from typing import TYPE_CHECKING
import logging
import random
from xml.etree import ElementTree as et
from ... import _LOG
from ...question import QQuestion
from ...answer import Item
from ..text import Var, FText
from .imscc import CC
if TYPE_CHECKING:
    from ...category import Category

_LOG = logging.getLogger()

class _CanvasImporter:

    _QREF = None

    def __init__(self, ns: dict = None, cat: Category = None):
        self._ns = ns
        self._cat = cat

    def _get_response_lid(self, body: et.Element):
        item = Item()
        for tmp in body.findall("./response_lid/render_choice/response_label", self._ns):
            tmap =  {"[": get_canvas_vars}
            text = tmp.find("material/mattext", self._ns)
            if text.get("texttype") == "text/html":
                tmap["<"] = "_get_tag"
            ans = FText.from_string(text.text, files=self._cat.resources, tagmap=tmap)
            item.options[tmp.get("ident")] = ans
        return item

    def _get_processings(self, item: et.Element):
        for id in item.findall(".//respcondition[@continue='No']/conditionvar/varequal", self._ns):
            correct_answers.append(id.text)

    def _parse_calculated(self, xml: et.ElementTree):
        """ Return an array of possible answers and their variable substitution """
        var_sets = []
        tolerance = 0
        try:
            if xml.find("answer_tolerance", self._ns) is not None:
                tolerance = xml.find("answer_tolerance", self._ns)
            for xml_var_set in xml.findall(".//var_set", self._ns):
                this_var_set = {
                    'id': xml_var_set.get("ident"),
                    'value': xml_var_set.find("answer").text,
                    'text': "",
                    'display': True,
                    'correct': True,
                    'tolerance': tolerance,
                    'variable': []
                }
                for xml_var_set_variable in xml_var_set.findall(".//var"):
                    this_var_set['variable'].append({
                        'name': xml_var_set_variable.get("name"),
                        'value': xml_var_set_variable.text
                    })
                    if this_var_set['text'] == "":
                        this_var_set['text'] = xml_var_set_variable.get("name") + " = " + xml_var_set_variable.text
                    else:
                        this_var_set['text'] = this_var_set['text'] + ", " + xml_var_set_variable.get("name") + " = " + xml_var_set_variable.text
                var_sets.append(this_var_set)  
        except OSError as e:
            _LOG.error("%s", e)
        except et.ParseError as e:
            _LOG.error("XML parser error: %s", e)
        return var_sets

    def _parse_fill_in_multiple_blanks(self, xml: et.ElementTree, qst: QQuestion):
        """ Return an array of possible answers """
        qst.body.parse(xml.find("presentation/material/mattext", self._ns).text,
                            {"[": get_canvas_vars})
        answers = []
        correct_answers = []
        for id in xml.findall(".//varequal", self._ns):
            correct_answers.append(id.text)
        try:
            for xml_answer_item in xml.findall(".//response_label", self._ns):
                this_answer = {}
                this_answer['id'] = xml_answer_item.get("ident")
                this_answer['text'] = xml_answer_item.find("material/mattext").text
                this_answer['correct'] = True if xml_answer_item.get("ident") in correct_answers else False
                this_answer['display'] = False
                answers.append(this_answer)
        except OSError as e:
            _LOG.error("%s", e)
        except et.ParseError as e:
            _LOG.error("XML parser error: %s", e)
        return answers

    def _parse_matching(self, xml: et.Element):
        """ Return an array of items and possible answers """
        answers = []
        correct_answer = {}
        for id in xml.findall(".//varequal", self._ns):
            correct_answer[id.get("respident")] = id.text
        try:
            for xml_response_lid in xml.findall(".//response_lid", self._ns):
                this_response_lid = {
                    'id': xml_response_lid.get("ident"),
                    'text': xml_response_lid.find("./material/mattext").text,
                    'display': True,
                    'options': []
                }
                for xml_option in xml_response_lid.findall(".//response_label"):
                    this_option = {}
                    this_option['id'] = xml_option.get("ident")
                    this_option['text'] = xml_option.find("material/mattext").text
                    this_option['display'] = True
                    this_option['correct'] = True if this_response_lid['id'] in correct_answer and correct_answer[this_response_lid['id']] == xml_option.get("ident") else False
                    this_response_lid['options'].append(this_option)
                if self.matching_random_shuffle_answer_options:
                    random.shuffle(this_response_lid['options']) 
                answers.append(this_response_lid)
        except OSError as e:
            _LOG.error("%s", e)
        except et.ParseError as e:
            _LOG.error("XML parser error: %s", e)
        if self.matching_random_shuffle_answers:
            random.shuffle(answers)
        return answers

    def _parse_multiple_answers(self, xml: et.Element):
        """ Return an array of possible answers """
        answers = []
        correct_answers = []
        for id in xml.findall(".//conditionvar/and/varequal", self._ns):
            correct_answers.append(id.text)
        try:
            for xml_answer_item in xml.findall(".//response_label", self._ns):
                answers.append(
                    {
                        'id': xml_answer_item.get("ident"),
                        'text': xml_answer_item.find("material/mattext").text,
                        'correct': True if xml_answer_item.get("ident") in correct_answers else False,
                        'display': True
                    }
                )
        except OSError as e:
            _LOG.error("%s", e)
        except et.ParseError as e:
            _LOG.error("XML parser error: %s", e)
        return answers

    def _parse_multiple_dropdowns(self, xml: et.Element, qst: QQuestion):
        """ Return an array of possible answers, grouped for each blank """
        qst.body.from_string(xml.find("presentation/material/mattext", self._ns).text,
                             {"[": get_canvas_vars})
        answers_group = []
        correct_answer = {}
        for id in xml.findall(".//varequal"):
            correct_answer[id.get("respident")] = id.text
        try:
            for lid in xml.findall(".//response_lid", self._ns):
                answers = []
                for xml_answer_item in lid.findall(".//response_label"):
                    this_answer = {}
                    this_answer['id'] = xml_answer_item.get("ident")
                    this_answer['text'] = xml_answer_item.find("material/mattext").text
                    this_answer['correct'] = True if lid.get("ident") in correct_answer and correct_answer[lid.get("ident")] == this_answer['id'] else False
                    this_answer['display'] = True
                    answers.append(this_answer)
                answers_group.append({
                    'group_id': lid.get("ident"),
                    'options': answers
                })
        except OSError as e:
            _LOG.error("%s", e)
        except et.ParseError as e:
            _LOG.error("XML parser error: %s", e)
        return answers_group

    def _parse_multiple_choice(self, item: et.Element, qst: QQuestion):
        """ Return an array of possible answers """
        body = item.find("presentation", self._ns)
        qst.body.from_string(body.find("material/mattext", self._ns).text)
        self._get_processings(item)
        self._get_response_lid(body)

    def _parse_numerical(self, xml: et.Element):
        """ Return an array of possible answers """
        answers = []
        i = 0
        try:
            for xml_cond in xml.findall(".//conditionvar", self._ns):
                i += 1
                value, minvalue, maxvalue = None, None, None
                if xml_cond.find("or/varequal") is not None:
                    value = xml_cond.find("or/varequal").text
                    minvalue = value
                    maxvalue = value
                if xml_cond.find("or/and") is not None:
                    xml_cond_range = xml_cond.find("or/and")
                if xml_cond.find("vargte") is not None or xml_cond.find("varlte") is not None:
                    xml_cond_range = xml_cond
                if xml_cond_range.find("vargte") is not None:
                    minvalue = xml_cond_range.find("vargte").text
                elif xml_cond_range.find("vargt") is not None:
                    minvalue = xml_cond_range.find("vargt").text
                if xml_cond_range.find("varlte") is not None:
                    maxvalue = xml_cond_range.find("varlte").text
                elif xml_cond_range.find("varlt") is not None:
                    maxvalue = xml_cond_range.find("varlt").text
                this_answer = {}
                this_answer['id'] = str(i)
                if value is not None:
                    this_answer['value'] = value
                if minvalue is not None:
                    this_answer['minvalue'] = minvalue
                if maxvalue is not None:
                    this_answer['maxvalue'] = maxvalue
                this_answer['correct'] = True
                this_answer['display'] = False
                answers.append(this_answer)
        except OSError as e:
            _LOG.error("%s", e)
        except et.ParseError as e:
            _LOG.error("XML parser error: %s", e)
        return answers

    def _parse_short_answer(self, xml: et.Element):
        """ Return an array of possible answers """
        answers = []
        i = 0
        try:
            for xml_answer_item in xml.findall(".//varequal", self._ns):
                i += 1
                answers.append(
                    {
                        'id': str(i),
                        'text': xml_answer_item.text,
                        'correct': True,
                        'display': False
                    }
                )
        except OSError as e:
            _LOG.error("%s", e)
        except et.ParseError as e:
            _LOG.error("XML parser error: %s", e)
        return answers

    def _parse_true_false(self, xml: et.Element):
        """ Return an array of possible answers """
        answers = []
        correct_answers = []
        for id in xml.findall(".//varequal", self._ns):
            correct_answers.append(id.text)

        try:
            for xml_answer_item in xml.findall(".//response_label", self._ns):
                answers.append(
                    {
                        'id': xml_answer_item.get("ident"),
                        'text': xml_answer_item.find("material/mattext").text,
                        'correct': True if xml_answer_item.get("ident") in correct_answers else False,
                        'display': True
                    }
                )
        except OSError as e:
            _LOG.error("%s", e)
        except et.ParseError as e:
            _LOG.error("XML parser error: %s", e)
        return answers

    def read(self, item: et.Element):
        meta = {}
        for item in item.findall("itemmetadata/qtimetadata/qtimetadatafield", self._ns):
            key = item.find("fieldlabel", self._ns).text
            meta[key] = item.find("fieldentry", self._ns).text
        if "cc_profile" in meta:
            qtype = _QTYPE_CC[meta["cc_profile"]]
        elif "question_type" in meta:
            qtype = _QTYPE_CP[meta["question_type"]]
        elif "cc_profile" in meta:
            qtype = _QTYPE_RS[meta["respondusapi_qtype"]]
        else:
            raise KeyError
        question = QQuestion(item.get("title"), item.get("ident"))
        question.points = meta["points_possible"]
        getattr(self, qtype)(item, question)
        return question


def get_canvas_vars(self):
    """Function to be passed to FText. Self will be FText
    Returns:
        Var: a variable
    """
    while self.text[self.stt[0]] == "]" and not self.stt[1]:
        self._nxt()
    return Var(self.text[self.stt[2]: self.stt[0]])


_QTYPE_CC = {
    "cc.multiple_choice.v0p1": "_parse_multiple_choice",
    "cc.true_false.v0p1": "_parse_true_false",
    "cc.multiple_response.v0p1": "_parse_multiple_answers",
    "cc.essay.v0p1": "",
}

_QTYPE_CP = {
    "multiple_choice_question": "_parse_multiple_choice",
    "true_false_question": "_parse_true_false",
    "multiple_answers_question": "_parse_multiple_answers",
    "short_answer_question": "_parse_short_answer",
    "fill_in_multiple_blanks_question": "_parse_fill_in_multiple_blanks",
    "multiple_dropdowns_question": "_parse_multiple_dropdowns",
    "matching_question": "_parse_matching",
    "numerical_question": "_parse_numerical",
    "calculated_question": "_parse_calculated"
}

_QTYPE_RS = {
    "multipleChoice": "_parse_multiple_choice",
    "trueFalse": "_parse_true_false",
    "multipleResponse": "_parse_multiple_answers",
    "essay": "",
    "fillInMultiple": "_parse_fill_in_multiple_blanks",
    "matching": "_parse_matching",
    "numerical": "_parse_numerical"
}


# -----------------------------------------------------------------------------


def read_cc_canvas(self: Category, filename: str) -> Category:
    """Read data out of the manifest and store it in data
    Args:
        file_path (str): _description_
    """
    qti = _CanvasImporter()
    parser = CC(filename, qti.read, self)
    parser.read()
