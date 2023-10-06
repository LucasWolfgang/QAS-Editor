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
import logging
import random
from typing import TYPE_CHECKING
from .enums import EmbeddedFormat, Grading, RespFormat, ShowUnits, ShowAnswer, ShuffleType,\
                   Distribution, Numbering, Synchronise, TextFormat, Status
from .utils import Serializable, MarkerError, AnswerError, File, Dataset, \
                   FText, Hint, Unit, TList, attribute_setup
from .answer import ACalculated, ACrossWord, Answer, EmbeddedItem, ANumerical,\
                    DragGroup, DragImage, SelectOption, Subquestion,\
                    DropZone, DragItem
if TYPE_CHECKING:
    from typing import List, Dict, Tuple
    from .enums import Direction
    from .category import Category
_LOG = logging.getLogger(__name__)


QNAME: Dict[str, _Question] = {}
MARKER_INT = 9635


class _Question(Serializable):
    """This is an abstract class Question used as a parent for specific
    types of Questions.
    """
    QNAME = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.QNAME is not None:
            QNAME[cls.QNAME] = cls

    def __init__(self, name="qstn", default_grade=1.0, question: FText = None,
                 dbid: int = None, remarks: FText = None, tags: TList = None,
                 feedbacks: Dict[float, FText] = None, time_lim: int = 60,
                 notes: str = "", free_hints: list = None):
        """[summary]
        Args:
            name (str): name of the question
            question (FText): text of the question
            default_grade (float): the default mark
            general_feedback (str, optional): general feedback.
            dbid (int, optional): id number.
        """
        self.name = str(name)
        self.default_grade = float(default_grade)
        self.time_lim = int(time_lim)
        self.dbid = int(dbid) if dbid else None
        self.notes = str(notes)
        self._question = FText()
        self.question = question
        self._remarks = FText()
        self.remarks = remarks
        self._feedbacks: Dict[float, FText] = feedbacks if feedbacks else {}
        self._tags = TList(str, tags)
        self._free_hints = TList(FText, free_hints)
        self.__parent = None
        _LOG.debug("New question (%s) created.", self)

    def __str__(self) -> str:
        return f"{self.QNAME}: '{self.name}' @{hex(id(self))}"

    question = FText.prop("_question", "Question text")
    remarks = FText.prop("_remarks", "Solution or global feedback")

    @property
    def feedbacks(self) -> Dict[float, FText]:
        """
        """
        return self._feedbacks

    @property
    def free_hints(self) -> TList:
        """
        """
        return self._free_hints

    @property
    def parent(self) -> Category:
        """_summary_
        """
        return self.__parent

    @parent.setter
    def parent(self, value):
        if (self.__parent is not None and self in self.__parent.questions) or \
                (value is not None and self not in value.questions):
            raise ValueError("This attribute can't be assigned directly. Use "
                             "parent's add/pop_question functions instead.")
        self.__parent = value
        _LOG.debug("Added (%s) to parent (%s).", self, value)

    @property
    def tags(self) -> TList:
        """_summary_
        """
        return self._tags

    def check(self):
        """Check if the instance parameters have valid values. Call this method
        before exporting the instance, or right after modifying many valid of
        a instance.
        """
        if (not isinstance(self.name, str) or self.time_lim < 0
                or (self.dbid is not None and not isinstance(self.dbid, int))
                or self.default_grade < 0):
            raise ValueError("Invalid value(s).")
        for key, value in self._feedbacks.items():
            if not isinstance(key, float) or not isinstance(value, FText):
                raise TypeError()


