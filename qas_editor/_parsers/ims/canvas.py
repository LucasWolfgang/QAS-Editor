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
from typing import TYPE_CHECKING
import re
import logging
import random
import hashlib
from xml.etree import ElementTree as et
from ... import _LOG
from .imscc import CC
if TYPE_CHECKING:
    from ...category import Category

_LOG = logging.getLogger()


class _CanvasImporter:

    _QREF = None

    def __init__(self):
        self._ns = None

    def _enumerate_blanks(self, text: str) -> str:
        """ Clarify blanks with index in question text """
        start = 0
        counter = 1
        newstring = ""
        blank_regex = r"(" + self.blanks_replace_str * self.blanks_question_n + ")"
        for m in re.finditer(blank_regex, text):
            end, newstart = m.span()
            newstring += text[start:end]
            rep = m.group(1).upper() + " <sup>" + str(counter) + "</sup>"
            newstring += rep
            start = newstart
            counter += 1
        return newstring

    @staticmethod
    def _substitute_variables_in_question(text: str, answer: dict) -> str:
        """ Clarify variable placeholders in question text """
        start = 0
        newstring = ""
        placeholder_regex = r"\[(.*?)\]"
        for m in re.finditer(placeholder_regex, text):
            end, newstart = m.span()
            newstring += text[start:end]
            for var in answer['variable']:
                if var['name'] == m.group(1):
                    rep = var['value']
            newstring += rep
            start = newstart
        return newstring

    def _parse_calculated(self, xml: et.ElementTree):
        """ Return an array of possible answers and their variable substitution """
        var_sets = []
        tolerance = 0
        try:
            if xml.find("ims:answer_tolerance") is not None:
                tolerance = xml.find("ims:answer_tolerance")
            for xml_var_set in xml.findall(".//ims:var_set"):
                this_var_set = {
                    'id': xml_var_set.get("ident"),
                    'value': xml_var_set.find("ims:answer").text,
                    'text': "",
                    'display': True,
                    'correct': True,
                    'tolerance': tolerance,
                    'variable': []
                }
                for xml_var_set_variable in xml_var_set.findall(".//ims:var"):
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

    def _parse_fill_in_multiple_blanks(xml: et.ElementTree):
        """ Return an array of possible answers """
        answers = []
        correct_answers = []
        for id in xml.findall(".//ims:varequal"):
            correct_answers.append(id.text)
        try:
            for xml_answer_item in xml.findall(".//ims:response_label"):
                this_answer = {}
                this_answer['id'] = xml_answer_item.get("ident")
                this_answer['text'] = xml_answer_item.find("ims:material/ims:mattext").text
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
        for id in xml.findall(".//ims:varequal"):
            correct_answer[id.get("respident")] = id.text
        try:
            for xml_response_lid in xml.findall(".//ims:response_lid"):
                this_response_lid = {
                    'id': xml_response_lid.get("ident"),
                    'text': xml_response_lid.find("./ims:material/ims:mattext").text,
                    'display': True,
                    'options': []
                }
                for xml_option in xml_response_lid.findall(".//ims:response_label"):
                    this_option = {}
                    this_option['id'] = xml_option.get("ident")
                    this_option['text'] = xml_option.find("ims:material/ims:mattext").text
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
        for id in xml.findall(".//ims:conditionvar/ims:and/ims:varequal"):
            correct_answers.append(id.text)
        try:
            for xml_answer_item in xml.findall(".//ims:response_label"):
                answers.append(
                    {
                        'id': xml_answer_item.get("ident"),
                        'text': xml_answer_item.find("ims:material/ims:mattext").text,
                        'correct': True if xml_answer_item.get("ident") in correct_answers else False,
                        'display': True
                    }
                )
        except OSError as e:
            _LOG.error("%s", e)
        except et.ParseError as e:
            _LOG.error("XML parser error: %s", e)
        return answers

    def _parse_multiple_dropdowns(self, xml: et.Element):
        """ Return an array of possible answers, grouped for each blank """
        answers_group = []
        correct_answer = {}
        for id in xml.findall(".//ims:varequal"):
            correct_answer[id.get("respident")] = id.text
        try:
            for xml_response_lid in xml.findall(".//ims:response_lid"):
                answers = []
                for xml_answer_item in xml_response_lid.findall(".//ims:response_label"):
                    this_answer = {}
                    this_answer['id'] = xml_answer_item.get("ident")
                    this_answer['text'] = xml_answer_item.find("ims:material/ims:mattext").text
                    this_answer['correct'] = True if xml_response_lid.get("ident") in correct_answer and correct_answer[xml_response_lid.get("ident")] == this_answer['id'] else False
                    this_answer['display'] = True
                    answers.append(this_answer)

                answers_group.append({
                    'group_id': xml_response_lid.get("ident"),
                    'options': answers
                })
        except OSError as e:
            _LOG.error("%s", e)
        except et.ParseError as e:
            _LOG.error("XML parser error: %s", e)
        return answers_group

    def _parse_multiple_choice(self, xml: et.Element):
        """ Return an array of possible answers """
        answers = []
        correct_answers = []
        for id in xml.findall(".//ims:respcondition[@continue='No']/ims:conditionvar/ims:varequal"):
            correct_answers.append(id.text)
        try:
            for xml_answer_item in xml.findall(".//ims:response_label"):
                image = []
                this_answer = {}
                this_answer['id'] = xml_answer_item.get("ident")
                this_answer['text'] = xml_answer_item.find("ims:material/ims:mattext").text
                this_answer['correct'] = True if xml_answer_item.get("ident") in correct_answers else False
                this_answer['display'] = True
                if this_answer['text'].lower().find("<img.*"):
                    for match in re.finditer('^<img src="([^"]+)".*>', this_answer['text'], re.DOTALL):
                        image.append({
                            'id': str(hashlib.md5(match.group(1).replace(self.img_href_ims_base, "").encode()).hexdigest()),
                            'href': match.group(1).replace(self.img_href_ims_base, "")
                        })
                    p = re.compile('<img src="([^"]+)".*>')
                    subn_tuple = p.subn('', this_answer['text'])
                    if subn_tuple[1] > 0:
                        this_answer['text'] = subn_tuple[0]
                if image:
                    this_answer['image'] = image
                answers.append(this_answer)
        except OSError as e:
            _LOG.error("%s", e)
        except et.ParseError as e:
            _LOG.error("XML parser error: %s", e)
        return answers

    def _parse_numerical(self, xml: et.Element):
        """ Return an array of possible answers """
        answers = []
        i = 0
        try:
            for xml_cond in xml.findall(".//ims:conditionvar"):
                i += 1
                value, minvalue, maxvalue = None, None, None
                if xml_cond.find("ims:or/ims:varequal") is not None:
                    value = xml_cond.find("ims:or/ims:varequal").text
                    minvalue = value
                    maxvalue = value
                if xml_cond.find("ims:or/ims:and") is not None:
                    xml_cond_range = xml_cond.find("ims:or/ims:and")
                if xml_cond.find("ims:vargte") is not None or xml_cond.find("ims:varlte") is not None:
                    xml_cond_range = xml_cond
                if xml_cond_range.find("ims:vargte") is not None:
                    minvalue = xml_cond_range.find("ims:vargte").text
                elif xml_cond_range.find("ims:vargt") is not None:
                    minvalue = xml_cond_range.find("ims:vargt").text
                if xml_cond_range.find("ims:varlte") is not None:
                    maxvalue = xml_cond_range.find("ims:varlte").text
                elif xml_cond_range.find("ims:varlt") is not None:
                    maxvalue = xml_cond_range.find("ims:varlt").text
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
            for xml_answer_item in xml.findall(".//ims:varequal"):
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
        for id in xml.findall(".//ims:varequal"):
            correct_answers.append(id.text)

        try:
            for xml_answer_item in xml.findall(".//ims:response_label"):
                answers.append(
                    {
                        'id': xml_answer_item.get("ident"),
                        'text': xml_answer_item.find("ims:material/ims:mattext").text,
                        'correct': True if xml_answer_item.get("ident") in correct_answers else False,
                        'display': True
                    }
                )
        except OSError as e:
            _LOG.error("%s", e)
        except et.ParseError as e:
            _LOG.error("XML parser error: %s", e)
        return answers

    def read(self, item: et.Element, ns: dict):
        raise NotImplementedError


