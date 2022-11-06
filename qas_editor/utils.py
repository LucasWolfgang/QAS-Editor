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
import logging
import shutil
import tempfile
import hashlib
import unicodedata
from io import BytesIO
from xml.sax import saxutils
from importlib import util
from urllib import request
from typing import TYPE_CHECKING
from .enums import FileAddr, TextFormat, Status, Distribution, MathType, MediaType

if TYPE_CHECKING:
    from typing import Dict, List, Tuple

LOG = logging.getLogger(__name__)
EXTRAS_FORMULAE = util.find_spec("sympy") is not None
EXTRAS_GUI = util.find_spec("PyQt5") is not None
                # moodle, sympy, latex
MDL_FUNCTION = {('arctan', 'atan'), ('arcsin', 'asin'), ('arccos', 'acos'),
                ('arctan', 'atan'), ('root', 'sqrt'), ('clip', ''), ('neg', '-')}
_INVALID_HTML_TAG_RE = re.compile(r'<(?!/?[a-zA-Z0-9]+(?: .*|/?)>)(?:.|\n)*?>')


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
            if ftype != FileAddr.EMBEDDED:
                fig.savefig(name, dpi=dpi, format="svg", transparent=True)
                res = File(name, FileAddr.LOCAL, name, **attr)
            else:
                buffer = BytesIO()
                fig.savefig(name, dpi=dpi, format="svg", transparent=True)
                buffer.close()
                res = str(base64.b64encode(buffer.getvalue()), "utf-8")
        except (ValueError, RuntimeError, ParseFatalException):
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
    """File used in questions. Can be either a local path, an URL, a Embedded
    encoded string. TODO May add PIL in the future too.
    """

    MEDIA_TYPES = {("jpeg", "jpg", "png", "svg"): MediaType.IMAGE}

    def __init__(self, path: str, data: str = None, **kwargs):
        super().__init__()
        self.source = data
        self.metadata = kwargs
        if path.startswith("@@PLUGINFILE@@") or data is not None:
            self._type = FileAddr.EMBEDDED
        elif os.path.exists(path):
            self._type = FileAddr.LOCAL
        else:
            try:
                with request.urlopen(self.path) as ifile:
                    ifile.read()
                self._type = FileAddr.URL
            except Exception:
                self._type = FileAddr.EMBEDDED
        self.path = path
        ext = path.rsplit(".", 1)[-1]
        for media_ext in self.MEDIA_TYPES:
            if ext in media_ext:
                self._media = self.MEDIA_TYPES[media_ext]
                break
        else:
            self._media = MediaType.FILE

    def __eq__(self, __o: object) -> bool:
        if not (isinstance(__o, File) and __o._media == self._media
                and __o._type == self._type):
            return False
        if self._type == FileAddr.EMBEDDED:
            tmp1 = self.path.replace("@@PLUGINFILE@@/", "")
            tmp2 = __o.path.replace("@@PLUGINFILE@@/", "")
        return tmp1 == tmp2

    def get_file(self):
        if self._type is FileAddr.LOCAL:
            return self.path
        name = self.path.rsplit("/",1)[1]
        if self._type == FileAddr.URL:
            with request.urlopen(self.path) as ifile, open(name) as ofile:
                ofile.write(ifile.read())
        elif self._type == FileAddr.EMBEDDED:
            with open(name) as ofile:
                ofile.write(base64.b64decode(self.source))
        return name

    def get_tag(self) -> str:
        if self.source is None:
            if self._type == FileAddr.URL:
                with request.urlopen(self.path) as ifile:
                    self.source = str(base64.b64encode(ifile.read()), "utf-8")
            elif self._type == FileAddr.LOCAL:
                with open(self.path, "rb") as ifile:
                    self.source = str(base64.b64encode(ifile.read()), "utf-8")
        name = self.path.rsplit("/",1)[1]
        return f'<file encoding="base64" name="{name}">{self.source}</file>'

    def get_reftag(self) -> str:
        output_bb = f'<img src="{self.path}"'
        for key, value in self.metadata.items():
            output_bb += f' {key}="{value}"'
        return output_bb + '/>'

    def moodle_link(self) -> str:
        """Returns a moodle like for a embedded (base64) file.
        """
        if self.path.startswith("@@PLUGINFILE@@/"):
            return self.path
        return f"@@PLUGINFILE@@/{self.path}"


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


