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
from typing import TYPE_CHECKING

from PyQt5.QtCore import reset
if TYPE_CHECKING:
    from typing import List, Dict
import re
import logging
import json
from xml.etree import ElementTree as et
from PIL import Image
from PyPDF2.pdf import PageObject
from PyPDF2 import PdfFileReader 
from enum import Enum
from .enums import Numbering
from . import questions
# import pikepdf

def _escape_cdata(text):
    try:
        if str.startswith(text, "<![CDATA[") and str.endswith(text, "]]>"):
            return text
        if "&" in text:
            text = text.replace("&", "&amp;")
        if "<" in text:
            text = text.replace("<", "&lt;")
        if ">" in text:
            text = text.replace(">", "&gt;")
        return text
    except (TypeError, AttributeError):
        et._raise_serialization_error(text)
et._escape_cdata = _escape_cdata

# ----------------------------------------------------------------------------------------

logger = logging.getLogger(__name__)

class ParseError(Exception):
    pass

class LineBuffer:

    def __init__(self, buffer) -> None:
        self.last = buffer.readline()
        self.__bfr = buffer
    
    def rd(self, inext:bool=False):
        if not self.last and inext: raise ParseError()
        tmp = self.last
        if inext:
            self.last = self.__bfr.readline()
            while self.last and self.last == "\n": self.last = self.__bfr.readline()
        return tmp

