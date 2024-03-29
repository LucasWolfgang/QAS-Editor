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

import csv
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Iterator, List

from .enums import TestStatus
from .parsers import (aiken, cloze, csv_card, gift, ims, kahoot, latex,
                      markdown, moodle, olx)
from .question import QQuestion
from .utils import File

if TYPE_CHECKING:
    from .utils import Dataset
_LOG = logging.getLogger(__name__)


SERIALIZERS = {
    "Aiken": ("read_aiken", "write_aiken", "txt"),
    "Cloze": ("read_cloze", "write_cloze", "cloze"),
    "GIFT": ("read_gift", "write_gift", "gift"),
    "JSON": ("read_json", "write_json", "json"),
    "Markdown": ("read_markdown", "write_markdown", "md"),
    "OLX": ("read_olx", "write_olx", "olx"),
    "QTI2.1": ("read_qti12", "write_qti12", "xml"),
    "LaTex": ("read_latex", "write_latex", "tex"),
    "Moodle": ("read_moodle", "write_moodle", "xml")
}
EXTS = ";;".join(f"{k}(*.{v[2]})" for k,v in SERIALIZERS.items())


class Category:  # pylint: disable=R0904
    """A category is a set of questions and other category that have enough
    similarities to be grouped together.
    """

    read_aiken = classmethod(aiken.read_aiken)
    read_cloze = classmethod(cloze.read_cloze)
    read_anki = classmethod(csv_card.read_anki)
    read_quizlet = classmethod(csv_card.read_quizlet)
    read_gift = classmethod(gift.read_gift)
    read_kahoot = classmethod(kahoot.read_kahoot)
    read_latex_l2m = classmethod(latex.read_l2m)
    read_latex_amc = classmethod(latex.read_amc)
    read_markdown = classmethod(markdown.read_markdown)
    read_moodle = classmethod(moodle.read_moodle)
    read_moodle_backup = classmethod(moodle.read_moodle_backup)
    read_olx = classmethod(olx.read_olx)
    read_qti12 = classmethod(ims.read_qti1v2)

    write_aiken = aiken.write_aiken
    write_cloze = cloze.write_cloze
    write_anki = csv_card.write_anki
    write_quizlet = csv_card.write_quizlet
    write_gift = gift.write_gift
    write_kahoot = kahoot.write_kahoot
    write_latex_l2m = latex.write_l2m
    write_markdown = markdown.write_markdown
    write_moodle = moodle.write_moodle
    write_olx = olx.write_olx

    def __init__(self, name: str = None):
        self.__questions: List[QQuestion] = []
        self.__categories: Dict[str, Category] = {}
        self.__name = name or "$course$"
        self.__parent = None
        self.metadata: Dict[str, str] = {}
        self.datasets: List[Dataset] = None
        self.resources: List[File] = []
        self.info: str = ""

    def __iter__(self):
        return self.__categories.__iter__()

    def __getitem__(self, key: str):
        return self.__categories[key]

    def __len__(self):
        return len(self.__categories)

    def __str__(self):
        return f"Category: '{self.name}' @{hex(id(self))}"

    @property
    def questions(self) -> Iterator[QQuestion]:
        """Set of questions of this category.
        """
        return iter(self.__questions)

    @property
    def name(self):
        """Name of the category.
        """
        return self.__name

    @name.setter
    def name(self, value: str):
        if self.__parent is not None:
            if value in self.__parent:
                raise ValueError(f"Question name \"{value}\" already "
                                 "exists on current category")
            self.__parent.pop_subcat(self.__name)
            self.__name = value
            self.__parent.add_subcat(self)
        else:
            self.__name = value

    @property
    def parent(self):
        """The parent of this category. Either <Category> or None.
        """
        return self.__parent

    @parent.setter
    def parent(self, value: Category):
        if (value is not None and self.name not in value) or\
                (self.__parent is not None and self.name in self.__parent):
            raise ValueError("This attribute shouldn't be assigned directly. U"
                             "se parent's add/pop_question functions instead.")
        self.__parent = value

    def add_subcat(self, child: Category | str) -> bool:
        """Adds a category child to this category. This implementation avoids
        issues related to duplicated names and parent set/unset.
        """
        if isinstance(child, str):
            if child in self.__categories:
                return None
            child = Category(child)
        elif child.name in self.__categories:
            return None
        if child.parent is not None:
            child.parent.pop_subcat(child.name)
        self.__categories[child.name] = child
        child.parent = self
        return child

    def add_question(self, question) -> bool:
        """_summary_
        Args:
            question (Question): _description_
        Returns:
            bool: _description_
        """
        if question in self.__questions or not isinstance(question, QQuestion):
            return False
        if question.parent is not None:
            question.parent.pop_question(question)
        self.__questions.append(question)
        question.parent = self
        return True

    def find(self, results: list, title: str = None, tags: list = None,
             text: str = None, qtype: QQuestion = None, dbid: int = None):
        """Find a question inside the category based on the provided arguments.
        If the argument is not passed (same as None), it is ignored.
        Args:
            results (list): An empty list the will be filled with the results.
            title (str): A regex that matchs the question's title.
            tags (list): A list of tags (str) used in the question.
            text (str): A regex that matchs the question's text.
            qtype (QQuestion): The question type of the question.
            dbid (int): The dbid of the question (exact same number).
        """
        for question in self.__questions:
            if (title is None or re.search(title, question.name)) and \
                 (tags is None or set(tags).issubset(set(question.tags))) and\
                 (text is None or re.search(text, question.question.get())) and\
                 (qtype is None or isinstance(question, qtype)) and \
                 (dbid is None or dbid == question.dbid):
                results.append(question)
        for cat in self.__categories.values():
            cat.find(results, title, tags, text, qtype, dbid)

    def gen_dbids(self, dont_use: list, initial: int = 0) -> int:
        """Generates unique IDs for each of the questions within this category
        in sequencially, starting from initial value.
        """
        self.get_dbids(dont_use)
        for question in self.__questions:
            while initial in dont_use:
                initial += 1
            if question.dbid is None:
                question.dbid = initial
                initial += 1
        for cat in self.__categories.values():
            initial = cat.gen_dbids(dont_use, initial)
        return initial

    def get_datasets(self, datasets: dict):
        """Fill a dictionary with all the databases objets found in this
        category. It asks for an empty dictionary instead of returning one.
        """
        for question in self.__questions:
            if hasattr(question, "datasets"):
                for data in question.datasets:
                    key = f"{data.status.name}> {data.name}"
                    if data.status == TestStatus.PRV:
                        key += f" ({hex(id(data))})"
                    if key in datasets and datasets[key] != data:
                        _LOG.error("Public dataset %s has different instances."
                                   "New found in %s.", data.name, self)
                    classes = datasets.setdefault(key, (data, []))[1]
                    classes.append(question)
        for cat in self.__categories.values():
            cat.get_datasets(datasets)

    def get_dbids(self, dbids: list):
        """Fill a list with all he IDs already in use in this category.
        """
        for question in self.__questions:
            if question.dbid:
                dbids.append(question.dbid)
        for cat in self.__categories.values():
            cat.get_dbids(dbids)

    def get_depth(self, consitent: bool) -> int:
        """The depth of classifications in this classification.
        Args:
            consitent (bool): if True, returns the smallest stack depth, otherwise
                returns the biggest stack depth.
        """
        value = 0
        for cat in self.__categories.values():
            tmp = cat.get_depth(consitent)
            if value != 0:
                value = min(tmp, value) if consitent else max(tmp, value)
            else:
                value = tmp
        return value + 1

    def get_size(self, recursive=False):
        """Total number of questions in this category, including subcategories.
        """
        total = len(self.__questions)
        if recursive:
            for cat in self.__categories.values():
                total += cat.get_size(True)
        return total

    def get_tags(self, tags: dict):
        """Fill a dictionary with all the tags defined in this category, being
        the tag used as a key, and the number of ocurrencies as values. It
        asks for an empty dictionary instead of returning one.
        """
        for question in self.__questions:
            for name in question.tags:
                tags[name] = tags.setdefault(name, 0) + 1
        for cat in self.__categories.values():
            cat.get_tags(tags)

    def get_question(self, index: int) -> QQuestion:
        """A helper to get an given index. Using <code>questions</code> would
        not work becuase it returns an iterator, which requires to be cast to
        list before accessing.
        """
        return self.__questions[index]

    def merge(self, child: Category):
        """Merge this <code>Category</code> with another one. This merge will
        move the subcats and questions of the provided <code>Category</code>
        to this one, ignoring duplicated, and deleting it in the end.
        """
        to_pop = []
        for cat in child:
            if child[cat].name in self.__categories:
                _LOG.warning("Question %s not merged. Name %s already in use",
                             cat, child[cat].name)
            elif child[cat].parent is not None:
                to_pop.append(cat)
        for question in child.questions:
            self.add_question(question)
        for cat_name in to_pop:
            cat = child.pop_subcat(cat_name)
            self.__categories[cat_name] = cat
            cat.parent = self
        del child
        return True

    def pop_question(self, question: QQuestion) -> bool:
        """_summary_

        Returns:
            bool: if the question was removed
        """
        if question not in self.__questions:
            return False
        self.__questions.remove(question)
        question.parent = None
        return True

    def pop_subcat(self, subcat: Category | str) -> Category:
        """Pop a given subcat. This was made a common method instead of a magic
        method on purpose. This allows removing the category

        Returns:
            bool: if the subcategory was removed
        """
        name = subcat.name if isinstance(subcat, Category) else subcat
        child = self.__categories.pop(name)
        child.parent = None
        return child

    def sort_questions(self, recursive: bool):
        """Sort the questions in this category.
        """
        self.__questions = sorted(self.__questions, key=lambda qst: qst.name)
        if recursive:
            for cat in self.__categories.values():
                cat.sort_questions(recursive)

    def sort_subcats(self, recursive: bool):
        """Sort the sub-categories (children) of this category.
        """
        self.__categories = dict(sorted(self.__categories.items(),
                                 key=lambda elem: elem[0]))
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
            ext = _path.rsplit(".", 1)[-1]
            for func in dir(cls):
                try:
                    if callable(getattr(cls, func)) and func[:6] == "write_":
                        obj = getattr(cls, func)(_path)
                        if obj:
                            top_quiz.merge(obj)
                            break
                except (ValueError, KeyError, TypeError):
                    pass
            else:
                _LOG.error("Failed to parse file %s. No valid parser"
                           " found for %s.", _path, ext)
        return top_quiz

    def update_links(self, filename: str, link_header: str, recursive: bool,
                     attrs: tuple = None):
        """Update the html that point to link on question texts.
        # TODO, define how to handle the changes
        Args:
            filename (str): _description_
            link_header (str): _description_
            attr (tuple, optional): Attributes to update. Defaults to all.
        """
        link_map = {}
        with open(filename, encoding="utf-8") as csvfile:
            for row in csv.DictReader(csvfile):
                link_map[row[link_header]] = row
        for file in self.resources:
            pass

@dataclass
class TestStatus:
    retries: int = 0
    """Number of total retries in the test"""
    grade: float = 0
    """Grade resulting for a given test"""


class Test:

    def __init__(self, data: List[QQuestion]|Category) -> None:
        self._idx = 0
        if isinstance(data, list):
            self._qlist = {qst: TestStatus() for qst in data}
        else:
            self._qlist = {}
            def get_next(cat):
                for question in data.questions:
                    self._qlist[question] = TestStatus()
                for subcat in cat:
                    get_next(subcat)
            get_next(data)

    def start(self):
        for question in self._qlist:
            yield question

    def process(self, question: QQuestion):
        pass
