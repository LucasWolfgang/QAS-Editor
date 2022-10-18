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
            if ftype == FileType.EMBEDDED:
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
            if ftype != FileType.EMBEDDED:
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
                 media: MediaType = None, **kwargs):
        super().__init__()
        self.name = name
        self.source = source
        self.metadata = kwargs
        self.path = source if ftype in (FileType.LOCAL, FileType.URL) else "/"
        self._type = ftype
        self._media = media if media else MediaType.FILE

    def set_type(self, value: FileType):
        """Update the resource type and modify it to match that type. FileType
        URL is not a valid value because the idea is to keep data local if it
        is already local.
        """
        if value in (FileType.URL, self._type):
            return  # We dont care about ANY or if the value is the same
        elif value == FileType.EMBEDDED:
            if self._type == FileType.URL:
                with request.urlopen(self.path) as ifile:
                    self.source = str(base64.b64encode(ifile.read()), "utf-8")
            elif self._type == FileType.LOCAL:
                with open(self.path, "rb") as ifile:
                    self.source = str(base64.b64encode(ifile.read()), "utf-8")
        elif value == FileType.LOCAL:
            if self.path == "/":
                with open(self.name, "w", "utf-8") as ifile:
                    if value == FileType.EMBEDDED:
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


class QHTMLParser(HTMLParser):
    """TODO
    """
    STARTEND = ["img", "input", "br", "hr", "meta"]

    class Element:

        def __init__(self, tag, attrib):
            self.tag = tag
            self.attrib = attrib
            self._children = []
            self.text = []

        def __repr__(self):
            return "<%s %r at %#x>" % (self.__class__.__name__, self.tag, id(self))

        def __len__(self):
            return len(self._children)

        def __getitem__(self, index):
            return self._children[index]

        def __setitem__(self, index, element):
            if isinstance(index, slice):
                for elt in element:
                    self._assert_is_element(elt)
            else:
                self._assert_is_element(element)
            self._children[index] = element

        def __delitem__(self, index):
            del self._children[index]


    def __init__(self, *, convert_charrefs: bool = ...) -> None:
        super().__init__(convert_charrefs=convert_charrefs)
        self.data = QHTMLParser.Element("top")
        self._current = self.data
        self._parent: List[QHTMLParser.Element] = []

    def handle_data(self, data):
        if not self._current.text:
            self._current.text = data
        else:
            self._current.tail = data

    def handle_starttag(self, tag, attrs):
        #print(f"{'-':>{len(self._parent)}}Start: {tag} {attrs}")
        attrs = {k:v for k, v in attrs}
        if tag not in self.STARTEND:
            self._parent.append(self._current)
            self._current = QHTMLParser.Element(tag, **attrs)
            self._parent[-1].append(self._current)

    def handle_endtag(self, tag: str) -> None:
        self._current = self._parent.pop()
        #print(f"{'-':>{len(self._parent)}}End: {tag}")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]):
        attrs = {k:v for k, v in attrs}
        #print(f"{'.':>{len(self._parent)}}Startend: {tag}")
        self._parent[-1].append(QHTMLParser.Element(tag, **attrs))

    def handle_entityref(self, name: str) -> None:
        print(f"Enti {name}")

    def handle_charref(self, name: str) -> None:
        print(f"Char {name}")

    def handle_comment(self, data: str) -> None:
        print(f"Comm {data}")

    def handle_decl(self, decl: str) -> None:
        print(f"Decl {decl}")

    def handle_pi(self, data: str) -> None:
        print(f"Pi {data}")

    @staticmethod
    def parse():
        data = """<?xml version='1.0' encoding='utf-8'?>
<p>a link <a href="https://github.com/nennigb/amc2moodle">here </a>and an image <img src="@@PLUGINFILE@@/4.png" alt="" role="presentation" style="" />and an equation \( \int_{2\pi} x^2 \mathrm{d} x \)</p>
<p style="text-align: center;">centered text</p>
<p style="text-align: left;">flush left text</p>
<p style="text-align: right;">flush right text</p>
<p style="text-align: left;">In moodle editor, there is also <sub>exponent</sub> and <sup>indice</sup> and <strike>that</strike></p>
<p style="text-align: left;">and svg file <img src="@@PLUGINFILE@@/dessin.svg" alt="escargot" style="vertical-align: text-bottom; margin: 0 0.5em;" class="img-responsive" width="100" height="141" /><br /></p>
"""
        parser = QHTMLParser()
        parser.feed(data)
        parser.close()
    #     return parser.data

    # def write(self):
        with open("test.xml", "w") as ofile:
            ofile.write("<?xml version='1.0' encoding='utf-8'?>\n")
            serialize_fxml(ofile.write, parser.data, True, True)


class FText(Serializable):
    """A formated text. 
    """

    def __init__(self, text: str = "", formatting: TextFormat = None,
                 bfile: List[File] = None):
        super().__init__()
        self.formatting = TextFormat.AUTO if formatting is None else formatting
        self._text = [text] if isinstance(text, str) else text
        self.bfile = bfile if bfile else []

    def __str__(self) -> str:
        return self.get()

    @property
    def text(self):
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

    def get(self, math_type: MathType = MathType.PLAIN,
            resource_callback: Callable = None) -> str:
        """_summary_
        Args:
            math_type (MathType, optional): _description_. Defaults to MathType.PLAIN.
            resource_callback (Callable, optional): _description_. Defaults to None.
        Raises:
            TypeError: _description_
        Returns:
            str: _description_
        """
        if len(self._text) == 1 or not EXTRAS_FORMULAE:
            return self._text[0]
        from sympy import printing, Symbol
        data = ""
        for item in self._text:  # Suposse few item, so no poor performance
            if isinstance(item, str) or math_type == MathType.PLAIN:
                data += str(item)
            elif hasattr(item, "MARKER_INT"):
                data += chr(item.MAKER_INT)
            elif EXTRAS_FORMULAE and isinstance(item, Symbol):
                if math_type == MathType.LATEX:
                    data += f"$${printing.latex(item)}$$"
                elif math_type == MathType.MATHJAX:
                    data += f"[mathjax]{printing.latex(item)}[/mathjax]"
                elif math_type == MathType.MATHML:
                    data += str(printing.mathml(item))
                elif math_type == MathType.ASCII:
                    data += str(printing.pretty(item))
                elif math_type == MathType.FILE:
                    res = render_latex(printing.latex(item), FileType.LOCAL)
                    if callable(resource_callback):
                        resource_callback(res)
            else:
                raise TypeError()
        return data

    @staticmethod
    def prop(attr: str, doc: str=""):
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
