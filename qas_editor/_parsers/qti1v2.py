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
from typing import TYPE_CHECKING, Dict
from random import shuffle
from xml.etree import ElementTree as et
from xml.dom import minidom
import tarfile
import zipfile
import logging
import hashlib
import re

_LOG = logging.getLogger(__name__)

class QTIParser1v2:
    """ Parse QTI 1.2 """

    # String in img href to remove from XML
    img_href_ims_base = "%24IMS-CC-FILEBASE%24/"

    # Character to replace [blanks] in questions with
    blanks_replace_str = "_"

    # Number of replace characters in question text
    blanks_question_n = 10

    # Number of characters in answer line template
    blanks_answer_n = 80

    # Random shuffle of answers in type "Matching Question"
    matching_random_shuffle_answers = True
    matching_random_shuffle_answer_options = True

    # If True, replace first set of variables in question text instead of displaying options
    calculated_display_var_set_in_text = False
    
    NAMESPACE = "http://www.imsglobal.org/xsd/ims_qtiasiv1p2"

    def read(self, file_path):
        data = {}
        """ Read data out of the manifest and store it in data """
        if tarfile.is_tarfile(file_path):
            with tarfile.open(file_path, 'r:gz') as tar:
                manifest = et.parse(tar.extractfile("imsmanifest.xml"))
        else:
            with zipfile.ZipFile(file_path, "r") as ifile:
                manifest = et.parse(ifile.extract("imsmanifest.xml"))

        qti_resource = {
            'assessment': []
        } 

        for xml_resource in manifest.getroot().findall(".//{http://www.imsglobal.org/xsd/imsccv1p1/imscp_v1p1}resource[@type='imsqti_xmlv1p2']"):
            this_assessment = {
                'id': xml_resource.get("identifier"),
                'metadata': self.get_metadata(xml_resource.get("identifier") + "/" + "assessment_meta.xml"),
                'question': []
            }

            # TODO: Should be prefixed with PATH part of input filename since paths in XML are relative
            this_assessment_xml = this_assessment['id'] + "/" + this_assessment['id'] + ".xml"

            for xml_item in et.parse(this_assessment_xml).getroot().findall(".//{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}item"):
                this_assessment['question'].append(self.get_question(xml_item))
            qti_resource['assessment'].append(this_assessment)


        self.readManifest(manifest)
        return data

    def readManifest(self, elem: et.ElementTree, data):
        assessment = elem.find('assessment')
        if assessment:
            data['title'] = assessment[0].get('title')
            sections = assessment[0].find('section')
            for s in sections:
                items = s.find('item')
                data['items'] = {}
                data['itemorder'] = []
                for i in items:
                    self.readItem(i, data['items'], data['itemorder'])

    def readItem(self, item, data, order):
        pass


