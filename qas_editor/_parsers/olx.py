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
import cgi
import shutil
import logging
from io import StringIO
import tarfile
from xml.etree import ElementTree as et
from html.parser import HTMLParser
from typing import TYPE_CHECKING
from ..question import  QMultichoice
from ..utils import serialize_fxml
if TYPE_CHECKING:
    from ..category import Category
    from ..question import _Question, _QHasOptions


__doc__="Parser for the Open Learning XML Format (OLX) from Open EdX"
_LOG = logging.getLogger(__name__)


class _OlxImporter:

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
        self.cxml: et.Element = None


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
    
    def _txrecursive(self, cat: "Category", dbids: dict):
        for file in cat.resources:
            file.path
            output = f"/static/{os.path.basename(file.path).replace(' ', '_')}"
            self._files[mfile.get('id')] = (output, fname)
            shutil.copy(f"{_moodle_dir}/files/{fhash[:2]}/{fhash}",
                        f"{_path}/{output}")
        if cat.get_size() > 0:
            for qst in cat.questions:
                tmp = self._QTYPE.get(qst.__class__)
                if tmp is None:
                    continue
                with open(f'{self._output_dir}/problem/{qst.dbid}.xml', "w") as ofile:
                    ofile.write("<?xml version='1.0' encoding='utf-8'?>\n")
                    serialize_fxml(ofile.write, tmp(qst), True, True)
                dbids[qst.dbid] = qst.name
        for name in cat:                            # Then add children data
            self._txrecursive(cat[name], dbids)

    def write(self, file_path: str):
        self.cat.gen_dbids([])   # We need that each question has a unique dbid
        _path = file_path.rsplit(".", 1)[0]
        _path, name = _path.rsplit("/", 1)
        shutil.rmtree(_path, True)
        for folder in ('about', 'chapter', 'course', 'html', 'problem',
                       'sequential', 'static', 'vertical'):
            os.makedirs(f"{_path}/{folder}")
        dbids = {}
        self._txrecursive(self.cat, dbids)
        if "moodle_course" in self.cat.metadata:
            _moodle_dir = self.cat.metadata["moodle_course"]
            moodx = et.parse(f"{_moodle_dir}/moodle_backup.xml").getroot()
            xml = et.parse(f'{_moodle_dir}/course/course.xml').getroot()
            name = xml.find('shortname').text
            contents = xml.find('summary').text
            if contents:
                chapter = et.SubElement(self.cxml,'chapter')
                url = self._to_url(f'course__{name}')
                et.SubElement(chapter, 'sequential', display_name=name, url_name=url)
                self._save_as_html(url, name, contents, self.pretty)
            self._moodle_translator(moodx, dbids)
        with open(f"{_path}/course.xml", 'w') as ofile:
            ofile.write("<?xml version='1.0' encoding='utf-8'?>\n")
        with tarfile.open(file_path, 'w:gz') as tar:
            for _dir in os.listdir(_path):
                tar.add(f"{_path}/{_dir}", arcname=os.path.basename(_dir))


# -----------------------------------------------------------------------------


def read_olx(cls, file_path: str):
    """[summary]
    Returns:
        [type]: [description]
    """
    with tarfile.open(file_path, 'r:gz') as tar:
        for path in tar:
            if path.isreg():
                print("a regular file.")
            elif path.isdir():
                print("a directory.")
            else:
                print("something else.")


def write_olx_lib(self: "Category", file_path: str, pretty=False, course=True):
    """[summary]
    Returns:
        [type]: [description]
    """
    tmp = _OlxImporter(self, pretty, course)
    tmp.write(file_path)


def write_olx_course(self: "Category", file_path: str, pretty=False, course=True):
    """[summary]
    Returns:
        [type]: [description]
    """
    tmp = _OlxImporter(self, pretty, course)
    tmp.write(file_path)