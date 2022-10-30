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


_LOG = logging.getLogger(__name__)
_moodle_dir = ""
_output_dir = ""

def _moodle_translator(moodx: et.Element, cxml: et.Element, qdict: dict,
                       static: dict, pretty: bool):
    """ Make the following translation:
     * section -> chapter
     * page, quiz, section -> sequential
    """
    seq = None
    vert = None
    sections = {}
    for activity in moodx.find('.//contents').findall('.//activity'):
        adir = activity.find('directory').text
        title = activity.find('title').text.strip()
        category = activity.find('modulename').text
        sectionid = activity.find('sectionid').text
        if not sectionid in sections:
            chapter = et.SubElement(cxml,'chapter')
            sections[sectionid] = chapter
            seq = _get_moodle_section(sectionid, chapter)
        else:
            chapter = sections[sectionid]
        if category in ('page', 'quiz'):
            seq = et.SubElement(chapter, 'sequential',  display_name=title,
                                url_name=_to_url(title))
            if category == "page":
                pxml, url, name = _get_moodle_page(adir)
                seq.set('display_name', name)
                htmlstr = pxml.find('.//content').text
                _save_as_html(url, name, htmlstr, pretty)
            else:
                qxml = et.parse(f'{_moodle_dir}/{adir}/quiz.xml').getroot()
                seq.set('display_name', qxml.find('.//name').text)
                for qinst in qxml.findall('.//question_instance'):
                    qnum = qinst.find('question').text
                    vert = et.SubElement(seq,'vertical')
                    et.SubElement(vert, 'problem', url_name=qdict[qnum])
        elif category in ('url', 'label', 'resource'):
            pxml, url_name, name = _get_moodle_page(adir, f'{category}.xml')
            if vert is None:   # use current vertical if exists
                vert = et.SubElement(seq, 'vertical', display_name=name,
                                     url_name=url_name)
            if category == 'url':
                url = cgi.escape(pxml.find('.//externalurl').text)
                htmlstr = pxml.find('.//intro').text or ''
                htmlstr = f'<p>{htmlstr}</p><p><a href="{url}">{name}</a></p>'
            elif category == 'label':
                htmlstr = pxml.find('.//intro').text
            elif category == 'resource':
                xml = et.parse(f'{_moodle_dir}/{adir}/inforef.xml').getroot()
                htmlstr = f'<h2>{cgi.escape(name)}</h2>'
                for fileid in xml.findall('.//id'):
                    fidnum = fileid.text
                    (url, filename) = static.get(fidnum, ('',''))
                    htmlstr += f'<p><a href="{url}">{filename}</a></p>'
            _save_as_html(url_name, name, htmlstr, pretty)
        else:
            _LOG.warning("Unknown %s, title %s, dir %s", category, title, adir)
        _LOG.info("Added %s, title %s, dir %s", category, title, adir)


_URLNAMES = []
_URL_CHAR_MAP = {',/().;=+ ': '_', '/': '__',
                 '&': 'and', '#': '_num_', '[': 'LB_', ']': '_RB'}
def _to_url(string: str, extra_ok_chars=""):
    global _URLNAMES, _URL_CHAR_MAP
    for m,v in _URL_CHAR_MAP.items():
        for ch in m:
            string = string.replace(ch,v)
    if string == '':
        string = 'x'
    string = string[:60]  # Set maximum num of chars to 60
    string = re.sub(r"[^0-9a-zA-Z_-"+ extra_ok_chars + r"]", "", string)
    cnt = 0
    tmp = string
    while tmp in _URLNAMES:
        tmp = string + str(cnt)
        cnt += 1
    _URLNAMES.append(tmp)
    return tmp


def _get_moodle_page(adir: str, fn='page.xml'):
    pxml = et.parse(f'{_moodle_dir}/{adir}/{fn}').getroot()
    name = pxml.find('.//name').text.strip().split('\n')[0].strip()
    fnpre = os.path.basename(adir) + '__' + name.replace(' ','_').replace('/','_')
    url_name = _to_url(fnpre)
    return pxml, url_name, name


def _get_moodle_section(sectionid: str, chapter: et.Element, pretty: bool):
    path = f'{_moodle_dir}/sections/section_{sectionid}/section.xml'
    section = et.parse(path).getroot()
    name = section.find('name').text.strip()
    contents = section.find('summary').text
    if not name or name=='$@NULL@$':
        _LOG.warning("Setion %s has no name. ID will be used", sectionid)
        name = sectionid
    chapter.set('display_name', name)
    url_name = _to_url(f'section_{sectionid}__{name}')
    seq = et.SubElement(chapter,'sequential', display_name=name,
                        url_name=url_name)
    _save_as_html(url_name, name, contents, pretty)
    return seq


def _save_as_html(url_name: str, name: str, htmlstr: str, clean_html: bool):
    htmlstr = htmlstr.replace('<o:p></o:p>','')
    def fix_static_src(m: re.Match):
        return ' src="/static/%s"' % (m.group(1).replace('%20','_'))
    htmlstr = re.sub(r' src="@@PLUGINFILE@@/([^"]+)"', fix_static_src, htmlstr)
    def fix_link(m: re.Match):
        dbid = m.group(1)
        _, rel_url_name, _ = _get_moodle_page(f'activities/page_{dbid}')
        return ' href="/jump_to_id/%s"' % (rel_url_name)
    htmlstr = re.sub(r' href="\$@PAGEVIEWBYID\*([^"]+)@\$"', fix_link, htmlstr)
    htmlstr = f'<html display_name="{name}">\n{htmlstr}\n</html>'
    if clean_html:
        tree = et.parse(StringIO(htmlstr), HTMLParser())
        htmlstr = et.tostring(tree, pretty_print=True)
    path = f'{_moodle_dir}/html/{url_name}.xml'
    with codecs.open(path,'w', encoding='utf8') as ofile:
        ofile.write(htmlstr)


