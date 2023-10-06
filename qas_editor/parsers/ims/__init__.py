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
import os
import shutil
import zipfile
import tarfile
from typing import TYPE_CHECKING, Dict, Callable
from xml.etree import ElementTree as et
from ... import _LOG, utils
if TYPE_CHECKING:
    from ...category import Category, _Question


class IMS:
    """ Parse CommonCartridge and Common Package formats 
    Attributes:
    """

    def __init__(self, path: str, qti_parser: Callable, category: Category,
                 tmpdir: str=None, manifest_cat=False, file_cat=False, qti_cat=True):
        self._meta = {}
        self._org = []
        self._cat = category
        self._res: Dict[str, Dict[str, str]] = {}
        self._path = path
        self._tmpp = tmpdir or f"{path.rsplit('.', 1)[0]}_tmp"
        self._mancat = manifest_cat
        self._filecat = file_cat
        self._qitcat = qti_cat
        self._qtiparser = qti_parser

    @property
    def category(self):
        return self._cat

    @staticmethod
    def _get_organization_item(item: et.Element):
        data = {}
        data["identifier"] = item.get("identifier")
        data["identifierref"] = item.get("identifierref")
        tmp = item.find("title")
        data["title"] = tmp.text if tmp else None
        data["children"] = []
        for child in item:
            tmp = IMS._get_organization_item(child)
            if tmp:
                data["children"] = tmp
        return data

    def get_manifest(self, nsmap: dict = None):
        """Return a intern representation of the manifest file. Common to all
        format AFAIK.
        """
        manifest, ns = utils.read_fxml(f"{self._tmpp}/imsmanifest.xml")
        if nsmap:
            for key, value in nsmap.items():
                ns[value] = ns.pop(key)
        metadata = manifest.find("metadata", ns)
        if metadata is not None:
            self._meta["schema"] = {
                "name": metadata.find("schema", ns).text,
                "version": metadata.find("schemaversion", ns).text,
            }
        for org in manifest.find("organizations", ns):
            tmp = {
                "identifier": org.get("identifier"), "children": [],
                "structure": org.get("structure")
            }
            for item in org:
                child = self._get_organization_item(item)
                if len(child):
                    tmp["children"].append(child)
            self._org.append(tmp)
        for res in manifest.find("resources", ns):
            resource = {
                "use": res.get("intended_use"), "type": res.get("type"),
                "refs": [], "files": []
            }
            for child in res:
                _, _, tag = child.tag.partition("}")
                if tag == "file":
                    resource["files"].append(child.get("href"))
                elif tag == "dependency":
                    resource["refs"].append(child.get("identifierref"))
                elif tag == "metadata":
                    resource["metadata"] = child
            self._res[res.get("identifier")] = resource
        return manifest, ns
    
    def _read_one_question(self, item: et.Element, ns: dict) -> _Question:
        """_summary_
        Args:
            item (et.Element): _description_
            ns (dict): _description_
        Returns:
            _Question: _description_
        """
        raise NotImplementedError

    def _read_questions(self, data: dict, stype: str, cat: Category):
        """_summary_
        Args:
            data (dict): _description_
            cat (Category): _description_
        """
        raise NotImplementedError

    def _write_one_question():
        raise NotImplementedError

    def _write_questions():
        raise NotImplementedError

    def descompress(self):
        if os.path.isdir(self._tmpp):
            return
        os.makedirs(self._tmpp)
        if zipfile.is_zipfile(self._path):
            with zipfile.ZipFile(self._path) as zip:
                zip.extractall(self._tmpp)
        elif tarfile.is_tarfile(self._path):
            with tarfile.open(self._path) as tarobj:
                tarobj.extractall(self._tmpp)
        else:
            raise TypeError("Format not spported")

    def read(self):
        """Helper function in case the class is being directly used by an user.
        """
        self._res.clear()
        self._meta.clear()
        self._org.clear()
        self.descompress()
        self.get_manifest()
        for item in self._res.values():
            types = item["type"].split("/")
            if not any(tmp.startswith("imsqti_") for tmp in types) or (
                "associatedcontent" in types and item["href"].endswith(".xml.qti")
            ):
                continue
            # TODO Used cat here til implement the organization based hierarchy
            self._read_questions(item, types, self._cat)

    def write(self):
        raise NotImplementedError
 

# -----------------------------------------------------------------------------


def read_qti(self: Category, filename: str):
    if os.path.isfile(f"{filename}/course_settings/canvas_export.txt"):
        pass


# -----------------------------------------------------------------------------


def read_qti1v2(self: Category, filename: str, tempdir: str):
    """_summary_
    Args:
        self (Category): _description_
        filename (str): _description_
        tempdir (str): _description_
    """
    #parser = QTIParser1v2(tempdir)
    shutil.rmtree(tempdir)


# -----------------------------------------------------------------------------


def read_qti2v1(self: Category, filename: str, tempdir: str):
    """_summary_
    Args:
        self (Category): _description_
        filename (str): _description_
        tempdir (str): _description_
    """
    pass


def read_qti3v0(self: Category, filename: str, tempdir: str):
    """_summary_
    Args:
        self (Category): _description_
        filename (str): _description_
        tempdir (str): _description_
    """
    pass


# -----------------------------------------------------------------------------


def read_imscc(cls, filename: str, category: str = "$course$") -> "Category":
    """_summary_
    Args:
        file_path (str): _description_
        category (str, optional): _description_. Defaults to "$".
    Returns:
        Quiz: _description_
    """
    quiz = cls(category)
    cnt = 0

    return quiz


def write_imscc(category: "Category", file_path: str):
    """_summary_
    Args:
        file_path (str): _description_
    """
    pass
