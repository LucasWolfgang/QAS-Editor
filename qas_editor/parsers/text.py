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

from html.parser import HTMLParser
from importlib import util
from io import TextIOWrapper
from typing import Callable, List

from ..enums import FileAddr, MathType, OutFormat
from ..utils import File, LinkRef, ParseError, render_latex

EXTRAS_FORMULAE = util.find_spec("sympy") is not None
if EXTRAS_FORMULAE:
    from sympy import Expr, printing

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
        self.attrs = attrib
        self._children = None if closed else []

    def __iter__(self):
        return iter(self._children)

    def append(self, item: XItem):
        """"Appends a child to the item.
        Args:
            item (XItem): _description_
        """
        self._children.append(item)

    def get(self, mtype: MathType, ftype: FileAddr) -> str:
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
        value += ">"
        for child in self._children:
            value += FText.to_string(child, mtype, ftype)
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

    def _get_file_ref(self, data: str):
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
            raise ParseError()
        self._stack[-1].append(XItem(tag, attrs, True))

    def handle_starttag(self, tag, attrs):
        self._stack.append(XItem(tag, attrs))
        self.root.append(self._stack[-1])

    def handle_endtag(self, tag):
        self._stack.pop()

    def handle_data(self, data):
        if self._stack[-1].tag not in ("", "a", "base", "base", "input", "link",
                                       "audio", "embed", "img", "video", "file", 
                                       "script", "source", "iframe", "track"):
            self._get_file_ref(data)
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


class TextParser():
    """A global text parser to generate FText instances
    """

    def __init__(self, **_):
        self.ftext = []
        self.text = ""
        self.pos = 0
        self.lst = 0
        self.scp = False

    def _wrapper(self, callback: Callable, size=1):
        if self.text[self.lst: self.pos]:
            self.ftext.append(self.text[self.lst: self.pos])
        self.pos += size
        self.lst = self.pos
        self.ftext.append(callback())
        self.lst = self.pos + 1

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

    def __init__(self, files: List[File] = None):
        super().__init__()
        self._files = files or []
        self._text = []

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
        if isinstance(item, str) or hasattr(item, "__str__"):
            res = str(item)
        elif hasattr(item, "MARKER_INT"):
            res = chr(item.MARKER_INT)
        elif isinstance(item, LinkRef):
            res = item.get_tag(ftype == FileAddr.EMBEDDED, otype)
        elif EXTRAS_FORMULAE and isinstance(item, Expr):
            if mtype == MathType.LATEX:
                res = f"$${printing.latex(item)}$$"
            elif mtype == MathType.MOODLE:
                res =  "{" + ("" if item.is_Atom else "=") + printing.latex(item) + "}"
            elif mtype == MathType.MATHJAX:
                res =  f"[mathjax]{printing.latex(item)}[/mathjax]"
            elif mtype == MathType.MATHML:
                res =  str(printing.mathml(item))
            elif mtype == MathType.ASCII:
                res =  str(printing.pretty(item))
            elif mtype == MathType.FILE:
                res = render_latex(printing.latex(item), ftype)
        else:
            raise TypeError(f"Item has unknown type {type(item)}")
        return res

    def parse(self, text: str, parser: Callable, **args):
        """Parses the provided string to a FText class by finding file pointers
        and math expression and returning them as a list.
        Args:
            text (str): _description_
        Returns:
            FText: _description_
        """
        if parser is None:
            self._text.append(text)
        else:
            if "files" not in args:
                args["files"] = self._files
            tmp = parser(**args).parse(text)
            self._text = tmp.ftext

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