class FText(Serializable):
    """A formated text. 
    """

    def __init__(self, text: str|list = "", formatting: TextFormat = TextFormat.AUTO,
                 bfile: List[File] = None):
        super().__init__()
        self.formatting = TextFormat(formatting)
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

    @classmethod
    def from_string(cls, string: str, exps=("{",), expe=("}",),
                    check_tags=True) -> Tuple[set, FText]:
        """This function suposse that at least once the 
        """
        def nxt(stt: list, string: str):
            stt[1] = (string[stt[0]] == "\\") and not stt[1]
            stt[0] += 1

        def get_exp(stt: list, varset: str, ftext: list, cnt=0):
            nxt(stt, string)
            if cnt == 0:
                ftext.append(string[stt[2]: stt[0]-1])
                stt[2] = stt[0]
                if string[stt[0]] == "=" and not stt[1]:
                    stt[2] +=1
            while all(string[stt[0]:stt[0]+len(en)] != en for en in expe):
                start = any(string[stt[0]:stt[0]+len(st)] == st for st in exps)
                if start and not stt[1]:
                    get_exp(stt, _vars, ftext, cnt+1)
                nxt(stt, string)
            if cnt == 0:
                expr = string[stt[2]: stt[0]]
                if EXTRAS_FORMULAE:
                    expr = expr.replace("{","").replace("}","")
                    expr = expr.replace("pi()","pi")
                    expr = parse_expr(expr)
                    varset |= expr.free_symbols
                    stt[2] = stt[0] + 1
                elif expr.isalpha():
                    varset |= expr
                ftext.append(expr)  

        def get_file(stt: list, ftext: list, stack: list):
            init = stt[0]
            while string[stt[0]] != ">":
                nxt(stt, string)
                if string[stt[0]] == "<":
                    init = stt[0]
            tag = string[init+1: stt[0]].split(" ", 1)[0]
            if tag == "img":
                dta = re.findall(r"(.+?)=\"(.+?)\"[ />]", string[init+5: stt[0]])
                dta = {k:v for k,v in dta}
                path = dta.pop("src")
                ftext.append(string[stt[2]: init])
                ftext.append(File(path, **dta))
                stt[2] = stt[0] + 1
            elif tag == "video":
                pass
            elif tag[0] == "/":
                tmp = stack.pop()
                if check_tags and tmp != tag[1:]:
                    raise ValueError()
            elif tag[-1] != "/":
                stack.append(tag)

        if EXTRAS_FORMULAE:
            from sympy.parsing.sympy_parser import parse_expr 
        ftext = []
        _vars = set()
        stack = []
        stt = [0, False, 0]  # Pointer, is escaped, last
        while stt[0] < len(string):
            if any(string[stt[0]:stt[0]+len(st)] == st for st in exps) and not stt[1]:
                get_exp(stt, _vars, ftext)
            elif string[stt[0]] == "<" and not stt[1]:
                get_file(stt, ftext, stack)
            nxt(stt, string)
        if string[stt[2]:]:
            ftext.append(string[stt[2]:])
        if len(stack) != 0:
            raise ValueError()
        return _vars, cls(ftext)

    def get(self, math_type: MathType = MathType.ASCII) -> str:
        """_summary_
        Args:
            math_type (MathType, optional): _description_. Defaults to MathType.PLAIN.
        Raises:
            TypeError: _description_
        Returns:
            str: _description_
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
            elif isinstance(item, File):
                data += item.get_reftag()
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
