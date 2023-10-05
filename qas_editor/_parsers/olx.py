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
import codecs
import os
import re
import json
import shutil
import logging
from io import StringIO
import tarfile
from xml.etree import ElementTree as et
from html.parser import HTMLParser
from typing import TYPE_CHECKING, Type
from ..question import  QMultichoice
from ..utils import serialize_fxml
if TYPE_CHECKING:
    from ..category import Category
    from ..question import _Question, _QHasOptions, QQuestion


__doc__="Parser for the Open Learning XML Format (OLX) from Open EdX"
_LOG = logging.getLogger(__name__)
_POLICY = { "course/1": { "tabs": [
    {"course_staff_only": True, "name": "Home", "type": "course_info"},
    {"course_staff_only": False, "name": "Course", "type": "courseware"},
    {"course_staff_only": False, "name": "Textbooks", "type": "textbooks"},
    {"course_staff_only": False, "name": "Discussion", "type": "discussion"},
    {"course_staff_only": False, "name": "Wiki", "type": "wiki", "is_hidden": True},
    {"course_staff_only": False, "name": "Progress", "type": "progress"}
] } }

class _OlxExporter:

    _URL_CHAR_MAP = {',/().;=+ ': '_', '/': '__', '&': 'and',
                      '#': '_num_', '[': 'LB_', ']': '_RB'}

    def __init__(self, category: Category, pretty: bool):
        self._QTYPE = {
            QMultichoice: self._to_qmultichoice
        }
        self._URLNAMES = []
        self._files = {}
        self._moodle_dir = ""
        self._output_dir = ""
        self.cat = category
        self.pretty = pretty

    def _to_url(self, string: str, extra_ok_chars=""):
        for m,v in self._URL_CHAR_MAP.items():
            for ch in m:
                string = string.replace(ch,v)
        if string == '':
            string = 'x'
        string = string[:60]  # Set maximum num of chars to 60
        string = re.sub(r"[^0-9a-zA-Z_-"+ extra_ok_chars + r"]", "", string)
        cnt = 0
        tmp = string
        while tmp in self._URLNAMES:
            tmp = string + str(cnt)
            cnt += 1
        self._URLNAMES.append(tmp)
        return tmp

    def _get_moodle_page(self, adir: str, fn='page.xml'):
        pxml = et.parse(f'{self._moodle_dir}/{adir}/{fn}').getroot()
        name = pxml.find('.//name').text.strip().split('\n')[0].strip()
        fnpre = os.path.basename(adir) + '__' + name.replace(' ','_').replace('/','_')
        url_name = self._to_url(fnpre)
        return pxml, url_name, name

    def _get_moodle_section(self, sectionid: str, chapter: et.Element, pretty: bool):
        path = f'{self._moodle_dir}/sections/section_{sectionid}/section.xml'
        section = et.parse(path).getroot()
        name = section.find('name').text.strip()
        contents = section.find('summary').text
        if not name or name=='$@NULL@$':
            _LOG.warning("Setion %s has no name. ID will be used", sectionid)
            name = sectionid
        chapter.set('display_name', name)
        url_name = self._to_url(f'section_{sectionid}__{name}')
        seq = et.SubElement(chapter,'sequential', display_name=name,
                            url_name=url_name)
        self._save_as_html(url_name, name, contents, pretty)
        return seq

    def _save_as_html(self, url_name: str, name: str, htmlstr: str, clean_html: bool):
        htmlstr = htmlstr.replace('<o:p></o:p>','')
        def fix_static_src(m: re.Match):
            return ' src="/static/%s"' % (m.group(1).replace('%20','_'))
        htmlstr = re.sub(r' src="@@PLUGINFILE@@/([^"]+)"', fix_static_src, htmlstr)
        def fix_link(m: re.Match):
            dbid = m.group(1)
            _, rel_url_name, _ = self._get_moodle_page(f'activities/page_{dbid}')
            return ' href="/jump_to_id/%s"' % (rel_url_name)
        htmlstr = re.sub(r' href="\$@PAGEVIEWBYID\*([^"]+)@\$"', fix_link, htmlstr)
        htmlstr = f'<html display_name="{name}">\n{htmlstr}\n</html>'
        if clean_html:
            tree = et.parse(StringIO(htmlstr), HTMLParser())
            htmlstr = et.tostring(tree, pretty_print=True)
        path = f'{self._moodle_dir}/html/{url_name}.xml'
        with codecs.open(path,'w', encoding='utf8') as ofile:
            ofile.write(htmlstr)

    def _to_problem(self, qst: _Question):
        page = et.Element('problem', show_reset_button=True,
                        weight=qst.default_grade, display_name=qst.name)
        return page

    def _to_problem_mt(self, qst: _QHasOptions):
        page = self._to_problem(qst)
        if qst.max_tries > 0:
            page.set('max_attempts', qst.max_tries)
        item = et.SubElement(page, "demandhint")
        for hint in qst._fail_hints:
            et.SubElement(item, "hint").text = hint.text
        return page

    def _to_problem_combfdbk(self, qst: _QHasOptions, elem: et.Element):
        elem.set("rerandomize", qst.shuffle.value)
        elem.set("showanswer", qst.show_ans.value)

    def _to_question(self, qst: _Question, elem: et.Element, tag: str):
        item = et.SubElement(elem, tag)
        et.SubElement(item, "label").text = qst.name  # <label> or <text> ?
        et.SubElement(item, "description").text = qst.question.text
        et.SubElement(item, "solution").text = qst.remarks
        return item

    def _to_qmultichoice(self, qst: QMultichoice) -> et.Element:
        page = self._to_problem_mt(qst)
        self._to_problem_combfdbk(qst, page)
        if qst.use_dropdown:  
            item = self._to_question(qst, page, "optionresponse")
            for opt in qst.options:
                opt_item = et.SubElement(item, "option", correct=opt.fraction==100)
                opt_item.text = opt.text
                et.SubElement(opt_item, "optionhint").text = opt.feedback
        else:
            item = self._to_question(qst, page, "multiplechoiceresponse")
            if not qst.single:
                item.set("partial_credit", "points")
            group = et.SubElement(item, "choicegroup", type="MultipleChoice")
            if qst.shuffle:
                group.set("shuffle", "true")
            for opt in qst.options:
                opt_item = et.SubElement(item, "choice", correct=opt.fraction==100)
                opt_item.text = opt.text
                et.SubElement(opt_item, "choicehint").text = opt.feedback
        return page
    
    def _txrecursive(self, cat: Category, dbids: dict, path: str, stack: tuple,
                     elem: et.Element):
        for file in cat.resources:
            output = f"/static/{os.path.basename(file.path).replace(' ', '_')}"
            shutil.copy(file.path, f"{path}/{output}")
        if cat.get_size() > 0:
            for qst in cat.questions:
                tmp = self._QTYPE.get(qst.__class__)
                if tmp is None:
                    continue
                with open(f'{self._output_dir}/problem/{qst.dbid}.xml', "w") as ofile:
                    ofile.write("<?xml version='1.0' encoding='utf-8'?>\n")
                    serialize_fxml(ofile.write, tmp(qst), True, True)
                dbids[qst.dbid] = qst.name
        if stack and elem:
            elem = et.SubElement(elem, stack[0], display_name=cat.name)
            stack = stack[1:] or stack
        for name in cat:                            # Then add children data
            self._txrecursive(cat[name], dbids)

    def write(self, file_path: str):
        self.cat.gen_dbids([])   # We need that each question has a unique dbid
        _path = os.path.dirname(file_path)
        shutil.rmtree(_path, True)
        for folder in ('about', 'chapter', 'course', 'html', 'problem',
                       'sequential', 'static', 'vertical', 'policies'):
            os.makedirs(f"{_path}/{folder}")
        dbids = {}
        stack = ("chapter", "sequential", "vertical")
        tmp = depth = self.cat.get_depth(True)
        cxml = et.Element("course", url_name="1", org="QAS", course="questions",
                          name=self.cat.name)
        if "moodle_course" in self.cat.metadata:
            # TODO not working yet
            _moodle_dir = self.cat.metadata["moodle_course"]
            moodx = et.parse(f"{_moodle_dir}/moodle_backup.xml").getroot()
            xml = et.parse(f'{_moodle_dir}/course/course.xml').getroot()
            name = xml.find('shortname').text
            contents = xml.find('summary').text
            if contents:
                chapter = et.SubElement(cxml,'chapter')
                url = self._to_url(f'course__{name}')
                et.SubElement(chapter, 'sequential', display_name=name, url_name=url)
                self._save_as_html(url, name, contents, self.pretty)
            #self._moodle_translator(moodx, dbids)
        else:
            tmp = cxml
            substack = stack[:max(3-depth, 0)]
            for tag in substack:
                tmp = et.SubElement(tmp, tag, display_name=f"QAS_{tag}")
            self._txrecursive(self.cat, dbids, tmp, substack)
            tmp = cxml  
            for tag in substack:
                tmp = et.SubElement(tmp, tag, display_name=f"QAS_{tag}")
        with open(f"{_path}/course.xml", 'w') as ofile:
            serialize_fxml(ofile.write, cxml, True, True)
        os.makedirs(f"{_path}/policies/1/")
        with open(f"{_path}/policies/1/policy.json", 'w') as ofile:
            json.dump(_POLICY, ofile)
        with tarfile.open(file_path, 'w:gz') as tar:
            for _dir in os.listdir(_path):
                tar.add(f"{_path}/{_dir}", arcname=os.path.basename(_dir))



