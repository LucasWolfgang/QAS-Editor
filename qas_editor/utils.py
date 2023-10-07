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
from io import BytesIO
from xml.sax import saxutils
from importlib import util
from urllib import request, parse
from xml.etree import ElementTree as et
from typing import Dict, List, Tuple, TypeVar, Generic, Iterable, TYPE_CHECKING
from .enums import FileAddr, OutFormat, TextFormat, Status, Distribution

EXTRAS_FORMULAE = util.find_spec("sympy") is not None
if EXTRAS_FORMULAE:
    from matplotlib import figure, font_manager, mathtext
    from matplotlib.backends import backend_agg
    from pyparsing import ParseFatalException  # Part of matplotlib package
if TYPE_CHECKING:
    from parsers.text import FText

T = TypeVar('T')
KT = TypeVar('KT')  # Key type.
VT = TypeVar('VT')  # Value type.
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


def attribute_setup(cls: T, attr: str, doc: str=""):
    """Generate get/set/del properties for a Ftext attribute.
    """
    def setter(self, value):
        if isinstance(value, cls):
            setattr(self, attr, value)
        elif value is not None:
            raise ValueError(f"Can't assign {value} to {attr}")
    def getter(self) -> T:
        return getattr(self, attr)
    return property[Generic[T]](getter, setter, doc=doc)

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


class TList(Generic[T]):
    """Typed List (or Datatype list) is a class that restricts the datatype of
    all the items to a single one defined in constructor.
    """

    def __init__(self, iterable: Iterable = None):
        self._items: List[T] = []
        if iterable is not None:
            self.extend(iterable)

    def append(self, __object):
        self._items.append(__object)


# -----------------------------------------------------------------------------


class ParseError(Exception):
    """Exception used when there is a Marker related error
    """


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

