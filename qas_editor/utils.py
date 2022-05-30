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
import copy
import logging
from xml.etree import ElementTree as et
from io import BytesIO
from PIL import Image
import base64

LOG = logging.getLogger(__name__)

PDF_IMAGE_FILTER = {"/DCTDecode": "jpg",  "/JPXDecode": "jp2",
                        "/CCITTFaxDecode": "tiff", "/FlateDecode": "png" }
PDF_IMAGE_CHANNEL = {"DeviceGray": "L",    # 8-bit pixels, black and white
                        "DeviceRGB": "RGB",   # 3x8-bit pixels, true color
                        "DeviceCMYK": "CMYK", # 4x8-bit pixels, color separation
                        "/DeviceN": "P", 
                        "/Indexed": "P"
                        }

def extract_pdf_images(file_path, page, external_refs: bool):
    images = {}
    rsc = page['/Resources']
    path = file_path.rsplit('.',1)[0]
    if '/XObject' in rsc:
        for xobj in rsc['/XObject'].values():
            if xobj['/Subtype'] != '/Image':
                continue
            # Getting image
            size = (xobj['/Width'], xobj['/Height'])
            data = xobj.read_from_stream()
            color_space = xobj['/ColorSpace'][0]
            mode = PDF_IMAGE_FILTER[color_space]
            if color_space == "/Indexed":
                psize = int(xobj['/ColorSpace'][2])
                palette = [255-int(n*psize/255) for n in \
                            range(256) for _ in range(3)]
            else:
                palette = None
            xformat = PDF_IMAGE_FILTER.get(xobj['/Filter'], "png")
            if palette:
                img.putpalette(palette)
            try:
                img = Image.frombytes(mode, size, data)
                END = f"width={size[0]} height={size[1]}>"
                if external_refs:
                    name = f"{path}_{xobj.idnum}.{xformat}"
                    img.save(name)
                    url = f"<img src={name} {END}"
                else:
                    buffer = BytesIO()
                    img.save(buffer, format=xformat)
                    img_str = base64.b64encode(buffer.getvalue())
                    url = f"<file src={name} {END}{img_str}</file>"
                images[xobj.idnum] = url
            except Exception:
                pass
            finally:
                img.close()
    return images

def serialize_fxml(write, elem, short_empty, pretty, level=0):
    """_summary_

    Args:
        write (_type_): _description_
        elem (_type_): _description_
        short_empty (_type_): _description_
        pretty (_type_): _description_
        level (int, optional): _description_. Defaults to 0.

    Raises:
        ValueError: _description_
        NotImplementedError: _description_
        ParseError: _description_
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
            path.append(str(__a))
            __a.compare(__b, path)
            path.pop()
        elif isinstance(__a, list):
            if len(__a) != len(__b):
                return False
            tmp: list = copy.copy(__b)
            for ita in __a:
                path.append(str(ita))
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
            if key not in ("_Question__parent", "_Category__parent") and not \
                    Serializable.__itercmp(val, __o.__dict__.get(key), path):
                cpr = __o.__dict__.get(key)
                if isinstance(val, list) and cpr:
                    val = ", ".join(map(str, val))
                    cpr = ", ".join(map(str, cpr))
                if isinstance(val, str) and len(val) > 20:
                    with open("raw1.tmp", "w") as ofile:
                        ofile.write(val)
                    with open("raw2.tmp", "w") as ofile:
                        ofile.write(cpr)
                    output = f"Items differs in {key}. See diff files."
                else:
                    output = f"Items differs in {key}:\n\t{val}\n\t{cpr}"
                raise ValueError(output)
        return True

    @classmethod
    def from_gift(cls, header: list, answer: list):
        """_summary_

        Args:
            header (list): _description_
            answer (list): _description_

        Returns:
            QMatching: _description_
        """
        raise NotImplementedError("GIFT not implemented")

    @classmethod
    def from_json(cls, data: dict) -> "Serializable":
        """_summary_

        Returns:
            Serializable: _description_
        """
        return cls(**data) if isinstance(data, dict) else None

    @classmethod
    def from_xml(cls, root: et.Element, tags: dict, attrs: dict):
        """Create a new class using XML data

        Args:
            root (et.Element): _description_
            tags (dict): _description_
            attrs (dict): _description_

        Returns:
            Serializable: _description_
        """
        if root is None:
            return None
        results = {}
        name = tags.pop(True, None)  # True is used as a key to ask for the tag
        if name:                     # If it is present, tag is mapped to <name>
            results[name] = root.tag
        for obj in root:
            if obj.tag in tags:
                cast_type, name, *_ = tags[obj.tag]
                if not isinstance(cast_type, type):
                    tmp = cast_type(obj, {}, {})
                else:
                    tmp = obj.text.strip() if obj.text else ""
                    if not tmp:
                        text = obj.find("text")
                        if text is not None:
                            tmp = text.text
                    if cast_type == bool:
                        tmp = tmp.lower() in ["true", "1", "t", ""]
                    elif tmp or cast_type == str:
                        tmp = cast_type(tmp)
                if len(tags[obj.tag]) == 3:
                    if name not in results:
                        results[name] = []
                    results[name].append(tmp)
                else:
                    results[name] = tmp
                    tags.pop(obj.tag)
        for key in tags:
            cast_type, name, *_ = tags[key]
            if cast_type == bool:  # Some tags act like False when missing
                results[name] = False
        if attrs:
            for key in attrs:
                cast_type, name = attrs[key]
                results[name] = root.get(key, None)
                if results[name] is not None:
                    results[name] = cast_type(results[name])
        return cls(**results)

    def to_xml(self, strict: bool) -> et.Element:
        """Create a XML representation of the object instance following the
        moodle standard. This function if first implemented as "virtual" in
        the Serializable class, raising an exception if not overriden.

        Args:
            root (et.Element): where the new tags will be added to
            strict (bool): if the tags added should only be the ones correctly
                interpreted by moodle.

        Returns:
            et.Element: The instance root element. In a organized XML, this
            should be always different from the "root" argument, but since
            Moodle uses tags, like the ones in CombinedFeedback, that can or
            not be valid, we end-up in this mess.
        """
        raise NotImplementedError("XML not implemented")


class ParseError(Exception):
    """Exception used when a parsing fails.
    """


class MarkerError(Exception):
    """Exception used when there is a Marker related error
    """


class AnswerError(Exception):
    """Exception used when a parsing fails.
    """


class LineBuffer:
    """Helps parsing text files that uses lines (\\n) as part of the standard
    somehow.
    """

    def __init__(self, buffer) -> None:
        self.last = buffer.readline()
        self.__bfr = buffer

    def read(self, inext: bool = False):
        """_summary_

        Args:
            inext (bool, optional): _description_. Defaults to False.

        Raises:
            ParseError: _description_

        Returns:
            _type_: _description_
        """
        if not self.last and inext:
            raise ParseError()
        tmp = self.last
        if inext:
            self.last = self.__bfr.readline()
            while self.last and self.last == "\n":
                self.last = self.__bfr.readline()
        return tmp
