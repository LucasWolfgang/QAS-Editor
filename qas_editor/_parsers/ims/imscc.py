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
from typing import TYPE_CHECKING, Dict
from xml.etree import ElementTree as et
from ... import _LOG, utils
from . import IMS

if TYPE_CHECKING:
    from ...category import Category


class CC(IMS):

    def _find_items(self, elems: et.Element, ns: dict, cat: Category):
        for elem in elems:
            if any(elem.tag.endswith(tmp) for tmp in ("assessment", "section", "objectbank")):
                tmp = Category(elem.get("title") or elem.get("ident"))
                CC._find_items(elem, ns, tmp)
            elif elem.tag.endswith("qtimetadata"):
                tmp = {}
                for meta in elem:
                    if meta.tag.endswith("qtimetadatafield"):
                        key = meta.find("fieldlabel", ns).text
                        tmp[key] = meta.find("fieldentry", ns).text
                    else:
                        _, _, key = meta.tag.partition("}")
                        tmp[key] = meta.text  # TODO may override custom field
                cat.metadata = tmp
            elif elem.tag.endswith("item"):
                if self._meta["schema"] in self._qtiparser:
                    qst = self._qtiparser[self._meta["schema"]](elem)
                elif "*" in self._qtiparser:
                    qst = self._qtiparser["*"](elem)
                else:
                    raise KeyError("No parser for the given schema")
                cat.add_question(qst)

    def get_manifest(self, nsmap: dict = None) -> dict:
        manifest, ns = super().get_manifest(nsmap)
        lom = manifest.find("ims:metadata/lomimscc:lom", ns)
        if lom is not None:
            self._meta["lom"] = {}
            gen = lom.find("lomimscc:general", ns)
            tmp = self._meta["lom"]["general"] = None if gen is None else {}
            if gen is not None:
                tmp1 = gen.find("lomimscc:title/lomimscc:string", ns)
                tmp["title"] = tmp1.text if tmp1 else None
                tmp1 = gen.find("lomimscc:language/lomimscc:string", ns)
                tmp["language"] = tmp1.text if tmp1 else None
                tmp1 = gen.find("lomimscc:description/lomimscc:string", ns)
                tmp["description"] = tmp1.text if tmp1 else None
                tmp["keywords"] = tmp1.text.split() if tmp1 else None
            tmp = lom.find("lomimscc:lifeCycle/lomimscc:contribute/" +
                        "lomimscc:date/lomimscc:dateTime", ns)
            text = None if tmp is None else tmp.text
            self._meta["lom"]["contribute_date"] = text
            elem = lom.find("lomimscc:rights", ns)
            tmp = self._meta["lom"]["rights"] = None if gen is None else {}
            if elem is not None:
                tmp1 = elem.find("lomimscc:copyrightAndOtherRestrictions/lomimscc:value", ns)
                self._meta["lom"]["is_restricted"] = tmp1.text if tmp1 else None
                tmp1 = elem.find("lomimscc:description/lomimscc:string", ns)
                self._meta["lom"]["description"] = tmp1.text if tmp1 else None
        return manifest, ns

    def _read_metadata(self, file: str) -> Dict[str, str]:
        """ Extracts basic metadata """
        metadata = {}
        try:
            xml, ns = utils.read_fxml(file)
            metadata = {
                'title': xml.find("title", ns).text,
                'description': xml.find("description", ns).text,
                'type': xml.find("quiz_type", ns).text,
                'points_possible': xml.find("points_possible", ns).text
            }
        except OSError as e:
            _LOG.error("%s", e)
        except et.ParseError as e:
            _LOG.error("XML parser error: %s", e)
        return metadata

    def _read_questions(self, args: dict, stype: str):
        """ Get question, metadata and answers/options """
        if args["refs"]:
            path = f"{self._tmpp}/{self._res[args['refs'][0]]['files'][0]}"
            self._read_metadata(path)
        root, ns = utils.read_fxml(f"{self._tmpp}/{args['files'][0]}")
        self._find_items(root, ns, self._cat)
