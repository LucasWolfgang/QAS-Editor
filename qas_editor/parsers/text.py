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
import os
import shutil
import subprocess
import tempfile
from html import parser, unescape
from importlib import util
from io import BytesIO, TextIOWrapper
from typing import Dict, List
from urllib import parse
from xml.sax import saxutils

from ..enums import FileAddr, MathType, Platform, TextFormat
from ..utils import File, ParseError

EXTRAS_FORMULAE = util.find_spec("sympy") is not None
if EXTRAS_FORMULAE:
    from matplotlib import figure, font_manager, mathtext
    from matplotlib.backends import backend_agg
    from pyparsing import ParseFatalException  # Part of matplotlib package
    from sympy import Expr, printing

_LOG = logging.getLogger(__name__)


_latex_cache: Dict[str, str] = {}
def render_latex(latex: str, path: str, scale=1.0):
    """TODO optimize. It has just too many calls. But at least it works...
    """
    key = saxutils.escape(latex, entities={'[': '(', ']': ')'})
    if key in _latex_cache:
        return _latex_cache[key]
    res = None
    name = f"eq{len(_latex_cache): 10}.svg"
    if latex[:2] == "$$":
        attr = {'style':'vertical-align:middle;'}
    else:
        attr = {'style':'display:block;margin-left:auto;margin-right:auto;'}
    if shutil.which("dvisvgm"):
        def run_me(cmd):
            flag = 0x08000000 if os.name == 'nt' else 0
            return subprocess.run(cmd, stdout=subprocess.PIPE, check=True, 
                                    creationflags=flag, cmd=path)

        with open(f"{path}/texput.tex", 'w', encoding='utf-8') as fh:
            fh.write("\\documentclass[varwidth,12pt]{standalone}"
                        "\n\\usepackage{amsmath}\n\\usepackage{amsmath}\n\n"
                        "\\begin{document}\n"+ latex + "\n\n\\end{document}")
        run_me(['latex', '-halt-on-error', '-interaction=nonstopmode',
                'text.tex'])
        if path:
            res = run_me(["dvisvgm", "--no-fonts", "--stdout", "text.dvi"])
            res = str(base64.b64encode(res.stdout), "utf-8")
        else:
            run_me(["dvisvgm", "--no-fonts", "-o", name, "text.dvi"])
            shutil.move(f"{path}/{name}", ".")
            res = f"{path}/{name}"
    elif EXTRAS_FORMULAE:
        try:
            prop = font_manager.FontProperties(size=12)
            dpi = 120 * scale
            parser = mathtext.MathTextParser("path")
            width, height, depth, _, _ = parser.parse(latex, dpi=72, prop=prop)
            fig = figure.Figure(figsize=(width / 72, height / 72))
            fig.text(0, depth / height, latex, fontproperties=prop, color='Black')
            backend_agg.FigureCanvasAgg(fig)  # set the canvas used
            if path:
                fig.savefig(f"{path}/{name}", dpi=dpi, format="svg", transparent=True)
                res = f"{path}/{name}"
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



class Var:
    """A variable used in case there is no sympy installed.
    """

    def __init__(self, text: str):
        self.data = text if not EXTRAS_FORMULAE else []


class XItem:
    """An (X)HTML item for the (X)HTML parser
    """

    def __init__(self, tag, attrib: dict = None, closed: bool = False):
        self.tag = tag
        self.attrs = attrib or None
        self._children = None if closed else []

    def __eq__(self, val: object) -> bool:
        return (isinstance(val, XItem) and val.tag == self.tag and
            val.attrs == self.attrs and val._children == self._children)

    def __getitem__(self, idx: int) -> XItem:
        return self._children[idx]

    def __iter__(self):
        return iter(self._children)

    def __len__(self):
        return len(self._children)

    def append(self, item: XItem):
        """"Appends a child to the item.
        Args:
            item (XItem): _description_
        """
        self._children.append(item)

    def extend(self, items: list):
        self._children.extend(items)

    def get(self, path: str, otype: Platform, ttype: TextFormat) -> str:
        """_summary_
        Args:
            mtype (MathType): _description_
            ftype (FileAddr): _description_
        Returns:
            str: _description_
        """
        value = f"<{self.tag} "
        if self.attrs:
            for key, val in self.attrs.items():
                value += f"{key}={val} "
        if self._children:
            value = value.rstrip() + ">"
            for child in self._children:
                value += FText.to_string(child, path, otype, ttype)
            value += f"</{self.tag}>"
        else:
            value = value.rstrip() + "/>"
        return value


