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

from .utils import Serializable, LineBuffer, serialize_fxml
from .questions import QTYPE, QMultichoice, QCloze, QDescription,\
                       QEssay, QNumerical, QMissingWord, QTrueFalse,\
                       QMatching, QShortAnswer, _Question
if TYPE_CHECKING:
    from typing import Dict, List   # pylint: disable=C0412
LOG = logging.getLogger(__name__)

# from PIL import Image
# from PyPDF2 import PdfFileReader, pdf
# import pikepdf


class Category(Serializable):  # pylint: disable=R0904
    """
    This class represents Quiz as a set of Questions.
    """

    SERIALIZERS = { "cloze": ("read_cloze", "write_cloze"),
                    "gift": ("read_gift", "write_gift"),
                    "json": ("read_json", "write_json"),
                    "md": ("read_markdown", "write_markdown"),
                    "pdf": ("read_pdf", "write_pdf"),
                    "tex": ("read_latex", "write_latex"),
                    "txt": ("read_aiken", "write_aiken"),
                    "xml": ("read_xml", "write_xml") }

    def __init__(self, name: str = "$course$"):
        self.__questions: List[_Question] = []
        self.__categories: Dict[str, Category] = {}
        self.__name = name
        self.__parent = None

    def __iter__(self):
        return self.__categories.__iter__()

    def __getitem__(self, key: str):
        return self.__categories[key]

    def __len__(self):
        return len(self.__categories)

    def __str__(self) -> str:
        return f"Category: '{self.name}' @{hex(id(self))}"

    @staticmethod
    def __gen_hier(top: "Category", category: str) -> Category:
        cat_list = category.strip().split("/")
        start = 1 if top.name == cat_list[0] else 0
        quiz = top
        for i in cat_list[start:]:
            quiz.add_subcat(Category(i))
            quiz = quiz[i]
        return quiz

    def _to_aiken(self) -> str:
        data = ""
        for question in self.__questions:
            if isinstance(question, QMultichoice):
                data += f"{question.question.text}\n"
                correct = "ANSWER: None\n\n"
                for num, ans in enumerate(question.options):
                    data += f"{chr(num+65)}) {ans.text}\n"
                    if ans.fraction == 100:
                        correct = f"ANSWER: {chr(num+65)}\n\n"
                data += correct
        for child in self.__categories.values():
            data += child._to_aiken()
        return data

    def _to_xml_element(self, root: et.Element, strict: bool) -> None:
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
                root.append(question.to_xml(strict))
        for child in self.__categories.values():    # Then add children data
            child._to_xml_element(root, strict)

    def _to_json(self, data: dict | list):
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
            elif isinstance(val, Enum):  # For the enums
                res = val.value
            elif hasattr(val, "__dict__"):  # for the objects
                tmp = val.__dict__.copy()
                if hasattr(val, "MOODLE"):
                    tmp["MOODLE"] = val.MOODLE
                if "_Question__parent" in tmp:
                    del tmp["_Question__parent"]
                elif "_Category__parent" in tmp:
                    del tmp["_Category__parent"]
                res = self._to_json(tmp)
            if res != val:
                if isinstance(data, dict):
                    data[i] = res
                else:
                    data[num] = res
        return data

    @property
    def name(self):
        """_summary_
        """
        return self.__name

    @name.setter
    def name(self, value: str):
        if self.__parent:
            if value in self.__parent.__categories:
                raise ValueError(f"Question name \"{value}\" already "
                                 "exists on current category")
            self.__parent.__categories.pop(self.__name)
            self.__parent.__categories[value] = self
        self.__name = value

    @property
    def parent(self):
        """_summary_
        """
        return self.__parent

    @parent.setter
    def parent(self, value: Category):
        if (value is not None and self.name not in value) or\
                (self.__parent is not None and self.name in self.__parent):
            raise ValueError("This attribute can't be assigned directly. Use "
                             "parent's add/pop_question functions instead.")
        self.__parent = value

    @property
    def questions(self):
        """_summary_
        """
        return self.__questions.__iter__()

    def add_subcat(self, child: Category) -> bool:
        """_summary_
        """
        if child.name in self.__categories:
            return False
        if child.parent is not None:
            child.parent.__categories.pop(child.name)
        self.__categories[child.name] = child
        child.parent = self
        return True

    def add_question(self, question) -> bool:
        """_summary_

        Args:
            question (Question): _description_

        Returns:
            bool: _description_
        """
        if question in self.__questions or not isinstance(question, _Question):
            return False
        if question.parent is not None:
            question.parent.pop_question(question)
        self.__questions.append(question)
        question.parent = self
        return True

    def get_datasets(self) -> list:
        datasets = []
        for question in self.__questions:
            if hasattr(question, "datasets"):
                datasets.extend(question.datasets)
        for cat in self.__categories.values():
            datasets.extend(cat.get_datasets())
        return datasets

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

    def get_size(self):
        """Total number of questions in this category, including subcategories.
        """
        total = len(self.__questions)
        for cat in self.__categories.values():
            total += len(cat)
        return total

    def get_tags(self, tags: dict):
        """
        """
        for question in self.__questions:
            for name in question.tags:
                tags[name] = tags.setdefault(name, 0) + 1
        for cat in self.__categories.values():
            cat.get_tags(tags)
        return tags

    def pop_question(self, question) -> bool:
        """_summary_

        Args:
            question (questions.Question): _description_

        Returns:
            bool: if the question was added
        """
        if question not in self.__questions:
            return False
        self.__questions.remove(question)
        question.parent = None
        return True

    def pop_subcat(self, subcat: Category) -> bool:
        """

        Returns:
            bool: if the subcategory was added
        """
        if subcat.name not in self.__questions:
            return False
        self.__categories.pop(subcat.name)
        subcat.parent = None
        return True

    def merge(self, child: Category):
        to_pop = []
        for cat in child:
            if child[cat].name in self.__categories:
                return False
            if child[cat].parent is not None:
                to_pop.append(cat)
            self.__categories[child[cat].name] = child[cat]
            child[cat].parent = self
        for question in child.questions:
            self.add_question(question)
        for cat in to_pop:
            child[cat].parent.__categories.pop(child[cat].name)
        del child

    @classmethod
    def read_aiken(cls, file_path: str, category: str = "$course$"):
        """_summary_

        Args:
            file_path (str): _description_
            category (str, optional): _description_. Defaults to "$".

        Returns:
            Quiz: _description_
        """
        quiz = cls(category)
        name = file_path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        cnt = 0
        for _path in glob.glob(file_path):
            with open(_path, encoding="utf-8") as ifile:
                buffer = LineBuffer(ifile)
                while buffer.read():
                    question = QMultichoice.from_aiken(buffer, f"{name}_{cnt}")
                    quiz.add_question(question)
                    cnt += 1
        return quiz

    @classmethod
    def read_cloze(cls, file_path: str, category: str = "$course$"):
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
    def read_files(cls, files: list, category: str = "$course$"):
        """_summary_

        Args:
            folder_path (str): _description_
            category (str, optional): _description_. Defaults to "$".

        Returns:
            list: _description_
        """
        top_quiz = cls(category)
        for _path in files:
            try:
                ext = _path.rsplit(".", 1)[-1]
                top_quiz.merge(getattr(cls, cls.SERIALIZERS[ext][0])(_path))
            except (ValueError, KeyError):
                LOG.exception(f"Failed to parse file {_path}.")
        return top_quiz

    @classmethod
    def read_gift(cls, file_path: str, category: str = "$course$"):
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
        data = re.sub(r"\n//.*?(?=\n)", "", data)  # Remove comments
        # Remove \n's inside a question
        data = re.sub(r"(?<!\})\n(?!::)", "", data) + "\n"
        tmp = re.findall(r"(?:\$CATEGORY:\s*(.+))|(?:\:\:(.+?)\:\:(\[.+?\])?"
                         r"(.+?)(?:(\{.*?)(?<!\\)\}(.*?))?)\n", data)
        for i in tmp:
            if i[0]:
                quiz = Category.__gen_hier(top_quiz, i[0])
            if not i[0]:
                question = None
                ans = re.findall(r"((?<!\\)(?:=|~|TRUE|FALSE|T|F|####|#))"
                                 r"(%[\d\.]+%)?((?:(?<=\\)[=~#]|[^~=#])*)",
                                 i[4])
                if not i[4]:
                    question = QDescription.from_gift(i, ans)
                elif not ans:
                    question = QEssay.from_gift(i, ans)
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
                quiz.add_question(question)
        return top_quiz

    @classmethod
    def read_json(cls, file_path: streams):
        """
        Generic file. This is the default file format used by the QAS Editor.
        """
        def _from_json(_dt: dict):
            quiz = cls(_dt["_Category__name"])
            for qst in _dt["_Category__questions"]:
                quiz.add_question(QTYPE[qst.pop("MOODLE")].from_json(qst))
            for i in _dt["_Category__categories"]:
                quiz.add_subcat(_from_json(_dt["_Category__categories"][i]))
            return quiz
        with open(file_path, "rb") as infile:
            data = json.load(infile)
        return _from_json(data)

    @classmethod
    def read_latex(cls, file_path: str, category: str = "$course$"):
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
                      category_mkr=r"\s*#\s+(.*)"):
        """[summary]

        Args:
            file_path (str): [description]
            question_mkr (str, optional): [description].
            answer_mkr (str, optional): [description].
            category_mkr (str, optional): [description].

        Raises:
            ValueError: [description]
        """
        with open(file_path, encoding="utf-8") as infile:
            lines = infile.readlines()
        lines.append("\n")
        lines.append("\n")
        lines.reverse()
        cnt = 0
        top_quiz = cls(category)
        quiz = top_quiz
        while lines:
            match = re.match(f"({category_mkr})|({question_mkr})|"
                             f"({answer_mkr})", lines[-1])
            if match:
                if match[1]:
                    quiz = Category.__gen_hier(top_quiz, match[2])
                    lines.pop()
                elif match[3]:
                    if quiz is None:
                        raise ValueError("No classification defined")
                    QMultichoice.from_markdown(lines, answer_mkr, question_mkr,
                                               f"{prefix}_{cnt}")
                    cnt += 1
                elif match[5]:
                    raise ValueError(f"Answer found out of a question "
                                     f"block: {match[5]}.")
            else:
                lines.pop()
        return top_quiz

    @classmethod
    def read_pdf(cls, file_path: str, ptitle=r"Question \d+",
                 include_image=True):
        """_summary_

        Args:
            file_path (str): _description_
            ptitle (str, optional): _description_.
            include_image (bool, optional): _description_.

        Returns:
            Quiz: _description_
        """
        raise NotImplementedError("PDF not implemented")
        # _simg = {'/DCTDecode': "jpg", '/JPXDecode': "jp2",
        #          '/CCITTFaxDecode': "tiff"}
        # with open(file_path, "rb") as infile:
        #     pdf_file = PdfFileReader(infile)
        #     for num in range(pdf_file.getNumPages()):
        #         page: pdf.PageObject = pdf_file.getPage(num)
        #         if '/XObject' not in page['/Resources']:
        #             continue
        #         xobj = page['/Resources']['/XObject'].getObject()
        #         for obj in xobj:
        #             if xobj[obj]['/Subtype'] != '/Image':
        #                 continue
        #             size = (xobj[obj]['/Width'], xobj[obj]['/Height'])
        #             data = xobj[obj].getData()
        #             color_space = xobj[obj]['/ColorSpace'][0]
        #             if color_space == '/DeviceRGB':
        #                 mode = "RGB"
        #             elif color_space in ["/DeviceN", "/Indexed"]:
        #                 mode = "P"
        #                 if color_space == "/Indexed":
        #                     psize = int(xobj[obj]['/ColorSpace'][2])
        #                     palette = [255-int(n*psize/255) for n in \
        #                                range(256) for _ in range(3)]
        #                 else:
        #                     palette = None
        #             else:
        #                 raise ValueError(f"Mode not tested yet: "
        #                                   "{xobj[obj]['/ColorSpace']}")
        #             if '/Filter' in xobj[obj]:
        #                 xfilter = xobj[obj]['/Filter']
        #                 if xfilter == '/FlateDecode':
        #                     img = Image.frombytes(mode, size, data)
        #                     if palette:
        #                         img.putpalette(palette)
        #                     img.save(f"page{num}_{obj[1:]}.png")
        #                 elif xfilter in _simg:
        #                     name = f"page{num}_{obj[1:]}.{_simg[xfilter]}"
        #                     img = open(name, "wb")
        #                     img.write(data)
        #                     img.close()
        #                 else:
        #                     raise ValueError(f"Filter error: {xfilter}")
        #             else:
        #                 img = Image.frombytes(mode, size, data)
        #                 img.save(obj[1:] + ".png")

    @classmethod
    def read_xml(cls, file_path: str, category: str = "$course$"):
        """[summary]

        Raises:
            TypeError: [description]

        Returns:
            [type]: [description]
        """
        if not category:
            raise ValueError("Category string should not be empty")
        data_root = et.parse(file_path)
        top_quiz: Category = cls(category)
        quiz = top_quiz
        for elem in data_root.getroot():
            if elem.tag != "question":
                continue
            if elem.get("type") == "category":
                quiz = Category.__gen_hier(top_quiz, elem[0][0].text)
            elif elem.get("type") not in QTYPE:
                raise TypeError(f"Type {elem.get('type')} not implemented")
            else:
                question = QTYPE[elem.get("type")].from_xml(elem, {}, {})
                quiz.add_question(question)
        return top_quiz

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

    def write_json(self, file_path: str, pretty=False) -> None:
        """[summary]

        Args:
            file_path (str): [description]
            pretty (bool, optional): [description]. Defaults to False.
        """
        tmp = self.__dict__.copy()
        del tmp["_Category__parent"]
        with open(file_path, "w", encoding="utf-8") as ofile:
            json.dump(self._to_json(tmp), ofile, indent=4 if pretty else None)

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

    def write_xml(self, file_path: str, pretty=False, strict=True):
        """Generates XML compatible with Moodle and saves to a file.

        Args:
            file_path (str): filename where the XML will be saved
            pretty (bool): saves XML pretty printed.
            strict (bool): saves using strict Moodle format.
        """
        root = et.Element("quiz")
        self._to_xml_element(root, strict)
        with et._get_writer(file_path, "utf-8") as write:
            write("<?xml version='1.0' encoding='utf-8'?>\n")
            serialize_fxml(write, root, True, pretty)
