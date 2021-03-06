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
import os
import subprocess
import base64
import copy
import logging
import shutil
import tempfile
from io import BytesIO
from xml.sax import saxutils
from html.parser import HTMLParser
from importlib import util
from urllib import request
from typing import TYPE_CHECKING
from .enums import FileType, TextFormat, Status, Distribution, MathType, MediaType

if TYPE_CHECKING:
    from typing import Dict, List, Callable

LOG = logging.getLogger(__name__)
EXTRAS_FORMULAE = util.find_spec("sympy") is not None
EXTRAS_GUI = util.find_spec("PyQt5") is not None


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


def nxt(stt: list, string: str):
    """A help function to parse text char by char.
    
    Args:
        stt (list): 0 - index, 1 - if escaped
        string (str): the string being parsed
    """
    stt[1] = (string[stt[0]] == "\\") and not stt[1]
    stt[0] += 1


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

_latex_cache: Dict[str, str] = {}
def render_latex(latex: str, ftype: FileType, scale=1.0):
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
            if ftype == FileType.B64:
                res = run_me(["dvisvgm", "--no-fonts", "--stdout", "text.dvi"])
                res = str(base64.b64encode(res.stdout), "utf-8")
            else:
                run_me("dvisvgm", "--no-fonts", "-o", name, "text.dvi")
                shutil.move(f"{workdir}/{name}", ".")
                res = File(name, FileType.LOCAL, name, MediaType.IMAGE, **attr)
    elif EXTRAS_FORMULAE:
        from matplotlib import figure, font_manager, mathtext
        from matplotlib.backends import backend_agg
        from pyparsing import ParseFatalException  # Part of matplotlib package
        try:
            prop = font_manager.FontProperties(size=12)
            dpi = 120 * scale
            parser = mathtext.MathTextParser("path")
            width, height, depth, _, _ = parser.parse(latex, dpi=72, prop=prop)
            fig = figure.Figure(figsize=(width / 72, height / 72))
            fig.text(0, depth / height, latex, fontproperties=prop, color='Black')
            backend_agg.FigureCanvasAgg(fig)  # set the canvas used
            if ftype != FileType.B64:
                fig.savefig(name, dpi=dpi, format="svg", transparent=True)
                res = File(name, FileType.LOCAL, name, MediaType.IMAGE, **attr)
            else:
                buffer = BytesIO()
                fig.savefig(name, dpi=dpi, format="svg", transparent=True)
                buffer.close()
                res = str(base64.b64encode(buffer.getvalue()), "utf-8")
        except (ValueError, RuntimeError, ParseFatalException):
            return None
    _latex_cache[key] = res
    return res



class Serializable:
    """An abstract class to be used as base for all serializable classes
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
    an list in C++, Java and other high-level compiled languages. Could use an
    array instead if it allowed any time to be used. TODO If there is something
    native we could use instead, it is worthy an PR to update.
    """

    def __init__(self, obj_type: object, iterable=None):
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


class ParseError(Exception):
    """Exception used when a parsing fails.
    """


class MarkerError(Exception):
    """Exception used when there is a Marker related error
    """


class AnswerError(Exception):
    """Exception used when a parsing fails.
    """


# -----------------------------------------------------------------------------


class File(Serializable):
    """File used in questions. Can be either a local path, an URL, a B64
    encoded string. TODO May add PIL in the future too. Currently is always
    converted into B64 to be embedded. May also change in the future.
    """

    def __init__(self, name: str, ftype: FileType, source: str = None,
                media: MediaType = MediaType.FILE, **kwargs):
        super().__init__()
        self.name = name
        self.source = source
        self.metadata = kwargs
        self.path = source if ftype in (FileType.LOCAL, FileType.URL) else "/"
        self._type = ftype
        self._media = media

    def set_type(self, value: FileType):
        """Update the resource type and modify it to match that type. FileType
        URL is not a valid value because the idea is to keep data local if it
        is already local.
        """
        if value in (FileType.URL, self._type):
            return  # We dont care about ANY or if the value is the same
        elif value == FileType.B64:
            if self._type == FileType.URL:
                with request.urlopen(self.path) as ifile:
                    self.source = str(base64.b64encode(ifile.read()), "utf-8")
            elif self._type == FileType.LOCAL:
                with open(self.path, "rb") as ifile:
                    self.source = str(base64.b64encode(ifile.read()), "utf-8")
        elif value == FileType.LOCAL:
            if self.path == "/":
                with open(self.name, "w", "utf-8") as ifile:
                    if value == FileType.B64:
                        ifile.write(base64.b64decode(self.source))
                    elif value == FileType.URL:
                        with request.urlopen(self.path) as ofile:
                            ifile.write(ofile.read())
                self.source = self.path = self.name
            else:
                self.source = self.path
        return

    def get_link(self, link: str) -> str:
        tag = "img" if self._media is MediaType.IMAGE else "file"
        output_bb = f'<{tag} src="{link}"'
        for key, value in self.metadata.items():
            output_bb += f' {key}="{value}"'
        return output_bb + '>'

    def moodle_link(self) -> str:
        """Returns a moodle like for a embedded (base64) file.
        """
        return f"@@PLUGINFILE@@/{self.name}"

    def edx_link(self, xid) -> str:
        """Returns a string that acts like a link in EdX text.
        """
        return f"@X@EmbeddedFile.requestUrlStub@X@bbcswebdav/xid-{xid}"


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


