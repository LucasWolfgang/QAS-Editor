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
from typing import TYPE_CHECKING
from xml.etree import ElementTree as et
from .canvas import CanvasImporter
from .qti1v2 import QTIParser1v2
from .bb import BBImporter
from ... import _LOG, utils
if TYPE_CHECKING:
    from ...category import Category


def _unpack_qti(filename: str, output: str):
    if zipfile.is_zipfile(filename):
        with zipfile.ZipFile(filename) as zip:
            zip.extractall(output)
    elif tarfile.is_tarfile(filename):
        with tarfile.open(filename) as tarobj:
            tarobj.extractall(output)
    else:
        raise TypeError("Format not spported")


def _get_manifest(path: str, nsmap: dict = None) -> dict:
    """Return a intern representation of the manifest file. Common to all
    format AFAIK.
    """
    data = {"organizations": [], "metadata": {}, "resources": []}
    manifest, ns = utils.read_fxml(path)
    ns["ims"] = ns.pop("")
    if nsmap:
        for key, value in nsmap.items():
            ns[value] = ns.pop(key)
    metadata = manifest.find("ims:metadata", ns)
    if metadata is not None:
        data["metadata"]["schema"] = {
            "name": metadata.find("ims:schema", ns).text,
            "version": metadata.find("ims:schemaversion", ns).text,
        }
        lom = metadata.find("lomimscc:lom", ns)
        data["metadata"]["lom"] = None if lom is None else {}
        if lom is not None:
            gen = lom.find("lomimscc:general", ns)
            tmp = data["metadata"]["lom"]["general"] = None if gen is None else {}
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
            data["metadata"]["lom"]["contribute_date"] = text

            elem = lom.find("lomimscc:rights", ns)
            tmp = data["metadata"]["lom"]["rights"] = None if gen is None else {}
            if elem is not None:
                tmp1 = elem.find("lomimscc:copyrightAndOtherRestrictions/lomimscc:value", ns)
                data["is_restricted"] = tmp1.text if tmp1 else None
                tmp1 = elem.find("lomimscc:description/lomimscc:string", ns)
                data["description"] = tmp1.text if tmp1 else None
    for org in manifest.find("ims:organizations", ns):
        tmp = {
            "identifier": org.get("identifier"),
            "structure": org.get("structure"),
            "children": []
        }
        for item in org:
            child = _get_organization_item(item)
            if len(child):
                tmp["children"].append(child)
        data["organizations"].append(tmp)
    for res in manifest.find("ims:resources", ns):
        resource = {
            'id': res.get("identifier") or ".",
            "type": res.get("type"),
            "href": res.get("href"),
            "intended_use": res.get("intended_use"),
            'meta': res.get("identifier") + "/assessment_meta.xml",
            'children': []
        }
        for child in res:
            _, _, tag = child.tag.partition("}")
            if tag == "file":
                tmp = child.get("href")
            elif tag == "dependency":
                tmp = child.get("identifierref")
            else:
                _LOG.warning("Unsupported Resource Type %s", tag)
                continue
            resource["children"].append(tmp)
        data['resources'].append(resource)


def _get_organization_item(item: et.Element):
    data = {}
    data["identifier"] = item.get("identifier")
    data["identifierref"] = item.get("identifierref")
    tmp = item.find("ims:title")
    data["title"] = tmp.text if tmp else None
    data["children"] = []
    for child in item:
        tmp = _get_organization_item(child)
        if tmp:
            data["children"] = tmp
    return data


# -----------------------------------------------------------------------------


def read_qti(self: Category, filename: str):
    shutil.unpack_archive(filename, "tmp")
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
    if tempdir is None:
        tempdir = filename
    os.makedirs(tempdir)
    shutil.unpack_archive(filename, tempdir)
    parser = QTIParser1v2(tempdir)
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


def read_blackboard(self: Category, file_path: str) -> None:
    """_summary_

    Args:
        file_path (str): _description_
    """
    raise NotImplementedError("Blackboard not implemented")


def write_blackboard(self: Category, file_path: str) -> None:
    """_summary_

    Args:
        file_path (str): _description_
    """
    pck = BBImporter()
    pck.write(self, file_path)
    pck.close()
    

# -----------------------------------------------------------------------------


def read_canvas(self, filename: str, tempdir: str=None):
    """Read data out of the manifest and store it in data
    Args:
        file_path (str): _description_
    """
    if tempdir is None:
        tempdir = filename
    os.makedirs(tempdir)
    shutil.unpack_archive(filename, tempdir)
    if os.path.isfile(f"{filename}/course_settings/canvas_export.txt"):
        parser = CanvasImporter(tempdir)
    else:
        parser = QTIParser1v2(tempdir)
    shutil.rmtree(tempdir)


# -----------------------------------------------------------------------------


def read_imscc(cls, file_path: str, category: str = "$course$") -> "Category":
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


def write_imscc(category: "Category", file_path: str) -> None:
    """_summary_
    Args:
        file_path (str): _description_
    """
    with open(file_path, "w", encoding="utf-8") as ofile:
        pass