class BB(QTIParser1v2):
    """ Parse QTI 1.2 """

    def readItem(self, item, data, order):
        """ Read an item out of the manifest. """
        itemid = item.getAttribute('ident')
        if itemid:
            order.append(itemid)
            data[itemid] = {}
            itemtitle = item.getAttribute('title')
            if itemtitle:
                data[itemid]['title'] = itemtitle
            self.readItemMetadata(item, data[itemid])
            self.readPresentation(item, data[itemid])
            self.readProcessingInfo(item, data[itemid])
        
    def readItemMetadata(self, item, data):
        """ Read the item's metadata """
        metadata = item.getElementsByTagName('qtimetadata')
        for m in metadata:
            fields = m.getElementsByTagName('qtimetadatafield')
            for f in fields:
                flabel = f.getElementsByTagName('fieldlabel')
                if flabel:
                    label = self.getTextValue(flabel[0])
                    fentry = f.getElementsByTagName('fieldentry')
                    if fentry:
                        entry = self.getTextValue(fentry[0])
                        if label:
                            if 'qmd_questiontype' == label:
                                if 'Multiple-choice' == entry:
                                    data['questiontype'] = 'Multiple Choice'
                                if 'Multiple-response' == entry:
                                    data['questiontype'] = 'Multiple Answer'
                                if 'True/false' == entry:
                                    data['questiontype'] = 'True/False'
                                if 'FIB-string' == entry:
                                    data['questiontype'] = 'Essay'
                            elif 'cc_profile' == label:
                                if 'cc.multiple_choice.v0p1' == entry:
                                    data['questiontype'] = 'Multiple Choice'
                                if 'cc.multiple_response.v0p1' == entry:
                                    data['questiontype'] = 'Multiple Answer'
                                if 'cc.true_false.v0p1' == entry:
                                    data['questiontype'] = 'True/False'
                                if 'cc.essay.v0p1' == entry:
                                    data['questiontype'] = 'Essay'
                            elif 'cc_weighting' == label:
                                data['questionscore'] = entry
                                
        if not data.has_key('questiontype'):
            data['questiontype'] = 'Unknown'

    def readPresentation(self, item, data):
        """ Read the item's presentation data """
        presentation = item.getElementsByTagName('presentation')
        for p in presentation:
            flow = p.getElementsByTagName('flow')
            if flow:
                for f in flow:
                    self.readQuestion(f, data)
                    self.readResponses(f, data)
            else:
                self.readQuestion(p, data)
                self.readResponses(p, data)

    def readQuestion(self, flow, data):
        """ Read the Question """
        material = flow.getElementsByTagName('material')
        if material and len(material) > 0:
            text, ttype = self.readMaterial(material[0])
            data['qtexttype'] = ttype
            data['question'] = text
                
    def readResponses(self, flow, data):
        """ Read responses """
        data['responses'] = []
        responses = flow.getElementsByTagName('response_lid')
        if responses:
            choice = responses[0].getElementsByTagName('render_choice')
            if choice:
                labels = choice[0].getElementsByTagName('response_label')
                for x in labels:
                    respid = x.getAttribute('ident')
                    if respid:
                        material = x.getElementsByTagName('material')
                        if material:
                            text, ttype = self.readMaterial(material[0])
                            data['responses'].append(
                                (respid,
                                 {'rtexttype':ttype, 'response':text, }))               

    def readProcessingInfo(self, item, data):
        """ Read processing info """
        resprocessing = item.getElementsByTagName('resprocessing')
        if resprocessing:
            rcond = resprocessing[0].getElementsByTagName('respcondition')
            for c in rcond:
                title = c.getAttribute('title')
                if title and title in ['CorrectResponse', 'Correct']:
                    veq = c.getElementsByTagName('varequal')
                    if veq:
                        if data.has_key('cresponse'):
                            data['cresponse'].append(self.getTextValue(veq[0]))
                        else:
                            data['cresponse'] = [self.getTextValue(veq[0])]
                
    def readMaterial(self, mat):
        text = None
        ttype = None
        mattext = mat.getElementsByTagName('mattext')
        if mattext:
            ttype = mattext[0].getAttribute('texttype')
            text = self.getTextValue(mattext[0])
        return text, ttype   

    def getTextValue(self, node):
        """ Get text value out of node. """
        for x in node.childNodes:
            if x.TEXT_NODE == x.nodeType:
                return x.nodeValue.strip()
        return None
                    

