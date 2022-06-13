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
from xml.etree import ElementTree as et
from typing import TYPE_CHECKING
from .enums import TextFormat, Grading, RespFormat, ShowUnits, Status,\
                   Distribution, Numbering, Synchronise
from .utils import Serializable, MarkerError, AnswerError, B64File, Dataset, \
                   FText, Hint, Tags, Unit
from .answer import Answer, ClozeItem, ANumerical, Subquestion,\
                    ACrossWord, DropZone, DragItem
if TYPE_CHECKING:
    from typing import List, Dict
    from .enums import Direction
    from .category import Category
LOG = logging.getLogger(__name__)


QNAME: Dict[str, _Question] = {}
QTYPE: Dict[str, _Question] = {}
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
        if cls.MOODLE is not None:
            QTYPE[cls.MOODLE] = cls

    def __init__(self, name="qstn", default_grade=1.0, question: FText = None,
                 dbid: int = None, feedback: FText = None, tags: Tags = None):
        """
        [summary]

        Args:
            name (str): name of the question
            question (FText): text of the question
            default_grade (float): the default mark
            general_feedback (str, optional): general feedback.
            dbid (int, optional): id number.
        """
        self.name = name
        self.question = FText("questiontext") if question is None else question
        self.default_grade = default_grade
        self.feedback = FText("generalfeedback") if feedback \
                is None else feedback
        self.dbid = dbid
        self.tags = Tags() if tags is None else tags
        self.__parent = None

    def __str__(self) -> str:
        return f"{self.QNAME}: '{self.name}' @{hex(id(self))}"

    @property
    def parent(self) -> Category:
        """_summary_

        Returns:
            Quiz: _description_
        """
        return self.__parent

    @parent.setter
    def parent(self, value):
        if (self.__parent is not None and self in self.__parent.questions) or \
                (value is not None and self not in value.questions):
            raise ValueError("This attribute can't be assigned directly. Use "
                             "parent's add/pop_question functions instead.")
        self.__parent = value


class _QuestionMT(_Question):

    def __init__(self, options: list = None, hints: List[Hint] = None,
                 penalty=0.5, **kwargs):
        super().__init__(**kwargs)
        self.penalty = penalty
        self.hints = [] if hints is None else hints
        self.options = [] if options is None else options


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
        self.if_correct = FText("correctfeedback") \
            if if_correct is None else if_correct
        self.if_incomplete = FText("partiallycorrectfeedback") \
            if if_incomplete is None else if_incomplete
        self.if_incorrect = FText("incorrectfeedback") \
            if if_incorrect is None else if_incorrect
        self.show_num = show_num
        self.shuffle = shuffle


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
    xml document but this seems to be just a bug. Th class don't use it.
    """
    MOODLE = "calculated"
    QNAME = "Calculated"

    def __init__(self, synchronize: Synchronise = None, units: List[Unit] = None,
                 datasets: List[Dataset] = None, **kwargs):
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
    XML format.
    """
    MOODLE = "calculatedsimple"
    QNAME = "Simplified Calculated"


class QCalculatedMultichoice(_QuestionMTCS):
    """Represents a "Calculated" question with multiple choices, behaving like
    a multichoice question where the answers are calculated using equations and
    datasets.
    """
    MOODLE = "calculatedmulti"
    QNAME = "Calculated Multichoice"

    def __init__(self, synchronize: Synchronise, numbering: Numbering = None,
                 single = False, datasets: List[Dataset] = None, **kwargs):
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

    def __init__(self, embedded_name=False, **kwargs):
        super().__init__(**kwargs)
        pattern = re.compile(r"(?!\\)\{(\d+)?(?:\:(.*?)\:)(.*?(?!\\)\})")
        gui_text = []
        start = 0
        if not self.options:   # if user profides options, assume text updated
            for match in pattern.finditer(self.question.text):
                item = ClozeItem.from_cloze(match)
                self.options.append(item)
                gui_text.append(self.question.text[start: match.start()])
                start = match.end()
            gui_text.append(self.question.text[start:])
            self.question.text = chr(MARKER_INT).join(gui_text)
        self.embedded_name = embedded_name

    def pure_text(self) -> str:
        char = chr(MARKER_INT)
        find = self.question.text.find(char)
        text = [self.name, "\n", self.question.text[:find]] if \
                self.embedded_name else [self.question.text[:find]]
        for question in self.options:
            text.append(question.to_text())
            end = self.question.text.find(char, find + 1)
            text.append(self.question.text[find + 1 : end])
            find = end
        text.append(self.question.text[-1])  # Wont be included by default
        return "".join(text)

    def check(self):
        """
        """
        markers = self.question.text.count(chr(MARKER_INT))
        if markers != len(self.options):
            raise MarkerError("Number of markers and questions differ")
        for question in self.options:
            if all(opt.fraction == 0 for opt in question.opts):
                raise AnswerError("All answer options have 0 grade")


