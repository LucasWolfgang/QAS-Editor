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
from asyncio import streams
import glob
import json
import logging
import re
from enum import Enum
from typing import TYPE_CHECKING
from xml.etree import ElementTree as et
from .questions import QDICT, Question, QMultichoice, QCloze, QDescription,\
                       QEssay, QNumerical, QMissingWord, QTrueFalse, QMatching,\
                       QShortAnswer
if TYPE_CHECKING:
    from typing import List, Dict   # pylint: disable=C0412
LOG = logging.getLogger(__name__)

#from PIL import Image
#from PyPDF2 import PdfFileReader, pdf
#import pikepdf

def _escape_cdata(text: str):
    try:
        if str.startswith(text, "<![CDATA[") and str.endswith(text, "]]>"):
            return text
        if "&" in text:
            text = text.replace("&", "&amp;")
        if "<" in text:
            text = text.replace("<", "&lt;")
        if ">" in text:
            text = text.replace(">", "&gt;")
    except (TypeError, AttributeError):
        et._raise_serialization_error(text)
    return text
et._escape_cdata = _escape_cdata

# ------------------------------------------------------------------------------

class ParseError(Exception):
    """Exception used when a parsing fails.
    """

# ------------------------------------------------------------------------------

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

# ------------------------------------------------------------------------------