class _QHasOptions(_Question):
    """Helper class for questions that have a exact answer. Dont misread the
    name, numeric questions also have options since you need to define a
    correct answer, among other scenarios to define the final grade.
    """
    ANS_TYPE = None

    def __init__(self, options: list = None, hints: List[Hint] = None,
                 max_tries=-1, shuffle: ShuffleType | bool = False,
                 show_ans: ShowAnswer | bool = False, ordered=True, **kwargs):
        super().__init__(**kwargs)
        self.max_tries = int(max_tries)
        self._fail_hints = TList(Hint, hints)
        self._options = TList(self.ANS_TYPE, options)
        self.ordered = bool(ordered)
        if isinstance(show_ans, ShowAnswer):
            self.show_ans = show_ans
        else:
            self.show_ans = ShowAnswer(show_ans)
        if isinstance(shuffle, ShuffleType):
            self.shuffle = shuffle
        else:
            self.shuffle = ShuffleType(shuffle)

    @property
    def options(self) -> TList:
        """_summary_
        """
        return self._options

    @property
    def fail_hints(self) -> TList:
        """_summary_
        """
        return self._fail_hints

    def check(self):
        super().check()
        fnum =  len(self._fail_hints)
        if self.max_tries > 0 and fnum > self.max_tries:
            raise ValueError(f"Number of Fail Hints ({fnum}) should be smaller"
                             f" than max_tries ({self.max_tries})")


class _QHasUnits:
    """Helper class used for questions that handle units.
    """

    def __init__(self, grading_type=Grading.IGNORE, unit_penalty=0.0,
                 show_unit=ShowUnits.TEXT, left=False, **kwargs):
        super().__init__(**kwargs)
        self.grading_type = grading_type
        self.unit_penalty = unit_penalty
        self.show_unit = show_unit
        self.left = left


class QCalculated(_QHasUnits, _QHasOptions):
    """Represents a "Calculated"q question, in which a numberical result should
    be provided. Note that <code>single</code> tag may show up in Moodle
    xml document but this seems to be just a bug. The class don't use it.
    """
    QNAME = "Calculated"
    ANS_TYPE = ACalculated

    def __init__(self, datasets: List[Dataset] = None, units: List[Unit] = None,
                 synchronize: Synchronise = None, **kwargs):
        """[summary]

        Args:
            synchronize (int): [description]
            units (List[Unit], optional): [description].
            datasets (List[Dataset], optional): Data set of variables to be
                used during question in equations.
        """
        super().__init__(**kwargs)
        self.synchronize = Synchronise.NO_SYNC if synchronize is None \
            else synchronize
        self.units = [] if units is None else units
        self.datasets = [] if datasets is None else datasets


class QCalculatedMC(_QHasOptions):
    """Represents a "Calculated" question with multiple choices, behaving like
    a multichoice question where the answers are calculated using equations and
    datasets.
    """
    QNAME = "Calculated Multichoice"
    ANS_TYPE = ACalculated

    def __init__(self, synchronize: Synchronise, numbering: Numbering = None,
                 single=False, datasets: List[Dataset] = None, **kwargs):
        super().__init__(**kwargs)
        self.synchronize = synchronize
        self.single = single
        self.numbering = Numbering.ALF_LR if numbering is None else numbering
        self.datasets = [] if datasets is None else datasets

    def add_dataset(self, status: Status, name: str, dist: Distribution,
                    minim: float, maxim: float, dec: int) -> None:
        """_summary_

        Args:
            status (Status): _description_
            name (str): _description_
            dist (Distribution): _description_
            minim (float): _description_
            maxim (float): _description_
            dec (int): _description_
        """
        data = Dataset(status, name, "calculated", dist, minim, maxim, dec)
        self.datasets.append(data)