class QDescription(_Question):
    """Represents a simple description. This is not a question. It has the same
    extructure as Question class and was add for compatiblity with the moodle
    XML format.
    """
    MOODLE = "description"
    QNAME = "Description"


class QDotConnect(_QuestionMT):
    """
    """
    QNAME = "Dot Connect"

    def __init__(self, ordered=False, **kwargs):
        super().__init__(**kwargs)
        self.ordered = ordered


class QDragAndDropText(_QuestionMTCS):
    """
    This class represents a drag and drop text onto image question.
    It inherits from abstract class Question.
    """
    MOODLE = "ddwtos"
    QNAME = "Drag and Drop Text"


class QDragAndDropImage(_QuestionMTCS):
    """This class represents a drag and drop onto image question.
    It inherits from abstract class Question.
    """
    MOODLE = "ddimageortext"
    QNAME = "Drag and Drop Image"

    def __init__(self, background: B64File = None,
                 zones: List[DropZone] = None, **kwargs):
        """Creates an drag and drop onto image type of question.

        Args:
            background (str): Filepath to the background image.
        """
        super().__init__(**kwargs)
        self.background = background
        self.zones = [] if zones is None else zones

    def add_image(self, text: str, group: int, file: str, unlimited=False):
        """Adds new DragItem with assigned DropZones.

        Args:
            file (str): path to image to be used as a drag image;
            text (str, optional): text of the drag text.
            group (int, optional): group.
            unlimited (bool, optional): if item is allowed to be used again.
                Defaults to False.
        """
        dragimage = DragItem(len(self.options) + 1, text, unlimited, group,
                             image=file)
        self.options.append(dragimage)

    def add_text(self, text: str, group: str, unlimited=False):
        """Adds new DragText with assigned DropZones.

        Args:
            text (str): text of the drag text.
            group (str): group.
            unlimited (bool, optional): if item is allowed to be used again.
                Defaults to False.
        """
        dragitem = DragItem(len(self.options) + 1, text, unlimited, group)
        self.options.append(dragitem)

    def add_zone(self, coord_x: int, coord_y: int, text: str, choice: int):
        """[summary]

        Args:
            x (int): [description]
            y (int): [description]
            text (str): [description]
            choice (int): [description]
        """
        self.zones.append(DropZone(coord_x, coord_y, text, choice,
                                   len(self.zones) + 1))


class QDragAndDropMarker(_QuestionMTCS):
    """Represents a Drag and Drop question where the items are markers.
    """
    MOODLE = "ddmarker"
    QNAME = "Drag and Drop Marker"

    def __init__(self, highlight=False, background: B64File = None,
                 zones: List[DropZone] = None,  **kwargs):
        """Creates an drag and drop onto image type of question.

        Args:
            background (str): Filepath to the background image.
        """
        super().__init__(**kwargs)
        self.background = background
        self.highlight = highlight
        self.zones = [] if zones is None else zones

    def add_option(self, text: str, no_of_drags: str, unlimited: bool = False):
        """[summary]

        Args:
            text (str): [description]
            no_of_drags (str): [description]
            unlimited (bool, optional): [description]. Defaults to False.
        """
        dragitem = DragItem(len(self.options) + 1, text, unlimited,
                            no_of_drags=no_of_drags)
        self.options.append(dragitem)


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

    def add_option(self, text: str, answer: str) -> None:
        """[summary]

        Args:
            text (str): [description]
            answer (str): [description]
        """
        self.options.append(Subquestion(TextFormat.AUTO, text, answer))