class Quiz:
    """
    This class represents Quiz as a set of Questions.
    """

    def __init__(self, name = "$course$", parent: "Quiz"=None):
        self._questions: List[questions.Question] = []
        self.__categories: Dict[str, Quiz] = {}
        self.__name = name
        self.__parent = None
        self.parent = parent

    def __iter__(self):
        return self.__categories.__iter__()

    def __getitem__(self, key: str):
        return self.__categories[key]

    @staticmethod
    def __gen_hier(top: "Quiz", category: str) -> tuple:
        cat_list = category.strip().split("/")
        if top is None: top = Quiz(cat_list[0])
        elif top.name != cat_list[0]: 
            raise ValueError(f"Top categroy names differ: {top.name} != {cat_list[0]}")
        quiz = top
        for i in cat_list[1:]:
            if i not in quiz.__categories: 
                quiz.__categories[i] = Quiz(i, quiz)
            quiz = quiz.__categories[i]
        return (top, quiz)

    def _indent(self, elem: et.Element, level: int=0):
        """[summary]

        Args:
            elem (et.Element): [description]
            level (int, optional): [description]. Defaults to 0.
        """
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                self._indent(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    def _to_aiken(self) -> str:
        data = ""
        for question in self._questions:
            if isinstance(question, questions.QMultichoice):
                data += f"{question.question_text.text}\n"
                correct = "ANSWER: None\n\n"
                for num, ans in enumerate(question.answers):
                    data += f"{chr(num+65)}) {ans.text}\n"
                    if ans.fraction == 100:
                        correct = f"ANSWER: {chr(num+65)}\n\n"
                data += correct
        for child in self.__categories:
            data += self.__categories[child]._to_aiken()
        return data

    def _to_xml_element(self, root: et.Element) -> None:
        """[summary]

        Args:
            root (et.Element): [description]
        """
        question = et.Element("question")                   # Add category on the top
        if len(self._questions) > 0:
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
            for question in self._questions:                # Add own questions first
                root.append(question.to_xml())
        for child in self.__categories.values():            # Then add children data
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
            if isinstance(val, list) or isinstance(val, dict):
                res = self._to_json(val.copy())
            elif isinstance(val, Enum): # For the enums
                res = val.value
            elif hasattr(val, "__dict__"): # for the objects
                tmp = val.__dict__.copy()
                if isinstance(val, questions.Question): 
                    tmp["_type"] = val._type
                    del tmp["_Question__parent"]
                elif isinstance(val, Quiz): 
                    del tmp["_Quiz__parent"]
                res = self._to_json(tmp)
            if res != val:
                if isinstance(data, dict): data[i] = res
                else: data[num] = res
        return data

    def get_hier(self) -> dict:
        """[summary]

        Args:
            root (dict): [description]
        """
        data = {}
        data["__questions__"] = self._questions
        for cat in self.__categories:
            data[cat] = self.__categories[cat].get_hier()
        return data

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, value: str):
        if self.__parent:
            if value in self.__parent.__categories:
                raise ValueError(f"Question name \"{value}\" already exists on current category")
            self.__parent.__categories.pop(self.__name)
            self.__parent.__categories[value] = self
        self.__name = value

    @name.getter
    def name(self) -> str:
        return self.__name

    @property
    def parent(self):
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

    @parent.getter
    def parent(self) -> "Quiz":
        return self.__parent

    @property
    def questions(self):
        return self._questions.__iter__()

    @classmethod
    def read_aiken(cls, file_path: str, category: str="$course$") -> "Quiz":
        """[summary]

        Args:
            file_path (str): [description]
        """
        quiz = cls(category)
        name = file_path.rsplit("/", 1)[-1][:-4]
        cnt = 0
        with open(file_path, encoding="utf-8") as ifile:
            buffer = LineBuffer(ifile)
            while buffer.rd():
                question = questions.QMultichoice.from_aiken(buffer, f"{name}_{cnt}")
                question.parent = quiz
                cnt += 1
        return quiz

    @classmethod
    def read_cloze(cls, file_path: str, category: str="$course$") -> "Quiz":
        top_quiz: Quiz = Quiz(category)
        with open(file_path, "r", encoding="utf-8") as ifile:
            question = questions.QCloze.from_cloze(ifile)
            question.parent = top_quiz
        return top_quiz

    @classmethod
    def read_gift(cls, file_path: str) -> "Quiz":
        top_quiz: Quiz = None
        quiz = top_quiz
        with open(file_path, "r", encoding="utf-8") as ifile:
            data = "\n" + ifile.read()
        data = re.sub(r"\n//.*?(?=\n)", "", data)           # Remove comments
        data = re.sub("(?<!\})\n(?!::)", "", data) + "\n"   # Remove \n's inside a question
        tmp = re.findall(r"(?:\$CATEGORY:\s*(.+))|(?:\:\:(.+?)\:\:(\[.+?\])?(.+?)(?:(\{.*?)(?<!\\)\}(.*?))?)\n", 
                        data)
        for i in tmp:
            if i[0]:
                top_quiz, quiz = Quiz.__gen_hier(top_quiz, i[0])
            if not i[0]:
                question = None
                ans = re.findall(r"((?<!\\)(?:=|~|TRUE|FALSE|T|F|####|#))(%[\d\.]+%)?((?:(?<=\\)[=~#]|[^~=#])*)", i[4])           
                if not i[4]:
                    question = questions.QDescription.from_gift(i, ans)
                elif not ans:
                    question = questions.QEssay.from_gift(i, ans)
                elif ans[0][0] == "#":
                    question = questions.QNumerical.from_gift(i, ans)
                elif i[5]:  
                    question = questions.QMissingWord.from_gift(i, ans)  
                elif ans[0][0] in ["TRUE", "FALSE", "T", "F"]:               
                    question = questions.QTrueFalse.from_gift(i, ans)
                elif all([a[0] in ["=", "#", "####"] for a in ans]):
                    if re.match(r"(.*?)(?<!\\)->(.*)", ans[0][2]):
                        question = questions.QMatching.from_gift(i, ans)
                    else:
                        question = questions.QShortAnswer.from_gift(i, ans)
                else:
                    question = questions.QMultichoice.from_gift(i, ans)
                question.parent = quiz
        return top_quiz

    @classmethod
    def read_json(cls, file_path: str) -> "Quiz":
        """
        Generic file. This is the default file format used by the QAS Editor.
        """
        qdict: Dict[str, questions.Question] = {
            getattr(questions, m)._type: getattr(questions, m) for m in questions.QTYPES
        }
        def _from_json(dt: dict, parent: Quiz):
            quiz = cls(dt["_Quiz__name"], parent)
            for i in range(len(dt["_questions"])):
                val = dt["_questions"][i]
                dt["_questions"][i] = qdict[val["_type"]].from_json(val)
                dt["_questions"][i].parent = quiz
            for i in dt["_Quiz__categories"]:
                val = dt["_Quiz__categories"][i] 
                dt["_Quiz__categories"][i] = _from_json(dt["_Quiz__categories"][i], quiz)
            return quiz
        with open(file_path, "rb") as infile:
            data = json.load(infile)
        return _from_json(data, None)

    @classmethod
    def read_latex(cls) -> "Quiz":
        # TODO
        pass

    @classmethod
    def read_markdown(cls, file_path: str, question_mkr :str="\s*\*\s+(.*)", 
                        answer_mkr: str="\s*-\s+(!)?(.*)", category_mkr: str="\s*#\s+(.*)", 
                        answer_numbering: Numbering=Numbering.ALF_LR, 
                        shuffle_answers: bool=True, single_answer_penalty_weight: int=0):
        """[summary]

        Args:
            file_path (str): [description]
            question_mkr (str, optional): [description]. Defaults to "\s*\*\s+(.*)".
            answer_mkr (str, optional): [description]. Defaults to "\s*-\s+(!)(.*)".
            category_mkr (str, optional): [description]. Defaults to "\s*#\s+(.*)".
            answer_numbering (Numbering, optional): [description]. Defaults to Numbering.ALF_LOWER.
            shuffle_answers (bool, optional): [description]. Defaults to True.
            single_answer_penalty_weight (int, optional): [description]. Defaults to 0.

        Raises:
            ValueError: [description]
            ValueError: [description]
            ValueError: [description]
        """
        regex_exp = f"({category_mkr})|({question_mkr})|({answer_mkr})"
        with open(file_path, encoding="utf-8") as infile:
            lines = infile.readlines()
        lines.append("\n") # Make sure that the document has 2 newlines in the end
        lines.append("\n")
        lines.reverse()
        cnt = 0
        top_quiz: Quiz = None
        quiz = top_quiz
        while lines:
            match = re.match(regex_exp, lines[-1])
            if match:
                if match[1]:
                    top_quiz, quiz = Quiz.__gen_hier(top_quiz, match[2])
                    lines.pop()
                elif match[3]:
                    if quiz is None:
                        raise ValueError("No classification defined for this question")
                    question = questions.QMultichoice.from_markdown( lines, 
                                    answer_mkr, question_mkr, answer_numbering, shuffle_answers,
                                    single_answer_penalty_weight, name=f"mkquestion_{cnt}")
                    question.parent = quiz
                elif match[5]:
                    raise ValueError(f"Answer found out of a question block: {match[5]}.")
            else:
                lines.pop()
        return top_quiz

    @classmethod
    def read_pdf(cls, file_path: str, ptitle="Question \d+", include_image=True):
        _serial_img = {'/DCTDecode': "jpg", '/JPXDecode': "jp2", '/CCITTFaxDecode': "tiff"}
        with open(file_path, "rb") as infile:
            pdf_file = PdfFileReader(infile)
            for page_num in range(pdf_file.getNumPages()):
                page: PageObject = pdf_file.getPage(page_num)
                if '/XObject' not in page['/Resources']:
                    continue
                xObject = page['/Resources']['/XObject'].getObject()
                for obj in xObject:
                    if xObject[obj]['/Subtype'] != '/Image':
                        continue
                    size = (xObject[obj]['/Width'], xObject[obj]['/Height'])
                    data = xObject[obj].getData()
                    if xObject[obj]['/ColorSpace'][0] == '/DeviceRGB':
                        mode = "RGB"
                    elif xObject[obj]['/ColorSpace'][0] in ["/DeviceN", "/Indexed"]:
                        mode = "P"
                        if xObject[obj]['/ColorSpace'][0] == "/Indexed":
                            psize = int(xObject[obj]['/ColorSpace'][2])
                            palette = [255-int(n*psize/255) for n in range(256) for _ in range(3)]
                        else: 
                            palette = None
                    else:
                        raise ValueError(f"Mode not tested yet: {xObject[obj]['/ColorSpace']}") 
                    if '/Filter' in xObject[obj]:
                        filter = xObject[obj]['/Filter']
                        if filter == '/FlateDecode':
                            img = Image.frombytes(mode, size, data)
                            if palette: 
                                img.putpalette(palette)
                            img.save(f"page{page_num}_{obj[1:]}.png")
                        elif filter in _serial_img:
                            img = open(f"page{page_num}_{obj[1:]}.{_serial_img[filter]}", "wb")
                            img.write(data)
                            img.close()
                        else:
                            raise ValueError(f"Filter not tested yet: {filter}") 
                    else:
                        img = Image.frombytes(mode, size, data)
                        img.save(obj[1:] + ".png")

    @classmethod
    def read_xml(cls, file_path: str, category: str="$course$") -> "Quiz":
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
            qdict: Dict[str, questions.Question] = {
                getattr(questions, m)._type: getattr(questions, m) for m in questions.QTYPES
            }
            if question.tag != "question":
                continue
            if question.get("type") == "category":
                top_quiz, quiz = Quiz.__gen_hier(top_quiz, question[0][0].text)         
            elif question.get("type") not in qdict:
                raise TypeError(f"The type {question.get('type')} not implemented")
            else:
                if top_quiz is None and quiz is None:
                    top_quiz: Quiz = Quiz(category)
                    quiz = top_quiz
                quiz._questions.append(qdict[question.get("type")].from_xml(question))
        return top_quiz

    def rem_question(self, question: questions.Question) -> bool:
        if question not in self._questions: return False
        question.parent = None
        self._questions.remove(question)
        return True

    def write_aiken(self, file_path: str) -> None:
        data = self._to_aiken()
        with open(file_path, "w") as ofile:
            ofile.write(data)
        
    def write_cloze(self, file_path: str) -> None:
        # TODO
        pass

    def write_gift(self, file_path: str) -> None:
        # TODO
        raise NotImplemented("Gift not implemented")

    def write_json(self, file_path: str, pretty_print: bool=False) -> None:
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
        # TODO
        raise NotImplemented("LaTex not implemented")

    def write_markdown(self, file_path: str) -> None:
        # TODO
        raise NotImplemented("Markdown not implemented")

    def write_pdf(self, file_path: str):
        # TODO
        raise NotImplemented("PDF not implemented")

    def write_xml(self, file_path: str, pretty_print: bool=False):
        """Generates XML compatible with Moodle and saves to a file.

        Args:
            file_path (str): filename where the XML will be saved
            pretty_print (bool, optional): (not implemented) saves XML pretty printed. Defaults to False.
        """
        quiz: et.ElementTree = et.ElementTree(et.Element("quiz"))
        root = quiz.getroot()
        self._to_xml_element(root)
        if pretty_print:
            self._indent(root)
        quiz.write(file_path, encoding="utf-8", xml_declaration=True, short_empty_elements=True)

