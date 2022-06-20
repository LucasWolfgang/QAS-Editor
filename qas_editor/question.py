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
from typing import TYPE_CHECKING
from .enums import ClozeFormat, Grading, RespFormat, ShowUnits, Status,\
                   Distribution, Numbering, Synchronise, TextFormat
from .utils import Serializable, MarkerError, AnswerError, B64File, Dataset, \
                   FText, Hint, Unit, TList
from .answer import ACalculated, ACrossWord, Answer, ClozeItem, ANumerical,\
                    DragGroup, DragImage, SelectOption, Subquestion,\
                    DropZone, DragItem
if TYPE_CHECKING:
    from typing import List, Dict, Iterator
    from .enums import Direction
    from .category import Category
LOG = logging.getLogger(__name__)


QNAME: Dict[str, _Question] = {}
MARKER_INT = 9635


class _Question(Serializable):
    """
    This is an abstract class Question used as a parent for specific
    types of Questions.
    """
    MOODLE = None
    QNAME = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.QNAME is not None:
            QNAME[cls.QNAME] = cls

    def __init__(self, name="qstn", default_grade=1.0, question: FText = None,
                 dbid: int = None, feedback: FText = None, tags: TList = None,
                 time_lim: int = 60):
        """
        [summary]

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
        self._question = FText("questiontext")
        self.question = question
        self._feedback = FText("generalfeedback")
        self.feedback = feedback
        self._tags = TList(str, tags)
        self.__parent = None

    def __str__(self) -> str:
        return f"{self.QNAME}: '{self.name}' @{hex(id(self))}"

    question = FText.prop("_question")
    feedback = FText.prop("_feedback")

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

    @property
    def tags(self) -> Iterator:
        """_summary_
        """
        return self._tags

    def check(self):
        """Check if the instance parameters have valid values. Call this method
        before exporting the instance, or right after modifying many valid of
        a instance.
        """
        if (not isinstance(self.name, str) or self.time_lim < 0 or (self.dbid
                is not None and not isinstance(self.dbid, (None, int)))
                or self.default_grade < 0):
            raise ValueError("Invalid value.")


class _QuestionMT(_Question):
    """
    """
    ANS_TYPE = None

    def __init__(self, options: list = None, hints: List[Hint] = None,
                 penalty=0.5, **kwargs):
        super().__init__(**kwargs)
        self.penalty = float(penalty)
        self.hints = [] if hints is None else hints
        self._options = TList(self.ANS_TYPE, options)

    @property
    def options(self) -> TList:
        """_summary_
        """
        return self._options


class _QuestionMTCS(_QuestionMT):
    """Represents classes that have both Multiple tries attributes and
    Combinated Feedbacks parameters. There are no classes that don't present
    all the 4 first attributes. Shuffle was added here too because it is
    also used by all the classes that uses the other 2 groups, except
    <code>QRandomMatching</code>. For now, this is the more efficient way to
    handle this. TODO: track future updates to shuffle attribute.
    """

    def __init__(self, if_correct: FText = None, if_incomplete: FText = None,
                 if_incorrect: FText = None, shuffle=False, show_num=False,
                 **kwargs):
        super().__init__(**kwargs)
        self._if_correct = FText("correctfeedback")
        self.if_correct = if_correct
        self._if_incomplete = FText("partiallycorrectfeedback")
        self.if_incomplete = if_incomplete
        self._if_incorrect = FText("incorrectfeedback")
        self.if_incorrect = if_incorrect
        self.show_num = show_num
        self.shuffle = shuffle

    if_correct = FText.prop("_if_correct")
    if_incomplete = FText.prop("_if_incomplete")
    if_incorrect = FText.prop("_if_incorrect")


class _QuestionMTUH(_QuestionMT):
    """A
    """

    def __init__(self, grading_type=Grading.IGNORE, unit_penalty=0.0,
                 show_unit=ShowUnits.TEXT, left=False, **kwargs):
        super().__init__(**kwargs)
        self.grading_type = grading_type
        self.unit_penalty = unit_penalty
        self.show_unit = show_unit
        self.left = left


class QCalculated(_QuestionMTUH):
    """Represents a "Calculated"q question, in which a numberical result should
    be provided. Note that <code>single</code> tag may show up in Moodle
    xml document but this seems to be just a bug. The class don't use it.
    """
    MOODLE = "calculated"
    QNAME = "Calculated"
    ANS_TYPE = ACalculated

    def __init__(self, datasets: List[Dataset] = None,
                 units: List[Unit] = None, synchronize: Synchronise = None,
                 **kwargs):
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


class QCalculatedSimple(QCalculated):
    """Same as QCalculated. Implemented only for compatibility with the moodle
    XML format. It may be removed in the future, so it is not recommended to be
    used.
    """
    MOODLE = "calculatedsimple"
    QNAME = "Simplified Calculated"


class QCalculatedMC(_QuestionMTCS):
    """Represents a "Calculated" question with multiple choices, behaving like
    a multichoice question where the answers are calculated using equations and
    datasets.
    """
    MOODLE = "calculatedmulti"
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


class QCloze(_QuestionMT):
    """This is a very simples class that hold cloze data. All data is compressed
    inside the question text, so no further implementation is necessary.
    """
    MOODLE = "cloze"
    QNAME = "Cloze"
    ANS_TYPE = ClozeItem
    _PATTERN = re.compile(r"(?!\\)\{(\d+)?(?:\:(.*?)\:)(.*?(?!\\)\})")

    def check(self):
        markers = self.question.text.count(chr(MARKER_INT))
        if markers != len(self.options):
            raise MarkerError("Number of markers and questions differ")
        for question in self.options:
            if all(opt.fraction == 0 for opt in question.opts):
                raise AnswerError("All answer options have 0 grade")

    @staticmethod
    def get_items(text: str):
        """Return a tuple with the Marked text and the data extracted.
        """
        gui_text = []
        start = 0
        options = []
        for match in QCloze._PATTERN.finditer(text):
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
                feedback = FText("feedback", fdb, TextFormat.PLAIN)
                opts.append(Answer(frac, tmp, feedback, TextFormat.PLAIN))
            item = ClozeItem(int(match[1]), ClozeFormat(match[2]), opts)
            options.append(item)
            gui_text.append(text[start: match.start()])
            start = match.end()
        gui_text.append(text[start:])
        return chr(MARKER_INT).join(gui_text), options

    def pure_text(self, embedded_name) -> str:
        """Return the text formatted as expected by the end-tool, which is
        currently only moodle.
        """
        char = chr(MARKER_INT)
        find = self.question.text.find(char)
        text = [self.name, "\n", self.question.text[:find]] if \
            embedded_name else [self.question.text[:find]]
        for question in self.options:
            text.append(question.to_text())
            end = self.question.text.find(char, find + 1)
            text.append(self.question.text[find + 1: end])
            find = end
        text.append(self.question.text[-1])  # Wont be included by default
        return "".join(text)


class QDescription(_Question):
    """A description that can have 1 or more subquestion.
    TODO fully replace it with a <code>Category</code> class.
    """
    MOODLE = "description"
    QNAME = "Description"

    def __init__(self, children: List[_Question] = None, **kwargs):
        super().__init__(**kwargs)
        self.children = children if children else TList(_Question)


class QDotConnect(_QuestionMT):
    """Connect the dots questions. In the question the student need to
    connect multiple nodes with one or more connection. Similar to the
    <code>QMatching</code> question.
    """
    QNAME = "Dot Connect"
    ANS_TYPE = Subquestion

    def __init__(self, ordered=False, **kwargs):
        super().__init__(**kwargs)
        self.ordered = ordered


class QDaDText(_QuestionMTCS):
    """Drag and drop text boxes into question text.
    """
    MOODLE = "ddwtos"
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


class QDaDImage(_QuestionMTCS):
    """Drag and Drop items onto drop zones, where the items are custom images.
    """
    MOODLE = "ddimageortext"
    QNAME = "Drag and Drop Image"
    ANS_TYPE = DragImage

    def __init__(self, background: B64File = None,
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
    MOODLE = "ddmarker"
    QNAME = "Drag and Drop Marker"
    ANS_TYPE = DragItem

    def __init__(self, highlight=False, **kwargs):
        super().__init__(**kwargs)
        self.highlight = highlight


class QEssay(_Question):
    """Represents an essay question, in which the answer is written as an essay
    and need to be submitted for review (no automatic correct/answer feedback
    provided).
    """
    MOODLE = "essay"
    QNAME = "Essay"

    def __init__(self, lines=10, attachments=0, max_bytes=0, file_types="",
                 rsp_required=True, atts_required=False,
                 min_words: int = None, max_words: int = None,
                 grader_info: FText = None,
                 template: FText = None, rsp_format=RespFormat.HTML,
                 **kwargs):
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


class QMatching(_QuestionMTCS):
    """Represents a Matching question, in which the goal is to find matchs.
    """
    MOODLE = "matching"
    QNAME = "Matching"
    ANS_TYPE = Subquestion


class QRandomMatching(_QuestionMTCS):
    """A Random Match question. Unlike to other MTCS questions, it does not
    have options, reusing other questions randomly instead. It was implemented
    more targetting Moodle, since other platforms dont store this in databases.
    """
    MOODLE = "randomsamatch"
    QNAME = "Random Matching"

    def __init__(self, choose: int = 0, subcats: bool = False, **kwargs):
        super().__init__(**kwargs)
        delattr(self, "_options")
        delattr(self, "shuffle")
        self.choose = choose
        self.subcats = subcats


class QMissingWord(_QuestionMTCS):
    """A Missing Word question.
    """
    MOODLE = "gapselect"
    QNAME = "Missing Word"
    ANS_TYPE = SelectOption

    def check(self):
        total = len(re.findall(r"\[\[[0-9]+\]\]", self.question.text))
        if total != len(self.options):
            raise MarkerError("Incorrect number of marker in text.")

    @staticmethod
    def get_items(text):
        """Return a tuple with the Marked text and the data extracted.
        """
        gui_text = []
        start = 0
        for match in re.finditer(r"\[\[[0-9]+\]\]", text):
            gui_text.append(text[start: match.start()])
            start = match.end()
        gui_text.append(text[start:])
        return chr(MARKER_INT).join(gui_text), None

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


class QMultichoice(_QuestionMTCS):
    """A Multiple choice question.
    """
    MOODLE = "multichoice"
    QNAME = "Multichoice"
    ANS_TYPE = Answer

    def __init__(self, single=True, show_instr=False,
                 numbering: Numbering = None, **kwargs):
        super().__init__(**kwargs)
        self.single = single
        self.show_instr = show_instr
        self.numbering = Numbering.ALF_LR if numbering is None else numbering


class QNumerical(_QuestionMTUH):
    """
    This class represents 'Numerical Question' question type.
    """
    MOODLE = "numerical"
    QNAME = "Numerical"
    ANS_TYPE = ANumerical

    def __init__(self, units: List[Unit] = None,  **kwargs):
        super().__init__(**kwargs)
        self.units = [] if units is None else units


class QShortAnswer(_QuestionMT):
    """This class represents 'Short answer' question.
    """
    MOODLE = "shortanswer"
    QNAME = "Short Answer"
    ANS_TYPE = Answer

    def __init__(self, use_case=False, **kwargs):
        super().__init__(**kwargs)
        self.use_case = use_case


class QTrueFalse(_Question):
    """This class represents true/false question.
    """
    MOODLE = "truefalse"
    QNAME = "True or False"

    def __init__(self, correct: bool, true_feedback: FText | str,
                 false_feedback: FText | str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.correct = correct
        self._true_feedback = FText("feedback")
        self.true_feedback = true_feedback
        self._false_feedback = FText("feedback")
        self.false_feedback = false_feedback

    true_feedback = FText.prop("_true_feedback")
    false_feedback = FText.prop("_false_feedback")


class QFreeDrawing(_Question):
    """Represents a question where the use is free to make any drawing. The
    result is submited for review (there is no automatic correct/wrong
    feedback).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class QLineDrawing(_Question):
    """Represents a question where the user should draw line either to complete
    an image or to draw a new one. The result is submited for review (there is
    no automatic correct/wrong feedback).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


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