class QCrossWord(_Question):
    """Represents a Crossword question.
    """

    def __init__(self, x_grid: int = 0, y_grid: int = 0,
                 words: List[ACrossWord] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.x_grid = x_grid
        self.y_grid = y_grid
        self.words = words if words else []      # The class only checks grid

    def add_word(self, word: str, coord_x: int, coord_y: int,
                 direction: Direction, clue: str) -> None:
        """_summary_

        Args:
            word (str): _description_
            coord_x (int): _description_
            coord_y (int): _description_
            direction (Direction): _description_
            clue (str): _description_

        Raises:
            ValueError: _description_
        """
        if coord_x < 0 or coord_x > self.x_grid+len(word) or \
                coord_y < 0 or coord_y > self.y_grid+len(word):
            raise ValueError("New word does not fit in the current grid")
        self.words.append(ACrossWord(word, coord_x, coord_y, clue, direction))

    def get_solution(self) -> bool:
        """
        Iterate over the object list to verify if it is valid.
        """
        solution: Dict[int, Dict[int, str]] = {}
        for word in self.words:
            if word.coord_x not in solution:
                solution[word.x] = {}
            if word.coord_y not in solution:
                solution[word.coord_x][word.coord_y] = {}


class QDaDImage(_QHasOptions):
    """Drag and Drop items onto drop zones, where the items are custom images.
    """
    QNAME = "Drag and Drop Image"
    ANS_TYPE = DragImage

    def __init__(self, background: File = None,
                 zones: List[DropZone] = None, **kwargs):
        super().__init__(**kwargs)
        self.background = background
        self._zones = TList(DropZone, zones)

    @property
    def zones(self):
        """Zones
        """
        return self._zones


class QDaDMarker(QDaDImage):
    """Drag and Drop items onto drop zones, where the items are markers.
    """
    QNAME = "Drag and Drop Marker"
    ANS_TYPE = DragItem

    def __init__(self, highlight=False, **kwargs):
        super().__init__(**kwargs)
        self.highlight = highlight


class QDaDText(_QHasOptions):
    """Drag and drop text boxes into question text.
    """
    QNAME = "Drag and Drop Text"
    ANS_TYPE = DragGroup

    def pure_text(self):
        """Return the text formatted as expected by the end-tool, which is
        currently only moodle.
        """
        char = chr(MARKER_INT)
        find = self.question.text.find(char)
        text = [self.question.text[:find]]
        for question in len(self.options):
            text.append(question.to_text())
            end = self.question.text.find(char, find + 1)
            text.append(self.question.text[find + 1: end])
            find = end
        text.append(self.question.text[-1])  # Wont be included by default
        return "".join(text)

    def check(self):
        pass


class QEmbedded(_QHasOptions):
    """An embedded question. Questions are marked on the text list using a 
    Marker defined using MARKER_INT.
    """
    QNAME = "Cloze"
    ANS_TYPE = EmbeddedItem
    _CLOZE_PATTERN = re.compile(r"(?!\\)\{(\d+)?(?:\:(.*?)\:)(.*?(?!\\)\})")

    def check(self):
        markers = self.question.text.count(chr(MARKER_INT))
        if markers != len(self.options):
            raise MarkerError("Number of markers and questions differ")
        for question in self.options:
            if all(opt.fraction == 0 for opt in question.opts):
                raise AnswerError("All answer options have 0 grade")

    @staticmethod
    def from_cloze_text(text: str) -> Tuple[list, list]:
        """Return a tuple with the Marked text and the data extracted.
        """
        ftext = []
        start = 0
        items = []
        for match in QEmbedded._CLOZE_PATTERN.finditer(text):
            opts = []
            for opt in match[3].split("~"):
                if not opt:
                    continue
                tmp = opt.strip("}~").split("#")
                if len(tmp) == 2:
                    tmp, fdb = tmp
                else:
                    tmp, fdb = tmp[0], ""
                frac = 0.0
                if tmp[0] == "=":
                    frac = 100.0
                    tmp = tmp[1:]
                elif tmp[0] == "%":
                    frac, tmp = tmp[1:].split("%")
                    frac = float(frac)
                feedback = FText(fdb, TextFormat.PLAIN)
                opts.append(Answer(frac, tmp, feedback, TextFormat.PLAIN))
            item = EmbeddedItem(int(match[1]), EmbeddedFormat(match[2]), opts)
            items.append(item)
            ftext.append(text[start: match.start()])
            ftext.append(item)
            start = match.end()
        ftext.append(text[start:])
        return ftext, items

    def to_cloze_text(self, embedded_name: bool) -> str:
        """Return the text formatted as expected by the end-tool, which is
        currently only moodle.
        """
        tmp = self.question.text.copy()
        text = [self.name, "\n", *tmp] if embedded_name else tmp
        for idx in range(len(text)):
            item = text[idx]
            if isinstance(item, EmbeddedItem):
                text[idx] = item.to_cloze()
        return "".join(text)


class QDrawing(_Question):
    """Represents a question where the use is free to make any drawing. The
    result is submited for review (there is no automatic correct/wrong
    feedback).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class QEssay(_Question):
    """Represents an essay question, in which the answer is written as an essay
    and need to be submitted for review (no automatic correct/answer feedback
    provided).
    """
    QNAME = "Essay"

    def __init__(self, lines=10, attachments=0, max_bytes=0, file_types="",
                 rsp_required=True, atts_required=False,
                 min_words: int = None, max_words: int = None,
                 grader_info: FText = None, template: FText = None,
                 rsp_format=RespFormat.HTML, **kwargs):
        super().__init__(**kwargs)
        self.rsp_format = rsp_format
        self.rsp_required = rsp_required
        self.lines = lines
        self.min_words = min_words
        self.max_words = max_words
        self.attachments = attachments
        self.atts_required = atts_required
        self.max_bytes = max_bytes
        self.file_types = file_types
        self.grader_info = grader_info
        self.template = template


class QMatching(_QHasOptions):
    """Represents a Matching question, in which the goal is to find matchs.
    """
    QNAME = "Matching"
    ANS_TYPE = Subquestion


class QMissingWord(_QHasOptions):
    """A Missing Word question.
    TODO: Fully replace it with QCloze, since it a simplified version of it.
    """
    QNAME = "Missing Word"
    ANS_TYPE = SelectOption

    def check(self):
        total = len(re.findall(r"\[\[[0-9]+\]\]", self.question.text))
        if total != len(self.options):
            raise MarkerError("Incorrect number of marker in text.")

    @staticmethod
    def get_items(text: str) -> Tuple[list, list]:
        """Return a tuple with the Marked text and the data extracted.
        """
        ftext = []
        start = 0
        for match in re.finditer(r"\[\[[0-9]+\]\]", text):
            ftext.append(text[start: match.start()])
            ftext.append(MARKER_INT)
            start = match.end()
        ftext.append(text[start:])
        return ftext, None

    def pure_text(self):
        """Return the text formatted as expected by the end-tool, which is
        currently only moodle.
        """
        char = chr(MARKER_INT)
        find = self.question.text.find(char)
        text = [self.question.text[:find]]
        for num in range(len(self.options)):
            text.append(str(num+1))
            end = self.question.text.find(char, find + 1)
            text.append(self.question.text[find + 1: end])
            find = end
        text.append(self.question.text[-1])  # Wont be included by default
        return "".join(text)


class QMultichoice(_QHasOptions):
    """A Multiple choice question.
    """
    QNAME = "Multichoice"
    ANS_TYPE = Answer

    def __init__(self, single=True, show_instr=False, use_dropdown=False,
                 numbering: Numbering = None, **kwargs):
        super().__init__(**kwargs)
        self.single = single
        self.show_instr = show_instr
        self.numbering = Numbering.ALF_LR if numbering is None else numbering
        self.use_dropdown = use_dropdown


class QNumerical(_QHasUnits, _QHasOptions):
    """
    This class represents 'Numerical Question' question type.
    """
    QNAME = "Numerical"
    ANS_TYPE = ANumerical

    def __init__(self, units: List[Unit] = None,  **kwargs):
        super().__init__(**kwargs)
        self.units = [] if units is None else units


class QProblem(_Question):
    """A class that accepts other questions as a internal enumeration. Used
    when there is a common header and 
    """
    QNAME = "Enumeration"

    def __init__(self, qtype = _Question, children: List[_Question] = None,  
                 numbering: Numbering = None,**kwargs):
        super().__init__(**kwargs)
        self.children = children if children else TList(qtype)
        self.numbering = Numbering.ALF_LR if numbering is None else numbering

    @classmethod
    def random_matching(cls, quantity: int, include_subcat: bool ,**kwargs):
        """Creates a random problem based on existing QMatching questions.
        Args:
            quantity (int): _description_
            include_subcat (bool): _description_
        """
        kwargs["qtype"] = QMatching
        problem = cls(**kwargs)
        possibilities = []
        used = []
        for question in problem.parent.questions:
            if isinstance(question, QMatching):
                possibilities.append(question)
        while len(used) < quantity:
            idx = random.randint(0, len(possibilities)-1)
            if idx not in used:
                used.append(idx)
                problem.children.append(possibilities[idx])
        return problem


class QRandomMatching(_QHasOptions):
    """A Random Match question. Unlike to other MTCS questions, it does not
    have options, reusing other questions randomly instead. It was implemented
    more targetting Moodle, since other platforms dont store this in databases.
    """
    QNAME = "Random Matching"

    def __init__(self, choose: int = 0, subcats: bool = False, **kwargs):
        super().__init__(**kwargs)
        delattr(self, "_options")
        delattr(self, "shuffle")
        self.choose = choose
        self.subcats = subcats


class QShortAnswer(_QHasOptions):
    """This class represents 'Short answer' question.
    TODO: Fully replace it with QCloze, since it a simplified version of it.
    """
    QNAME = "Short Answer"
    ANS_TYPE = Answer

    def __init__(self, use_case=False, **kwargs):
        super().__init__(**kwargs)
        self.use_case = use_case


class QTrueFalse(_Question):
    """This class represents true/false question. It could be child of
    _QHasOptions, but due to its simplificity, it was derived from _Question
    """
    QNAME = "True or False"

    def __init__(self, correct: bool, true_feedback: FText | str,
                 false_feedback: FText | str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.correct = correct
        self._true_feedback = FText()
        self.true_feedback = true_feedback
        self._false_feedback = FText()
        self.false_feedback = false_feedback

    true_feedback = FText.prop("_true_feedback")
    false_feedback = FText.prop("_false_feedback")


class QQuestion:
    """New global question type, which is based on the QTI format, instead of 
    Moodle, which was the previous one.
    """

    def __init__(self, name="qstn", dbid: int = None, tags: TList = None,
                 notes: str = ""):
        """[summary]
        Args:
            name (str): name of the question
            question (FText): text of the question
            default_grade (float): the default mark
            dbid (int, optional): id number.
        """
        self.name = str(name)
        self.dbid = int(dbid) if dbid else None
        self.notes = str(notes)
        self._time_lim = 0
        self._body = None
        self._notes = None
        self._tags = TList(str, tags)
        self.__parent: Category = None
        _LOG.debug("New question (%s) created.", self)

    def __str__(self) -> str:
        return f"{self.QNAME}: '{self.name}' @{hex(id(self))}"

    body = attribute_setup(FText, "_body", "Question body")
    time_lim = attribute_setup(int, "_time_lim")

    @property
    def parent(self) -> Category:
        """_summary_
        """
        return self.__parent

    @parent.setter
    def parent(self, value: Category):
        if (self.__parent is not None and self in self.__parent.questions) or \
                (value is not None and self not in value.questions):
            raise ValueError("This attribute can't be assigned directly. Use "
                             "parent's add/pop_question functions instead.")
        self.__parent = value
        _LOG.debug("Added (%s) to parent (%s).", self, value)

    @property
    def tags(self) -> TList:
        """_summary_
        """
        return self._tags

    def check(self):
        """Check if the instance parameters have valid values. Call this method
        before exporting the instance, or right after modifying many valid of
        a instance.
        """
        if (not isinstance(self.name, str) or self.time_lim < 0
                or (self.dbid is not None and not isinstance(self.dbid, int))):
            raise ValueError("Invalid value(s).")
        for key, value in self._feedbacks.items():
            if not isinstance(key, float) or not isinstance(value, FText):
                raise TypeError()
            