class Canvas(QTIParser1v2):

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
            if xml.find("{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}answer_tolerance") is not None:
                tolerance = xml.find("{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}answer_tolerance")
            for xml_var_set in xml.findall(".//{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}var_set"):
                this_var_set = {
                    'id': xml_var_set.get("ident"),
                    'value': xml_var_set.find("{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}answer").text,
                    'text': "",
                    'display': True,
                    'correct': True,
                    'tolerance': tolerance,
                    'variable': []
                }
                for xml_var_set_variable in xml_var_set.findall(".//{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}var"):
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

        for id in xml.findall(".//{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}varequal"):
            correct_answers.append(id.text)
        try:
            for xml_answer_item in xml.findall(".//{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}response_label"):
                this_answer = {}
                this_answer['id'] = xml_answer_item.get("ident")
                this_answer['text'] = xml_answer_item.find("{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}material/{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}mattext").text
                this_answer['correct'] = True if xml_answer_item.get("ident") in correct_answers else False
                this_answer['display'] = False
                answers.append(this_answer)
        except OSError as e:
            _LOG.error("%s", e)
        except et.ParseError as e:
            _LOG.error("XML parser error: %s", e)
        return answers

    def _parse_matching(self, xml: et.ElementTree):
        """ Return an array of items and possible answers """
        answers = []
        correct_answer = {}

        for id in xml.findall(".//{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}varequal"):
            correct_answer[id.get("respident")] = id.text
        try:
            for xml_response_lid in xml.findall(".//{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}response_lid"):
                this_response_lid = {
                    'id': xml_response_lid.get("ident"),
                    'text': xml_response_lid.find("./{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}material/{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}mattext").text,
                    'display': True,
                    'options': []
                }
                for xml_option in xml_response_lid.findall(".//{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}response_label"):
                    this_option = {}
                    this_option['id'] = xml_option.get("ident")
                    this_option['text'] = xml_option.find("{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}material/{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}mattext").text
                    this_option['display'] = True
                    this_option['correct'] = True if this_response_lid['id'] in correct_answer and correct_answer[this_response_lid['id']] == xml_option.get("ident") else False
                    this_response_lid['options'].append(this_option)
                if self.matching_random_shuffle_answer_options:
                    shuffle(this_response_lid['options']) 
                answers.append(this_response_lid)
        except OSError as e:
            _LOG.error("%s", e)
        except et.ParseError as e:
            _LOG.error("XML parser error: %s", e)
        if self.matching_random_shuffle_answers:
            shuffle(answers)
        return answers


    def _parse_multiple_answers(self, xml: et.ElementTree):
        """ Return an array of possible answers """
        answers = []
        correct_answers = []

        for id in xml.findall(".//{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}conditionvar/{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}and/{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}varequal"):
            correct_answers.append(id.text)
        try:
            for xml_answer_item in xml.findall(".//{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}response_label"):
                answers.append(
                    {
                        'id': xml_answer_item.get("ident"),
                        'text': xml_answer_item.find("{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}material/{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}mattext").text,
                        'correct': True if xml_answer_item.get("ident") in correct_answers else False,
                        'display': True
                    }
                )
        except OSError as e:
            _LOG.error("%s", e)
        except et.ParseError as e:
            _LOG.error("XML parser error: %s", e)
        return answers


    def _parse_multiple_dropdowns(self, xml: et.ElementTree):
        """ Return an array of possible answers, grouped for each blank """
        answers_group = []
        correct_answer = {}

        for id in xml.findall(".//{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}varequal"):
            correct_answer[id.get("respident")] = id.text

        try:
            for xml_response_lid in xml.findall(".//{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}response_lid"):
                answers = []
                for xml_answer_item in xml_response_lid.findall(".//{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}response_label"):
                    this_answer = {}
                    this_answer['id'] = xml_answer_item.get("ident")
                    this_answer['text'] = xml_answer_item.find("{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}material/{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}mattext").text
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

    def _parse_multiple_choice(self, xml: et.ElementTree):
        """ Return an array of possible answers """
        answers = []
        correct_answers = []

        for id in xml.findall(".//{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}respcondition[@continue='No']/{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}conditionvar/{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}varequal"):
            correct_answers.append(id.text)
        try:
            for xml_answer_item in xml.findall(".//{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}response_label"):
                image = []
                this_answer = {}
                this_answer['id'] = xml_answer_item.get("ident")
                this_answer['text'] = xml_answer_item.find("{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}material/{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}mattext").text
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

    def _parse_numerical(self, xml: et.ElementTree):
        """ Return an array of possible answers """
        answers = []
        i = 0
        try:
            for xml_cond in xml.findall(".//{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}conditionvar"):
                i += 1
                value, minvalue, maxvalue = None, None, None
                if xml_cond.find("{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}or/{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}varequal") is not None:
                    value = xml_cond.find("{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}or/{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}varequal").text
                    minvalue = value
                    maxvalue = value
                if xml_cond.find("{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}or/{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}and") is not None:
                    xml_cond_range = xml_cond.find("{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}or/{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}and")
                if xml_cond.find("{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}vargte") is not None or xml_cond.find("{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}varlte") is not None:
                    xml_cond_range = xml_cond
                if xml_cond_range.find("{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}vargte") is not None:
                    minvalue = xml_cond_range.find("{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}vargte").text
                elif xml_cond_range.find("{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}vargt") is not None:
                    minvalue = xml_cond_range.find("{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}vargt").text
                if xml_cond_range.find("{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}varlte") is not None:
                    maxvalue = xml_cond_range.find("{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}varlte").text
                elif xml_cond_range.find("{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}varlt") is not None:
                    maxvalue = xml_cond_range.find("{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}varlt").text
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

    def _parse_short_answer(self, xml):
        """ Return an array of possible answers """
        answers = []
        i = 0
        try:
            for xml_answer_item in xml.findall(".//{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}varequal"):
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

    def _parse_true_false(self, xml):
        """ Return an array of possible answers """
        answers = []
        correct_answers = []

        for id in xml.findall(".//{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}varequal"):
            correct_answers.append(id.text)

        try:
            for xml_answer_item in xml.findall(".//{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}response_label"):
                answers.append(
                    {
                        'id': xml_answer_item.get("ident"),
                        'text': xml_answer_item.find("{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}material/{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}mattext").text,
                        'correct': True if xml_answer_item.get("ident") in correct_answers else False,
                        'display': True
                    }
                )
        except OSError as e:
            _LOG.error("%s", e)
        except et.ParseError as e:
            _LOG.error("XML parser error: %s", e)
        return answers

    def get_metadata(self, file: str) -> Dict[str, str]:
        """ Extracts basic metadata """
        metadata = {}
        try:
            xml = et.parse(file).getroot()
            metadata = {
                'title': xml.find("./{http://canvas.instructure.com/xsd/cccv1p0}title").text,
                'description': xml.find("./{http://canvas.instructure.com/xsd/cccv1p0}description").text,
                'type': xml.find("./{http://canvas.instructure.com/xsd/cccv1p0}quiz_type").text,
                'points_possible': xml.find("./{http://canvas.instructure.com/xsd/cccv1p0}points_possible").text
            }
        except OSError as e:
            _LOG.error("%s", e)
        except et.ParseError as e:
            _LOG.error("XML parser error: %s", e)
        return metadata

    def get_question(self, xml_item: et.ElementTree):
        """ Get question, metadata and answers/options """
        xml_item_metadata = xml_item.find("{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}itemmetadata/{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}qtimetadata")
        this_question = {
            'id': str(xml_item.get("ident")),
            'title': str(xml_item.get("title")),
            'question_type': xml_item_metadata.find("{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}qtimetadatafield[{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}fieldlabel = 'question_type']/{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}fieldentry").text,
            'points_possible': xml_item_metadata.find("{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}qtimetadatafield[{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}fieldlabel = 'points_possible']/{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}fieldentry").text,
            'text': xml_item.find("{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}presentation/{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}material/{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}mattext").text
        }

        image = []

        # Try and find images in text to separate them
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
        if this_question['question_type'] == "multiple_choice_question":
            this_question['answer'] = self._parse_multiple_choice(xml_item)
        elif this_question['question_type'] == "true_false_question":
            this_question['answer'] = self._parse_true_false(xml_item)
        elif this_question['question_type'] == "multiple_answers_question":
            this_question['answer'] = self._parse_multiple_answers(xml_item)
        elif this_question['question_type'] == "short_answer_question":
            this_question['answer'] = self._parse_short_answer(xml_item)
        elif this_question['question_type'] == "fill_in_multiple_blanks_question":
            this_question['answer'] = self._parse_fill_in_multiple_blanks(xml_item)
        elif this_question['question_type'] == "multiple_dropdowns_question":
            this_question['answer'] = self._parse_multiple_dropdowns(xml_item)
        elif this_question['question_type'] == "matching_question":
            this_question['answer'] = self._parse_matching(xml_item)
        elif this_question['question_type'] == "numerical_question":
            this_question['answer'] = self._parse_numerical(xml_item)
        elif this_question['question_type'] == "calculated_question":
            this_question['answer'] = self._parse_calculated(xml_item)

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


# -----------------------------------------------------------------------------


def read_qti_canvas(self, file_path: str):
    """Read data out of the manifest and store it in data
    Args:
        file_path (str): _description_
    """
    parser = Canvas()
    parser.read(file_path)


