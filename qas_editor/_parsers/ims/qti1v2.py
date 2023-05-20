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
from typing import TYPE_CHECKING
from xml.etree import ElementTree as et
import logging

_LOG = logging.getLogger(__name__)


class QTIParser1v2:
    """ Parse QTI 1.2 
    Attributes:
    """

    def read(self, elem: et.ElementTree, data: dict):
        assessment = elem.find('assessment')
        if assessment:
            data['title'] = assessment[0].get('title')
            sections = assessment[0].find('section')
            for s in sections:
                items = s.find('item')
                data['items'] = {}
                data['itemorder'] = []
                for i in items:
                    self.read_item(i, data['items'], data['itemorder'])

    def read_item(self, item, data, order):
        pass


class BBImporter(QTIParser1v2):
    """
    """

    def __init__(self, manifest: str):
        super().__init__()

    def read(self, item: et.Element, data: dict, order: list):
        """ Read an item out of the manifest. """
        itemid = item.attrib.get('ident')
        if itemid:
            order.append(itemid)
            data[itemid] = {}
            itemtitle = item.attrib.get('title')
            if itemtitle:
                data[itemid]['title'] = itemtitle
            self._read_item_metadata(item, data[itemid])
            self._read_presentation(item, data[itemid])
            self._read_processingInfo(item, data[itemid])
        
    def _read_item_metadata(self, item: et.Element, data: dict, ns: dict):
        """ Read the item's metadata """
        for m in item.findall('./qtimetadata/qtimetadatafield', ns):
            flabel = f.find('fieldlabel')
            if flabel:
                label = self._get_text_value(flabel)
                fentry = f.find('fieldentry')
                if fentry:
                    entry = self._get_text_value(fentry[0])
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
        if 'questiontype' not in data:
            data['questiontype'] = 'Unknown'

    def _read_presentation(self, item: et.Element, data):
        """ Read the item's presentation data """
        presentation = item.findall('presentation')
        for p in presentation:
            flow = p.findall('flow')
            if flow:
                for f in flow:
                    self._read_question(f, data)
                    self._read_responses(f, data)
            else:
                self._read_question(p, data)
                self._read_responses(p, data)

    def _read_question(self, flow, data):
        """ Read the Question """
        material = flow.findall('material')
        if material and len(material) > 0:
            text, ttype = self._read_material(material[0])
            data['qtexttype'] = ttype
            data['question'] = text
                
    def _read_responses(self, flow: et.Element, data: dict):
        """ Read responses """
        data['responses'] = []
        responses = flow.findall('response_lid')
        if responses:
            choice = responses[0].findall('render_choice')
            if choice:
                labels = choice[0].findall('response_label')
                for x in labels:
                    respid = x.getAttribute('ident')
                    if respid:
                        material = x.findall('material')
                        if material:
                            text, ttype = self._read_material(material[0])
                            data['responses'].append(
                                (respid,
                                 {'rtexttype':ttype, 'response':text, }))               

    def _read_processingInfo(self, item: et.Element, data: dict):
        """ Read processing info """
        resprocessing = item.findall('resprocessing')
        if resprocessing:
            rcond = resprocessing[0].findall('respcondition')
            for c in rcond:
                title = c.getAttribute('title')
                if title and title in ['CorrectResponse', 'Correct']:
                    veq = c.findall('varequal')
                    if veq:
                        if data.has_key('cresponse'):
                            data['cresponse'].append(self._get_text_value(veq[0]))
                        else:
                            data['cresponse'] = [self._get_text_value(veq[0])]
                
    def _read_material(self, mat: et.Element):
        text = None
        ttype = None
        mattext = mat.findall('mattext')
        if mattext:
            ttype = mattext[0].getAttribute('texttype')
            text = self._get_text_value(mattext[0])
        return text, ttype   

    def _get_text_value(self, node: et.ElementTree):
        """ Get text value out of node. """
        for x in node.childNodes:
            if x.TEXT_NODE == x.nodeType:
                return x.nodeValue.strip()
        return None
                    
