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

import logging
from html import parser, unescape
from importlib import util
from io import TextIOWrapper
from typing import Callable, List
from urllib import parse

from ..enums import FileAddr, MathType, OutFormat
from ..utils import File, ParseError, render_latex

EXTRAS_FORMULAE = util.find_spec("sympy") is not None
if EXTRAS_FORMULAE:
    from sympy import Expr, printing

_LOG = logging.getLogger(__name__)


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

    def get(self, mtype: MathType, ftype: FileAddr, otype: OutFormat) -> str:
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
                value += FText.to_string(child, mtype, ftype, otype)
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
            query = parse.parse_qs(unescape(parse.urlparse(value).query))
            return query.get("url", [""])[0]
        elif "$CANVAS_OBJECT_REFERENCE$" in value:
            return parse.unquote(value).replace("$CANVAS_OBJECT_REFERENCE$/quizzes/", 
                                                "/jump_to_id/")
        elif "@@PLUGINFILE@@" in value:
            return parse.unquote(value).replace("@@PLUGINFILE@@", "/")

    def get(self, embedded: bool, otype: OutFormat) -> str:
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
        if self.tag == "iframe" and otype == OutFormat.OLX:
            output_bb = '<video ' # TODO probably need something else here
        elif self.tag == "transcript" or self.file.mtype == "transcript":
            return '<transcript language="" src="">'
        else:
            output_bb = f'<{self.tag}'
        if embedded:
            output_bb += f'data:{self.file.mtype};base64,{self.file.data}" '
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


class XHTMLParser(parser.HTMLParser):
    """A parser for HTML and XML that may contain other formats"""

    AUTOCLOSE = ("source", "area", "track", "input", "col", "embed", "hr", 
                 "link", "meta", "br", "base", "wbr", "img")
    REFS = ("a", "base", "base", "input", "link", "img", "audio", "embed",
            "video", "file", "track", "script", "source", "iframe")

    def __init__(self, convert_charrefs: bool = True, check_closing: bool = False,
                 files: List[File] = None):
        super().__init__(convert_charrefs=convert_charrefs)
        self.ftext: list = None
        self._stack: List[XItem] = [XItem("")]
        self._check = check_closing
        self.files = files or []

    def handle_startendtag(self, tag: str, attrs: tuple):
        if self._check or tag not in self.AUTOCLOSE:
            raise ParseError()
        attrs = dict(attrs)
        if tag in self.REFS:
            xitem = LinkRef(tag, None, attrs)
            if attrs.get("src", "")[:5] == "data:":
                data, scr = attrs.pop("src").split(";", 1)
                _, ext = data.split("/", 1)
                path = f"/{len(self.files)}.{ext}"
                xitem.file = file = File(path, scr[7:])
            else:
                path = attrs.pop("src")
                for item in self.files:
                    if item.path == path:
                        file = xitem.file = item
                        break
                else:
                    file = xitem.file = File(path)
            if file not in self.files:
                self.files.append(file)
        else:
            xitem = XItem(tag, attrs)
        self._stack[-1].append(xitem)

    def handle_starttag(self, tag: str, attrs: tuple):
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
            file = File(path, data)
            if file not in self.files:
                self.files.append(file)
        else:
            self._stack[-1].append(data)

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


class TextParser():
    """A global text parser to generate FText instances
    """

    def __init__(self, **_):
        self.ftext = []
        self.text = ""
        self.pos = 0
        self.lst = 0
        self.scp = False

    def _nxt(self):
        self.scp = (self.text[self.pos] == "\\") and not self.scp
        self.pos += 1

    def do(self):
        """Modify this functions in super classes.
        """

    def clean_up(self):
        """Clean up process
        """
        if self.text[self.lst:]:
            self.ftext.append(self.text[self.lst:])

    def parse(self, data: str|TextIOWrapper):
        """Parse the data provided.
        Args:
            data (str | TextIOWrapper): data to be parsed
        Raises:
            ParseError: If the data is not a string or TextIO
        """
        if isinstance(data, str):
            self.text = data
        elif isinstance(data, TextIOWrapper):
            self.text = data.read()
        else:
            raise ParseError()
        while self.pos < len(self.text):
            self.do()
            self._nxt()
        self.clean_up()


class FText:
    """A formated text. 
    Attributes:
        text (list): 
        files (List[File]): Local reference of the list of files used.
    """

    def __init__(self, parser = None):
        super().__init__()
        if parser is not None:
            self._text = parser.ftext
            if hasattr(parser, "files"):
                self._files = parser.files
            else:
                self._files = []
        else:
            self._text = []
            self._files = []

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
    def to_string(item, mtype: MathType, ftype: FileAddr, otype: OutFormat) -> str|File:
        """_summary_
        Args:
            item (_type_): _description_
            math_type (MathType, optional): _description_. Defaults to None.
        Returns:
            str: _description_
        """
        if isinstance(item, str):
            res = item
        elif isinstance(item, XItem):
            res = item.get(mtype, ftype, otype)
        elif hasattr(item, "MARKER_INT"):
            res = chr(item.MARKER_INT)
        elif isinstance(item, LinkRef):
            res = item.get(ftype == FileAddr.EMBEDDED, otype)
        elif EXTRAS_FORMULAE and isinstance(item, Expr):
            if mtype == MathType.LATEX:
                res = f"$${printing.latex(item)}$$"
            elif mtype == MathType.MOODLE:
                res =  "{" + ("" if item.is_Atom else "=") + printing.latex(item) + "}"
            elif mtype == MathType.MATHJAX:
                res =  f"[mathjax]{printing.latex(item)}[/mathjax]"
            elif mtype == MathType.MATHML:
                res = str(printing.mathml(item))
            elif mtype == MathType.ASCII:
                res = str(printing.pretty(item))
            elif mtype == MathType.FILE:
                res = render_latex(printing.latex(item), ftype)
        else:
            raise TypeError(f"Item has unknown type {type(item)}")
        return res

    def get(self, mtype=MathType.ASCII, ftype=FileAddr.LOCAL, 
            otype: OutFormat=OutFormat.QTI) -> str:
        """Get a string representation of the object. This representation 
        replaces Items with marker.
        Args:
            math_type (MathType, optional): Which type of 
        Returns:
            str: A string representation of the object
        """
        data = ""
        for item in self._text:
            data += self.to_string(item, mtype, ftype, otype)
        return data
