""""
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
import re
import os
import subprocess
import base64
import copy
import html
import logging
import shutil
import tempfile
import hashlib
import unicodedata
import mimetypes
from io import TextIOWrapper
from html.parser import HTMLParser
from io import BytesIO
from xml.sax import saxutils
from importlib import util
from urllib import request, parse
from xml.etree import ElementTree as et
from typing import Dict, List, Tuple, Callable
from .enums import FileAddr, OutFormat, TextFormat, Status, Distribution, MathType

EXTRAS_FORMULAE = util.find_spec("sympy") is not None
if EXTRAS_FORMULAE:
    from sympy.parsing.sympy_parser import parse_expr
    from sympy.parsing.latex import parse_latex
    from matplotlib import figure, font_manager, mathtext
    from matplotlib.backends import backend_agg
    from pyparsing import ParseFatalException  # Part of matplotlib package


_LOG = logging.getLogger(__name__)
EXTRAS_GUI = util.find_spec("PyQt5") is not None
                # moodle, sympy, latex
MDL_FUNCTION = {('arctan', 'atan'), ('arcsin', 'asin'), ('arccos', 'acos'),
                ('arctan', 'atan'), ('root', 'sqrt'), ('clip', ''), ('neg', '-')}


def gen_hier(cls, top, category: str):
    """Generates a categorty hierarchy based on the provided string.
    TODO consider putting it in another file.
    """
    cat_list = category.strip().split("/")
    start = 1 if top.name == cat_list[0] else 0
    quiz = top
    for i in cat_list[start:]:
        quiz.add_subcat(cls(i))
        quiz = quiz[i]
    return quiz


def serialize_fxml(write, elem, short_empty, pretty, level=0):
    """
    """
    tag = elem.tag
    text = elem.text
    if pretty:
        write(level * "  ")
    write(f"<{tag}")
    for key, value in elem.attrib.items():
        value = _escape_attrib_html(value)
        write(f" {key}=\"{value}\"")
    if (isinstance(text, str) and text) or text is not None or \
            len(elem) or not short_empty:
        if len(elem) and pretty:
            write(">\n")
        else:
            write(">")
        write(_escape_cdata(text))
        for child in elem:
            serialize_fxml(write, child, short_empty, pretty, level+1)
        if len(elem) and pretty:
            write(level * "  ")
        write(f"</{tag}>")
    else:
        write(" />")
    if pretty:
        write("\n")
    if elem.tail:
        write(_escape_cdata(elem.tail))


def _escape_cdata(data):
    if data is None:
        return ""
    if isinstance(data, (int, float)):
        return str(data)
    if ("&" in data or "<" in data or ">" in data) and not\
            (str.startswith(data, "<![CDATA[") and str.endswith(data, "]]>")):
        return f"<![CDATA[{data}]]>"
    return data


def _escape_attrib_html(data):
    if data is None:
        return ""
    if isinstance(data, (int, float)):
        return str(data)
    if "&" in data:
        data = data.replace("&", "&amp;")
    if ">" in data:
        data = data.replace(">", "&gt;")
    if "\"" in data:
        data = data.replace("\"", "&quot;")
    return data


def read_fxml(source) -> Tuple[et.Element, Dict[str, str]]:
    """_summary_
    Args:
        source (_type_): _description_
    Returns:
        Tuple[et.Element, Dict[str, str]]: Root and namespaces
    """
    parser = et.XMLPullParser(events=("start-ns",))
    close_source = False
    if not hasattr(source, "read"):
        source = open(source, "rb")
        close_source = True
    try:
        while True:
            data = source.read(65536)
            if not data:
                break
            parser.feed(data)
        root = parser._close_and_return_root()
    finally:
        if close_source:
            source.close()
    ns = dict([node for _, node in parser.read_events()])
    return root, ns


_latex_cache: Dict[str, str] = {}
def render_latex(latex: str, ftype: FileAddr, scale=1.0):
    """TODO optimize. It has just too many calls. But at least it works...
    """
    key = saxutils.escape(latex, entities={'[': '(', ']': ')'})
    if key in _latex_cache:
        return _latex_cache[key]
    res = None
    name = f"eq{len(_latex_cache): 05}.svg"
    if latex[:2] == "$$":
        attr = {'style':'vertical-align:middle;'}
    else:
        attr = {'style':'display:block;margin-left:auto;margin-right:auto;'}
    if shutil.which("dvisvgm"):
        with tempfile.TemporaryDirectory() as workdir:
            def run_me(cmd):
                flag = 0x08000000 if os.name == 'nt' else 0
                return subprocess.run(cmd, stdout=subprocess.PIPE, check=True, 
                                    creationflags=flag, cmd=workdir)

            with open(f"{workdir}/texput.tex", 'w', encoding='utf-8') as fh:
                fh.write("\\documentclass[varwidth,12pt]{standalone}"
                         "\n\\usepackage{amsmath}\n\\usepackage{amsmath}\n\n"
                         "\\begin{document}\n"+ latex + "\n\n\\end{document}")
            run_me(['latex', '-halt-on-error', '-interaction=nonstopmode',
                    'text.tex'])
            if ftype == FileAddr.EMBEDDED:
                res = run_me(["dvisvgm", "--no-fonts", "--stdout", "text.dvi"])
                res = str(base64.b64encode(res.stdout), "utf-8")
            else:
                run_me("dvisvgm", "--no-fonts", "-o", name, "text.dvi")
                shutil.move(f"{workdir}/{name}", ".")
                res = File(name, FileAddr.LOCAL, name, **attr)
    elif EXTRAS_FORMULAE:
        try:
            prop = font_manager.FontProperties(size=12)
            dpi = 120 * scale
            parser = mathtext.MathTextParser("path")
            width, height, depth, _, _ = parser.parse(latex, dpi=72, prop=prop)
            fig = figure.Figure(figsize=(width / 72, height / 72))
            fig.text(0, depth / height, latex, fontproperties=prop, color='Black')
            backend_agg.FigureCanvasAgg(fig)  # set the canvas used
            if ftype != FileAddr.EMBEDDED:
                fig.savefig(name, dpi=dpi, format="svg", transparent=True)
                res = File(name, FileAddr.LOCAL, name, **attr)
            else:
                buffer = BytesIO()
                fig.savefig(name, dpi=dpi, format="svg", transparent=True)
                buffer.close()
                res = str(base64.b64encode(buffer.getvalue()), "utf-8")
        except (ValueError, RuntimeError):
            return None
        except ParseFatalException:
            return None
    _latex_cache[key] = res
    return res


def clean_q_name(string: str):
    """ Cleanup a string to conformed to AMC labels.
    """
    nfkd_form = unicodedata.normalize('NFKD', string)
    remap = {ord('œ'): 'oe', ord('Œ'): 'OE', ord('æ'): 'ae', ord('Æ'): 'AE',
             ord('€'): ' Euros', ord('ß'): 'ss', ord('¿'): '?'}
    out = u"".join([c for c in nfkd_form if not unicodedata.combining(c)])
    out = out.translate(remap)
    out = re.sub(r'[^0-9a-zA-Z:\-]+', ' ', out)
    return out.strip()


def attribute_setup(cls, attr: str, doc: str=""):
    """Generate get/set/del properties for a Ftext attribute.
    """
    def setter(self, value):
        if isinstance(value, cls):
            setattr(self, attr, value)
        elif value is not None:
            raise ValueError(f"Can't assign {value} to {attr}")
    def getter(self) -> FText:
        return getattr(self, attr)
    return property(getter, setter, doc=doc)

# -----------------------------------------------------------------------------


class Serializable:
    """An abstract class to be used as base for all serializable classes. Its
    main usage is to verify equality, and not to do the process itself.
    """

    def __str__(self) -> str:
        return f"{self.__class__} @{hex(id(self))}"

    @staticmethod
    def __itercmp(__a, __b, path: list):
        if not isinstance(__b, __a.__class__):
            return False
        if hasattr(__a, "compare"):
            path.append(__a)
            __a.compare(__b, path)
            path.pop()
        elif isinstance(__a, list):
            if len(__a) != len(__b):
                return False
            tmp: list = copy.copy(__b)
            for ita in __a:
                path.append(ita)
                idx = 0
                for idx, itb in enumerate(tmp):
                    if Serializable.__itercmp(ita, itb, path):
                        break
                else:
                    return False
                tmp.pop(idx)
                path.pop()
        elif isinstance(__a, dict):
            for key, value in __a.items():
                if not Serializable.__itercmp(value, __b.get(key), path):
                    return False
        elif __a != __b:
            return False
        return True

    @staticmethod
    def check_hash(path1: str, path2: str):
        """Return the md5 sum after removing all withspace.
        Args:
            path1 (str): File name 1.
            path2 (str): File name 2.
        Returns:
            bool: if the checksum are equal.
        """
        ignored_exp = [' ', '\t', '\n']
        with open(path1) as f1:
            content1 = f1.read()
            for exp in ignored_exp:
                content1 = content1.replace(exp, '')
        with open(path2) as f2:
            content2 = f2.read()
            for exp in ignored_exp:
                content2 = content2.replace(exp, '')
        h1 = hashlib.md5(content1.encode()).hexdigest()
        h2 = hashlib.md5(content2.encode()).hexdigest()
        return h1 == h2

    def compare(self, __o: object, path: list) -> bool:
        """A
        """
        if not isinstance(__o, self.__class__):
            return False
        for key, val in self.__dict__.items():
            cpr = __o.__dict__.get(key)
            if key not in ("_Question__parent", "_Category__parent") and not \
                    Serializable.__itercmp(val, cpr, path):
                raise ValueError(f"In {path} > {key}. Use debugger.")
        return True


class TList(list):
    """Type List (or Datatype list) is a class that restricts the datatype of
    all the items to a single one defined in constructor. It works exactly like
    an list in C++, Java and other compiled languages. Could use an array 
    instead if it allowed any time to be used. TODO If there is something
    native we could use instead, it is worthy an PR to update.
    """

    def __init__(self, obj_type: type, iterable=None):
        super().__init__()
        self.__type = obj_type
        if iterable is not None:
            self.extend(iterable)

    @property
    def datatype(self):
        """The datatype of the items in this list.
        """
        return self.__type

    @datatype.setter
    def datatype(self, value):
        if not all(isinstance(obj, value) for obj in self):
            self.clear()
        self.__type = value

    def append(self, __object):
        if isinstance(__object, self.__type):
            super().append(__object)

    def extend(self, __iterable):
        if all(isinstance(obj, self.__type) for obj in __iterable):
            super().extend(__iterable)


# -----------------------------------------------------------------------------


class MarkerError(Exception):
    """Exception used when there is a Marker related error
    """


class AnswerError(Exception):
    """Exception used when a parsing fails.
    """


# -----------------------------------------------------------------------------


class File(Serializable):
    """File used in questions. Can be either a local path, an URL, a Embedded
    encoded string.
    Attributes:
        path (str): path to the file in the filesystem or network.
        data (str): file data in base64 format.
        metadata (**kwargs): File specific metadata, such as author, id, etc.
    """

    def __init__(self, path: str, data: str = None, mimetype: str = None,
                 **metadata):
        super().__init__()
        self.data = data
        self.path = path
        self.metadata = metadata
        self.mtype = mimetype
        self.children = None
        if self.mtype is None and path:
            try:
                self.mtype = mimetypes.guess_type(path)[0]
            except Exception:
                pass
        if data is not None:
            self._type = FileAddr.EMBEDDED
        elif os.path.exists(path):
            self._type = FileAddr.LOCAL
        else:
            try:
                with request.urlopen(self.path) as ifile:
                    ifile.read()
                self._type = FileAddr.URL
            except Exception:
                self._type = FileAddr.LOCAL
                _LOG.exception("It was not possible to find the file %s", path)


    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, File):
            return False
        return __o.path == self.path and __o._type and self._type

    def get_data(self):
        if self.data is None:
            if self._type == FileAddr.URL:
                with request.urlopen(self.path) as ifile:
                    self.data = str(base64.b64encode(ifile.read()), "utf-8")
            elif self._type == FileAddr.LOCAL:
                with open(self.path, "rb") as ifile:
                    self.data = str(base64.b64encode(ifile.read()), "utf-8")
        return self.data

    def get_tag(self, path: str = None) -> str:
        """_summary_
        Returns:
            str: _description_
        """
        _path, name = (path or self.path).split("/", 1)
        output_bb = f'<file name="{name}" path="{_path}"'
        for key, value in self.metadata.items():
            output_bb += f' {key}="{value}"'
        self.get_data()
        return f"{output_bb}/>{self.data}</file>"


class LinkRef(Serializable):
    """A text reference of a file or link. Used in a FText to allow instance
    specific metadata.
    Attributes:
        file (File):
        metadata (Dict[str, str]):
    """

    REFS = {
        #Name       #Moodle             #QTI
        "<file>" : ["@@PLUGINFILE@@", "$IMS-CC-FILEBASE$"]
    }

    def __init__(self, tag: str, file: File, **kwargs):
        super().__init__()
        self.tag = tag
        self.file = file
        self.metadata = kwargs

    def _replace_href_scr(self, value: str, format: OutFormat):
        if "$IMS-CC-FILEBASE$" in value:
            new_item = parse.unquote(value).replace("$IMS-CC-FILEBASE$", "/static")
            return new_item.split("?")[0].replace("&amp;", "&")
        elif "$WIKI_REFERENCE$" in value:
            search_key = parse.unquote(value).replace("$WIKI_REFERENCE$/pages/", "")
            search_key = search_key.split("?")[0] + ".html"
            if self.file.path.endswith(search_key):
                return f"/jump_to_id/{self.file.metadata['identifier']}"
            _LOG.warning("Unable to process Wiki link - %s", value)
        elif "$CANVAS_OBJECT_REFERENCE$/external_tools" in value:
            query = parse.parse_qs(html.unescape(parse.urlparse(value).query))
            return query.get("url", [""])[0]
        elif "$CANVAS_OBJECT_REFERENCE$" in value:
            return parse.unquote(value).replace("$CANVAS_OBJECT_REFERENCE$/quizzes/", 
                                                "/jump_to_id/")
        elif "@@PLUGINFILE@@" in value:
            return parse.unquote(value).replace("@@PLUGINFILE@@", "/")

    def _handle_iframe(format: OutFormat):
        if format == OutFormat.OLX:
            elem = et.Element("video")

    def get_tag(self, embedded: bool, format: OutFormat) -> str:
        for val in ("href", "src"):
            if val in self.metadata:
                self.metadata[val] = self._replace_href_scr(self.metadata[val])
        if self.tag == "iframe" and format == OutFormat.OLX:
            output_bb = f'<video ' # TODO probably need something else here
        elif self.tag == "transcript" or self.file.mtype == "transcript":
            return f'<transcript language="" src="">'
        else:
            output_bb = f'<{self.tag}'
        if embedded:
            output_bb += f'data:{self.file.mtype};base64,{self.file.data}" '
        else:
            output_bb += self._replace_href_scr(self.file.path) + '" '
        for key, value in self.metadata.items():
            output_bb += f' {key}="{value}"'
        for key, value in self.file.metadata.items():
            if key not in self.metadata:
                output_bb += f' {key}="{value}"'
        if self.file.children:
            output_bb += '>'
            for value in self.file.children:
                output_bb += value.get_tag()
            output_bb += f'</{self.tag}>'
        else:
            output_bb += '/>'


class Dataset(Serializable):
    """A
    """

    def __init__(self, status: Status, name: str, ctype: str,
                 distribution: Distribution, minimum: float, maximum: float,
                 decimals: int, items: dict = None) -> None:
        super().__init__()
        self.status = status
        self.name = name
        self.ctype = ctype
        self.distribution = distribution
        self.minimum = minimum
        self.maximum = maximum
        self.decimals = decimals
        self.items = items if items else {}

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, self.__class__):
            return False
        if Status.PRV in (self.status, __o.status):
            return False
        return self.__dict__ == __o.__dict__

    def __str__(self) -> str:
        return f"{self.status.name} > {self.name} ({hex(id(self))})"

    def generate(self):
        if self.distribution == Distribution.UNI:
            pass
        else:
            pass


class XItem:

    def __init__(self, tag, attrib: dict = None, closed: bool = False):
        self.tag = tag
        self.attrs = attrib
        self._children = None if closed else []

    def __iter__(self):
        return iter(self._children)

    def append(self, item: XItem):
        self._children.append(item)

    def __str__(self) -> str:
        value = f"<{self.tag} "
        if self.attrs:
            for key, val in self.attrs.items():
                value += f"{key}={val} "
        value += ">"
        for child in self._children:
            value += str(child)
        value = f"</{self.tag}>"
        return value


class XHTMLParser(HTMLParser):
    """A parser for HTML and XML that may contain other formats"""

    def __init__(self, convert_charrefs: bool = True, check_closing: bool = False,
                 files: List[File] = None):
        super().__init__(convert_charrefs=convert_charrefs)
        self.root = XItem("")
        self._stack = [self.root]
        self._check = check_closing
        self.files = files or []

    def __str__(self) -> str:
        """Hope this will not need to be enhanced due to performance metrics
        Returns:
            str: resulting text
        """
        return str(self.root)

    def _get_file_ref(self, tag: str, data: str):
        tag = self._stack[-1].tag
        attrs = self._stack[-1].attrs
        if tag == "file":
            path = attrs.pop("path", "/") + attrs.pop("name")
            file = File(path, data)
        else:
            if attrs.get("src", "")[:5] == "data:":
                data, scr = attrs.pop("src").split(";", 1)
                _, ext = data.split("/", 1)
                path = f"/{len(self.files)}.{ext}"
                file = File(path, scr[7:])  # Consider this is a base64 data
            else:
                path = attrs.pop("src")
                for item in self.files:
                    if item.path == path:
                        return LinkRef(tag, item, **attrs)
                file = File(path, None)
        self.files.append(file)
        return LinkRef(tag, file, **attrs)

    def handle_startendtag(self, tag, attrs):
        if self._check or tag not in ("source", "area", "track", "input", "col",
                 "embed", "hr",  "link", "meta", "br", "base", "wbr", "img"):
            raise ParseFatalException()
        self._stack[-1].append(XItem(tag, attrs, True))

    def handle_starttag(self, tag, attrs):
        self._stack.append(XItem(tag, attrs))
        self.root.append(self._stack[-1])

    def handle_endtag(self, tag):
        self._stack.pop()

    def handle_data(self, data):
        if self._stack[-1].attrs not in ("a", "base", "base", "link", "audio", 
                                "embed", "iframe", "img", "input", "script",  
                                "source","track", "video", "file"):
            self._get_file_ref(data)
        else:
            self._stack[-1].append(data)

    def parse(self, data: str|TextIOWrapper):
        if isinstance(data, str):
            self.feed(data)
            self.close()
        elif isinstance(data, TextIOWrapper):
            for line in data:
                self.feed(line)
            self.close()
        else:
            raise ParseFatalException()


class TextParser():
    """A global text parser to generate FText instances
    """

    def __init__(self, text: str, check_tags: bool, files: List[File] = None,
                 token_map: dict = None):
        self.stack = []
        self.ftext = []
        self.text = text
        self._tmap = token_map
        self.pos = 0
        self.lst = 0
        self.scp = False
        self.stt = [0, False, 0]  # Pos, escaped, Last pos
        self.lastattr = None
        self.check_tags = check_tags
        self.files = files or []

    def _wrapper(self, callback: Callable, size=1):
        if self.text[self.stt[2]: self.stt[0]]:
            self.ftext.append(self.text[self.stt[2]: self.stt[0]])
        self.stt[0] += size
        self.stt[2] = self.stt[0]
        self.ftext.append(callback())
        self.stt[2] = self.stt[0] + 1

    def _get_file_ref(self, tag: str, attrs: dict):
        if tag == "file":
            path = attrs.pop("path", "/") + attrs.pop("name")
            last = self.stt[0] + 1
            while self.text[self.stt[0]:self.stt[0]+2] != "</" and not self.stt[1]:
                self._nxt()
            self.stt[0] = self.stt[0] - 1  # Get back to allow parsing tag
            file = File(path, self.text[last: self.stt[0]])
        else:
            if attrs.get("src", "")[:5] == "data:":
                data, scr = attrs.pop("src").split(";", 1)
                _, ext = data.split("/", 1)
                path = f"/{len(self.files)}.{ext}"
                file = File(path, scr[7:])  # Consider this is a base64 data
            else:
                path = attrs.pop("src")
                for item in self.files:
                    if item.path == path:
                        return LinkRef(tag, item, **attrs)
                file = File(path, None)
        self.files.append(file)
        return LinkRef(tag, file, **attrs)
        
    def _nxt(self):
        self.stt[1] = (self.text[self.stt[0]] == "\\") and not self.stt[1]
        self.stt[0] += 1

    def _get_tag(self) -> LinkRef | None:
        while self.text[self.stt[0]] != ">" and not self.stt[1]:
            self._nxt()
        tmp = self.text[self.stt[2]-1: self.stt[0] + 1]  # includes final ">"
        tag = tmp[1:-1].split(" ", 1)[0]
        result = None
        if tag in ("a", "base", "base", "link", "audio", "embed", "iframe", 
                   "img", "input", "script", "source", "track", "video", "file"):
            data = {k:v for k,v in re.findall(r"(\S+?)=\"(.+?)\"[ />]", tmp)}
            result = self._get_file_ref(tag, data)
        else:
            result = tmp
        if tag[0] == "/":
            tmp = self.stack.pop()
            if self.check_tags and tmp != tag[1:]:
                raise ValueError(f"Tag {tag} is not being closed ({self.stt[2]})")
        elif tmp[-2] != "/" and tag not in ("source", "area", "track", "input",
            "col", "embed", "hr",  "link", "meta", "br", "base", "wbr", "img"):
            self.stack.append(tag)
        return result


    def _get_latex_exp(self):
        while self.text[self.stt[0]] == ")" and self.stt[1]:  # This is correct: "\("
            self._nxt()
        return parse_latex(self.text[self.stt[2]: self.stt[0]])

    def do(self):
        """Modify this functions in super classes.
        """
        if (self.text[self.stt[0]] == "<" and not self.stt[1]):
            self._wrapper(self._get_tag)
        elif EXTRAS_FORMULAE:
            if self.text[self.stt[0]:self.stt[0]+2] == "{=" and not self.stt[1]:
                self._wrapper(self._get_moodle_exp, 2)
            elif self.text[self.stt[0]] == "(" and self.stt[1]: 
                self._wrapper(self._get_latex_exp)  # This is correct: "\("
            elif self.text[self.stt[0]] == "{" and not self.stt[1]:
                self._wrapper(self._get_moodle_var)
        else:
            for key, value in self._tmap.items():
                if self.text[self.stt[0]:self.stt[0]+len(key)] == key and not self.stt[1]:
                    if isinstance(value, str):
                        self._wrapper(getattr(self, value))
                    else:
                        self._wrapper(value(self))

    def clean_up(self):
        if self.text[self.stt[2]:]:
            self.ftext.append(self.text[self.stt[2]:])
        if self.check_tags and len(self.stack) != 0:
            raise ValueError(f"One or more tags are not closed: {self.stack}.")

    def parse(self, data: str|TextIOWrapper):
        if isinstance(data, str):
            self.text = data
        elif isinstance(data, TextIOWrapper):
            self.text = data.read()
        else:
            raise ParseFatalException()
        while self.stt[0] < len(self.text):
            self.do()
            self._nxt()
        self.clean_up()
        return FText(self.ftext, None, self.files)


class FText(Serializable):
    """A formated text. 
    Attributes:
        text (list): 
    """

    def __init__(self, text: str|List[str] = None, formatting = TextFormat.AUTO,
                 files: List[File] = None):
        super().__init__()
        self.formatting = TextFormat(formatting)
        self._text = text
        if text and isinstance(text, list):
            self._text = [text]
        self.files = files  # Local reference of the list of files used.

    def __str__(self) -> str:
        return self.get()

    @property
    def text(self) -> List[str|LinkRef]:
        """A list of strings, file references, questions and math expressions 
        (if EXTRAS_FORMULAE).
        """
        return self._text

    @text.getter
    def text(self) -> list:
        return self._text

    @text.setter
    def text(self, value):
        if isinstance(value, str):
            self._text = [value]
        elif isinstance(value, list):
            self._text = value
        else:
            raise ValueError()

    @classmethod
    def from_string(cls, text: str, formatting=TextFormat.AUTO, check_tags=True,
                    files: list = None, tagmap: dict=None) -> FText:
        """Parses the provided string to a FText class by finding file pointers
        and math expression and returning them as a list.
        Args:
            text (str): _description_
            formatting (_type_, optional): _description_. Defaults to TextFormat.AUTO.
            check_tags (bool, optional): _description_. Defaults to True.
            check_math (bool, optional): _description_. Defaults to True.
            files (list, optional): _description_. Defaults to None.
        Returns:
            FText: _description_
        """
        parser = TextParser(text, check_tags, files, tagmap)
        parser.parse()
        return cls(parser.ftext, formatting, parser.files)

    def get(self, math_type=MathType.ASCII, embedded=False) -> str:
        """Get a string representation of the object
        Args:
            math_type (MathType, optional): Which type of 
        Returns:
            str: A string representation of the object
        """
        from sympy.core import Pow
        if EXTRAS_FORMULAE:
            from sympy import printing, Expr
        data = ""
        for item in self._text:  # Suposse few item, so no poor performance
            if isinstance(item, str):
                data += str(item)
            elif hasattr(item, "MARKER_INT"):
                data += chr(item.MARKER_INT)
            elif isinstance(item, LinkRef):
                data += item.get_tag()
            elif EXTRAS_FORMULAE and isinstance(item, Expr):
                if math_type == MathType.LATEX:
                    data += f"$${printing.latex(item)}$$"
                elif math_type == MathType.MOODLE:
                    data += "{" + ("" if item.is_Atom else "=") + printing.latex(item) + "}"
                elif math_type == MathType.MATHJAX:
                    data += f"[mathjax]{printing.latex(item)}[/mathjax]"
                elif math_type == MathType.MATHML:
                    data += str(printing.mathml(item))
                elif math_type == MathType.ASCII:
                    data += str(printing.pretty(item))
                elif math_type == MathType.FILE:
                    data += render_latex(printing.latex(item), FileAddr.LOCAL)
            else:
                raise TypeError(f"Item has unknown type {type(item)}")
        return data

    @staticmethod
    def prop(attr: str, doc: str="") -> FText:
        """Generate get/set/del properties for a Ftext attribute.
        """
        def setter(self, value):
            data = getattr(self, attr)
            if isinstance(value, FText):
                setattr(self, attr, value)
            elif isinstance(value, (list, str)):
                data.text = value
            elif value is not None:
                raise ValueError(f"Can't assign {value} to {attr}")
        def getter(self) -> FText:
            return getattr(self, attr)
        return property(getter, setter, doc=doc)


class Hint(Serializable):
    """Represents a hint to be displayed when a wrong answer is provided
    to a "multiple tries" question. The hints are give in the listed order.
    """

    def __init__(self, formatting: TextFormat, text: str, show_correct: bool,
                 clear_wrong: bool, state_incorrect: bool = False):
        self.formatting = formatting
        self.text = text
        self.show_correct = show_correct
        self.clear_wrong = clear_wrong
        self.state_incorrect = state_incorrect


class Unit(Serializable):
    """A
    """

    def __init__(self, unit_name: str, multiplier: float):
        super().__init__()
        self.unit_name = unit_name
        self.multiplier = multiplier


class Equation(Serializable):
    """Represents an equation in a formulary. It can be define to be used in
    either a quiz description or a question header.
    """

    def __init__(self, name: str, text: FText):
        self.name = name
        self.text = text


class Table(Serializable):
    """Represents a table in a formulary. It can be define to be used in
    either a quiz description or a question header.
    """

    def __init__(self, name: str, text: FText):
        self.name = name
        self.text = text


class Rule(Serializable):
    """Represents a theory, law or other set of sentences that describe a
    given phenomenum. It can be define to be used in either a quiz description
    or a question header.
    """

    def __init__(self, name: str, text: FText, proof: FText):
        self.name = name
        self.text = text
        self.proof = proof


class Var(Serializable):

    def __init__(self, text: FText):
        self.data = text if not EXTRAS_FORMULAE else []