class Quiz: # pylint: disable=R0904
    """
    This class represents Quiz as a set of Questions.
    """

    def __init__(self, name: str = "$course$", parent: "Quiz" = None):
        self.__questions: List[Question] = []
        self.__categories: Dict[str, Quiz] = {}
        self.__name = name
        self.__parent = None
        self.parent = parent    # Already using the property setter

    def __iter__(self):
        return self.__categories.__iter__()

    def __getitem__(self, key: str):
        return self.__categories[key]

    def __len__(self):
        total = len(self.__questions)
        for cat in self.__categories.values():
            total += len(cat)
        return total

    def __setitem__(self, __k: str, __v: "Quiz"):
        if not isinstance(__k, str) or not isinstance(__v, Quiz):
            raise ValueError(f"{__k} is not a string or {__v} is not a Quiz")
        return self.__categories.__setitem__(__k, __v)

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Quiz):
            return False
        if self.__questions != __o.__questions:
            LOG.debug(f"Quizes {self.name} not equal. Questions differ.")
            return False
        if self.__categories != __o.__categories:
            LOG.debug(f"Quizes {self.name} not equal. Categories differ.")
            return False
        return True

    @staticmethod
    def __gen_hier(top: "Quiz", category: str) -> tuple:
        cat_list = category.strip().split("/")
        start = 1 if top.name == cat_list[0] else 0
        quiz = top
        for i in cat_list[start:]:
            if i not in quiz:
                quiz[i] = Quiz(i, quiz)
            quiz = quiz[i]
        return quiz

    def _indent(self, elem: et.Element, level: int = 0):
        """[summary]

        Args:
            elem (et.Element): [description]
            level (int, optional): [description]. Defaults to 0.
        """
        i = "\n" + level * "  "
        if len(elem) != 0:
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for tag in elem:
                self._indent(tag, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    def _to_aiken(self) -> str:
        data = ""
        for question in self.__questions:
            if isinstance(question, QMultichoice):
                data += f"{question.question_text.text}\n"
                correct = "ANSWER: None\n\n"
                for num, ans in enumerate(question.answers):
                    data += f"{chr(num+65)}) {ans.text}\n"
                    if ans.fraction == 100:
                        correct = f"ANSWER: {chr(num+65)}\n\n"
                data += correct
        for child in self.__categories.values():
            data += child._to_aiken()
        return data

    def _to_xml_element(self, root: et.Element) -> None:
        """[summary]

        Args:
            root (et.Element): [description]
        """
        question = et.Element("question")           # Add category on the top
        if len(self.__questions) > 0:
            question.set("type", "category")
            category = et.SubElement(question, "category")
            catname = [self.__name]
            tmp = self.parent
            while tmp:
                catname.append(tmp.name)
                tmp = tmp.parent
            catname.reverse()
            et.SubElement(category, "text").text = "/".join(catname)
            root.append(question)
            for question in self.__questions:       # Add own questions first
                root.append(question.to_xml())
        for child in self.__categories.values():    # Then add children data
            child._to_xml_element(root)

    def _to_json(self, data: dict|list):
        """[summary]

        Args:
            data (dict): [description]

        Returns:
            [type]: [description]
        """
        for num, i in enumerate(data):
            res = val = data[i] if isinstance(data, dict) else i
            if isinstance(val, (list, dict)):
                res = self._to_json(val.copy())
            elif isinstance(val, Enum): # For the enums
                res = val.value
            elif hasattr(val, "__dict__"): # for the objects
                tmp = val.__dict__.copy()
                if isinstance(val, Question):
                    tmp["_type"] = val._type
                    del tmp["_Question__parent"]
                elif isinstance(val, Quiz):
                    del tmp["_Quiz__parent"]
                res = self._to_json(tmp)
            if res != val:
                if isinstance(data, dict):
                    data[i] = res
                else: data[num] = res
        return data

    # --------------------------------------------------------------------------

    @property
    def name(self):
        """_summary_
        """
        return self.__name

    @name.setter
    def name(self, value: str):
        if self.__parent:
            if value in self.__parent.__categories:
                raise ValueError(f"Question name \"{value}\" already exists on current category")
            self.__parent.__categories.pop(self.__name)
            self.__parent.__categories[value] = self
        self.__name = value

    @property
    def parent(self):
        """_summary_
        """
        return self.__parent

    @parent.setter
    def parent(self, value: "Quiz") -> None:
        if value and self.__name in value.__categories:
            raise ValueError(f"Question name \"{self.__name}\" already exists on new category")
        if self.__parent:
            self.__parent.__categories.pop(self.__name)
        if isinstance(value, Quiz):
            value.__categories[self.__name] = self
            self.__parent = value
        else:
            self.__parent = None

    @property
    def questions(self):
        """_summary_
        """
        return self.__questions.__iter__()

    # --------------------------------------------------------------------------

    def add_question(self, question: Question) -> bool:
        """_summary_

        Args:
            question (Question): _description_

        Returns:
            bool: _description_
        """
        if question in self.__questions:
            return False
        if question.parent is not None:
            question.parent.rem_question(question)
        self.__questions.append(question)
        question.parent = self
        return True


    def get_hier(self) -> dict:
        """[summary]

        Args:
            root (dict): [description]
        """
        data = {}
        data["__questions__"] = self.__questions
        for name, quiz in self.__categories.values():
            data[name] = quiz.get_hier()
        return data

    @classmethod
    def read_aiken(cls, file_path: str, category: str = "$course$") -> "Quiz":
        """_summary_

        Args:
            file_path (str): _description_
            category (str, optional): _description_. Defaults to "$".

        Returns:
            Quiz: _description_
        """
        quiz = cls(category)
        name = file_path.rsplit("/", 1)[-1][:-4]
        cnt = 0
        for _path in glob.glob(file_path):
            with open(_path, encoding="utf-8") as ifile:
                buffer = LineBuffer(ifile)
                while buffer.read():
                    question = QMultichoice.from_aiken(buffer, f"{name}_{cnt}")
                    question.parent = quiz
                    cnt += 1
        return quiz

    @classmethod
    def read_cloze(cls, file_path: str, category: str = "$course$") -> "Quiz":
        """Reads a Cloze file.

        Args:
            file_path (str): _description_
            category (str, optional): _description_. Defaults to "$".

        Returns:
            Quiz: _description_
        """
        top_quiz = cls(category)
        with open(file_path, "r", encoding="utf-8") as ifile:
            top_quiz.add_question(QCloze.from_cloze(ifile))
        LOG.info(f"Created new Quiz instance from cloze file {file_path}")
        return top_quiz

    @classmethod
    def read_files(cls, files: list, category: str = "$course$") -> list:
        """_summary_

        Args:
            folder_path (str): _description_
            category (str, optional): _description_. Defaults to "$".

        Returns:
            list: _description_
        """
        _read_methods = {
            "txt": cls.read_aiken,
            "cloze": cls.read_cloze,
            "gift": cls.read_gift,
            "json": cls.read_json,
            "latex": cls.read_latex,
            "md": cls.read_markdown,
            "pdf": cls.read_pdf,
            "xml": cls.read_xml
        }
        top_quiz = cls(category)
        for _path in files:
            try:
                ext = _path.rsplit(".", 1)[-1]
                if ext in _read_methods:
                    quiz = _read_methods[ext](_path)
                    for cat in quiz:
                        top_quiz[cat] = quiz[cat]
                    for question in quiz.questions:
                        top_quiz.add_question(question)
            except ValueError:
                LOG.exception(f"Failed to parse file {_path}.")
        return top_quiz

    @classmethod
    def read_gift(cls, file_path: str, category: str = "$course$") -> "Quiz":
        """Reads a gift file.

        Args:
            file_path (str): _description_

        Raises:
            ValueError: _description_
            TypeError: _description_
            NotImplemented: _description_

        Returns:
            Quiz: _description_
        """
        top_quiz = cls(category)
        quiz = top_quiz
        data = ""
        with open(file_path, "r", encoding="utf-8") as ifile:
            data += "\n" + ifile.read()
        data = re.sub(r"\n//.*?(?=\n)", "", data)           # Remove comments
        data = re.sub(r"(?<!\})\n(?!::)", "", data) + "\n"   # Remove \n's inside a question
        tmp = re.findall(r"(?:\$CATEGORY:\s*(.+))|(?:\:\:(.+?)\:\:(\[.+?\])?"+
                         r"(.+?)(?:(\{.*?)(?<!\\)\}(.*?))?)\n", data)
        for i in tmp:
            if i[0]:
                quiz = Quiz.__gen_hier(top_quiz, i[0])
            if not i[0]:
                question = None
                ans = re.findall(r"((?<!\\)(?:=|~|TRUE|FALSE|T|F|####|#))"+
                                 r"(%[\d\.]+%)?((?:(?<=\\)[=~#]|[^~=#])*)", i[4])
                if not i[4]:
                    question = QDescription.from_gift(i)
                elif not ans:
                    question = QEssay.from_gift(i)
                elif ans[0][0] == "#":
                    question = QNumerical.from_gift(i, ans)
                elif i[5]:
                    question = QMissingWord.from_gift(i, ans)
                elif ans[0][0] in ["TRUE", "FALSE", "T", "F"]:
                    question = QTrueFalse.from_gift(i, ans)
                elif all(a[0] in ["=", "#", "####"] for a in ans):
                    if re.match(r"(.*?)(?<!\\)->(.*)", ans[0][2]):
                        question = QMatching.from_gift(i, ans)
                    else:
                        question = QShortAnswer.from_gift(i, ans)
                else:
                    question = QMultichoice.from_gift(i, ans)
                question.parent = quiz
        return top_quiz

    @classmethod
    def read_json(cls, file_path: streams) -> "Quiz":
        """
        Generic file. This is the default file format used by the QAS Editor.
        """
        def _from_json(_dt: dict, parent: Quiz):
            quiz = cls(_dt["_Quiz__name"], parent)
            for i in range(len(_dt["_questions"])):
                val = _dt["_questions"][i]
                _dt["_questions"][i] = QDICT[val["_type"]].from_json(val)
                _dt["_questions"][i].parent = quiz
            for i in _dt["_Quiz__categories"]:
                val = _dt["_Quiz__categories"][i]
                _dt["_Quiz__categories"][i] = _from_json(_dt["_Quiz__categories"][i], quiz)
            return quiz
        with open(file_path, "rb") as infile:
            data = json.load(infile)
        return _from_json(data, None)

    @classmethod
    def read_latex(cls, file_path: str, category: str = "$course$") -> "Quiz":
        """_summary_

        Returns:
            Quiz: _description_
        """
        # TODO
        raise NotImplementedError("LaTeX not implemented")

    @classmethod
    def read_markdown(cls, file_path: str, category="$course$",
                      prefix="mk_", question_mkr=r"\s*\*\s+(.*)",
                      answer_mkr=r"\s*-\s+(!)?(.*)",
                      category_mkr=r"\s*#\s+(.*)") -> "Quiz":
        """[summary]

        Args:
            file_path (str): [description]
            question_mkr (str, optional): [description]. Defaults to r\"\\s*\\*\\s+(.*)\".
            answer_mkr (str, optional): [description]. Defaults to r\"\\s*-\\s+(!)(.*)\".
            category_mkr (str, optional): [description]. Defaults to r\"\\s*#\\s+(.*)\".

        Raises:
            ValueError: [description]
        """
        with open(file_path, encoding="utf-8") as infile:
            lines = infile.readlines()
        lines.append("\n") # Make sure that the document has 2 newlines in the end
        lines.append("\n")
        lines.reverse()
        cnt = 0
        top_quiz = cls(category)
        quiz = top_quiz
        while lines:
            match = re.match(f"({category_mkr})|({question_mkr})|({answer_mkr})", lines[-1])
            if match:
                if match[1]:
                    quiz = Quiz.__gen_hier(top_quiz, match[2])
                    lines.pop()
                elif match[3]:
                    if quiz is None:
                        raise ValueError("No classification defined for this question")
                    QMultichoice.from_markdown(lines, answer_mkr, question_mkr,
                                               f"{prefix}_{cnt}")
                    cnt += 1
                elif match[5]:
                    raise ValueError(f"Answer found out of a question block: {match[5]}.")
            else:
                lines.pop()
        return top_quiz

    @classmethod
    def read_pdf(cls, file_path: str, ptitle: str = r"Question \d+",
                 include_image: bool = True) -> "Quiz":
        """_summary_

        Args:
            file_path (str): _description_
            ptitle (str, optional): _description_. Defaults to r"Question \\d+".
            include_image (bool, optional): _description_. Defaults to True.

        Returns:
            Quiz: _description_
        """
        raise NotImplementedError("PDF not implemented")
        # _serial_img = {'/DCTDecode': "jpg", '/JPXDecode': "jp2", '/CCITTFaxDecode': "tiff"}
        # with open(file_path, "rb") as infile:
        #     pdf_file = PdfFileReader(infile)
        #     for page_num in range(pdf_file.getNumPages()):
        #         page: pdf.PageObject = pdf_file.getPage(page_num)
        #         if '/XObject' not in page['/Resources']:
        #             continue
        #         xobj = page['/Resources']['/XObject'].getObject()
        #         for obj in xobj:
        #             if xobj[obj]['/Subtype'] != '/Image':
        #                 continue
        #             size = (xobj[obj]['/Width'], xobj[obj]['/Height'])
        #             data = xobj[obj].getData()
        #             if xobj[obj]['/ColorSpace'][0] == '/DeviceRGB':
        #                 mode = "RGB"
        #             elif xobj[obj]['/ColorSpace'][0] in ["/DeviceN", "/Indexed"]:
        #                 mode = "P"
        #                 if xobj[obj]['/ColorSpace'][0] == "/Indexed":
        #                     psize = int(xobj[obj]['/ColorSpace'][2])
        #                     palette = [255-int(n*psize/255) for n in range(256) for _ in range(3)]
        #                 else:
        #                     palette = None
        #             else:
        #                 raise ValueError(f"Mode not tested yet: {xobj[obj]['/ColorSpace']}")
        #             if '/Filter' in xobj[obj]:
        #                 xfilter = xobj[obj]['/Filter']
        #                 if xfilter == '/FlateDecode':
        #                     img = Image.frombytes(mode, size, data)
        #                     if palette:
        #                         img.putpalette(palette)
        #                     img.save(f"page{page_num}_{obj[1:]}.png")
        #                 elif xfilter in _serial_img:
        #                     img = open(f"page{page_num}_{obj[1:]}.{_serial_img[xfilter]}", "wb")
        #                     img.write(data)
        #                     img.close()
        #                 else:
        #                     raise ValueError(f"Filter not tested yet: {xfilter}")
        #             else:
        #                 img = Image.frombytes(mode, size, data)
        #                 img.save(obj[1:] + ".png")

    @classmethod
    def read_xml(cls, file_path: str, category: str = "$course$") -> "Quiz":
        """[summary]

        Raises:
            TypeError: [description]

        Returns:
            [type]: [description]
        """
        data_root = et.parse(file_path)
        top_quiz: Quiz = None
        quiz = top_quiz
        for question in data_root.getroot():
            if question.tag != "question":
                continue
            if question.get("type") == "category":
                quiz = Quiz.__gen_hier(top_quiz, question[0][0].text)
            elif question.get("type") not in QDICT:
                raise TypeError(f"The type {question.get('type')} not implemented")
            else:
                if top_quiz is None and quiz is None:
                    top_quiz: Quiz = Quiz(category)
                    quiz = top_quiz
                quiz.__questions.append(QDICT[question.get("type")].from_xml(question))
        return top_quiz

    def rem_question(self, question: Question) -> bool:
        """_summary_

        Args:
            question (questions.Question): _description_

        Returns:
            bool: _description_
        """
        if question not in self.__questions:
            return False
        self.__questions.remove(question)
        question.parent = None
        return True

    def write_aiken(self, file_path: str) -> None:
        """_summary_

        Args:
            file_path (str): _description_
        """
        data = self._to_aiken()
        with open(file_path, "w", encoding="utf-8") as ofile:
            ofile.write(data)

    def write_cloze(self, file_path: str) -> None:
        """_summary_

        Args:
            file_path (str): _description_

        Raises:
            NotImplementedError: _description_
        """
        # TODO
        raise NotImplementedError("Cloze not implemented")

    def write_gift(self, file_path: str) -> None:
        """_summary_

        Args:
            file_path (str): _description_

        Raises:
            NotImplementedError: _description_
        """
        # TODO
        raise NotImplementedError("Gift not implemented")

    def write_json(self, file_path: str, pretty_print: bool = False) -> None:
        """[summary]

        Args:
            file_path (str): [description]
            pretty_print (bool, optional): [description]. Defaults to False.
        """
        tmp = self.__dict__.copy()
        del tmp["_Quiz__parent"]
        with open(file_path, "w", encoding="utf-8") as ofile:
            json.dump(self._to_json(tmp), ofile, indent=4 if pretty_print else 0)

    def write_latex(self, file_path: str) -> None:
        """_summary_

        Args:
            file_path (str): _description_

        Raises:
            NotImplementedError: _description_
        """
        # TODO
        raise NotImplementedError("LaTex not implemented")

    def write_markdown(self, file_path: str) -> None:
        """_summary_

        Args:
            file_path (str): _description_

        Raises:
            NotImplementedError: _description_
        """
        # TODO
        raise NotImplementedError("Markdown not implemented")

    def write_pdf(self, file_path: str):
        """_summary_

        Args:
            file_path (str): _description_

        Raises:
            NotImplementedError: _description_
        """
        # TODO
        raise NotImplementedError("PDF not implemented")

    def write_xml(self, file_path: str, pretty_print: bool = False):
        """Generates XML compatible with Moodle and saves to a file.

        Args:
            file_path (str): filename where the XML will be saved
            pretty_print (bool, optional): (not implemented) saves XML pretty
                printed. Defaults to False.
        """
        quiz: et.ElementTree = et.ElementTree(et.Element("quiz"))
        root = quiz.getroot()
        self._to_xml_element(root)
        if pretty_print:
            self._indent(root)
        quiz.write(file_path, encoding="utf-8", xml_declaration=True,
                   short_empty_elements=True)