class _CanvasCPImporter(_CanvasImporter):

    def read(self, item: et.Element, ns: dict):
        raise NotImplementedError


_QTYPE = {
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


def _read_cc(self, item: et.Element, ns: dict):
    meta = item.find("itemmetadata/qtimetadata", ns)
    qtype = meta.find("qtimetadatafield[fieldlabel = 'question_type']" +
                    "/fieldentry", self._ns).text
    this_question = {
        'id': str(item.get("ident")),
        'title': str(item.get("title")),
        'points_possible': meta.find("qtimetadatafield[fieldlabel = point"+
                                    "'s_possible']/fieldentry", self._ns).text
    }
    image = []

    item.find("presentation/material/mattext").text
    if this_question['text'].lower().find("<p>.*<img"):
        for match in re.finditer('<p>.*<img.+src=\"([^\"]+)\".*>.*</p>', this_question['text'], re.DOTALL):
            this_href = re.sub(r"\?.+$", "", match.group(1)).replace(self.img_href_ims_base, "")
            image.append({
                'id': str(hashlib.md5(this_href.encode()).hexdigest()),
                'href': this_href
            })
        p = re.compile('<p>.*<img.+src=\"([^\"]+)\".*>.*</p>')
        subn_tuple = p.subn('', this_question['text'])
        if subn_tuple[1] > 0:
            this_question['text'] = subn_tuple[0]
    elif this_question['text'].lower().find("<img"):
        for match in re.finditer('<img.+src=\"([^\"]+)\".*>', this_question['text'], re.DOTALL):
            this_href = re.sub(r"\?.+$", "", match.group(1)).replace(self.img_href_ims_base, "")
            image.append({
                'id': str(hashlib.md5(this_href.encode()).hexdigest()),
                'href': this_href
            })
        p = re.compile('<img.+src=\"([^\"]+)\".*>')
        subn_tuple = p.subn('', this_question['text'])
        if subn_tuple[1] > 0:
            this_question['text'] = subn_tuple[0]
    if image:
        this_question['image'] = image
    # Parse answers for each type of question
    
    # Replace [variable] in question text with blanks
    if (this_question['question_type'] == "fill_in_multiple_blanks_question" or this_question['question_type'] == "multiple_dropdowns_question") and this_question['text'].find(r"\[(.*?)\]"):
        blank = self.blanks_replace_str * self.blanks_question_n
        p = re.compile(r"\[(.*?)\]")
        subn_tuple = p.subn(blank, this_question['text'])
        if subn_tuple[1] > 0:
            this_question['text'] = subn_tuple[0]
        if this_question['question_type'] == "multiple_dropdowns_question":
            this_question['text'] = self._enumerate_blanks(this_question['text'])
    if this_question['question_type'] == "calculated_question":
        if self.calculated_display_var_set_in_text:
            this_question['text'] = self._substitute_variables_in_question(this_question['text'], this_question['answer'][0])
    return this_question


def _read_cp(self, item: et.Element, ns: dict):
    meta = item.find("itemmetadata/qtimetadata", ns)
    qtype = meta.find("qtimetadatafield[fieldlabel = 'question_type']" +
                    "/fieldentry", self._ns).text


# -----------------------------------------------------------------------------


def read_cc_canvas(self, filename: str) -> "Category":
    """Read data out of the manifest and store it in data
    Args:
        file_path (str): _description_
    """
    parser = CC(filename, {"IMS Common Cartridge": _read_cc})
    parser.read()
