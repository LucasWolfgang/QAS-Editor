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

    def __init__(self, tempdir: str):
        self._td = tempdir
        self.metadata = {}
        self.organizations = {}
        self.resources = {}

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