class QRandomMatching(_QuestionMTCS):
    """Represents a Random match question.
    """
    MOODLE = "randomsamatch"
    QNAME = "Random Matching"

    def __init__(self, choose: int = 0, subcats: bool = False, **kwargs):
        super().__init__(**kwargs)
        delattr(self, "options")
        delattr(self, "shuffle")
        self.choose = choose
        self.subcats = subcats


class QMissingWord(_QuestionMTCS):
    """ Represents a "Missing Word" question.
    """
    MOODLE = "gapselect"
    QNAME = "Missing Word"

    def update(self):
        for i in re.finditer(r"\[\[[0-9]+\]\]", self.toPlainText()):
            self.__tags.append(i.span())


class QMultichoice(_QuestionMTCS):
    """This class represents 'Multiple choice' question.
    """
    MOODLE = "multichoice"
    QNAME = "Multichoice"

    def __init__(self, single=True, show_instr=False,
                 numbering: Numbering = None, **kwargs):
        super().__init__(**kwargs)
        self.single = single
        self.show_instr = show_instr
        self.numbering = Numbering.ALF_LR if numbering is None else numbering


class QNumerical(_QuestionMTUH):
    """
    This class represents 'Numerical Question' moodle question type.
    Units are currently not implemented, only numerical answer, which
    are specified as text and absolute tolerance value are implemented
    """
    MOODLE = "numerical"
    QNAME = "Numerical"

    def __init__(self, units: List[Unit] = None,  **kwargs):
        super().__init__(**kwargs)
        self.units = [] if units is None else units

    def add_option(self, text: str, tol: float, fraction: float,
                   feedback: str = None) -> None:
        """_summary_

        Args:
            tol (float): _description_
            fraction (float): _description_
            text (str): _description_
            feedback (str, optional): _description_. Defaults to None.
        """
        self.options.append(ANumerical(tol, fraction=fraction, text=text,
                                            formatting=feedback))


class QShortAnswer(_QuestionMT):
    """
    This class represents 'Short answer' question.
    """
    MOODLE = "shortanswer"
    QNAME = "Short Answer"

    def __init__(self, use_case = False, **kwargs):
        super().__init__(**kwargs)
        self.use_case = use_case


class QTrueFalse(_Question):
    """
    This class represents true/false question.
    """
    MOODLE = "truefalse"
    QNAME = "True or False"

    def __init__(self, options: list, **kwargs) -> None:
        super().__init__(**kwargs)
        if options is not None:
            if len(options) != 2:
                raise ValueError()
            for answer in options:
                if answer.text.lower() == "true":
                    self.__true = answer
                    self.__correct = answer.fraction == 100
                elif answer.text.lower() == "false":
                    self.__false = answer
        else:
            self.__true = Answer(100, "true", FText("feedback"), TextFormat.AUTO)
            self.__false = Answer(0, "false", FText("feedback"), TextFormat.AUTO)
            self.__correct = True

    def set_feedbacks(self, correct: FText, incorrect: FText):
        """_summary_

        Args:
            correct (FText): _description_
            incorrect (FText): _description_
        """
        self.__true.feedback = correct if self.correct else incorrect
        self.__false.feedback = correct if not self.correct else incorrect

    @property
    def correct(self) -> bool:
        """_summary_

        Returns:
            bool: _description_
        """
        return self.__correct

    @correct.setter
    def correct(self, value: bool) -> None:
        """_summary_

        Args:
            value (bool): _description_
        """
        self.__true.fraction = 100 if value else 0
        self.__false.fraction = 100 if not value else 0
        self.__correct = value

    @property
    def false(self):
        return self.__false

    @property
    def true(self):
        return self.__true


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
        self.words.append(ACrossWord(word, coord_x, coord_y, direction, clue))

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