# -----------------------------------------------------------------------------


def _to_problem(qst: _Question):
    page = et.Element('problem', show_reset_button=True,
                      weight=qst.default_grade, display_name=qst.name)
    return page


def _to_problem_mt(qst: _QHasOptions):
    page = _to_problem(qst)
    if qst.max_tries > 0:
        page.set('max_attempts', qst.max_tries)
    item = et.SubElement(page, "demandhint")
    for hint in qst._fail_hints:
        et.SubElement(item, "hint").text = hint.text
    return page


def _to_problem_combfdbk(qst: _QHasOptions, elem: et.Element):
    elem.set("rerandomize", qst.shuffle.value)
    elem.set("showanswer", qst.show_ans.value)


def _to_question(qst: _Question, elem: et.Element, tag: str):
    item = et.SubElement(elem, tag)
    et.SubElement(item, "label").text = qst.name  # <label> or <text> ?
    et.SubElement(item, "description").text = qst.question.text
    et.SubElement(item, "solution").text = qst.remarks
    return item


def _to_qmultichoice(qst: QMultichoice) -> et.Element:
    page = _to_problem_mt(qst)
    _to_problem_combfdbk(qst, page)
    if qst.use_dropdown:  
        item = _to_question(qst, page, "optionresponse")
        for opt in qst.options:
            opt_item = et.SubElement(item, "option", correct=opt.fraction==100)
            opt_item.text = opt.text
            et.SubElement(opt_item, "optionhint").text = opt.feedback
    else:
        item = _to_question(qst, page, "multiplechoiceresponse")
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


# -----------------------------------------------------------------------------


def read_olx(cls,  file_path: str):
    with tarfile.open(file_path, 'r:gz') as tar:
        for path in tar:
            if path.isreg():
                print("a regular file.")
            elif path.isdir():
                print("a directory.")
            else:
                print("something else.")

# -----------------------------------------------------------------------------


_QTYPE = {
    QMultichoice: _to_qmultichoice
}


def _txrecursive(cat: "Category", dbids: dict):
    if cat.get_size() > 0:
        for qst in cat.questions:
            tmp = _QTYPE.get(qst.__class__)
            if tmp is None:
                continue
            problem = tmp(qst)
            with open(f'{_output_dir}/problem/{qst.dbid}.xml', "w") as ofile:
                ofile.write("<?xml version='1.0' encoding='utf-8'?>\n")
                serialize_fxml(ofile.write, problem, True, True)
            dbids[qst.dbid] = qst.name
    for name in cat:                            # Then add children data
        _txrecursive(cat[name], dbids)


def write_olx(self: "Category", file_path: str, pretty=False, org="QAS"):
    """[summary]
    Returns:
        [type]: [description]
    """
    global _moodle_dir, _output_dir
    self.gen_dbids([])   # We need that each question has a unique dbid
    _output_dir, _ = os.path.splitext(file_path)
    shutil.rmtree(_output_dir, True)
    for folder in ('about', 'chapter', 'course', 'html', 'problem',
                   'sequential', 'static', 'vertical'):
        os.makedirs(f"{_output_dir}/{folder}")
    dbids = {}
    _txrecursive(self, dbids)

    # Create course files
    cxml = et.Element('course', display_name=name)
    if "moodle_course" in self.metadata:
        _moodle_dir = self.metadata["moodle_course"]
        moodx = et.parse(f"{_moodle_dir}/moodle_backup.xml").getroot()
        info = moodx.find('.//information')
        name = info.find('.//original_course_fullname').text

        staticfiles = {}
        fxml = et.parse(f"{_moodle_dir}/files.xml").getroot()
        for mfile in fxml.findall('file'):
            fhash = mfile.find('contenthash').text
            fname = mfile.find('filename').text
            if fname == '.':
                continue
            output = f"/static/{fname.replace(' ', '_')}"
            staticfiles[mfile.get('id')] = (output, fname)
            shutil.copy(f"{_moodle_dir}/files/{fhash[:2]}/{fhash}",
                        f"{_output_dir}/{output}")

        xml = et.parse(f'{_moodle_dir}/course/course.xml').getroot()
        name = xml.find('shortname').text
        contents = xml.find('summary').text
        if contents:
            chapter = et.SubElement(cxml,'chapter')
            url = _to_url(f'course__{name}')
            et.SubElement(chapter, 'sequential', display_name=name, url_name=url)
            _save_as_html(url, name, contents, pretty)
        _moodle_translator(moodx, cxml, dbids, staticfiles, pretty)
        name = _to_url(info.find('.//original_course_shortname').text, '.')
    else:
        name = "qas_translated"
    with open(_output_dir, "w") as ofile:
        ofile.write("<?xml version='1.0' encoding='utf-8'?>\n")
        serialize_fxml(ofile.write, cxml, True, pretty)
    with open(f"{_output_dir}/course.xml", 'w') as ofile:
        ofile.write(f'<course url_name="{name}" course="{name}"/>\n')

    with tarfile.open(file_path, 'w:gz') as tar:
        for _dir in os.listdir(_output_dir):
            tar.add(f"{_output_dir}/{_dir}", arcname=os.path.basename(_dir))