class LinkRef:
    """A text reference of a file or link. Used in a FText to allow instance
    specific metadata.
    Attributes:
        file (File):
        metadata (Dict[str, str]):
    """

    def __init__(self, tag: str, file: File, attrs):
        super().__init__()
        self.tag = tag
        self.file = file
        self.attrs = attrs

    def _replace_href_scr(self, value: str, format: Platform):
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
            query = parse.parse_qs(unescape(parse.urlparse(value).query))
            return query.get("url", [""])[0]
        elif "$CANVAS_OBJECT_REFERENCE$" in value:
            return parse.unquote(value).replace("$CANVAS_OBJECT_REFERENCE$/quizzes/", 
                                                "/jump_to_id/")
        elif "@@PLUGINFILE@@" in value:
            return parse.unquote(value).replace("@@PLUGINFILE@@", "/")

    def get(self, embedded: bool, otype: Platform) -> str:
        """_summary_
        Args:
            embedded (bool): _description_
            format (OutFormat): _description_
        Returns:
            str: _description_
        """
        for val in ("href", "src"):
            if val in self.attrs:
                self.attrs[val] = self._replace_href_scr(self.attrs[val])
        if self.tag == "iframe" and otype == Platform.OLX:
            output_bb = '<video ' # TODO probably need something else here
        elif self.tag == "transcript" or self.file.mime == "transcript":
            return '<transcript language="" src="">'
        else:
            output_bb = f'<{self.tag}'
        if embedded:
            output_bb += f'data:{self.file.mime};base64,{self.file.data}" '
        else:
            output_bb += self._replace_href_scr(self.file.path) + '" '
        for key, value in self.attrs.items():
            output_bb += f' {key}="{value}"'
        for key, value in self.file.metadata.items():
            if key not in self.attrs:
                output_bb += f' {key}="{value}"'
        if self.file.children:
            output_bb += '>'
            for value in self.file.children:
                output_bb += value.get_tag()
            output_bb += f'</{self.tag}>'
        else:
            output_bb += '/>'


class PlainParser():
    """A interface for plain text files that dont need any parsing. Same as
    justing putting the text in a list.
    """

    def __init__(self, rpath: str):
        self.ftext = []
        self._rpath = rpath

    def parse(self, data: str|TextIOWrapper):
        """Parse the data provided.
        Args:
            data (str | TextIOWrapper): data to be parsed
        Raises:
            ParseError: If the data is not a string or TextIO
        """
        if isinstance(data, str):
            self.ftext = [data]
        elif isinstance(data, TextIOWrapper):
            self.ftext = [data.read()]
        else:
            raise ParseError()


class XHTMLParser(parser.HTMLParser):
    """A parser for HTML and XML that may contain other formats"""

    AUTOCLOSE = ("source", "area", "track", "input", "col", "embed", "hr", 
                 "link", "meta", "br", "base", "wbr", "img")
    REFS = ("a", "base", "base", "input", "link", "img", "audio", "embed",
            "video", "file", "track", "script", "source", "iframe")

    def __init__(self, rpath: str, convert_charrefs: bool = True, 
                 check_closing: bool = False, files: List[File] = None):
        super().__init__(convert_charrefs=convert_charrefs)
        self.ftext: list = None
        self.files = files or []
        self._stack: List[XItem] = [XItem("")]
        self._check = check_closing
        self._rpath = rpath

    def handle_startendtag(self, tag: str, attrs: List[tuple]):
        if self._check and tag not in self.AUTOCLOSE:
            raise ParseError(f"Tag {tag} should not be autoclosed")
        attrs = dict(attrs)
        if tag in self.REFS:
            xitem = LinkRef(tag, None, attrs)
            if attrs.get("src", "")[:5] == "data:":
                data, scr = attrs.pop("src").split(";", 1)
                _, ext = data.split("/", 1)
                path = f"/{len(self.files)}.{ext}"
                xitem.file = file = File(path, scr[7:], self._rpath)
            else:
                path = attrs.pop("src")
                for item in self.files:
                    if item.path == path:
                        file = xitem.file = item
                        break
                else:
                    file = xitem.file = File(path, None, self._rpath)
            if file not in self.files:
                self.files.append(file)
        else:
            xitem = XItem(tag, attrs, True)
        self._stack[-1].append(xitem)

    def handle_starttag(self, tag: str, attrs: tuple):
        if tag in self.AUTOCLOSE:
            return self.handle_startendtag(tag, attrs)
        if tag in self.REFS:
            item = LinkRef(tag, None, dict(attrs))
        else:
            item = XItem(tag, dict(attrs))
        self._stack.append(item)
        self._stack[-2].append(item)

    def handle_endtag(self, _):
        self._stack.pop()

    def handle_data(self, data: str):
        if self._stack[-1].tag == "file":
            attrs = self._stack[-1].attrs
            path = attrs.pop("path", "/") + attrs.pop("name")
            file = File(path, data, self._rpath)
            if file not in self.files:
                self.files.append(file)
        elif isinstance(self._stack[-1], XItem):
            self._stack[-1].append(data)
        else:
            _LOG.warning(f"A {self._stack[-1]. __class__} got an unexpected value: {data}")

    def parse(self, data: str|TextIOWrapper):
        """Parse the data provided.
        Args:
            data (str | TextIOWrapper): data to be parsed
        Raises:
            ParseError: If the data is not a string or TextIO
        """
        if isinstance(data, str):
            self.feed(data)
            self.close()
        elif isinstance(data, TextIOWrapper):
            for line in data:
                self.feed(line)
            self.close()
        else:
            raise ParseError()
        self.ftext = list(self._stack[0])


