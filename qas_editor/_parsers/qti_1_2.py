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
from typing import TYPE_CHECKING
from xml.etree import ElementTree as et
import logging

_LOG = logging.getLogger(__name__)

def get_metadata(file):
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
    except etree.ParseError as e:
        _LOG.error("XML parser error: %s", e)
    return metadata


# -----------------------------------------------------------------------------


def read_qti(self, file_path: str) -> None:
    """_summary_

    Args:
        file_path (str): _description_
    """
    # TODO
    raise NotImplementedError("Canvas LMS not implemented")


def write_qti(self, file_path: str) -> None:
    """_summary_

    Args:
        file_path (str): _description_
    """
    xml_doc = et.parse(file_path)

    qti_resource = {
        'assessment': []
    } 

    for xml_resource in xml_doc.getroot().findall(".//{http://www.imsglobal.org/xsd/imsccv1p1/imscp_v1p1}resource[@type='imsqti_xmlv1p2']"):
        this_assessment = {
            'id': xml_resource.get("identifier"),
            'metadata': get_metadata(xml_resource.get("identifier") + "/" + "assessment_meta.xml"),
            'question': []
        }

        # TODO: Should be prefixed with PATH part of input filename since paths in XML are relative
        this_assessment_xml = this_assessment['id'] + "/" + this_assessment['id'] + ".xml"

        for xml_item in et.parse(this_assessment_xml).getroot().findall(".//{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}item"):
            this_assessment['question'].append(item.get_question(xml_item))
        qti_resource['assessment'].append(this_assessment)


