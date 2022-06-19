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
import re
from typing import TYPE_CHECKING

from .utils import Serializable
from .questions import _Question
from .enums import Status
from ._parsers import aiken, cloze, gift, json, kahoot, latex, markdown, moodle
if TYPE_CHECKING:
    from typing import Dict, List   # pylint: disable=C0412
LOG = logging.getLogger(__name__)


SERIALIZERS = { 
    "cloze": ("read_cloze", "write_cloze"),
    "gift": ("read_gift", "write_gift"),
    "json": ("read_json", "write_json"),
    "md": ("read_markdown", "write_markdown"),
    "pdf": ("read_pdf", "write_pdf"),
    "tex": ("read_latex", "write_latex"),
    "txt": ("read_aiken", "write_aiken"),
    "xml": ("read_moodle", "write_moodle")
}


class Category(Serializable):  # pylint: disable=R0904
    """
    This class represents Quiz as a set of Questions.
    """

    read_aiken = classmethod(aiken.read_aiken)
    read_cloze = classmethod(cloze.read_cloze)
    read_gift = classmethod(gift.read_gift)
    read_json = classmethod(json.read_json)
    read_kahoot = classmethod(kahoot.read_kahoot)
    read_latex = classmethod(latex.read_latex)
    read_markdown = classmethod(markdown.read_markdown)
    read_moodle = classmethod(moodle.read_moodle)

    write_aiken = aiken.write_aiken
    write_cloze = cloze.write_cloze
    write_json = json.write_json
    write_kahoot = kahoot.write_kahoot
    write_gift = gift.write_gift
    write_latex = latex.write_latex
    write_markdown = markdown.write_markdown
    write_moodle = moodle.write_moodle

    def __init__(self, name: str = None):
        self.__questions: List[_Question] = []
        self.__categories: Dict[str, Category] = {}
        self.__name = name if name else "$course$"
        self.__parent = None
        self.data = {}
        self.info = None

    def __iter__(self):
        return self.__categories.__iter__()

    def __getitem__(self, key: str):
        return self.__categories[key]

    def __len__(self):
        return len(self.__categories)

    def __str__(self) -> str:
        return f"Category: '{self.name}' @{hex(id(self))}"

    @staticmethod
    def gen_hier(top: "Category", category: str) -> Category:
        cat_list = category.strip().split("/")
        start = 1 if top.name == cat_list[0] else 0
        quiz = top
        for i in cat_list[start:]:
            quiz.add_subcat(Category(i))
            quiz = quiz[i]
        return quiz

    @property
    def questions(self):
        """_summary_
        """
        return self.__questions.__iter__()

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

    def find(self, results: list, title: str = None, tags: list = None, 
             text: str = None, qtype: _Question = None, dbid: int = None):
        """
        """
        for question in self.__questions:
            if (title is None or re.search(title, question.name)) and \
                 (tags is None or set(tags).issubset(set(question.tags))) and \
                 (text is None or re.search(text, question.question.text)) and \
                 (qtype is None or isinstance(question, qtype)) and \
                 (dbid is None or dbid == question.dbid):
                results.append(question)       
        for cat in self.__categories.values():
            cat.find(results, title, tags, text, qtype, dbid)

    def get_datasets(self, datasets: dict):
        """
        """
        for question in self.__questions:
            if hasattr(question, "datasets"):
                for data in question.datasets:
                    key = f"{data.status.name}> {data.name}"
                    if data.status == Status.PRV:
                        key += f" ({hex(id(data))})"
                    if key in datasets and datasets[key] != data:
                        LOG.error("Public dataset %s has different instances."
                                  "New found in %s.", data.name, self)
                    classes = datasets.setdefault(key, (data, []))[1]
                    classes.append(question)
        for cat in self.__categories.values():
            cat.get_datasets(datasets)

    def get_size(self, recursive=False):
        """Total number of questions in this category, including subcategories.
        """
        total = len(self.__questions)
        if recursive:
            for cat in self.__categories.values():
                total += cat.get_size(True)
        return total

    def get_tags(self, tags: dict):
        """
        """
        for question in self.__questions:
            for name in question.tags:
                tags[name] = tags.setdefault(name, 0) + 1
        for cat in self.__categories.values():
            cat.get_tags(tags)

    def get_question(self, index: int) -> _Question:
        """A helper to get an given index. Using <code>questions</code> would
        not work becuase it returns an iterator, which requires to be cast to
        list before accessing.
        """
        return self.__questions[index]


    def merge(self, child: Category):
        """
        """
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

    def sort_questions(self, recursive: bool):
        """
        """
        self.__questions = sorted(self.__questions, key = lambda qst: qst.name)
        if recursive:
            for cat in self.__categories.values():
                cat.sort_questions(recursive)

    def sort_subcats(self, recursive: bool):
        """
        """
        self.__categories = { key: val for key, val in 
                sorted(self.__categories.items(), key = lambda elem: elem[0]) }
        if recursive:
            for cat in self.__categories.values():
                cat.sort_subcats(recursive)

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
                top_quiz.merge(getattr(cls, SERIALIZERS[ext][0])(_path))
            except (ValueError, KeyError):
                LOG.exception(f"Failed to parse file {_path}.")
        return top_quiz