class _HTMLResourceParser(HTMLParser):
    """TODO
    """

    def __init__(self, *, convert_charrefs: bool = ...) -> None:
        super().__init__(convert_charrefs=convert_charrefs)
        self.data = []
    
    def handle_starttag(self, tag, attrs):
        if tag == "img":
            pass
        else:
            self.data.append(f"<img")

    def handle_data(self, data):
        self.data.append(data)


class FText(Serializable):
    """A formated text. 
    """

    def __init__(self, name: str, text="", formatting: TextFormat = None,
                 bfile: List[File] = None):
        super().__init__()
        self.name = name
        self.formatting = TextFormat.AUTO if formatting is None else formatting
        self._text = text
        self.bfile = bfile if bfile else []
        self.math_type = MathType.PLAIN

    @property
    def text(self):
        return self._text

    @text.getter
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, value):
        if EXTRAS_FORMULAE:
            if isinstance(value, str):
                self._text = [value]
        else:
            self._text = value

    def get_string(self, resource_callback: Callable):
        if not EXTRAS_FORMULAE:
            return self._text
        from sympy import printing, Symbol
        data = ""
        for item in self._text:  # Suposse few item, so no poor performance
            if isinstance(item, str) or self.math_type == MathType.PLAIN:
                data += str(item)
            elif EXTRAS_FORMULAE and isinstance(item, Symbol):
                if self.math_type == MathType.LATEX:
                    data += f"$${printing.latex(item)}$$"
                elif self.math_type == MathType.MATHJAX:
                    data += f"[mathjax]{printing.latex(item)}[/mathjax]"
                elif self.math_type == MathType.MATHML:
                    data += printing.mathml(item)
                elif self.math_type == MathType.ASCII:
                    data += printing.pretty(item)
                elif self.math_type == MathType.FILE:
                    res = render_latex(printing.latex(item), FileType.LOCAL)
                    resource_callback(res)
            elif isinstance(item, File):
                pass
            else:
                raise TypeError()
        return data

    @staticmethod
    def prop(attr: str, doc: str=""):
        """Generate get/set/del properties for a Ftext attribute.
        """
        def setter(self, value):
            data = getattr(self, attr)
            print(data, value)
            if isinstance(value, FText) and value.name == data.name:
                setattr(self, attr, value)
            elif isinstance(value, str):
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
                 clear_wrong: bool, state_incorrect: bool = False) -> None:
        self.formatting = formatting
        self.text = text
        self.show_correct = show_correct
        self.clear_wrong = clear_wrong
        self.state_incorrect = state_incorrect


class Unit(Serializable):
    """A
    """

    def __init__(self, unit_name: str, multiplier: float) -> None:
        super().__init__()
        self.unit_name = unit_name
        self.multiplier = multiplier


class Equation(Serializable):
    """Represents an equation in a formulary. It can be define to be used in
    either a quiz description or a question header.
    """

    def __init__(self, name: str, text: FText) -> None:
        self.name = name
        self.text = text


class Table(Serializable):
    """Represents a table in a formulary. It can be define to be used in
    either a quiz description or a question header.
    """

    def __init__(self, name: str, text: FText) -> None:
        self.name = name
        self.text = text


class Rule(Serializable):
    """Represents a theory, law or other set of sentences that describe a
    given phenomenum. It can be define to be used in either a quiz description
    or a question header.
    """

    def __init__(self, name: str, text: FText, proof: FText) -> None:
        self.name = name
        self.text = text
        self.proof = proof