class _OlxImporter:

    def __init__(self, category: Type[Category], header: tarfile.TarInfo,
                 tar: tarfile.TarFile, use_hier: bool=True):
        self._QTYPE = {
            "choiceresponse": "_from_choiceresponse",
            "multiplechoiceresponse": "_from_multiplechoiceresponse",
            "optionresponse": "_from_"
        }
        self._URLNAMES = []
        self._files = {}
        self._catcls = category
        self._tar = tar
        self._hdr = header
        self._hier = use_hier
        self._root = "."

    def _read_question(self, item: et.Element, name: str):
        qst = QQuestion(item.get("display_name", name))
        text = []
        for child in item:
            if child.tag in ("h1", "h2", "h3", "p", "pre"):
                text.append(child.text)
            elif child.tag in self._QTYPE:
                getattr(self, self._QTYPE[child.tag])(child)
            else:
                print(f"Tag not implemented: {item.tag}")
        qst.body.text = text

    def _from_choiceresponse(self, item: et.Element, text: list):
        for child in item:
            if child.tag in ("h1", "h2", "h3", "p", "pre"):
                pass

    def _from_optionresponse(self, item: et.Element):
        pass

    def _read_multiplechoiceresponse(self, item: et.Element):
        pass

    def _read_hier_single(self, tag: et.Element, cat: Category):
        total = 0
        cat.name = tag.get("display_name")
        for child in tag:
            name = child.get('url_name')
            path = f"{self._root}/{child.tag}/{name}.xml"
            if child.tag in ("chapter", "sequential", "vertical", "library_content"):      
                tmp = self._catcls(name) if self._hier else cat
                if not len(child):
                    child = et.parse(self._tar.extractfile(path)).getroot()
                val = self._read_hier_single(child, tmp)
                if val != 0:
                    cat.add_subcat(tmp)
                    total += val
            elif child.tag == "problem":
                stm = et.parse(self._tar.extractfile(path)).getroot()
                qst = self._read_question(et.parse(stm).getroot(), name)
                cat.add_question(qst)
                total += 1
        return total

  
    def read(self):
        self._root = os.path.dirname(self._hdr.path)
        header = et.parse(self._tar.extractfile(self._hdr)).getroot()
        cat = self._catcls(header.get('url_name'))
        if len(header) == 0: # Uses separeted file 
            path = f"{self._root}/course/{header.get('url_name')}.xml"
            crs = et.parse(self._tar.extractfile(path)).getroot()
            self._read_hier_single(crs, cat)
        else:
            self._read_hier_single(header, cat)
        return cat


# -----------------------------------------------------------------------------


def read_olx(cls, file_path: str):
    """[summary]
    Returns:
        [type]: [description]
    """
    with tarfile.open(file_path, 'r:xz') as tar:
        for path in tar:
            if path.isreg() and path.path.split("/")[1][-4:] == ".xml":
                break
        else:
            raise ValueError("File is not valid")
        tmp = _OlxImporter(cls, path, tar)
        res = tmp.read()
    return res


def write_olx(self: "Category", file_path: str, pretty=False, course=True):
    """[summary]
    Returns:
        [type]: [description]
    """
    tmp = _OlxExporter(self, pretty, course)
    tmp.write(file_path)
