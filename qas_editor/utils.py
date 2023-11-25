# Question and Answer Sheet Editor <https://github.com/LucasWolfgang/QAS-Editor>
# Copyright (C) 2022  Lucas Wolfgang
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
## Description

"""
from __future__ import annotations

import base64
import logging
import mimetypes
import os
import re
import shutil
import subprocess
import tempfile
import unicodedata
from enum import Enum
from importlib import util
from io import BytesIO
from typing import Dict, Generic, Iterable, List, Tuple, TypeVar
from urllib import request
from xml.etree import ElementTree as et
from xml.sax import saxutils

from .enums import Distribution, FileAddr, Status, TextFormat

EXTRAS_FORMULAE = util.find_spec("sympy") is not None
if EXTRAS_FORMULAE:
    from matplotlib import figure, font_manager, mathtext
    from matplotlib.backends import backend_agg
    from pyparsing import ParseFatalException  # Part of matplotlib package

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
    """Serializes an XML root item, adding formating
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
                run_me(["dvisvgm", "--no-fonts", "-o", name, "text.dvi"])
                shutil.move(f"{workdir}/{name}", ".")
                res = File(name, FileAddr.LOCAL, **attr)
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
                res = File(name, FileAddr.LOCAL, **attr)
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
    out = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    out = out.translate(remap)
    out = re.sub(r'[^0-9a-zA-Z:\-]+', ' ', out)
    return out.strip()


# -----------------------------------------------------------------------------

class Compare:
    """An abstract class to be used as base for all serializable classes. Its
    main usage is to verify equality, and not to do the process itself.
    """

    @staticmethod
    def _cmp_dict(itma: dict, itmb: dict, path: list):
        for key, value in itma.items():
            if key in ("_QQuestion__parent", "_Category__parent"):
                continue
            path.append(str(key))
            Compare._itercmp(value, itmb.get(key), path)
            path.pop()
        return True

    @staticmethod
    def _cmp_list(itma: list, itmb: list, path: list):
        if len(itma) != len(itmb):
            raise ValueError(f"Len diff ({len(itma)},{len(itmb)}) in {path[:100]}.")
        for idx, (ita, itb) in enumerate(zip(itma, itmb)):
            path.append(idx)
            Compare._itercmp(ita, itb, path)
            path.pop()

    @staticmethod
    def _itercmp(__a, __b, path: list):
        if not isinstance(__b, __a.__class__):
            raise TypeError(f"In {path}. Use debugger.")
        if isinstance(__a, list):
            Compare._cmp_list(__a, __b, path)
        elif isinstance(__a, dict):
            Compare._cmp_dict(__a, __b, path)
        elif hasattr(__a, "__dict__") and not isinstance(__a, Enum):
            Compare._cmp_dict(__a.__dict__, __b.__dict__, path)
        elif (isinstance(__a, str) and __a.strip() != __b.strip()) or (
                not isinstance(__a, str) and __a != __b):
            raise ValueError(f"Value diff ({__a},{__b}) in {path[:100]}.")

    @staticmethod
    def compare( __a: object, __b: object) -> bool:
        """A
        """
        if type(__b) != type(__a):
            return False
        path = []
        Compare._itercmp(__a, __b, path)
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

    def extend(self, __object):
        self._items.extend(__object)


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


class File:
    """File used in questions. Can be either a local path, an URL, a Embedded
    encoded string.
    Attributes:
        path (str): path to the file in the filesystem or network.
        data (str): file data in base64 format.
        metadata (**kwargs): File specific metadata, such as author, id, etc.
    """

    ROOTS = (
        #Moodle            #QTI                #Relative paths
        "@@PLUGINFILE@@", "$IMS-CC-FILEBASE$", "", ".", ".."
    )

    def __init__(self, path: str, data: str = None, **metadata):
        super().__init__()
        self.data = data
        path = path.replace("\\", "/")
        tmp = path.split("/", 1)
        if len(tmp) == 1:
            tmp.insert(0, "")
        if tmp[0] in self.ROOTS:
            path = "///"+tmp[1]
        self.path = path
        self.metadata = metadata
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


class Dataset:
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
        """_summary_
        """
        if self.distribution == Distribution.UNI:
            pass
        else:
            pass


class Hint:
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


class Unit:
    """A
    """

    def __init__(self, unit_name: str, multiplier: float):
        super().__init__()
        self.unit_name = unit_name
        self.multiplier = multiplier
 