class Parser():
    """Abstract class to represent parsers. All parsers must have (at least) 
    these attributes and methods.
    """

    def __init__(self):
        self.ftext: list = []
        self.files: List[File] = None
        self._rpath: str = None

    def parse(self, data: str|TextIOWrapper) -> None:
        """Parse the data provided.
        Args:
            data (str | TextIOWrapper): data to be parsed
        Raises:
            ParseError: If the data is not a string or TextIO
        """
        return None


class FText:
    """A formatted text.
    """

    def __init__(self, parser: Parser|str = None, files: List[File] = None):
        self._text = []
        self._files = files if files is not None else []
        if parser is not None:
            self.add(parser)

    def __iter__(self):
        return iter(self._text)

    def __len__(self):
        return len(self._text)

    def __getitem__(self, idx: int):
        return self._text[idx] 

    @property
    def files(self):
        """Files referenced in this FText instance.
        """
        return self._files

    @files.setter
    def files(self, value):
        if isinstance(value, list):
            self._files = value

    @property
    def text(self) -> list:
        """A list of strings, file references, questions and math expressions 
        (if EXTRAS_FORMULAE).
        """
        return self._text

    @staticmethod
    def to_string(item, path: str, otype: Platform, ttype: TextFormat) -> str:
        """_summary_
        Args:
            item (_type_): _description_
            math_type (MathType, optional): _description_. Defaults to None.
        Returns:
            str: _description_
        """
        res = ""
        if isinstance(item, str):
            res = item
        elif isinstance(item, XItem):
            res = item.get(path, otype, ttype)
        elif hasattr(item, "MARKER_INT"):
            res = chr(item.MARKER_INT)
        elif isinstance(item, LinkRef):
            res = item.get(path, otype)
        elif EXTRAS_FORMULAE and isinstance(item, Expr):
            if ttype == TextFormat.PLAIN:
                res = str(printing.pretty(item))
            elif ttype in (TextFormat.LATEX, TextFormat.MD):
                res = f"$${printing.latex(item)}$$"
            elif ttype == TextFormat.HTML:
                res = str(printing.mathml(item))
            elif ttype == TextFormat.XHTML:
                if path:
                    res = f'<img src="{render_latex(printing.latex(item), path)}"/>'
                else:
                    res = str('<img src="data:image/png;base64, ' +
                          render_latex(printing.latex(item), path) + '"/>')
            elif otype == Platform.MOODLE and path:
                res = str("{" + ("" if item.is_Atom else "=") + printing.latex(item) + "}")
            elif otype == Platform.OLX:
                res =  f"[mathjax]{printing.latex(item)}[/mathjax]"
        else:
            raise TypeError(f"Item has unknown type {type(item)}")
        return res

    def get(self, mtype=MathType.ASCII, ftype=FileAddr.LOCAL, 
            otype: Platform=Platform.NONE) -> str:
        """Get a string representation of the object. This representation 
        replaces Items with marker.
        Args:
            math_type (MathType, optional): Which type of 
        Returns:
            str: A string representation of the object
        """
        data = ""
        for item in self._text:
            tmp = self.to_string(item, mtype, ftype, otype)
            if tmp:
                data += tmp
        return data

    def add(self, parser: Parser|str):
        if isinstance(parser, str):
            self._text.append(parser)
        else:
            self._text.extend(parser.ftext)
            if hasattr(parser, "files"):
                for file in parser.files:
                    if file not in self._files:
                        self._files.append(file)

